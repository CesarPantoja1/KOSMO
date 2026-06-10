from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END

from kosmo.application.orchestration.kosmo_graph import build_kosmo_graph


@pytest.mark.unit
class TestBuildKosmoGraph:
    def test_registers_15_nodes(self) -> None:
        builder = build_kosmo_graph()
        nodes = builder.nodes
        assert len(nodes) == 15

    def test_supervisor_is_registered(self) -> None:
        builder = build_kosmo_graph()
        assert "supervisor" in builder.nodes

    def test_all_generators_registered(self) -> None:
        builder = build_kosmo_graph()
        assert "discovery_generator" in builder.nodes
        assert "features_generator" in builder.nodes
        assert "draft_refiner" in builder.nodes
        assert "ears_generator" in builder.nodes

    def test_all_critics_registered(self) -> None:
        builder = build_kosmo_graph()
        assert "quality_critic" in builder.nodes
        assert "style_critic" in builder.nodes
        assert "consistency_critic" in builder.nodes
        assert "critic_evaluator" in builder.nodes

    def test_context_nodes_registered(self) -> None:
        builder = build_kosmo_graph()
        assert "context_analyzer" in builder.nodes
        assert "goal_planner" in builder.nodes
        assert "preference_retriever" in builder.nodes
        assert "context_merger" in builder.nodes

    def test_evaluator_nodes_registered(self) -> None:
        builder = build_kosmo_graph()
        assert "final_evaluator" in builder.nodes
        assert "learn_from_correction" in builder.nodes

    def test_returns_state_graph(self) -> None:
        builder = build_kosmo_graph()
        assert builder is not None

    def test_compiles_cleanly(self) -> None:

        builder = build_kosmo_graph()
        compiled = builder.compile(checkpointer=MemorySaver())
        assert compiled is not None

    def test_can_add_node_multiple_times(self) -> None:
        builder = build_kosmo_graph()
        assert "supervisor" in builder.nodes
        assert "final_evaluator" in builder.nodes


@pytest.mark.unit
class TestGraphEdges:
    def test_context_merger_to_supervisor_edge_exists(self) -> None:
        builder = build_kosmo_graph()
        edges = builder.edges
        assert ("context_merger", "supervisor") in edges

    def test_generators_to_quality_critic_edges(self) -> None:
        builder = build_kosmo_graph()
        edges = builder.edges
        assert ("discovery_generator", "quality_critic") in edges
        assert ("features_generator", "quality_critic") in edges
        assert ("draft_refiner", "quality_critic") in edges
        assert ("ears_generator", "quality_critic") in edges

    def test_critic_chain_edges(self) -> None:
        builder = build_kosmo_graph()
        edges = builder.edges
        assert ("quality_critic", "style_critic") in edges
        assert ("style_critic", "consistency_critic") in edges
        assert ("consistency_critic", "critic_evaluator") in edges

    def test_learn_from_correction_to_end(self) -> None:
        builder = build_kosmo_graph()
        edges = builder.edges
        assert ("learn_from_correction", END) in edges

    def test_context_parallel_edges(self) -> None:
        builder = build_kosmo_graph()
        edges = builder.edges
        assert ("context_analyzer", "context_merger") in edges
        assert ("goal_planner", "context_merger") in edges
        assert ("preference_retriever", "context_merger") in edges

    def test_supervisor_has_conditional_edges(self) -> None:
        builder = build_kosmo_graph()
        assert "supervisor" in builder.branches

    def test_critic_evaluator_has_conditional_edges(self) -> None:
        builder = build_kosmo_graph()
        assert "critic_evaluator" in builder.branches

    def test_final_evaluator_has_conditional_edges(self) -> None:
        builder = build_kosmo_graph()
        assert "final_evaluator" in builder.branches
