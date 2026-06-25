from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from kosmo.contracts.sdd.document import (
    AcceptanceCriterion,
    EARSPattern,
)
from kosmo.contracts.sdd.ids import FeatureId, RequirementId


@dataclass(frozen=True)
class EARSRequirement:
    id: RequirementId
    feature_id: FeatureId
    feature_number: int
    requirement_number: int
    pattern: EARSPattern
    trigger: str
    system: str
    response: str
    source_statement: str
    rationale: str
    traceability: list[str] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def display_id(self) -> str:
        return f"REQ-{self.feature_number}.{self.requirement_number}"
