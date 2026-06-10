from pydantic import BaseModel, Field


class DiscoveryOutputSection(BaseModel):
    vision: str = Field(default="", min_length=1)
    problem_space: str = Field(default="", min_length=1)
    actors: str = Field(default="", min_length=1)
    value_proposition: str = Field(default="", min_length=1)
    use_cases: str = Field(default="", min_length=1)
    core_capabilities: str = Field(default="", min_length=1)
    business_rules: str = Field(default="", min_length=1)
    quality_attributes: str = Field(default="", min_length=1)
    scope: str = Field(default="", min_length=1)


class DiscoveryOutputSchema(BaseModel):
    model_config = {"extra": "forbid"}

    vision: str = Field(default="")
    problem_space: str = Field(default="")
    actors: str = Field(default="")
    value_proposition: str = Field(default="")
    use_cases: str = Field(default="")
    core_capabilities: str = Field(default="")
    business_rules: str = Field(default="")
    quality_attributes: str = Field(default="")
    scope: str = Field(default="")


class SuggestedFeatureSchema(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=20, max_length=600)
    rationale: str = Field(default="", max_length=300)
    inferred_from: list[str] = Field(default_factory=list)
    category: str = Field(default="")


class FeaturesOutputSchema(BaseModel):
    """Schema para /suggest: exactamente 3 sugerencias (no persiste)."""

    model_config = {"extra": "forbid"}

    suggestions: list[SuggestedFeatureSchema] = Field(
        min_length=3,
        max_length=3,
        description="Exactamente 3 sugerencias de caracteristicas ricas",
    )


class GenerateFeaturesOutputSchema(BaseModel):
    """Schema para /generate: exactamente 5 caracteristicas (persiste)."""

    model_config = {"extra": "forbid"}

    suggestions: list[SuggestedFeatureSchema] = Field(
        min_length=5,
        max_length=5,
        description="Exactamente 5 caracteristicas de negocio ricas e inferidas del Discovery",
    )


class AcceptanceCriterionSchema(BaseModel):
    description: str = Field(default="")
    scenario: str = Field(default="")
    expected_result: str = Field(default="")
    verified_by: str = Field(default="")


class EARSRequirementSchema(BaseModel):
    pattern: str = Field(default="ubiquitous")
    trigger: str | None = Field(default=None)
    system: str = Field(default="El sistema")
    response: str = Field(min_length=5)
    acceptance_criteria: list[AcceptanceCriterionSchema] = Field(default_factory=list)
    source_statement: str = Field(min_length=10)
    rationale: str = Field(default="")
    traceability: list[str] = Field(default_factory=list)


class EARSOutputSchema(BaseModel):
    model_config = {"extra": "forbid"}

    ubiquitous: list[EARSRequirementSchema] = Field(default_factory=list)
    event: list[EARSRequirementSchema] = Field(default_factory=list)
    state: list[EARSRequirementSchema] = Field(default_factory=list)
    optional: list[EARSRequirementSchema] = Field(default_factory=list)
    unwanted: list[EARSRequirementSchema] = Field(default_factory=list)
    complex: list[EARSRequirementSchema] = Field(default_factory=list)


class CriticDimensionScore(BaseModel):
    dimension: str
    score: float = Field(ge=0, le=10)
    notes: str = ""


class CriticOutputSchema(BaseModel):
    model_config = {"extra": "allow"}

    severity: str = Field(description="'blocker', 'warning' o 'none'")
    message: str = ""
    findings: list[str] = Field(default_factory=list)
    dimension_scores: dict[str, float] = Field(default_factory=dict)


class EvaluationDimensionScore(BaseModel):
    dimension: str
    score: float = Field(ge=0, le=10)


class EvaluationOutputSchema(BaseModel):
    model_config = {"extra": "forbid"}

    pureza_negocio: float = Field(default=0, ge=0, le=10)
    cobertura_ears: float = Field(default=0, ge=0, le=10)
    verificabilidad_funcional: float = Field(default=0, ge=0, le=10)
    densidad_criterios: float = Field(default=0, ge=0, le=10)
    ortografia: float = Field(default=0, ge=0, le=10)
    blockers: list[str] = Field(default_factory=list)
    overall_verdict: str = Field(default="needs_revision")
    summary: str = ""
