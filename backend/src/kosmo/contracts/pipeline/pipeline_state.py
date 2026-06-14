from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
    EARSPhaseOutput,
    FeaturesPhaseOutput,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, PipelineId, ProjectId, UserId


@dataclass
class PhaseTransitionRecord:
    from_phase: SpecPhase
    to_phase: SpecPhase
    transitioned_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    human_approved: bool = False
    validation_passed: bool = False
    notes: str | None = None


@dataclass
class KOSMOPipelineState:
    project_id: ProjectId
    user_id: UserId
    pipeline_id: PipelineId = field(default_factory=lambda: PipelineId("pipe_placeholder"))

    current_phase: SpecPhase = SpecPhase.DESCUBRIMIENTO

    features: list[Feature] = field(default_factory=list)
    requirements_by_feature: dict[FeatureId, list[EARSRequirement]] = field(default_factory=dict)

    discovery_output: DiscoveryPhaseOutput | None = None
    features_output: FeaturesPhaseOutput | None = None
    ears_outputs: dict[FeatureId, EARSPhaseOutput] = field(default_factory=dict)

    user_preferences: list[UserPreference] = field(default_factory=list)

    phase_history: list[PhaseTransitionRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
