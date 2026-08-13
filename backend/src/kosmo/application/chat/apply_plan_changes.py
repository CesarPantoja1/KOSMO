from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import structlog

from kosmo.contracts import EstadoPlanCambio, PlanCambio
from kosmo.contracts.persistence import UnitOfWork
from kosmo.contracts.pipeline.orchestrator_ports import AgentPort
from kosmo.contracts.pipeline.phase_contexts import PlanChangeResolutionContext
from kosmo.contracts.pipeline.phase_outputs import ResolvedSection
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import DocumentNotFoundError, ProjectNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository
from kosmo.domain.sdd.document_converters import document_to_markdown, markdown_to_document
from kosmo.domain.sdd.feature_attribute import feature_attribute
from kosmo.domain.sdd.plan_diffs import apply_change_diff, collapse_whitespace, find_section
from kosmo.domain.sdd.section_parser import section_heading_preserved, section_spans

_log = structlog.get_logger(__name__)


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
    def __init__(self, uow: UnitOfWork, agent: AgentPort | None = None) -> None:
        self._uow = uow
        self._agent = agent

    async def execute(self, input_data: ApplyPlanChangesInput) -> ApplyPlanChangesOutput:
        # ponytail: una transaccion para todo el caso de uso; las llamadas LLM
        # de resolucion ocurren con la conexion ociosa. Separar lectura/computo/
        # escritura en fases cortas corresponde a FIX-02.
        async with self._uow as uow:
            project = await uow.projects.by_id(input_data.project_id)
            if project is None:
                raise ProjectNotFoundError(
                    project_id=str(input_data.project_id),
                    instance=f"/api/v1/projects/{input_data.project_id}/plan/apply",
                )

            if input_data.phase not in {SpecPhase.DESCUBRIMIENTO, SpecPhase.CARACTERISTICAS, SpecPhase.REQUISITOS}:
                raise ValueError(f"Aplicación de cambios no soportada para la fase '{input_data.phase.value}'")

            all_changes = await uow.chat.list_plan_changes(input_data.project_id, input_data.phase)
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
                    uow, input_data.project_id, matched
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
                if applied:
                    await uow.documents.save_discovery(
                        project_id=input_data.project_id,
                        document=markdown_to_document(final_markdown),
                    )
                    for change in applied:
                        await uow.chat.update_plan_change_status(
                            project_id=input_data.project_id,
                            change_id=change.id,
                            status=EstadoPlanCambio.APPLIED,
                        )
                    await uow.documents.save_version(
                        project_id=input_data.project_id,
                        phase=input_data.phase,
                        markdown=markdown_before,
                        change_ids=[c.id for c in applied],
                    )
            elif input_data.phase == SpecPhase.REQUISITOS:
                applied, phase_failed = await self._apply_requirement_changes(uow, matched)
                if phase_failed and self._agent is not None:
                    by_plan_id = {c.id: c for c in matched}
                    failed_plan = [by_plan_id[fc.id] for fc in phase_failed if fc.id in by_plan_id]
                    if failed_plan:
                        llm_applied, llm_still = await self._resolve_requirement_failures_with_llm(
                            uow, input_data.project_id, failed_plan
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
                if applied:
                    for change in applied:
                        await uow.chat.update_plan_change_status(
                            project_id=input_data.project_id,
                            change_id=change.id,
                            status=EstadoPlanCambio.APPLIED,
                        )
            else:
                applied, phase_failed = await self._apply_feature_changes(uow, input_data.project_id, matched)
                if applied:
                    for change in applied:
                        await uow.chat.update_plan_change_status(
                            project_id=input_data.project_id,
                            change_id=change.id,
                            status=EstadoPlanCambio.APPLIED,
                        )
            failed.extend(phase_failed)

            for fc in phase_failed:
                _log.warning(
                    "plan.apply_change_failed",
                    change_id=str(fc.id),
                    reason=fc.reason,
                    section=fc.section,
                )

            return ApplyPlanChangesOutput(
                applied_count=len(applied),
                failed_count=len(failed),
                applied_changes=applied,
                failed_changes=failed,
            )

    def _locate_section(self, markdown: str, change: PlanCambio) -> tuple[str, int, int] | None:
        if change.section:
            sec_text, start, end = find_section(markdown, change.section)
            if sec_text is not None:
                return change.section, start, end
        if change.diff.before:
            for heading, start, end in section_spans(markdown):
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
            if new_text is None or not section_heading_preserved(markdown[start:end], new_text):
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
        uow: UnitOfWork,
        project_id: ProjectId,
        failed: list[PlanCambio],
    ) -> tuple[list[PlanCambio], list[PlanCambio]]:
        agent = self._agent
        if agent is None or not failed:
            return [], failed

        grouped: dict[str, list[PlanCambio]] = {}
        for c in failed:
            fid = _feature_id_from_change(c)
            if fid:
                grouped.setdefault(fid, []).append(c)

        # La sesion compartida no es concurrente: lecturas secuenciales antes del gather
        markdowns: dict[str, str | None] = {}
        for fid in grouped:
            markdowns[fid] = await uow.requirements.by_feature_id(FeatureId(fid))

        async def _resolve_one(fid: str, changes: list[PlanCambio]) -> tuple[str, str | None]:
            markdown = markdowns[fid]
            if markdown is None:
                return fid, None
            new_text = await llm_resolve_markdown(
                agent,
                project_id,
                f"Requisitos de {fid}",
                markdown,
                changes,
            )
            return fid, new_text

        results = await asyncio.gather(*[_resolve_one(fid, changes) for fid, changes in grouped.items()])
        resolved_by_fid = dict(results)

        newly_applied: list[PlanCambio] = []
        still_failed: list[PlanCambio] = []
        for fid, changes in grouped.items():
            new_text = resolved_by_fid[fid]
            if new_text is None:
                still_failed.extend(changes)
                continue
            await uow.requirements.save(FeatureId(fid), new_text)
            newly_applied.extend(changes)

        still_failed.extend(c for c in failed if _feature_id_from_change(c) is None)
        return newly_applied, still_failed

    async def _apply_discovery_changes(
        self, uow: UnitOfWork, project_id: ProjectId, changes: list[PlanCambio]
    ) -> tuple[list[PlanCambio], list[FailedChange], str, str]:
        document = await uow.documents.get_discovery(project_id)
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
                previous_md = await uow.documents.get_latest_version(project_id, SpecPhase.DESCUBRIMIENTO)
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
        self, uow: UnitOfWork, project_id: ProjectId, changes: list[PlanCambio]
    ) -> tuple[list[PlanCambio], list[FailedChange]]:
        applied: list[PlanCambio] = []
        failed: list[FailedChange] = []
        for change in changes:
            attribute = feature_attribute(change.section)
            if attribute is None:
                failed.append(
                    FailedChange(
                        id=change.id,
                        reason=f"El atributo '{change.section}' no es modificable",
                        section=change.section,
                    )
                )
                continue
            feature = await uow.features.by_id(FeatureId(change.context_id)) if change.context_id else None
            if feature is None and not change.context_id:
                candidates = [
                    item
                    for item in await uow.features.list_by_project(project_id)
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
            await uow.features.save(feature)
            applied.append(change)
        return applied, failed

    async def _apply_requirement_changes(
        self, uow: UnitOfWork, changes: list[PlanCambio]
    ) -> tuple[list[PlanCambio], list[FailedChange]]:
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
            markdown = await uow.requirements.by_feature_id(fid_typed)
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
                await uow.requirements.save(fid_typed, markdown)

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
