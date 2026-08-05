from __future__ import annotations

from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository


async def resolve_feature_id(repo: FeatureRepository, project_id: ProjectId, id_or_slug: str) -> FeatureId | None:
    if id_or_slug.startswith("feat_"):
        return FeatureId(id_or_slug)

    features = await repo.list_by_project(project_id)
    for f in features:
        if f.slug == id_or_slug:
            return f.id
    return None
