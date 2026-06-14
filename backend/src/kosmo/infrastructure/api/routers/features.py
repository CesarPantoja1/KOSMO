from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from kosmo.contracts.sdd.ids import FeatureId, ProjectId

router = APIRouter(tags=["features"])


class ApproveFeatureRequest(BaseModel):
    project_id: str


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
                "status": f.status.value,
                "rationale": f.rationale,
                "inferred_from": f.inferred_from,
            }
        )
    return {
        "features": features_data,
        "validation": {
            "is_valid": output.validation_result.is_valid,
            "errors": output.validation_result.errors,
            "warnings": output.validation_result.warnings,
        },
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
                "status": f.status.value,
            }
            for f in features
        ]
    }


@router.patch("/api/v1/features/{feature_id}/status")
async def approve_feature(
    feature_id: str,
    body: ApproveFeatureRequest,
    request: Request,
) -> dict:
    uc = request.app.state.pipeline_components.approve_feature_uc
    feature = await uc.execute(
        project_id=ProjectId(body.project_id),
        feature_id=FeatureId(feature_id),
    )
    return {
        "id": str(feature.id),
        "display_id": feature.display_id,
        "title": feature.title,
        "status": feature.status.value,
    }
