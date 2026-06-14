from __future__ import annotations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from kosmo.contracts.sdd.errors import FeatureNotFoundError
from kosmo.contracts.sdd.ids import FeatureId, ProjectId

router = APIRouter(tags=["requirements"])


class GenerateRequirementsRequest(BaseModel):
    project_id: str


class SaveRequirementsRequest(BaseModel):
    project_id: str
    markdown: str


async def _resolve_feature_id(
    request: Request, project_id: str, id_or_slug: str
) -> FeatureId:
    if id_or_slug.startswith("feat_"):
        return FeatureId(id_or_slug)

    feature_repo = request.app.state.pipeline_components.feature_repo
    features = await feature_repo.list_by_project(ProjectId(project_id))
    match = next((f for f in features if f.slug == id_or_slug), None)
    if match is None:
        raise FeatureNotFoundError(
            feature_id=id_or_slug,
            instance=f"/api/v1/features/{id_or_slug}/requirements",
        )
    return match.id


@router.post("/api/v1/features/{feature_id}/requirements/generate")
async def generate_requirements(
    feature_id: str,
    body: GenerateRequirementsRequest,
    request: Request,
) -> dict:
    fid = await _resolve_feature_id(request, body.project_id, feature_id)
    uc = request.app.state.pipeline_components.generate_ears_uc
    output = await uc.execute(
        project_id=ProjectId(body.project_id),
        feature_id=fid,
    )
    return {
        "feature_id": str(output.feature_id),
        "feature_number": output.feature_number,
        "requirements_markdown": output.requirements_markdown,
        "total": len(output.requirements),
    }


@router.get("/api/v1/features/{feature_id}/requirements")
async def get_requirements(
    feature_id: str,
    project_id: str = Query(...),
    request: Request = None,
) -> dict:
    uc = request.app.state.pipeline_components.get_requirements_uc
    markdown = await uc.execute(
        project_id=ProjectId(project_id),
        id_or_slug=feature_id,
    )
    return {"document_markdown": markdown or ""}


@router.put("/api/v1/features/{feature_id}/requirements")
async def save_requirements(
    feature_id: str,
    body: SaveRequirementsRequest,
    request: Request,
) -> dict:
    fid = await _resolve_feature_id(request, body.project_id, feature_id)
    uc = request.app.state.pipeline_components.save_requirements_uc
    await uc.execute(
        feature_id=fid,
        markdown=body.markdown,
    )
    return {"feature_id": feature_id, "message": "ok"}
