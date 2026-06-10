from __future__ import annotations

import pytest

from kosmo.contracts.sdd.discovery import DiscoveryDocument
from kosmo.contracts.sdd.ears import EARSRequirement
from kosmo.contracts.sdd.feature import Feature, FeatureId
from kosmo.contracts.sdd.ids import RequirementId
from kosmo.contracts.sdd.spec import SpecPhase
from kosmo.contracts.sdd.state import (
    CritiqueRecord,
    KOSMOState,
    SupervisorStage,
    ToolCallRecord,
)
from kosmo.domain.sdd.id_generator import IdGenerator


class TestKOSMOStateDefaults:
    @pytest.mark.unit
    def test_default_phase_is_descubrimiento(self) -> None:
        state = KOSMOState(project_id="prj_01", user_id="usr_01")
        assert state.phase == SpecPhase.DESCUBRIMIENTO

    @pytest.mark.unit
    def test_default_supervisor_stage_is_context(self) -> None:
        state = KOSMOState(project_id="prj_01", user_id="usr_01")
        assert state.supervisor_stage == SupervisorStage.CONTEXT

    @pytest.mark.unit
    def test_default_max_iterations_is_ten(self) -> None:
        state = KOSMOState(project_id="prj_01", user_id="usr_01")
        assert state.max_iterations == 10
        assert state.max_critic_iterations == 3

    @pytest.mark.unit
    def test_empty_collections_by_default(self) -> None:
        state = KOSMOState(project_id="prj_01", user_id="usr_01")
        assert state.features == []
        assert state.requirements == []
        assert state.critique_log == []
        assert state.tool_call_history == []
        assert state.errors == []
        assert state.agent_outputs == {}
        assert state.shared_scratchpad == {}

    @pytest.mark.unit
    def test_human_input_pending_false_by_default(self) -> None:
        state = KOSMOState(project_id="prj_01", user_id="usr_01")
        assert state.human_input_pending is False
        assert state.output_ready is False

    @pytest.mark.unit
    def test_graph_deps_excluded_from_serialization(self) -> None:
        state = KOSMOState(project_id="prj_01", user_id="usr_01")
        serialized = state.model_dump(mode="json")
        assert "graph_deps" not in serialized

    @pytest.mark.unit
    def test_serialization_includes_all_persisted_fields(self) -> None:
        state = KOSMOState(project_id="prj_01", user_id="usr_01")
        serialized = state.model_dump(mode="json")
        required_fields = [
            "project_id",
            "user_id",
            "phase",
            "supervisor_stage",
            "features",
            "requirements",
            "critique_log",
            "tool_call_history",
            "max_iterations",
            "generation_attempts",
        ]
        for field in required_fields:
            assert field in serialized, f"Missing field: {field}"

    @pytest.mark.unit
    def test_errors_field_accepts_strings(self) -> None:
        state = KOSMOState(project_id="prj_01", user_id="usr_01", errors=["Test error"])
        assert "Test error" in state.errors


class TestToolCallRecord:
    @pytest.mark.unit
    def test_has_timestamp_auto_generated(self) -> None:
        record = ToolCallRecord(agent_id="test", tool_name="test_tool", params={})
        assert record.timestamp is not None

    @pytest.mark.unit
    def test_result_and_error_optional(self) -> None:
        record = ToolCallRecord(agent_id="test", tool_name="test_tool", params={})
        assert record.result is None
        assert record.error is None

    @pytest.mark.unit
    def test_error_is_recorded(self) -> None:
        record = ToolCallRecord(
            agent_id="test",
            tool_name="test_tool",
            params={},
            error="Something failed",
        )
        assert record.error == "Something failed"


class TestCritiqueRecord:
    @pytest.mark.unit
    def test_has_timestamp(self) -> None:
        record = CritiqueRecord(agent_id="test", severity="warning", message="Test")
        assert record.timestamp is not None

    @pytest.mark.unit
    def test_severity_and_message_required(self) -> None:
        record = CritiqueRecord(agent_id="test", severity="blocker", message="Blocked")
        assert record.severity == "blocker"
        assert record.message == "Blocked"

    @pytest.mark.unit
    def test_field_is_optional(self) -> None:
        record = CritiqueRecord(agent_id="test", severity="none", message="OK")
        assert record.field is None


class TestSupervisorStage:
    @pytest.mark.unit
    def test_four_stages_defined(self) -> None:
        stages = list(SupervisorStage)
        assert len(stages) == 4
        assert SupervisorStage.CONTEXT in stages
        assert SupervisorStage.GENERATE in stages
        assert SupervisorStage.EVALUATE in stages
        assert SupervisorStage.DONE in stages

    @pytest.mark.unit
    def test_stage_values_are_strings(self) -> None:
        assert SupervisorStage.CONTEXT.value == "context"
        assert SupervisorStage.GENERATE.value == "generate"


class TestStateWithLiveEntities:
    @pytest.mark.unit
    def test_state_holds_features(self) -> None:
        feature = Feature(
            id=FeatureId(IdGenerator.generate("feature")),
            project_id="prj_01",
            title="Test Feature",
            description="A test",
        )
        state = KOSMOState(project_id="prj_01", user_id="usr_01", features=[feature])
        assert len(state.features) == 1
        assert state.features[0].title == "Test Feature"

    @pytest.mark.unit
    def test_state_holds_requirements(self) -> None:
        req = EARSRequirement(
            id=RequirementId(IdGenerator.generate("requirement")),
            pattern="ubiquitous",
            system="El sistema",
            response="debe funcionar",
            source_statement="The system shall work",
        )
        state = KOSMOState(project_id="prj_01", user_id="usr_01", requirements=[req])
        assert len(state.requirements) == 1

    @pytest.mark.unit
    def test_state_holds_discovery_document(self) -> None:
        discovery = DiscoveryDocument(vision="Test vision")
        state = KOSMOState(project_id="prj_01", user_id="usr_01", discovery=discovery)
        assert state.discovery is not None
        assert state.discovery.vision == "Test vision"

    @pytest.mark.unit
    def test_state_with_critique_log(self) -> None:
        log_entries = [
            CritiqueRecord(agent_id="q", severity="warning", message="warn"),
            CritiqueRecord(agent_id="s", severity="blocker", message="stop"),
        ]
        state = KOSMOState(project_id="prj_01", user_id="usr_01", critique_log=log_entries)
        assert len(state.critique_log) == 2

    @pytest.mark.unit
    def test_state_with_tool_call_history(self) -> None:
        entries = [
            ToolCallRecord(agent_id="gen1", tool_name="llm", params={}, result="ok"),
        ]
        state = KOSMOState(project_id="prj_01", user_id="usr_01", tool_call_history=entries)
        assert len(state.tool_call_history) == 1


class TestVerifyScope:
    @pytest.mark.unit
    def test_verify_scope_passes_with_valid_ids(self) -> None:
        from kosmo.application.orchestration.helpers import verify_scope

        state = KOSMOState(project_id="prj_01", user_id="usr_01")
        verify_scope(state)

    @pytest.mark.unit
    def test_verify_scope_fails_with_empty_project_id(self) -> None:
        from kosmo.application.orchestration.helpers import verify_scope

        state = KOSMOState(project_id="", user_id="usr_01")
        with pytest.raises(AssertionError, match="project_id"):
            verify_scope(state)

    @pytest.mark.unit
    def test_verify_scope_fails_with_empty_user_id(self) -> None:
        from kosmo.application.orchestration.helpers import verify_scope

        state = KOSMOState(project_id="prj_01", user_id="")
        with pytest.raises(AssertionError, match="user_id"):
            verify_scope(state)
