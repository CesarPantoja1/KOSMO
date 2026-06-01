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
    verified_by: str = ""


class EARSRequirement(BaseModel):
    id: RequirementId
    pattern: EARSPattern
    trigger: str | None = Field(default=None, description="WHEN / IF / WHILE / WHERE")
    system: str
    response: str
    acceptance_criteria: list[AcceptanceCriterion] = []
    source_statement: str
    traceability: list[str] = []
