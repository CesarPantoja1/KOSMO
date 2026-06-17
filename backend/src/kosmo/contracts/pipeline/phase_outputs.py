from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId


@dataclass(frozen=True)
class GenerationMetadata:
    llm_calls: int = 0
    total_tokens: int = 0
    retry_count: int = 0
    reasoning_log: list[str] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    tool_results: list[dict[str, Any]] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    generation_time_ms: int = 0
    model_used: str = ""


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    warnings: list[str] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    quality_score: float | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class DiscoveryPhaseOutput:
    discovery_document: RichTextDocument
    validation_result: ValidationResult
    generation_metadata: GenerationMetadata


@dataclass(frozen=True)
class FeaturesPhaseOutput:
    features: list[Feature]
    validation_result: ValidationResult
    generation_metadata: GenerationMetadata


@dataclass(frozen=True)
class SuggestFeaturesOutput:
    suggestions: list[SuggestedFeature]
    excluded_titles: list[str]
    domain_inferred: str


@dataclass(frozen=True)
class SuggestedFeature:
    number: int
    title: str
    description: str
    rationale: str
    inferred_from: list[str] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


@dataclass(frozen=True)
class EARSPhaseOutput:
    feature_id: FeatureId
    feature_number: int
    requirements: list[EARSRequirement]
    requirements_markdown: str
    validation_result: ValidationResult
    generation_metadata: GenerationMetadata