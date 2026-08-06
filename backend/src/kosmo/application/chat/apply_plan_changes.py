from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from unicodedata import normalize

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts import ChatRepository, EstadoPlanCambio, PlanCambio
from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.pipeline.phase_contexts import PlanChangeResolutionContext
from kosmo.contracts.pipeline.phase_outputs import ResolvedSection
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import DocumentNotFoundError, ProjectNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import (
    DocumentRepository,
    FeatureRepository,
    ProjectRepository,
    RequirementRepository,
)
from kosmo.domain.sdd.document_converters import document_to_markdown, markdown_to_document
from kosmo.domain.sdd.plan_diffs import apply_change_diff, collapse_whitespace, find_section

_log = structlog.get_logger(__name__)


def _section_spans(markdown: str) -> list[tuple[str, int, int]]:
    matches = list(re.finditer(r"^(#{1,6})\s+(.+)$", markdown, re.MULTILINE))
    spans: list[tuple[str, int, int]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        spans.append((m.group(2), m.start(), end))
    return spans


def _section_heading_preserved(original: str, rewritten: str) -> bool:
    def _first_heading(text: str) -> str:
        m = re.search(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)
        return re.sub(r"\s+", "", (m.group(1) if m else "")).lower()

    original_heading = _first_heading(original)
    if not original_heading:
        return True
    return original_heading in re.sub(r"\s+", "", rewritten).lower()


async def llm_resolve_markdown(
    agent: AgentPort,
    project_id: ProjectId,
    section_name: str,
    markdown: str,
    changes: list[PlanCambio],
) -> str | None:
    context = PlanChangeResolutionContext(
        section_name=section_name,
        section_markdown=markdown,
        changes=changes,
    )
    try:
        result = await agent.execute_with_skill(
            skill_name="plan_change_resolve",
            context=context,
            project_id=project_id,
        )
    except Exception:
        _log.warning("plan.llm_resolve_failed", section=section_name, exc_info=True)
        return None
    if not isinstance(result, ResolvedSection):
        _log.warning(
            "plan.llm_resolve_bad_output",
            section=section_name,
            output_type=repr(result)[:200],
        )
        return None
    new_text = result.section_markdown.strip()
    if not new_text or new_text == markdown.strip():
        _log.warning("plan.llm_resolve_invalid_section", section=section_name)
        return None
    return new_text


@dataclass(frozen=True)
class ApplyPlanChangesInput:
    project_id: ProjectId
    phase: SpecPhase
    change_ids: list[PlanChangeId]


@dataclass(frozen=True)
class FailedChange:
    id: PlanChangeId
    reason: str
    section: str = ""


@dataclass(frozen=True)
class ApplyPlanChangesOutput:
    applied_count: int
    failed_count: int
    applied_changes: list[PlanCambio] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    failed_changes: list[FailedChange] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]

    @property
    def applied_ids(self) -> list[str]:
        return [str(c.id) for c in self.applied_changes]


class ApplyPlanChangesUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        chat_repo: ChatRepository,
        document_repo: DocumentRepository,
        feature_repo: FeatureRepository | None = None,
        requirement_repo: RequirementRepository | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        agent: AgentPort | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._chat_repo = chat_repo
        self._document_repo = document_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._session_factory = session_factory
        self._agent = agent

    async def execute(self, input_data: ApplyPlanChangesInput) -> ApplyPlanChangesOutput:
        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/plan/apply",
            )

        if input_data.phase not in {SpecPhase.DESCUBRIMIENTO, SpecPhase.CARACTERISTICAS, SpecPhase.REQUISITOS}:
            raise ValueError(f"Aplicación de cambios no soportada para la fase '{input_data.phase.value}'")

        all_changes = await self._chat_repo.list_plan_changes(input_data.project_id, input_data.phase)
        by_id = {c.id: c for c in all_changes}

        matched: list[PlanCambio] = []
        failed: list[FailedChange] = []
        final_markdown = ""

        for cid in input_data.change_ids:
            change = by_id.get(cid)
            if change is None:
                failed.append(
                    FailedChange(
                        id=cid,
                        reason=f"El cambio {cid} no pertenece al plan de esta fase",
                        section="",
                    )
                )
            else:
                matched.append(change)

        if input_data.phase == SpecPhase.DESCUBRIMIENTO:
            applied, phase_failed, final_markdown, markdown_before = await self._apply_discovery_changes(
                input_data.project_id, matched
            )
            if phase_failed and self._agent is not None:
                by_plan_id = {c.id: c for c in matched}
                failed_plan = [by_plan_id[fc.id] for fc in phase_failed if fc.id in by_plan_id]
                if failed_plan:
                    final_markdown, llm_applied, llm_still = await self._resolve_failed_with_llm(
                        input_data.project_id, failed_plan, final_markdown
                    )
                    applied.extend(llm_applied)
                    phase_failed = [
                        FailedChange(
                            id=c.id,
                            reason="El cambio no se pudo resolver de forma segura.",
                            section=c.section or "",
                        )
                        for c in llm_still
                    ]
            if applied and self._session_factory is not None:
                await self._persist_with_uow(input_data.project_id, applied, final_markdown, markdown_before)
        elif input_data.phase == SpecPhase.REQUISITOS:
            applied, phase_failed = await self._apply_requirement_changes(matched)
            if phase_failed and self._agent is not None:
                by_plan_id = {c.id: c for c in matched}
                failed_plan = [by_plan_id[fc.id] for fc in phase_failed if fc.id in by_plan_id]
                if failed_plan:
                    llm_applied, llm_still = await self._resolve_requirement_failures_with_llm(
                        input_data.project_id, failed_plan
                    )
                    applied.extend(llm_applied)
                    phase_failed = [
                        FailedChange(
                            id=c.id,
                            reason="El cambio no se pudo resolver de forma segura.",
                            section=c.section or "",
                        )
                        for c in llm_still
                    ]
            if applied and self._session_factory is not None:
                await self._mark_changes_applied_uow(input_data.project_id, applied)
        else:
            applied, phase_failed = await self._apply_feature_changes(input_data.project_id, matched)
            if applied and self._session_factory is not None:
                await self._mark_changes_applied_uow(input_data.project_id, applied)
        failed.extend(phase_failed)

        for fc in phase_failed:
            _log.warning(
                "plan.apply_change_failed",
                change_id=str(fc.id),
                reason=fc.reason,
                section=fc.section,
            )

        if self._session_factory is None or not applied:
            if input_data.phase == SpecPhase.DESCUBRIMIENTO and applied:
                doc = markdown_to_document(final_markdown)  # type: ignore[reportPossiblyUnboundVariable]
                await self._document_repo.save_discovery(project_id=input_data.project_id, document=doc)
            for change in applied:
                await self._chat_repo.update_plan_change_status(
                    project_id=input_data.project_id,
                    change_id=change.id,
                    status=EstadoPlanCambio.APPLIED,
                )
            if input_data.phase == SpecPhase.DESCUBRIMIENTO and applied:
                await self._document_repo.save_version(  # type: ignore[call-arg]
                    project_id=input_data.project_id,
                    phase=input_data.phase,
                    markdown=markdown_before,  # type: ignore[reportPossiblyUnboundVariable]
                    change_ids=[c.id for c in applied],
                )

        return ApplyPlanChangesOutput(
            applied_count=len(applied),
            failed_count=len(failed),
            applied_changes=applied,
            failed_changes=failed,
        )

    async def _persist_with_uow(
        self, project_id: ProjectId, applied: list[PlanCambio], markdown: str, markdown_before: str
    ) -> None:
        async with self._session_factory() as session:  # type: ignore[reportOptionalMemberAccess]
            await self._document_repo.save_discovery(
                project_id=project_id,
                document=markdown_to_document(markdown),
                _session=session,  # type: ignore[call-arg]
            )
            for change in applied:
                await self._chat_repo.update_plan_change_status(
                    project_id=project_id,
                    change_id=change.id,
                    status=EstadoPlanCambio.APPLIED,
                    _session=session,  # type: ignore[call-arg]
                )
            await self._document_repo.save_version(  # type: ignore[call-arg]
                project_id=project_id,
                phase=SpecPhase.DESCUBRIMIENTO,
                markdown=markdown_before,
                change_ids=[c.id for c in applied],
                _session=session,  # type: ignore[call-arg]
            )
            await session.commit()

    async def _mark_changes_applied_uow(self, project_id: ProjectId, applied: list[PlanCambio]) -> None:
        async with self._session_factory() as session:  # type: ignore[reportOptionalMemberAccess]
            for change in applied:
                await self._chat_repo.update_plan_change_status(
                    project_id=project_id,
                    change_id=change.id,
                    status=EstadoPlanCambio.APPLIED,
                    _session=session,  # type: ignore[call-arg]
                )
            await session.commit()

    def _locate_section(self, markdown: str, change: PlanCambio) -> tuple[str, int, int] | None:
        if change.section:
            sec_text, start, end = find_section(markdown, change.section)
            if sec_text is not None:
                return change.section, start, end
        if change.diff.before:
            for heading, start, end in _section_spans(markdown):
                if change.diff.before in markdown[start:end]:
                    return heading, start, end
        return None

    async def _resolve_failed_with_llm(
        self,
        project_id: ProjectId,
        failed: list[PlanCambio],
        markdown: str,
    ) -> tuple[str, list[PlanCambio], list[PlanCambio]]:
        agent = self._agent
        if agent is None or not failed:
            return markdown, [], failed

        sections: dict[int, str] = {}
        ends: dict[int, int] = {}
        changes_by_section: dict[int, list[PlanCambio]] = {}
        unlocated: list[PlanCambio] = []

        for change in failed:
            span = self._locate_section(markdown, change)
            if span is None:
                unlocated.append(change)
                continue
            heading, start, end = span
            sections.setdefault(start, heading)
            ends[start] = end
            changes_by_section.setdefault(start, []).append(change)

        # Fusionar grupos anidados: los cambios de la subseccion se resuelven con su seccion padre
        starts = sorted(changes_by_section)
        for outer in starts:
            for inner in list(starts):
                if inner == outer:
                    continue
                if outer < inner < ends[outer]:
                    changes_by_section[outer].extend(changes_by_section.pop(inner))
                    sections.pop(inner)
                    ends.pop(inner)

        async def _resolve_one(
            heading: str, start: int, end: int, changes: list[PlanCambio]
        ) -> tuple[int, int, str] | None:
            new_text = await llm_resolve_markdown(agent, project_id, heading, markdown[start:end], changes)
            if new_text is None or not _section_heading_preserved(markdown[start:end], new_text):
                _log.warning("plan.llm_resolve_invalid_section", section=heading)
                return None
            return start, end, new_text

        tasks = [_resolve_one(sections[s], s, ends[s], changes_by_section[s]) for s in sorted(changes_by_section)]
        results: list[tuple[int, int, str] | None] = await asyncio.gather(*tasks)

        resolved_starts: set[int] = set()
        new_markdown = markdown
        for result in sorted([r for r in results if r is not None], key=lambda r: r[0], reverse=True):
            start, end, new_text = result
            new_markdown = new_markdown[:start] + new_text + new_markdown[end:]
            resolved_starts.add(start)

        newly_applied = [c for s, changes in changes_by_section.items() if s in resolved_starts for c in changes]
        still_failed = [
            c for s, changes in changes_by_section.items() if s not in resolved_starts for c in changes
        ] + unlocated
        return new_markdown, newly_applied, still_failed

    async def _resolve_requirement_failures_with_llm(
        self,
        project_id: ProjectId,
        failed: list[PlanCambio],
    ) -> tuple[list[PlanCambio], list[PlanCambio]]:
        agent = self._agent
        requirement_repo = self._requirement_repo
        if agent is None or not failed or requirement_repo is None:
            return [], failed

        grouped: dict[str, list[PlanCambio]] = {}
        for c in failed:
            fid = _feature_id_from_change(c)
            if fid:
                grouped.setdefault(fid, []).append(c)

        newly_applied: list[PlanCambio] = []
        still_failed: list[PlanCambio] = []

        async def _resolve_one(fid: str, changes: list[PlanCambio]) -> tuple[str, list[PlanCambio]]:
            fid_typed = FeatureId(fid)
            markdown = await requirement_repo.by_feature_id(fid_typed)
            if markdown is None:
                return fid, changes
            new_text = await llm_resolve_markdown(
                agent,
                project_id,
                f"Requisitos de {fid}",
                markdown,
                changes,
            )
            if new_text is None:
                return fid, changes
            await requirement_repo.save(fid_typed, new_text)
            return fid, []

        results = await asyncio.gather(*[_resolve_one(fid, changes) for fid, changes in grouped.items()])
        for fid, changes in grouped.items():
            _resolved_fid, still = next((r for r in results if r[0] == fid), (fid, changes))
            newly_applied.extend(c for c in changes if c not in still)
            still_failed.extend(still)

        still_failed.extend(c for c in failed if _feature_id_from_change(c) is None)
        return newly_applied, still_failed

    async def _apply_discovery_changes(
        self, project_id: ProjectId, changes: list[PlanCambio]
    ) -> tuple[list[PlanCambio], list[FailedChange], str, str]:
        document = await self._document_repo.get_discovery(project_id)
        if document is None:
            raise DocumentNotFoundError(
                document_type="discovery",
                instance=f"/api/v1/projects/{project_id}/plan/apply",
            )

        markdown_before = document_to_markdown(document)
        markdown = markdown_before
        applied: list[PlanCambio] = []
        failed: list[FailedChange] = []

        def _position(change: PlanCambio) -> int:
            if change.section and change.diff.before:
                sec_text, sec_start, _sec_end = find_section(markdown, change.section)
                if sec_text:
                    idx = sec_text.find(change.diff.before)
                    if idx >= 0:
                        return sec_start + idx
            if change.diff.before:
                idx = markdown.find(change.diff.before)
                if idx >= 0:
                    return idx
            return -1

        ordered = sorted(changes, key=_position, reverse=True)

        for change in ordered:
            result = apply_change_diff(
                markdown, before=change.diff.before, after=change.diff.after, section=change.section
            )
            if result is None:
                already_applied = False
                if change.section and change.diff.after.strip():
                    sec_text, _s, _e = find_section(markdown, change.section)
                    search_in = sec_text if sec_text is not None else markdown
                    norm_after = collapse_whitespace(change.diff.after)
                    if norm_after and norm_after in collapse_whitespace(search_in):
                        _log.info(
                            "plan.change_already_applied",
                            change_id=str(change.id),
                            section=change.section,
                        )
                        applied.append(change)
                        already_applied = True
                if not already_applied:
                    _log.warning(
                        "plan.before_text_not_found",
                        change_id=str(change.id),
                        section=change.section,
                        before=change.diff.before[:200],
                    )
                    failed.append(
                        FailedChange(
                            id=change.id,
                            reason=(
                                f"El texto original no se encuentra en la sección '{change.section or 'documento'}'."
                            ),
                            section=change.section,
                        )
                    )
                else:
                    continue
            elif result == markdown:
                applied.append(change)
            else:
                markdown = result
                applied.append(change)

        if not applied and failed:
            try:
                previous_md = await self._document_repo.get_latest_version(project_id, SpecPhase.DESCUBRIMIENTO)
                if previous_md is not None and previous_md != markdown_before:
                    from kosmo.domain.sdd.discovery_diff import diff_discovery_versions

                    section_changes = diff_discovery_versions(previous_md, markdown_before)
                    if section_changes:
                        _log.info(
                            "plan.version_diff_found",
                            change_count=len(changes),
                            section_count=len(section_changes),
                        )
                        for change in changes:
                            applied.append(change)
                        return applied, [], markdown_before, previous_md
            except Exception:
                _log.warning("plan.version_diff_fallback_failed", exc_info=True)

        return applied, failed, markdown, markdown_before

    async def _apply_feature_changes(
        self, project_id: ProjectId, changes: list[PlanCambio]
    ) -> tuple[list[PlanCambio], list[FailedChange]]:
        if self._feature_repo is None:
            raise ValueError("La aplicación de cambios de características no está configurada.")

        applied: list[PlanCambio] = []
        failed: list[FailedChange] = []
        for change in changes:
            attribute = _feature_attribute(change.section)
            if attribute is None:
                failed.append(
                    FailedChange(
                        id=change.id,
                        reason=f"El atributo '{change.section}' no es modificable",
                        section=change.section,
                    )
                )
                continue
            feature = await self._feature_repo.by_id(FeatureId(change.context_id)) if change.context_id else None
            if feature is None and not change.context_id:
                candidates = [
                    item
                    for item in await self._feature_repo.list_by_project(project_id)
                    if change.diff.before in getattr(item, attribute)
                ]
                feature = candidates[0] if len(candidates) == 1 else None
            if feature is None or feature.project_id != project_id:
                reason = (
                    "El cambio no identifica de forma única la característica que debe modificarse"
                    if not change.context_id
                    else "La característica asociada al cambio ya no existe"
                )
                failed.append(FailedChange(id=change.id, reason=reason, section=change.section))
                continue
            current = getattr(feature, attribute)
            replacement = apply_change_diff(current, before=change.diff.before, after=change.diff.after)
            if replacement is None:
                failed.append(
                    FailedChange(
                        id=change.id,
                        reason="El fragmento original ya no se encuentra en la característica",
                        section=change.section,
                    )
                )
                continue
            setattr(feature, attribute, replacement)
            if attribute == "title":
                feature.slug = replacement.lower().replace(" ", "-")
            await self._feature_repo.save(feature)
            applied.append(change)
        return applied, failed

    async def _apply_requirement_changes(
        self,
        changes: list[PlanCambio],
    ) -> tuple[list[PlanCambio], list[FailedChange]]:
        if self._requirement_repo is None:
            raise ValueError("La aplicación de cambios de requisitos no está configurada.")

        grouped: dict[str, list[PlanCambio]] = {}
        for c in changes:
            fid = _feature_id_from_change(c)
            if fid:
                grouped.setdefault(fid, []).append(c)

        if not grouped:
            reason = "No se pudo determinar la característica para los cambios de requisitos"
            return [], [FailedChange(id=c.id, reason=reason) for c in changes]

        applied: list[PlanCambio] = []
        failed: list[FailedChange] = []
        for fid, f_changes in grouped.items():
            fid_typed = FeatureId(fid)
            markdown = await self._requirement_repo.by_feature_id(fid_typed)
            if markdown is None:
                for c in f_changes:
                    failed.append(
                        FailedChange(
                            id=c.id,
                            reason=f"No hay requisitos para la característica {fid}",
                            section=c.section,
                        )
                    )
                continue

            for change in f_changes:
                result = apply_change_diff(markdown, before=change.diff.before, after=change.diff.after)
                if result is None:
                    failed.append(
                        FailedChange(
                            id=change.id,
                            reason="El fragmento original ya no se encuentra en los requisitos",
                            section=change.section,
                        )
                    )
                elif result == markdown:
                    applied.append(change)
                else:
                    markdown = result
                    applied.append(change)

            if any(a.id == c.id for c in f_changes for a in applied):
                await self._requirement_repo.save(fid_typed, markdown)

        return applied, failed


def _feature_id_from_change(change: PlanCambio) -> str | None:
    if change.context_id and change.context_id.startswith("feat_"):
        return change.context_id
    return None


async def revert_to_version(
    document_repo: DocumentRepository,
    project_id: ProjectId,
    version_id: str,
) -> str | None:
    markdown: object | None = await document_repo.get_version(version_id)
    if markdown is None:
        return None
    if not isinstance(markdown, str):  # type: ignore[reportUnnecessaryIsInstance]
        return None
    await document_repo.save_discovery(project_id=project_id, document=markdown_to_document(markdown))
    return markdown


def _feature_attribute(section: str) -> str | None:
    normalized = "".join(char for char in normalize("NFKD", section).lower() if char.isalnum())
    if normalized in {"titulo", "titulodelacaracteristica"}:
        return "title"
    if normalized in {"descripcion", "descripciondelacaracteristica"}:
        return "description"
    if normalized in {"origen", "origendelacaracteristica"}:
        return "origin"
    return None
