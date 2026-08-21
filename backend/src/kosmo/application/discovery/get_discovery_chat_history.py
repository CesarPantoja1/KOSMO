from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.chat import ChatRepository, HistorialChat
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import ChatSessionId, ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository


@dataclass(frozen=True)
class GetDiscoveryChatHistoryInput:
    project_id: ProjectId
    before: str | None = None
    session_id: ChatSessionId | None = None


@dataclass(frozen=True)
class GetDiscoveryChatHistoryOutput:
    project_id: ProjectId
    history: HistorialChat | None


class GetDiscoveryChatHistoryUseCase:
    def __init__(
        self,
        project_repo: ProjectRepository,
        chat_repo: ChatRepository,
    ) -> None:
        self._project_repo = project_repo
        self._chat_repo = chat_repo

    async def execute(self, input_data: GetDiscoveryChatHistoryInput) -> GetDiscoveryChatHistoryOutput:
        project = await self._project_repo.by_id(input_data.project_id)
        if project is None:
            raise ProjectNotFoundError(
                project_id=str(input_data.project_id),
                instance=f"/api/v1/projects/{input_data.project_id}/discovery/chat",
            )

        history = await self._chat_repo.get_history(
            project_id=input_data.project_id,
            phase=SpecPhase.DESCUBRIMIENTO,
            before=input_data.before,
            session_id=input_data.session_id,
        )

        return GetDiscoveryChatHistoryOutput(
            project_id=input_data.project_id,
            history=history,
        )
