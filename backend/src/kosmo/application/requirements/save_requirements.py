from __future__ import annotations

from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository


class SaveRequirementsUseCase:
    def __init__(self, feature_repo: FeatureRepository) -> None:
        self._feature_repo = feature_repo

    async def execute(
        self,
        project_id: ProjectId,
        feature_id: FeatureId,
        document: RichTextDocument,
    ) -> None:
        _ = project_id
        feature = await self._feature_repo.by_id(feature_id)
        if feature is None:
            raise FeatureNotFoundError(
                feature_id=str(feature_id),
                instance=f"/features/{feature_id}",
            )

        feature.requirements_document = document
        await self._feature_repo.save(feature)
