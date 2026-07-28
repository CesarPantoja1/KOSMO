from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts import (
    ChatRepository,
    ChatRole,
    EstadoPlanCambio,
    PlanCambio,
    PlanChangeId,
    SugerenciaCambio,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import (
    PlanChangeNotFoundError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository


@dataclass(frozen=True)
class PlanStateOutput:
    project_id: ProjectId
    phase: SpecPhase
    context: str
    changes: list[PlanCambio]
    pending_count: int
    conflict_count: int


class ManagePlanChangesUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        chat_repo: ChatRepository,
    ) -> None:
        self._project_repo = project_repo
        self._chat_repo = chat_repo

    async def _verify_project(self, project_id: ProjectId) -> None:
        project = await self._project_repo.by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(project_id),
                instance=f"/api/v1/projects/{project_id}/plan",
            )

    def _build_state(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        context_id: str | None,
        changes: list[PlanCambio],
    ) -> PlanStateOutput:
        pending_states = {EstadoPlanCambio.PENDING, EstadoPlanCambio.ADDED}
        return PlanStateOutput(
            project_id=project_id,
            phase=phase,
            context=context_id or str(project_id),
            changes=changes,
            pending_count=sum(1 for c in changes if c.status in pending_states),
            conflict_count=sum(1 for c in changes if c.status == EstadoPlanCambio.CONFLICT),
        )

    async def get_plan_state(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        context_id: str | None = None,
    ) -> PlanStateOutput:
        await self._verify_project(project_id)
        changes = await self._chat_repo.list_plan_changes(project_id, phase)
        return self._build_state(project_id, phase, context_id, changes)

    async def _find_suggestion(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        change_id: str,
        context_id: str | None = None,
    ) -> SugerenciaCambio:
        history = await self._chat_repo.get_history(project_id, phase, context_id)
        if history is not None:
            for msg in history.messages:
                if (
                    msg.role == ChatRole.ASSISTANT
                    and msg.suggested_change is not None
                    and msg.suggested_change.id == change_id
                ):
                    return msg.suggested_change
        raise PlanChangeNotFoundError(
            change_id=change_id,
            instance=f"/api/v1/projects/{project_id}/plan/changes",
        )

    async def _raise_if_change_not_found(
        self,
        project_id: ProjectId,
        change_id: PlanChangeId,
    ) -> None:
        raise PlanChangeNotFoundError(
            change_id=str(change_id),
            instance=f"/api/v1/projects/{project_id}/plan/changes/{change_id}",
        )

    async def add_change(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        change_id: str,
        context_id: str | None = None,
    ) -> PlanStateOutput:
        await self._verify_project(project_id)

        existing = await self._chat_repo.list_plan_changes(project_id, phase)
        if any(str(c.id) == change_id for c in existing):
            return self._build_state(project_id, phase, context_id, existing)

        suggestion = await self._find_suggestion(project_id, phase, change_id, context_id)

        plan_change = PlanCambio(
            id=PlanChangeId(change_id),
            section=suggestion.section,
            description=suggestion.description,
            diff=suggestion.diff,
            status=EstadoPlanCambio.ADDED,
            origin="chat",
            rationale=suggestion.rationale,
        )
        await self._chat_repo.add_plan_change(project_id, phase, plan_change)

        changes = await self._chat_repo.list_plan_changes(project_id, phase)
        return self._build_state(project_id, phase, context_id, changes)

    async def remove_change(
        self,
        project_id: ProjectId,
        change_id: PlanChangeId,
        phase: SpecPhase,
        context_id: str | None = None,
    ) -> PlanStateOutput:
        await self._verify_project(project_id)

        removed = await self._chat_repo.remove_plan_change(project_id, change_id)
        if not removed:
            await self._raise_if_change_not_found(project_id, change_id)

        changes = await self._chat_repo.list_plan_changes(project_id, phase)
        return self._build_state(project_id, phase, context_id, changes)

    async def _update_status(
        self,
        project_id: ProjectId,
        change_id: PlanChangeId,
        phase: SpecPhase,
        status: EstadoPlanCambio,
        context_id: str | None = None,
    ) -> PlanStateOutput:
        await self._verify_project(project_id)

        updated = await self._chat_repo.update_plan_change_status(project_id, change_id, status)
        if updated is None:
            await self._raise_if_change_not_found(project_id, change_id)

        changes = await self._chat_repo.list_plan_changes(project_id, phase)
        return self._build_state(project_id, phase, context_id, changes)

    async def accept_change(
        self,
        project_id: ProjectId,
        change_id: PlanChangeId,
        phase: SpecPhase,
        context_id: str | None = None,
    ) -> PlanStateOutput:
        return await self._update_status(project_id, change_id, phase, EstadoPlanCambio.APPLIED, context_id)

    async def discard_change(
        self,
        project_id: ProjectId,
        change_id: PlanChangeId,
        phase: SpecPhase,
        context_id: str | None = None,
    ) -> PlanStateOutput:
        return await self._update_status(project_id, change_id, phase, EstadoPlanCambio.DISCARDED, context_id)

    async def discard_plan(
        self,
        project_id: ProjectId,
        phase: SpecPhase,
        context_id: str | None = None,  # noqa: ARG002
    ) -> None:
        await self._verify_project(project_id)
        await self._chat_repo.clear_plan(project_id, phase)
