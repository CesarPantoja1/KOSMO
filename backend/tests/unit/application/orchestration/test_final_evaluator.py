from __future__ import annotations

import json

import pytest

from kosmo.application.orchestration.nodes.final_evaluator import final_evaluator_node
from kosmo.contracts.orchestration.graph_deps import GraphDependencies
from kosmo.contracts.sdd.state import KOSMOState, SupervisorStage

_APPROVED = json.dumps(
    {
        "completeness": 8,
        "correctness": 9,
        "style_consistency": 7,
        "user_preferences": 8,
        "blockers": [],
        "overall_verdict": "approved",
        "summary": "Todo correcto",
    }
)

_NEEDS_REVISION = json.dumps(
    {
        "completeness": 3,
        "correctness": 5,
        "style_consistency": 6,
        "user_preferences": 5,
        "blockers": ["Faltan secciones requeridas"],
        "overall_verdict": "needs_revision",
        "summary": "Incompleto",
    }
)


@pytest.mark.unit
class TestFinalEvaluator:
    async def test_approved_output_ready(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_response(_APPROVED)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {"generated_document_md": "content"},
            }
        )
        result = await final_evaluator_node(state)
        assert result["output_ready"] is True
        assert result["validation_status"] == "approved"
        assert result["generation_attempts"] == 0
        assert result["critic_iteration"] == 0

    async def test_needs_revision_under_max_retries(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_response(_NEEDS_REVISION)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {"generated_document_md": "content"},
                "generation_attempts": 2,
                "max_iterations": 10,
            }
        )
        result = await final_evaluator_node(state)
        assert result["output_ready"] is False
        assert result["validation_status"] == "needs_revision"
        assert result["generation_attempts"] == 3
        assert result["supervisor_stage"] == SupervisorStage.EVALUATE

    async def test_no_deps_skips(self, kosmo_state: KOSMOState) -> None:
        result = await final_evaluator_node(kosmo_state)
        assert result["output_ready"] is False
        assert result["validation_status"] == "needs_revision"

    async def test_llm_failure_graceful(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_failure()
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {"generated_document_md": "content"},
            }
        )
        result = await final_evaluator_node(state)
        assert result["validation_status"] == "needs_revision"

    async def test_resets_generation_attempts_on_approval(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_response(_APPROVED)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {"generated_document_md": "content"},
                "generation_attempts": 5,
            }
        )
        result = await final_evaluator_node(state)
        assert result["generation_attempts"] == 0


@pytest.mark.unit
class TestFinalEvaluatorCritiqueLog:
    async def test_appends_to_critique_log_on_approval(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_response(_APPROVED)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {"generated_document_md": "content"},
            }
        )
        result = await final_evaluator_node(state)
        assert len(result["critique_log"]) == 1
        assert result["critique_log"][0].agent_id == "final_evaluator"

    async def test_appends_to_critique_log_on_revision(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_response(_NEEDS_REVISION)
        state = kosmo_state.model_copy(
            update={
                "graph_deps": graph_deps,
                "shared_scratchpad": {"generated_document_md": "content"},
                "generation_attempts": 0,
                "max_iterations": 10,
            }
        )
        result = await final_evaluator_node(state)
        assert len(result["critique_log"]) == 1
        assert result["critique_log"][0].severity == "blocker"


@pytest.mark.unit
class TestRouteAfterEvaluator:
    def test_not_ready_returns_supervisor(self) -> None:
        from kosmo.application.orchestration.kosmo_graph import route_after_evaluator

        state = KOSMOState(
            project_id="prj_01",
            user_id="usr_01",
            output_ready=False,
            validation_status="needs_revision",
        )
        assert route_after_evaluator(state) == "supervisor"

    def test_ready_returns_end(self) -> None:
        from langgraph.graph import END

        from kosmo.application.orchestration.kosmo_graph import route_after_evaluator

        state = KOSMOState(
            project_id="prj_01",
            user_id="usr_01",
            output_ready=True,
        )
        assert route_after_evaluator(state) == END

    def test_rejected_returns_end(self) -> None:
        from langgraph.graph import END

        from kosmo.application.orchestration.kosmo_graph import route_after_evaluator

        state = KOSMOState(
            project_id="prj_01",
            user_id="usr_01",
            output_ready=False,
            validation_status="rejected",
        )
        assert route_after_evaluator(state) == END
