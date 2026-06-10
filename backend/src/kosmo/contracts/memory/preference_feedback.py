from pydantic import BaseModel, Field


class PreferenceFeedback(BaseModel):
    preference_id: str = ""
    feedback_type: str = Field(description="'reinforced' | 'violated' | 'irrelevant'")
    context: str = ""
    score: float = Field(default=0.0, ge=-1.0, le=1.0)
