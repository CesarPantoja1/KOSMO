from datetime import UTC, datetime

from pydantic import BaseModel, Field


class PipelineEvent(BaseModel):
    event_id: str
    spec_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str


class NodeStarted(PipelineEvent):
    event_type: str = "node_started"
    node_name: str


class NodeCompleted(PipelineEvent):
    event_type: str = "node_completed"
    node_name: str
    artifact_count: int = 0


class ArtifactProduced(PipelineEvent):
    event_type: str = "artifact_produced"
    artifact_kind: str
    artifact_id: str


class ValidationFailed(PipelineEvent):
    event_type: str = "validation_failed"
    node_name: str
    findings: list[str]


class ValidationRetry(PipelineEvent):
    event_type: str = "validation_retry"
    node_name: str
    attempt: int
    max_attempts: int


class RegenerationTriggered(PipelineEvent):
    event_type: str = "regeneration_triggered"
    node_name: str
    reason: str


class PhaseTransition(PipelineEvent):
    event_type: str = "phase_transition"
    from_phase: str
    to_phase: str
