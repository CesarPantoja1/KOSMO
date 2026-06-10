from __future__ import annotations

import json

import pytest

from kosmo.application.orchestration.nodes.context_analyzer import context_analyzer_node
from kosmo.application.orchestration.nodes.context_merger import context_merger_node
from kosmo.application.orchestration.nodes.goal_planner import goal_planner_node
from kosmo.application.orchestration.nodes.preference_retriever import preference_retriever_node
from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.orchestration.graph_deps import GraphDependencies
from kosmo.contracts.sdd.state import KOSMOState

_ANALYSIS_JSON = json.dumps(
    {
        "domain": "ecommerce",
        "key_entities": ["product", "order"],
        "complexity_level": "medium",
        "gaps_identified": ["payment integration"],
        "recommended_focus": "inventory management",
        "context_brief": "SaaS platform for inventory",
    }
)

_GOALS_JSON = json.dumps(
    {
        "sub_goals": ["Define product catalog", "Design inventory workflow"],
        "success_criteria": ["Catalog has >= 10 fields"],
        "dependencies": [],
        "parallelizable_tasks": ["UI design", "API spec"],
        "estimated_sections": 5,
    }
)


@pytest.mark.unit
class TestContextAnalyzer:
    async def test_extracts_domain(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_response(_ANALYSIS_JSON)
        state = kosmo_state.model_copy(update={"graph_deps": graph_deps})
        result = await context_analyzer_node(state)
        output = result["agent_outputs"]["context_analyzer"]
        assert output["domain"] == "ecommerce"

    async def test_no_deps_empty(self, kosmo_state: KOSMOState) -> None:
        result = await context_analyzer_node(kosmo_state)
        assert result["agent_outputs"]["context_analyzer"] == {}

    async def test_llm_failure_graceful(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_failure()
        state = kosmo_state.model_copy(update={"graph_deps": graph_deps})
        result = await context_analyzer_node(state)
        assert result["agent_outputs"]["context_analyzer"] == {}
        assert "errors" in result


@pytest.mark.unit
class TestGoalPlanner:
    async def test_decomposes_phase(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_response(_GOALS_JSON)
        state = kosmo_state.model_copy(update={"graph_deps": graph_deps})
        result = await goal_planner_node(state)
        output = result["agent_outputs"]["goal_planner"]
        assert "sub_goals" in output

    async def test_no_deps_empty(self, kosmo_state: KOSMOState) -> None:
        result = await goal_planner_node(kosmo_state)
        assert result["agent_outputs"]["goal_planner"] == {}

    async def test_llm_failure_graceful(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        graph_deps.llm_client.set_failure()
        state = kosmo_state.model_copy(update={"graph_deps": graph_deps})
        result = await goal_planner_node(state)
        assert result["agent_outputs"]["goal_planner"] == {}
        assert "errors" in result


@pytest.mark.unit
class TestContextMerger:
    async def test_consolidates_all_outputs(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "agent_outputs": {
                    "context_analyzer": {"domain": "test"},
                    "goal_planner": {"sub_goals": ["goal1"]},
                    "preference_retriever": {"preferences_prompt": "Use lists"},
                },
            }
        )
        result = await context_merger_node(state)
        scratchpad = result["shared_scratchpad"]
        assert scratchpad["context_analyzer_output"]["domain"] == "test"
        assert scratchpad["goal_planner_output"]["sub_goals"] == ["goal1"]
        assert scratchpad["preference_retriever_output"]["preferences_prompt"] == "Use lists"

    async def test_preserves_existing_scratchpad(self, kosmo_state: KOSMOState) -> None:
        state = kosmo_state.model_copy(
            update={
                "agent_outputs": {"context_analyzer": {"domain": "test"}},
                "shared_scratchpad": {"existing_key": "existing_value"},
            }
        )
        result = await context_merger_node(state)
        assert result["shared_scratchpad"]["existing_key"] == "existing_value"


@pytest.mark.unit
class TestPreferenceRetriever:
    async def test_no_prefs_ok(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        state = kosmo_state.model_copy(update={"graph_deps": graph_deps})
        result = await preference_retriever_node(state)
        output = result["agent_outputs"]["preference_retriever"]
        assert output["preferences_prompt"] == ""

    async def test_fetches_and_formats_preferences(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        pref = UserPreference(
            id="pref_01",
            user_id="usr_test01",
            project_id="prj_test01",
            document_type="discovery",
            rule_text="Prefiere listas numeradas en lugar de parrafos",
        )
        await graph_deps.preference_repo.add(pref)
        state = kosmo_state.model_copy(update={"graph_deps": graph_deps})
        result = await preference_retriever_node(state)
        output = result["agent_outputs"]["preference_retriever"]
        assert "Prefiere listas" in output["preferences_prompt"]
        assert "1." in output["preferences_prompt"]

    async def test_filters_by_project_id(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        pref_a = UserPreference(
            id="pref_a",
            user_id="usr_test01",
            project_id="prj_test01",
            document_type="discovery",
            rule_text="Rule for project A",
        )
        pref_b = UserPreference(
            id="pref_b",
            user_id="usr_test01",
            project_id="prj_other",
            document_type="discovery",
            rule_text="Rule for project B",
        )
        await graph_deps.preference_repo.add(pref_a)
        await graph_deps.preference_repo.add(pref_b)
        state = kosmo_state.model_copy(update={"graph_deps": graph_deps})
        result = await preference_retriever_node(state)
        output = result["agent_outputs"]["preference_retriever"]
        assert "Rule for project A" in output["preferences_prompt"]
        assert "Rule for project B" not in output["preferences_prompt"]

    async def test_increments_usage(
        self, graph_deps: GraphDependencies, kosmo_state: KOSMOState
    ) -> None:
        pref = UserPreference(
            id="pref_usage",
            user_id="usr_test01",
            project_id="prj_test01",
            document_type="discovery",
            rule_text="Test rule",
        )
        await graph_deps.preference_repo.add(pref)
        state = kosmo_state.model_copy(update={"graph_deps": graph_deps})
        await preference_retriever_node(state)
        assert graph_deps.preference_repo._usage_counts.get("pref_usage") == 1

    async def test_no_deps_still_works(self, kosmo_state: KOSMOState) -> None:
        result = await preference_retriever_node(kosmo_state)
        output = result["agent_outputs"]["preference_retriever"]
        assert output["preferences_prompt"] == ""


@pytest.mark.unit
class TestNoopResult:
    def test_noop_result_returns_needs_revision(self) -> None:
        from kosmo.application.orchestration.helpers import noop_result

        result = noop_result()
        assert result["validation_status"] == "needs_revision"

    def test_noop_result_custom_errors(self) -> None:
        from kosmo.application.orchestration.helpers import noop_result

        result = noop_result(["Custom error"])
        assert "Custom error" in result["errors"]
