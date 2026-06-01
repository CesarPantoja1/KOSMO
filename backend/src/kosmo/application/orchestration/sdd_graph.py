from typing import Any

from langgraph.graph import END, StateGraph

from kosmo.contracts.sdd.spec import SpecPhase
from kosmo.contracts.sdd.state import SDDState


def build_sdd_graph(
    capture_node: Any,
    analyze_node: Any,
    design_node: Any,
    plan_node: Any,
) -> StateGraph:
    builder = StateGraph(SDDState)

    builder.add_node("spec_capture", capture_node)
    builder.add_node("analyzer", analyze_node)
    builder.add_node("architect", design_node)
    builder.add_node("planner", plan_node)

    builder.set_entry_point("spec_capture")
    builder.add_edge("spec_capture", "analyzer")
    builder.add_edge("analyzer", "architect")
    builder.add_edge("architect", "planner")
    builder.add_edge("planner", END)

    return builder


def create_capture_node(_capture_uc: object) -> object:
    async def node(_state: SDDState) -> dict[str, object]:
        return {"phase": SpecPhase.CARACTERISTICAS, "errors": []}

    return node


def create_analyze_node(_requirements_uc: object) -> object:
    async def node(_state: SDDState) -> dict[str, object]:
        return {"phase": SpecPhase.REQUISITOS, "errors": []}

    return node


def create_design_node(_design_uc: object) -> object:
    async def node(_state: SDDState) -> dict[str, object]:
        return {"phase": SpecPhase.MODELO, "errors": []}

    return node


def create_plan_node(_tasks_uc: object) -> object:
    async def node(_state: SDDState) -> dict[str, object]:
        return {"phase": SpecPhase.PROTOTIPO, "errors": []}

    return node
