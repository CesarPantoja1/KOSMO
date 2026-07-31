from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.chat import ChatRepository, HistorialChat
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, RequirementId
from kosmo.contracts.sdd.repositories import FeatureRepository


@dataclass(frozen=True)
class GetRequirementChatHistoryInput:
    feature_id: FeatureId
    requirement_id: RequirementId


@dataclass(frozen=True)
class GetRequirementChatHistoryOutput:
    requirement_id: RequirementId
    history: HistorialChat | None


class GetRequirementChatHistoryUseCase:
    def __init__(
        self,
        feature_repo: FeatureRepository,
        chat_repo: ChatRepository,
    ) -> None:
        self._feature_repo = feature_repo
        self._chat_repo = chat_repo

    async def execute(self, input_data: GetRequirementChatHistoryInput) -> GetRequirementChatHistoryOutput:
        feature = await self._feature_repo.by_id(input_data.feature_id)
        if feature is None:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/features/{input_data.feature_id}/requirements/{input_data.requirement_id}/chat",
            )

        history = await self._chat_repo.get_history(
            project_id=feature.project_id,
            phase=SpecPhase.REQUISITOS,
            context_id=str(input_data.requirement_id),
        )

        return GetRequirementChatHistoryOutput(
            requirement_id=input_data.requirement_id,
            history=history,
        )
