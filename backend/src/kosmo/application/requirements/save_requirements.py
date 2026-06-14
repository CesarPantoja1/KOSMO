from __future__ import annotations

from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.repositories import RequirementRepository


class SaveRequirementsUseCase:
    def __init__(self, requirement_repo: RequirementRepository) -> None:
        self._requirement_repo = requirement_repo

    async def execute(
        self,
        feature_id: FeatureId,
        markdown: str,
    ) -> None:
        await self._requirement_repo.save(feature_id, markdown)
