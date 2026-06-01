from pydantic import BaseModel, Field


class RawIdea(BaseModel):
    text: str
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    optional_context: str = ""


class DiscoveryDocument(BaseModel):
    vision: str = ""
    problem_space: str = ""
    actors: str = ""
    value_proposition: str = ""
    use_cases: str = ""
    core_capabilities: str = ""
    business_rules: str = ""
    quality_attributes: str = ""
    scope: str = ""


class ProjectRoadmap(BaseModel):
    features: list[str] = []
    dependencies: list[tuple[str, str]] = []
    suggested_order: list[str] = []
