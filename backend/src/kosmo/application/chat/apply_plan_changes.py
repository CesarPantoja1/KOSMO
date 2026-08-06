from __future__ import annotations

from dataclasses import dataclass, field
from unicodedata import normalize

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from kosmo.contracts import ChatRepository, EstadoPlanCambio, PlanCambio
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
from kosmo.domain.sdd.plan_diffs import apply_change_diff

_log = structlog.get_logger(__name__)


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
    ) -> None:
        self._project_repo = project_repo
        self._chat_repo = chat_repo
        self._document_repo = document_repo
        self._feature_repo = feature_repo
        self._requirement_repo = requirement_repo
        self._session_factory = session_factory

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
            if applied and self._session_factory is not None:
                await self._persist_with_uow(input_data.project_id, applied, final_markdown, markdown_before)
        elif input_data.phase == SpecPhase.REQUISITOS:
            applied, phase_failed = await self._apply_requirement_changes(matched)
            if applied and self._session_factory is not None:
                await self._mark_changes_applied_uow(input_data.project_id, applied)
        else:
            applied, phase_failed = await self._apply_feature_changes(input_data.project_id, matched)
            if applied and self._session_factory is not None:
                await self._mark_changes_applied_uow(input_data.project_id, applied)
        failed.extend(phase_failed)

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
        for change in changes:
            result = apply_change_diff(
                markdown, before=change.diff.before, after=change.diff.after, section=change.section
            )
            if result is None:
                failed.append(
                    FailedChange(
                        id=change.id,
                        reason="El fragmento original ya no se encuentra en el documento",
                        section=change.section,
                    )
                )
            elif result == markdown:
                applied.append(change)
            else:
                markdown = result
                applied.append(change)

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
