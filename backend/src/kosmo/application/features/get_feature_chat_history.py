from __future__ import annotations

from dataclasses import dataclass

from kosmo.contracts.chat import ChatRepository, HistorialChat
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.ids import ChatSessionId, FeatureId
from kosmo.contracts.sdd.repositories import FeatureRepository


@dataclass(frozen=True)
class GetFeatureChatHistoryInput:
    feature_id: FeatureId
    before: str | None = None
    session_id: ChatSessionId | None = None


@dataclass(frozen=True)
class GetFeatureChatHistoryOutput:
    feature_id: FeatureId
    history: HistorialChat | None


class GetFeatureChatHistoryUseCase:
    def __init__(
        self,
        feature_repo: FeatureRepository,
        chat_repo: ChatRepository,
    ) -> None:
        self._feature_repo = feature_repo
        self._chat_repo = chat_repo

    async def execute(self, input_data: GetFeatureChatHistoryInput) -> GetFeatureChatHistoryOutput:
        feature = await self._feature_repo.by_id(input_data.feature_id)
        if feature is None:
            raise FeatureNotFoundError(
                feature_id=str(input_data.feature_id),
                instance=f"/api/v1/features/{input_data.feature_id}/chat",
            )

        history = await self._chat_repo.get_history(
            project_id=feature.project_id,
            phase=SpecPhase.CARACTERISTICAS,
            context_id=str(feature.id),
            before=input_data.before,
            session_id=input_data.session_id,
        )

        return GetFeatureChatHistoryOutput(
            feature_id=input_data.feature_id,
            history=history,
        )
