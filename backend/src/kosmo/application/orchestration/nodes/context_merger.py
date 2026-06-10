from __future__ import annotations

from kosmo.application.orchestration.helpers import verify_scope
from kosmo.contracts.sdd.state import KOSMOState
from kosmo.contracts.telemetry import traced


@traced("context_merger.execute")
async def context_merger_node(state: KOSMOState) -> dict[str, object]:
    """Consolida outputs de analyzer, planner y retriever en shared_scratchpad.

    Politica de resolucion de conflictos (merge determinista):
    - Los outputs se mergean en orden: context_analyzer -> goal_planner -> preference_retriever.
    - Si dos outputs contienen la misma clave, el ultimo en el orden prevalece.
    - Esto garantiza que las preferencias del usuario (preference_retriever) tengan
      maxima prioridad, seguidas por los objetivos (goal_planner), y finalmente
      el contexto base (context_analyzer).

    Reads: agent_outputs, shared_scratchpad
    Writes: shared_scratchpad
    """
    verify_scope(state)

    outputs = state.agent_outputs

    return {
        "shared_scratchpad": {
            **state.shared_scratchpad,
            "context_analyzer_output": outputs.get("context_analyzer", {}),
            "goal_planner_output": outputs.get("goal_planner", {}),
            "preference_retriever_output": outputs.get("preference_retriever", {}),
        },
    }
