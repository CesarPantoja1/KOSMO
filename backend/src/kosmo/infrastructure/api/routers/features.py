from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from kosmo.contracts.sdd.ids import ProjectId

router = APIRouter(tags=["features"])


class SaveSelectedFeaturesRequest(BaseModel):
    project_id: str
    selected_suggestions: list[dict]


@router.post("/api/v1/projects/{project_id}/features/generate")
async def generate_features(project_id: str, request: Request) -> dict:
    uc = request.app.state.pipeline_components.generate_features_uc
    output = await uc.execute(project_id=ProjectId(project_id))
    features_data = []
    for f in output.features:
        features_data.append(
            {
                "id": str(f.id),
                "display_id": f.display_id,
                "number": f.number,
                "title": f.title,
                "slug": f.slug,
                "description": f.description,
                "rationale": f.rationale,
                "inferred_from": f.inferred_from,
                "created_at": f.created_at.isoformat().replace("+00:00", "Z"),
                "updated_at": f.updated_at.isoformat().replace("+00:00", "Z"),
            }
        )
    return {
        "features": features_data,
        "total": len(features_data),
    }


@router.get("/api/v1/projects/{project_id}/features")
async def get_features(project_id: str, request: Request) -> dict:
    uc = request.app.state.pipeline_components.get_pipeline_status_uc
    state = await uc.execute(ProjectId(project_id))
    if state is None:
        return {"features": [], "total": 0}
    features_data = []
    for f in state.features:
        features_data.append(
            {
                "id": str(f.id),
                "display_id": f.display_id,
                "number": f.number,
                "title": f.title,
                "slug": f.slug,
                "description": f.description,
                "rationale": f.rationale,
                "inferred_from": f.inferred_from,
                "created_at": f.created_at.isoformat().replace("+00:00", "Z"),
                "updated_at": f.updated_at.isoformat().replace("+00:00", "Z"),
            }
        )
    return {
        "features": features_data,
        "total": len(features_data),
    }


@router.post("/api/v1/projects/{project_id}/features/suggest")
async def suggest_features(project_id: str, request: Request) -> dict:
    uc = request.app.state.pipeline_components.suggest_features_uc
    output = await uc.execute(project_id=ProjectId(project_id))
    suggestions_data = []
    for s in output.suggestions:
        suggestions_data.append(
            {
                "number": s.number,
                "display_id": f"C{s.number:02d}",
                "title": s.title,
                "description": s.description,
                "rationale": s.rationale,
                "inferred_from": s.inferred_from,
            }
        )
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
    features = await uc.execute(
        project_id=ProjectId(project_id),
        selected_suggestions=suggestions,
    )
    return {
        "features": [
            {
                "id": str(f.id),
                "display_id": f.display_id,
                "number": f.number,
                "title": f.title,
                "slug": f.slug,
                "description": f.description,
                "created_at": f.created_at.isoformat().replace("+00:00", "Z"),
                "updated_at": f.updated_at.isoformat().replace("+00:00", "Z"),
            }
            for f in features
        ],
        "total": len(features),
    }
