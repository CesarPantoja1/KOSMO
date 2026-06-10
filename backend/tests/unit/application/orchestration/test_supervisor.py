from __future__ import annotations

import pytest

from kosmo.application.orchestration.kosmo_graph import route_after_supervisor
from kosmo.application.orchestration.nodes.supervisor import (
    _route_to_generator,
    route_after_critic_evaluator,
    supervisor_node,
)
from kosmo.contracts.sdd.spec import SpecPhase
from kosmo.contracts.sdd.state import KOSMOState, SupervisorStage


@pytest.mark.unit
class TestSupervisorNode:
    async def test_human_input_pending_blocks(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={"human_input_pending": True, "human_prompt": "Esperando input"}
        )
        result = await supervisor_node(state)
        assert result["human_input_pending"] is True
        assert result["output_ready"] is False

    async def test_max_iterations_exceeded(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(update={"generation_attempts": 10, "max_iterations": 10})
        result = await supervisor_node(state)
        assert result["supervisor_stage"] == SupervisorStage.DONE
        assert result["human_input_pending"] is True
        assert any("max_iterations" in str(e) for e in result.get("errors", []))

    async def test_max_iterations_not_yet_exceeded_continues(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(update={"generation_attempts": 5, "max_iterations": 10})
        result = await supervisor_node(state)
        assert result.get("supervisor_stage") == SupervisorStage.GENERATE

    async def test_context_stage_dispatches_to_generate(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(update={"supervisor_stage": SupervisorStage.CONTEXT})
        result = await supervisor_node(state)
        assert result["supervisor_stage"] == SupervisorStage.GENERATE

    async def test_evaluate_stage_with_needs_revision_retries(
        self, kosmo_state: KOSMOState
    ) -> None:
        state = kosmo_state.model_copy(
            update={
                "supervisor_stage": SupervisorStage.EVALUATE,
                "validation_status": "needs_revision",
                "output_ready": False,
                "generation_attempts": 1,
                "max_iterations": 10,
            }
        )
        result = await supervisor_node(state)
        assert result["supervisor_stage"] == SupervisorStage.GENERATE

    async def test_evaluate_stage_done_when_output_ready(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "supervisor_stage": SupervisorStage.EVALUATE,
                "output_ready": True,
            }
        )
        result = await supervisor_node(state)
        assert result["supervisor_stage"] == SupervisorStage.DONE

    async def test_done_stage_returns_output_ready(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(update={"supervisor_stage": SupervisorStage.DONE})
        result = await supervisor_node(state)
        assert result["output_ready"] is True


@pytest.mark.unit
class TestRouteToGenerator:
    def test_descubrimiento_routes_to_discovery(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(update={"phase": SpecPhase.DESCUBRIMIENTO})
        result = _route_to_generator(state)
        assert result["current_subtask"] == "discovery_generator"
        assert result["supervisor_stage"] == SupervisorStage.EVALUATE

    def test_caracteristicas_routes_to_features(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(update={"phase": SpecPhase.CARACTERISTICAS})
        result = _route_to_generator(state)
        assert result["current_subtask"] == "features_generator"

    def test_caracteristicas_improve_routes_to_draft_refiner(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "phase": SpecPhase.CARACTERISTICAS,
                "shared_scratchpad": {"generator_action": "improve"},
            }
        )
        result = _route_to_generator(state)
        assert result["current_subtask"] == "draft_refiner"

    def test_requisitos_routes_to_ears(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(update={"phase": SpecPhase.REQUISITOS})
        result = _route_to_generator(state)
        assert result["current_subtask"] == "ears_generator"

    def test_modelo_unimplemented_returns_done(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(update={"phase": SpecPhase.MODELO})
        result = _route_to_generator(state)
        assert result["supervisor_stage"] == SupervisorStage.DONE
        assert result["human_input_pending"] is True

    def test_implementacion_unimplemented_returns_done(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(update={"phase": SpecPhase.IMPLEMENTACION})
        result = _route_to_generator(state)
        assert result["supervisor_stage"] == SupervisorStage.DONE


@pytest.mark.unit
class TestRouteAfterCriticEvaluator:
    def test_needs_revision_within_limit_returns_generator(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "critic_verdict": "needs_revision",
                "critic_iteration": 1,
                "max_critic_iterations": 3,
                "current_subtask": "features_generator",
            }
        )
        result = route_after_critic_evaluator(state)
        assert result == "features_generator"

    def test_needs_revision_fallback_to_discovery(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "critic_verdict": "needs_revision",
                "critic_iteration": 0,
                "max_critic_iterations": 3,
                "current_subtask": None,
            }
        )
        result = route_after_critic_evaluator(state)
        assert result == "discovery_generator"

    def test_exceeds_max_critic_iterations_goes_to_final(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "critic_verdict": "needs_revision",
                "critic_iteration": 3,
                "max_critic_iterations": 3,
            }
        )
        result = route_after_critic_evaluator(state)
        assert result == "final_evaluator"

    def test_approved_goes_to_final_evaluator(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(update={"critic_verdict": "approved"})
        result = route_after_critic_evaluator(state)
        assert result == "final_evaluator"


@pytest.mark.unit
class TestRouteAfterSupervisor:
    def test_human_input_pending_returns_end(self, kosmo_state: KOSMOState) -> None:
        from langgraph.graph import END

        state = kosmo_state.model_copy(update={"human_input_pending": True})
        result = route_after_supervisor(state)
        assert result == END

    def test_context_returns_parallel_sends(self, kosmo_state: KOSMOState) -> None:
        from langgraph.types import Send

        state = kosmo_state.model_copy(update={"supervisor_stage": SupervisorStage.CONTEXT})
        result = route_after_supervisor(state)
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(s, Send) for s in result)
        destinations = {s.node for s in result}
        assert destinations == {"context_analyzer", "goal_planner", "preference_retriever"}

    def test_generate_returns_current_subtask(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "supervisor_stage": SupervisorStage.GENERATE,
                "current_subtask": "features_generator",
            }
        )
        result = route_after_supervisor(state)
        assert result == "features_generator"

    def test_generate_fallback_when_no_subtask(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "supervisor_stage": SupervisorStage.GENERATE,
                "current_subtask": None,
            }
        )
        result = route_after_supervisor(state)
        assert result == "discovery_generator"

    def test_evaluate_returns_final_evaluator(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(update={"supervisor_stage": SupervisorStage.EVALUATE})
        result = route_after_supervisor(state)
        assert result == "final_evaluator"

    def test_done_returns_end(self, kosmo_state: KOSMOState) -> None:
        from langgraph.graph import END

        state = kosmo_state.model_copy(update={"supervisor_stage": SupervisorStage.DONE})
        result = route_after_supervisor(state)
        assert result == END


@pytest.mark.unit
class TestCompressContext:
    def test_should_compress_empty_state_is_false(self, kosmo_state: KOSMOState) -> None:
        from kosmo.domain.agents.context_compressor import should_compress

        assert should_compress(kosmo_state) is False

    def test_estimate_tokens_approximates_four_chars_per_token(self) -> None:
        from kosmo.domain.agents.context_compressor import estimate_tokens

        assert estimate_tokens("hello world") == 2  # 11 chars / 4 = 2
        assert estimate_tokens("") == 1  # min 1
