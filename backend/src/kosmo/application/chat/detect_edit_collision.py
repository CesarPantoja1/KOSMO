from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts import ChatRepository, EstadoPlanCambio, PlanCambio
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository

_ACTIVE_STATUSES = frozenset({EstadoPlanCambio.PENDING, EstadoPlanCambio.ADDED, EstadoPlanCambio.CONFLICT})


def _fragment_present(diff_before: str, current_content: str) -> bool:
    """Retorna True si el fragmento diff_before sigue presente en current_content."""
    return diff_before.strip() in current_content


@dataclass(frozen=True)
class DetectEditCollisionInput:
    project_id: ProjectId
    phase: SpecPhase
    section: str
    current_content: str


@dataclass(frozen=True)
class DetectEditCollisionOutput:
    collisions: list[PlanCambio]

    @property
    def has_collision(self) -> bool:
        return len(self.collisions) > 0


class DetectEditCollisionUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        chat_repo: ChatRepository,
    ) -> None:
        self._project_repo = project_repo
        self._chat_repo = chat_repo

    async def execute(self, input_data: DetectEditCollisionInput) -> DetectEditCollisionOutput:
        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/plan/collision",
            )

        changes = await self._chat_repo.list_plan_changes(input_data.project_id, input_data.phase)

        candidates = [
            c
            for c in changes
            if c.section == input_data.section
            and c.status in _ACTIVE_STATUSES
            and not _fragment_present(c.diff.before, input_data.current_content)
        ]

        collisions: list[PlanCambio] = []
        for candidate in candidates:
            updated = await self._chat_repo.update_plan_change_status(
                project_id=input_data.project_id,
                change_id=candidate.id,
                status=EstadoPlanCambio.CONFLICT,
                user_version=input_data.current_content,
            )
            if updated is not None:
                collisions.append(updated)

        return DetectEditCollisionOutput(collisions=collisions)
