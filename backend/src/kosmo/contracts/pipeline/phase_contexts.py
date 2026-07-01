from __future__ import annotations

from dataclasses import dataclass, field

from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.sdd.document import RichTextDocument
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import ProjectId


@dataclass(frozen=True)
class DiscoveryPhaseContext:
    project_name: str
    project_description: str
    user_preferences: list[UserPreference] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


@dataclass(frozen=True)
class DiscoveryRefinePhaseContext:
    current_document: RichTextDocument
    user_instructions: str
    user_preferences: list[UserPreference] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


@dataclass(frozen=True)
class FeaturesPhaseContext:
    discovery_document: RichTextDocument
    existing_feature_titles: list[str] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    project_id: ProjectId = ProjectId("")
    user_preferences: list[UserPreference] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


@dataclass(frozen=True)
class EARSPhaseContext:
    discovery_document: RichTextDocument
    feature: Feature
    feature_number: int
    user_preferences: list[UserPreference] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


@dataclass(frozen=True)
class SuggestFeaturesContext:
    discovery_document: RichTextDocument
    existing_feature_titles: list[str] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    next_feature_number: int = 1
    user_preferences: list[UserPreference] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
