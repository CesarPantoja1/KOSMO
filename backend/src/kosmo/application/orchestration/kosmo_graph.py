from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.types import Send

from kosmo.application.orchestration.nodes.context_analyzer import (
    context_analyzer_node,
)
from kosmo.application.orchestration.nodes.context_merger import context_merger_node
from kosmo.application.orchestration.nodes.critic_evaluator import critic_evaluator_node
from kosmo.application.orchestration.nodes.critic_merger import critic_merger_node
from kosmo.application.orchestration.nodes.critics import (
    consistency_critic_node,
    quality_critic_node,
    style_critic_node,
)
from kosmo.application.orchestration.nodes.discovery_generator import (
    discovery_generator_node,
)
from kosmo.application.orchestration.nodes.draft_refiner import draft_refiner_node
from kosmo.application.orchestration.nodes.ears_generator import ears_generator_node
from kosmo.application.orchestration.nodes.features_generator import (
    features_generator_node,
)
from kosmo.application.orchestration.nodes.final_evaluator import final_evaluator_node
from kosmo.application.orchestration.nodes.goal_planner import goal_planner_node
from kosmo.application.orchestration.nodes.learn_from_correction import (
    learn_from_correction_node,
)
from kosmo.application.orchestration.nodes.preference_feedback import (
    preference_feedback_node,
)
from kosmo.application.orchestration.nodes.preference_retriever import (
    preference_retriever_node,
)
from kosmo.application.orchestration.nodes.supervisor import (
    route_after_critic_evaluator,
    supervisor_node,
)
from kosmo.contracts.sdd.state import KOSMOState, SupervisorStage


def route_after_supervisor(state: KOSMOState) -> list[Send] | str:
    """Rutea desde supervisor: paralelo (Send) en CONTEXT, string en otros stages."""
    if state.human_input_pending:
        return END

    stage = state.supervisor_stage
    if stage == SupervisorStage.CONTEXT:
        return [
            Send("context_analyzer", {}),
            Send("goal_planner", {}),
            Send("preference_retriever", {}),
        ]
    if stage == SupervisorStage.GENERATE:
        return state.current_subtask or "discovery_generator"
    if stage == SupervisorStage.EVALUATE:
        return "final_evaluator"
    return END


def route_after_evaluator(state: KOSMOState) -> str:
    return END


def build_kosmo_graph() -> StateGraph:  # type: ignore[no-any-unimported]
    builder = StateGraph(KOSMOState)

    builder.add_node("supervisor", supervisor_node)

    builder.add_node("context_analyzer", context_analyzer_node)
    builder.add_node("goal_planner", goal_planner_node)
    builder.add_node("preference_retriever", preference_retriever_node)
    builder.add_node("context_merger", context_merger_node)

    builder.add_node("discovery_generator", discovery_generator_node)
    builder.add_node("features_generator", features_generator_node)
    builder.add_node("draft_refiner", draft_refiner_node)
    builder.add_node("ears_generator", ears_generator_node)

    builder.add_node("quality_critic", quality_critic_node)
    builder.add_node("style_critic", style_critic_node)
    builder.add_node("consistency_critic", consistency_critic_node)
    builder.add_node("critic_merger", critic_merger_node)
    builder.add_node("critic_evaluator", critic_evaluator_node)

    builder.add_node("final_evaluator", final_evaluator_node)
    builder.add_node("preference_feedback", preference_feedback_node)
    builder.add_node("learn_from_correction", learn_from_correction_node)

    builder.set_entry_point("supervisor")

    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "context_analyzer": "context_analyzer",
            "goal_planner": "goal_planner",
            "preference_retriever": "preference_retriever",
            "discovery_generator": "discovery_generator",
            "features_generator": "features_generator",
            "draft_refiner": "draft_refiner",
            "ears_generator": "ears_generator",
            "final_evaluator": "final_evaluator",
            END: END,
        },
    )

    builder.add_edge("context_analyzer", "context_merger")
    builder.add_edge("goal_planner", "context_merger")
    builder.add_edge("preference_retriever", "context_merger")
    builder.add_edge("context_merger", "supervisor")

    builder.add_edge("discovery_generator", "quality_critic")
    builder.add_edge("discovery_generator", "style_critic")
    builder.add_edge("discovery_generator", "consistency_critic")
    builder.add_edge("features_generator", "quality_critic")
    builder.add_edge("features_generator", "style_critic")
    builder.add_edge("features_generator", "consistency_critic")
    builder.add_edge("draft_refiner", "quality_critic")
    builder.add_edge("draft_refiner", "style_critic")
    builder.add_edge("draft_refiner", "consistency_critic")
    builder.add_edge("ears_generator", "quality_critic")
    builder.add_edge("ears_generator", "style_critic")
    builder.add_edge("ears_generator", "consistency_critic")

    builder.add_edge("quality_critic", "critic_merger")
    builder.add_edge("style_critic", "critic_merger")
    builder.add_edge("consistency_critic", "critic_merger")

    builder.add_edge("critic_merger", "critic_evaluator")

    builder.add_conditional_edges(
        "critic_evaluator",
        route_after_critic_evaluator,
        {
            "discovery_generator": "discovery_generator",
            "features_generator": "features_generator",
            "draft_refiner": "draft_refiner",
            "ears_generator": "ears_generator",
            "final_evaluator": "final_evaluator",
        },
    )

    builder.add_conditional_edges(
        "final_evaluator",
        route_after_evaluator,
        {
            "supervisor": "supervisor",
            END: "preference_feedback",
        },
    )

    builder.add_edge("preference_feedback", "learn_from_correction")
    builder.add_edge("learn_from_correction", END)

    return builder
