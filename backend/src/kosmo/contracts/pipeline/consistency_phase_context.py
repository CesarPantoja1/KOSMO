from __future__ import annotations

from dataclasses import dataclass, field

from kosmo.contracts.ai.chat import AppliedChange
from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.sdd.document import SpecPhase


@dataclass(frozen=True)
class DownstreamArtifact:
    artifact_id: str
    artifact_type: str
    title: str
    description: str


@dataclass(frozen=True)
class ConsistencyPhaseContext:
    source_phase: SpecPhase
    target_phase: SpecPhase
    applied_changes: list[AppliedChange] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    downstream_artifacts: list[DownstreamArtifact] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    user_preferences: list[UserPreference] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    source_content: str = ""
