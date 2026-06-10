from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from kosmo.contracts.sdd.ids import ProjectId
from kosmo.infrastructure.api.schemas_preferences import (
    DeletedResponse,
    PreferencesListResponse,
    UpdateConfidenceRequest,
    UpdateConfidenceResponse,
)

router = APIRouter(prefix="/users/{user_id}/preferences", tags=["preferences"])


@router.get("", response_model=PreferencesListResponse)
async def list_preferences(user_id: str, request: Request) -> dict:
    preference_repo = getattr(request.app.state, "preference_repo", None)
    if not preference_repo:
        raise HTTPException(status_code=503, detail="Preference repository not available")

    project_id = request.query_params.get("project_id")
    document_type = request.query_params.get("document_type")
    limit = int(request.query_params.get("limit", "50"))

    prefs = await preference_repo.get_by_user(
        user_id=user_id,
        project_id=ProjectId(project_id) if project_id else None,
        document_type=document_type,
        limit=limit,
    )

    return {
        "preferences": [
            {
                "id": p.id,
                "rule_text": p.rule_text,
                "document_type": p.document_type,
                "confidence": p.confidence,
                "usage_count": p.usage_count,
                "project_id": p.project_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in prefs
        ],
        "total": len(prefs),
    }


@router.delete("/{preference_id}", response_model=DeletedResponse)
async def delete_preference(user_id: str, preference_id: str, request: Request) -> dict:
    preference_repo = getattr(request.app.state, "preference_repo", None)
    if not preference_repo:
        raise HTTPException(status_code=503, detail="Preference repository not available")

    await preference_repo.delete(preference_id)
    return {"deleted": True, "preference_id": preference_id}


@router.patch("/{preference_id}/confidence", response_model=UpdateConfidenceResponse)
async def update_confidence(
    user_id: str,
    preference_id: str,
    body: UpdateConfidenceRequest,
    request: Request,
) -> dict:
    preference_repo = getattr(request.app.state, "preference_repo", None)
    if not preference_repo:
        raise HTTPException(status_code=503, detail="Preference repository not available")

    await preference_repo.update_confidence(preference_id, body.delta)
    return {"updated": True, "preference_id": preference_id, "delta": body.delta}
