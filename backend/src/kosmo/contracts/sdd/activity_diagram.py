from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from kosmo.contracts.sdd.ids import ActivityDiagramId, FeatureId


@dataclass(frozen=True)
class DiagramaActividad:
    id: ActivityDiagramId
    feature_id: FeatureId
    diagram_syntax: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
