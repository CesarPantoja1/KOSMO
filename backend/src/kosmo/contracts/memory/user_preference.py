from datetime import UTC, datetime

from pydantic import BaseModel, Field

from kosmo.contracts.sdd.ids import ProjectId


class UserPreference(BaseModel):
    id: str
    user_id: str
    project_id: ProjectId | None = None
    document_type: str
    rule_text: str
    corpus: list[str] = Field(default_factory=list)
    context_snippet: str = ""
    confidence: float = 1.0
    usage_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
