from __future__ import annotations

import structlog

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import get_deps, verify_scope
from kosmo.contracts.sdd.state import KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced


@traced("preference_retriever.execute")
async def preference_retriever_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    """Recupera preferencias del usuario desde BD y las formatea para inyeccion en prompts.

    Reads: graph_deps, user_id, project_id
    Writes: agent_outputs["preference_retriever"], tool_call_history
    """
    verify_scope(state)

    deps = get_deps(config)
    records = list(state.tool_call_history)
    log = structlog.get_logger()
    preferences_text = ""
    retrieval_error: str | None = None

    if deps.preference_repo:
        try:
            prefs = await deps.preference_repo.get_by_user(
                user_id=state.user_id,
                project_id=state.project_id,
                limit=20,
            )

            if prefs:
                lines = ["## Preferencias del Usuario (aprendidas de correcciones anteriores)"]
                for i, p in enumerate(prefs, 1):
                    lines.append(f"{i}. {p.rule_text}")
                lines.append("")
                lines.append(
                    "Aplica estas preferencias al generar contenido. "
                    "Si dos entran en conflicto, prioriza la mas reciente."
                )
                preferences_text = "\n".join(lines)

                for p in prefs:
                    await deps.preference_repo.increment_usage([p.id])

        except Exception:
            retrieval_error = "Failed to retrieve user preferences"
            log.warning(
                "preference_retriever.error",
                user_id=state.user_id,
                project_id=state.project_id,
                exc_info=True,
            )

    records.append(
        ToolCallRecord(
            agent_id="preference_retriever",
            tool_name="db_read",
            params={"action": "get_preferences"},
            result="found" if preferences_text else "empty",
            error=retrieval_error,
        )
    )

    result: dict[str, object] = {
        "agent_outputs": {
            **state.agent_outputs,
            "preference_retriever": {
                "preferences_prompt": preferences_text,
                "retrieval_error": retrieval_error,
            },
        },
        "tool_call_history": records,
    }

    if retrieval_error:
        result["errors"] = [retrieval_error]

    return result
