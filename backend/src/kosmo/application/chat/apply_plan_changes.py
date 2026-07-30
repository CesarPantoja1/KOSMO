from __future__ import annotations

from dataclasses import dataclass, field
from unicodedata import normalize

from kosmo.contracts import ChatRepository, EstadoPlanCambio, PlanCambio
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import DocumentNotFoundError, ProjectNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository, FeatureRepository, ProjectRepository
from kosmo.domain.sdd.document_converters import document_to_markdown, markdown_to_document
from kosmo.domain.sdd.plan_diffs import apply_change_diff


@dataclass(frozen=True)
class ApplyPlanChangesInput:
    project_id: ProjectId
    phase: SpecPhase
    change_ids: list[PlanChangeId]


@dataclass(frozen=True)
class FailedChange:
    id: PlanChangeId
    reason: str


@dataclass(frozen=True)
class ApplyPlanChangesOutput:
    applied_count: int
    failed_count: int
    failed_changes: list[FailedChange] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]

    @property
    def applied_ids(self) -> list[str]:
        return [str(fc.id) for fc in self.failed_changes]


class ApplyPlanChangesUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        chat_repo: ChatRepository,
        document_repo: DocumentRepository,
        feature_repo: FeatureRepository | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._chat_repo = chat_repo
        self._document_repo = document_repo
        self._feature_repo = feature_repo

    async def execute(self, input_data: ApplyPlanChangesInput) -> ApplyPlanChangesOutput:
        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/plan/apply",
            )

        if input_data.phase not in {SpecPhase.DESCUBRIMIENTO, SpecPhase.CARACTERISTICAS}:
            raise ValueError(f"Aplicación de cambios no soportada para la fase '{input_data.phase.value}'")

        all_changes = await self._chat_repo.list_plan_changes(input_data.project_id, input_data.phase)
        by_id = {c.id: c for c in all_changes}

        matched: list[PlanCambio] = []
        failed: list[FailedChange] = []

        for cid in input_data.change_ids:
            change = by_id.get(cid)
            if change is None:
                failed.append(FailedChange(id=cid, reason=f"El cambio {cid} no pertenece al plan de esta fase"))
            else:
                matched.append(change)

        if input_data.phase == SpecPhase.DESCUBRIMIENTO:
            applied, phase_failed = await self._apply_discovery_changes(input_data.project_id, matched)
        else:
            applied, phase_failed = await self._apply_feature_changes(input_data.project_id, matched)
        failed.extend(phase_failed)

        for change in applied:
            await self._chat_repo.update_plan_change_status(
                project_id=input_data.project_id,
                change_id=change.id,
                status=EstadoPlanCambio.APPLIED,
            )

        return ApplyPlanChangesOutput(
            applied_count=len(applied),
            failed_count=len(failed),
            failed_changes=failed,
        )

    async def _apply_discovery_changes(
        self, project_id: ProjectId, changes: list[PlanCambio]
    ) -> tuple[list[PlanCambio], list[FailedChange]]:
        document = await self._document_repo.get_discovery(project_id)
        if document is None:
            raise DocumentNotFoundError(
                document_type="discovery",
                instance=f"/api/v1/projects/{project_id}/plan/apply",
            )

        markdown = document_to_markdown(document)
        applied: list[PlanCambio] = []
        failed: list[FailedChange] = []
        for change in changes:
            result = apply_change_diff(markdown, before=change.diff.before, after=change.diff.after)
            if result is None:
                failed.append(
                    FailedChange(id=change.id, reason="El fragmento original ya no se encuentra en el documento")
                )
            else:
                markdown = result
                applied.append(change)

        if applied:
            await self._document_repo.save_discovery(project_id, markdown_to_document(markdown))
        return applied, failed

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
                failed.append(FailedChange(id=change.id, reason=f"El atributo '{change.section}' no es modificable"))
                continue
            feature = await self._feature_repo.by_id(FeatureId(change.context_id)) if change.context_id else None
            if feature is None and not change.context_id:
                candidates = [
                    item for item in await self._feature_repo.list_by_project(project_id)
                    if change.diff.before in getattr(item, attribute)
                ]
                feature = candidates[0] if len(candidates) == 1 else None
            if feature is None or feature.project_id != project_id:
                reason = (
                    "El cambio no identifica de forma única la característica que debe modificarse"
                    if not change.context_id
                    else "La característica asociada al cambio ya no existe"
                )
                failed.append(FailedChange(id=change.id, reason=reason))
                continue
            current = getattr(feature, attribute)
            replacement = apply_change_diff(current, before=change.diff.before, after=change.diff.after)
            if replacement is None:
                failed.append(
                    FailedChange(
                        id=change.id,
                        reason="El fragmento original ya no se encuentra en la característica",
                    )
                )
                continue
            setattr(feature, attribute, replacement)
            if attribute == "title":
                feature.slug = replacement.lower().replace(" ", "-")
            await self._feature_repo.save(feature)
            applied.append(change)
        return applied, failed


def _feature_attribute(section: str) -> str | None:
    normalized = "".join(char for char in normalize("NFKD", section).lower() if char.isalnum())
    if normalized in {"titulo", "titulodelacaracteristica"}:
        return "title"
    if normalized in {"descripcion", "descripciondelacaracteristica"}:
        return "description"
    if normalized in {"origen", "origendelacaracteristica"}:
        return "origin"
    return None
