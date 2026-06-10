from enum import StrEnum

from pydantic import BaseModel, Field

from kosmo.contracts.sdd.ids import RequirementId


class EARSPattern(StrEnum):
    UBIQUITOUS = "ubiquitous"
    EVENT = "event"
    STATE = "state"
    OPTIONAL = "optional"
    UNWANTED = "unwanted"
    COMPLEX = "complex"


class AcceptanceCriterion(BaseModel):
    description: str
    scenario: str = Field(
        default="",
        description="Formato Dado-Cuando-Entonces: contexto → evento → resultado observable",
    )
    expected_result: str = Field(
        default="",
        description="Resultado concreto y verificable que espera el negocio",
    )
    verified_by: str = ""


class EARSRequirement(BaseModel):
    id: RequirementId
    pattern: EARSPattern
    trigger: str | None = Field(default=None, description="WHEN / IF / WHILE / WHERE")
    system: str = Field(
        default="El sistema", description="Sujeto del requisito, perspectiva de negocio"
    )
    response: str
    acceptance_criteria: list[AcceptanceCriterion] = []
    source_statement: str
    rationale: str = Field(
        default="",
        description="Justificación breve: por qué el negocio necesita este comportamiento",
    )
    traceability: list[str] = []
