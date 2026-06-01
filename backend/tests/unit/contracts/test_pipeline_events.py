from kosmo.contracts.sdd.events import (
    ArtifactProduced,
    NodeCompleted,
    NodeStarted,
    PhaseTransition,
    ValidationFailed,
    ValidationRetry,
)


class TestPipelineEvents:
    def test_node_started(self) -> None:
        event = NodeStarted(event_id="evt-1", spec_id="spec-1", node_name="analyzer")
        assert event.event_type == "node_started"
        assert event.node_name == "analyzer"

    def test_node_completed(self) -> None:
        event = NodeCompleted(
            event_id="evt-2", spec_id="spec-1", node_name="analyzer", artifact_count=12
        )
        assert event.event_type == "node_completed"
        assert event.artifact_count == 12

    def test_artifact_produced(self) -> None:
        event = ArtifactProduced(
            event_id="evt-3", spec_id="spec-1", artifact_kind="requirements", artifact_id="R-1"
        )
        assert event.event_type == "artifact_produced"
        assert event.artifact_kind == "requirements"

    def test_validation_failed(self) -> None:
        event = ValidationFailed(
            event_id="evt-4",
            spec_id="spec-1",
            node_name="analyzer",
            findings=["Pattern not recognized"],
        )
        assert event.event_type == "validation_failed"
        assert len(event.findings) == 1

    def test_validation_retry(self) -> None:
        event = ValidationRetry(
            event_id="evt-5", spec_id="spec-1", node_name="analyzer", attempt=2, max_attempts=3
        )
        assert event.event_type == "validation_retry"
        assert event.attempt == 2

    def test_phase_transition(self) -> None:
        event = PhaseTransition(
            event_id="evt-6", spec_id="spec-1", from_phase="discovery", to_phase="requirements"
        )
        assert event.from_phase == "discovery"
        assert event.to_phase == "requirements"
