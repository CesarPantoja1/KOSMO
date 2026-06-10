from pydantic import BaseModel, Field


class ContextAnalyzerOutput(BaseModel):
    domain: str = ""
    key_entities: list[str] = Field(default_factory=list)
    complexity_level: str = ""
    gaps_identified: list[str] = Field(default_factory=list)
    recommended_focus: str = ""
    context_brief: str = ""


class GoalPlannerOutput(BaseModel):
    sub_goals: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)


class PreferenceRetrieverOutput(BaseModel):
    preferences_prompt: str = ""
    retrieval_error: str | None = None


class GenerationOutput(BaseModel):
    generated_document: dict | None = None
    generated_document_md: str = ""
    generated_document_tree: dict | None = None
    generated_ears: list[dict] = Field(default_factory=list)
    generated_features: list[dict] = Field(default_factory=list)
    refined_content: str = ""
    generated_content_md: str = ""
    ears_batch_score: dict = Field(default_factory=dict)


class Scratchpad(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    context_analyzer_output: ContextAnalyzerOutput | None = None
    goal_planner_output: GoalPlannerOutput | None = None
    preference_retriever_output: PreferenceRetrieverOutput | None = None
    generation: GenerationOutput | None = None
    current_feature_title: str = ""
    current_feature_description: str = ""
    current_feature_id: str = ""
    current_feature_status: str = ""
    generator_action: str = "generate"
    improve_instruction: str = ""
    current_draft: str = ""
    phase_context: str = ""
    context_summary: str = ""
    correction_original: str = ""
    correction_corrected: str = ""
    correction_document_type: str = ""

    def to_dict(self) -> dict[str, object]:
        return self.model_dump()
