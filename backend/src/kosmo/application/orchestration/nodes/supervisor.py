from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import get_deps, verify_scope
from kosmo.contracts.sdd.spec import SpecPhase
from kosmo.contracts.sdd.state import KOSMOState, SupervisorStage
from kosmo.contracts.telemetry import traced
from kosmo.domain.agents.context_compressor import compress_context, should_compress


@traced("supervisor.execute")
async def supervisor_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    """Orquestador principal. Stage machine: CONTEXT -> GENERATE -> EVALUATE -> DONE.

    Reads: supervisor_stage, generation_attempts, max_iterations, phase,
           shared_scratchpad, human_input_pending
    Writes: supervisor_stage, human_input_pending, human_prompt,
            current_subtask, output_ready, errors
    """
    verify_scope(state)

    if state.human_input_pending:
        return {
            "human_input_pending": True,
            "human_prompt": state.human_prompt,
            "output_ready": False,
        }

    if state.generation_attempts >= state.max_iterations:
        return {
            "supervisor_stage": SupervisorStage.DONE,
            "human_input_pending": True,
            "human_prompt": (
                f"Maximo de intentos ({state.max_iterations}) alcanzado. Revision manual requerida."
            ),
            "errors": [f"Pipeline exceeded max_iterations ({state.max_iterations})"],
        }

    stage = state.supervisor_stage
    if stage == SupervisorStage.CONTEXT:
        return await _dispatch_context(state, config)
    if stage == SupervisorStage.GENERATE:
        return _route_to_generator(state)
    if stage == SupervisorStage.EVALUATE:
        return _handle_evaluation(state)

    return {"output_ready": True}


async def _dispatch_context(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    result: dict[str, object] = {"supervisor_stage": SupervisorStage.GENERATE}

    action = state.shared_scratchpad.get("generator_action", "generate")
    if action == "improve":
        result["current_subtask"] = "draft_refiner"
    elif state.phase == SpecPhase.DESCUBRIMIENTO:
        result["current_subtask"] = "discovery_generator"
    elif state.phase == SpecPhase.CARACTERISTICAS:
        result["current_subtask"] = "features_generator"
    elif state.phase == SpecPhase.REQUISITOS:
        result["current_subtask"] = "ears_generator"

    deps = get_deps(config)
    if should_compress(state):
        summary = await compress_context(state, deps.llm_client)
        if summary:
            result["shared_scratchpad"] = {
                **state.shared_scratchpad,
                "context_summary": summary,
            }

    return result


def _route_to_generator(state: KOSMOState) -> dict[str, object]:
    phase = state.phase
    scratchpad = dict(state.shared_scratchpad)
    action = scratchpad.get("generator_action", "generate")

    if phase == SpecPhase.DESCUBRIMIENTO:
        gen_node = "discovery_generator"
    elif phase == SpecPhase.CARACTERISTICAS:
        gen_node = "draft_refiner" if action == "improve" else "features_generator"
    elif phase == SpecPhase.REQUISITOS:
        gen_node = "ears_generator"
    elif phase in (SpecPhase.MODELO, SpecPhase.IMPLEMENTACION):
        return {
            "shared_scratchpad": scratchpad,
            "current_subtask": None,
            "supervisor_stage": SupervisorStage.DONE,
            "errors": [f"Fase {phase.value} no implementada en el pipeline actual"],
            "human_input_pending": True,
            "human_prompt": f"La fase {phase.value} requiere implementacion manual.",
        }
    else:
        return {
            "errors": [f"Fase desconocida: {phase}"],
            "supervisor_stage": SupervisorStage.DONE,
        }

    return {
        "shared_scratchpad": scratchpad,
        "current_subtask": gen_node,
        "supervisor_stage": SupervisorStage.GENERATE,
    }


def _handle_evaluation(state: KOSMOState) -> dict[str, object]:
    return {"supervisor_stage": SupervisorStage.DONE}


def route_after_critic_evaluator(state: KOSMOState) -> str:
    if (
        state.critic_verdict == "needs_revision"
        and state.critic_iteration < state.max_critic_iterations
    ):
        return state.current_subtask or "discovery_generator"
    return "final_evaluator"
