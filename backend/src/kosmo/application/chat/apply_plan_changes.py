from __future__ import annotations

from dataclasses import dataclass, field

from kosmo.contracts import ChatRepository, EstadoPlanCambio, PlanCambio
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import DocumentNotFoundError, ProjectNotFoundError
from kosmo.contracts.sdd.ids import PlanChangeId, ProjectId
from kosmo.contracts.sdd.repositories import DocumentRepository, ProjectRepository
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
    ) -> None:
        self._project_repo = project_repo
        self._chat_repo = chat_repo
        self._document_repo = document_repo

    async def execute(self, input_data: ApplyPlanChangesInput) -> ApplyPlanChangesOutput:
        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/plan/apply",
            )

        if input_data.phase != SpecPhase.DESCUBRIMIENTO:
            raise ValueError(
                f"Aplicación de cambios no soportada para la fase '{input_data.phase.value}'"
            )

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

        document = await self._document_repo.get_discovery(input_data.project_id)
        if document is None:
            raise DocumentNotFoundError(
                document_type="discovery",
                instance=f"/api/v1/projects/{input_data.project_id}/plan/apply",
            )

        markdown = document_to_markdown(document)
        applied: list[PlanCambio] = []

        for change in matched:
            result = apply_change_diff(markdown, before=change.diff.before, after=change.diff.after)
            if result is None:
                failed.append(
                    FailedChange(
                        id=change.id,
                        reason="El fragmento original ya no se encuentra en el documento",
                    )
                )
            else:
                markdown = result
                applied.append(change)

        if applied:
            new_document = markdown_to_document(markdown)
            await self._document_repo.save_discovery(input_data.project_id, new_document)

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
