from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PreferenceItem(BaseModel):
    id: str
    rule_text: str
    document_type: str = ""
    confidence: float = 1.0
    usage_count: int = 0
    project_id: str | None = None
    created_at: datetime | None = None


class PreferencesListResponse(BaseModel):
    preferences: list[PreferenceItem] = Field(default_factory=list)
    total: int = 0


class DeletedResponse(BaseModel):
    deleted: bool = True
    preference_id: str


class UpdateConfidenceRequest(BaseModel):
    delta: float = Field(default=0.0, ge=-1.0, le=1.0)


class UpdateConfidenceResponse(BaseModel):
    updated: bool = True
    preference_id: str
    delta: float
