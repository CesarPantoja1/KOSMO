from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from kosmo.contracts.sdd.ids import ProjectId
from kosmo.infrastructure.api.routers.helpers import resolve_project

router = APIRouter(tags=["features"])


class SaveSelectedFeaturesRequest(BaseModel):
    project_id: str
    selected_suggestions: list[dict]


async def _get_project_id(request: Request, id_or_slug: str) -> ProjectId:
    project = await resolve_project(request, id_or_slug)
    return project.id


@router.post("/api/v1/projects/{project_id}/features/generate")
async def generate_features(project_id: str, request: Request) -> dict:
    uc = request.app.state.pipeline_components.generate_features_uc
    pid = await _get_project_id(request, project_id)
    output = await uc.execute(project_id=pid)
    features_data = [
        {
            "display_id": f.display_id,
            "title": f.title,
            "slug": f.slug,
            "description": f.description,
        }
        for f in output.features
    ]
    return {"features": features_data, "total": len(features_data)}


@router.get("/api/v1/projects/{project_id}/features")
async def get_features(project_id: str, request: Request) -> dict:
    pid = await _get_project_id(request, project_id)
    feature_repo = request.app.state.pipeline_components.feature_repo
    features = await feature_repo.list_by_project(pid)
    features_data = [
        {
            "display_id": f.display_id,
            "title": f.title,
            "slug": f.slug,
            "description": f.description,
        }
        for f in features
    ]
    return {"features": features_data, "total": len(features_data)}


@router.get("/api/v1/projects/{project_id}/features/{slug}")
async def get_feature_by_slug(project_id: str, slug: str, request: Request) -> dict:
    from kosmo.contracts.sdd.errors import FeatureNotFoundError

    pid = await _get_project_id(request, project_id)
    feature_repo = request.app.state.pipeline_components.feature_repo
    features = await feature_repo.list_by_project(pid)
    feature = next((f for f in features if f.slug == slug), None)
    if feature is None:
        raise FeatureNotFoundError(
            feature_id=slug,
            instance=f"/api/v1/projects/{project_id}/features/{slug}",
        )
    return {
        "id": str(feature.id),
        "display_id": feature.display_id,
        "number": feature.number,
        "title": feature.title,
        "slug": feature.slug,
        "description": feature.description,
        "rationale": feature.rationale,
        "inferred_from": feature.inferred_from,
        "created_at": feature.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": feature.updated_at.isoformat().replace("+00:00", "Z"),
    }


@router.post("/api/v1/projects/{project_id}/features/suggest")
async def suggest_features(project_id: str, request: Request) -> dict:
    pid = await _get_project_id(request, project_id)
    uc = request.app.state.pipeline_components.suggest_features_uc
    output = await uc.execute(project_id=pid)
    suggestions_data = [
        {
            "number": s.number,
            "display_id": f"C{s.number:02d}",
            "title": s.title,
            "description": s.description,
            "rationale": s.rationale,
            "inferred_from": s.inferred_from,
        }
        for s in output.suggestions
    ]
    return {
        "suggestions": suggestions_data,
        "excluded_titles": output.excluded_titles,
        "domain_inferred": output.domain_inferred,
    }


@router.post("/api/v1/projects/{project_id}/features")
async def save_selected_features(
    project_id: str,
    body: SaveSelectedFeaturesRequest,
    request: Request,
) -> dict:
    from kosmo.contracts.pipeline.phase_outputs import SuggestedFeature

    uc = request.app.state.pipeline_components.save_features_uc
    suggestions = [
        SuggestedFeature(
            number=s.get("number", 0),
            title=s.get("title", ""),
            description=s.get("description", ""),
            rationale=s.get("rationale", ""),
            inferred_from=s.get("inferred_from", []),
        )
        for s in body.selected_suggestions
    ]
    pid = await _get_project_id(request, project_id)
    features = await uc.execute(
        project_id=pid,
        selected_suggestions=suggestions,
    )
    features_data = [
        {
            "display_id": f.display_id,
            "title": f.title,
            "slug": f.slug,
            "description": f.description,
        }
        for f in features
    ]
    return {"features": features_data, "total": len(features_data)}
