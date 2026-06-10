from __future__ import annotations

from kosmo.application.orchestration.helpers import verify_scope
from kosmo.contracts.sdd.state import CritiqueRecord, KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced


@traced("critic_evaluator.execute")
async def critic_evaluator_node(state: KOSMOState) -> dict[str, object]:
    """Gate obligatorio post-criticos. Decide reenviar a generador o pasar a evaluador final.

    Reads: critique_log, critic_iteration, max_critic_iterations
    Writes: critic_verdict, critic_iteration, validation_status
    """
    verify_scope(state)

    recent = _last_three_critiques(state.critique_log)
    records = list(state.tool_call_history)

    blocked = [c for c in recent if c.severity == "blocker"]
    warnings = [c for c in recent if c.severity == "warning"]
    iteration = state.critic_iteration + 1

    if blocked:
        return _handle_blocked(blocked, iteration, records)
    if warnings and iteration < state.max_critic_iterations:
        return _handle_warnings(warnings, iteration, records)
    return _handle_approved(records)


def _last_three_critiques(log: list[CritiqueRecord]) -> list[CritiqueRecord]:
    return log[-3:] if len(log) >= 3 else log


def _handle_blocked(
    blocked: list[CritiqueRecord], iteration: int, records: list[ToolCallRecord]
) -> dict[str, object]:
    messages = "; ".join(c.message for c in blocked)
    feedback = _build_structured_feedback(blocked)
    records.append(
        ToolCallRecord(
            agent_id="critic_evaluator",
            tool_name="critic_gate",
            params={"verdict": "blocked", "blockers": len(blocked)},
            result="needs_revision",
        )
    )
    return {
        "critic_verdict": "needs_revision",
        "critic_iteration": iteration,
        "validation_status": "needs_revision",
        "critique_log": [
            CritiqueRecord(
                agent_id="critic_evaluator",
                severity="blocker",
                message=f"Criticos bloquearon la salida: {messages[:500]}. {feedback}",
            )
        ],
        "tool_call_history": records,
        "errors": [f"Critic evaluator blocked: {messages[:200]}"],
    }


def _handle_warnings(
    warnings: list[CritiqueRecord],
    iteration: int,
    records: list[ToolCallRecord],
) -> dict[str, object]:
    messages = "; ".join(c.message for c in warnings)
    feedback = _build_structured_feedback(warnings)
    records.append(
        ToolCallRecord(
            agent_id="critic_evaluator",
            tool_name="critic_gate",
            params={"verdict": "warning", "iteration": iteration},
            result="needs_revision",
        )
    )
    return {
        "critic_verdict": "needs_revision",
        "critic_iteration": iteration,
        "validation_status": "needs_revision",
        "critique_log": [
            CritiqueRecord(
                agent_id="critic_evaluator",
                severity="warning",
                message=f"Reenvio a generador (iter {iteration}): {messages[:500]}. {feedback}",
            )
        ],
        "tool_call_history": records,
    }


def _handle_approved(records: list[ToolCallRecord]) -> dict[str, object]:
    records.append(
        ToolCallRecord(
            agent_id="critic_evaluator",
            tool_name="critic_gate",
            params={"verdict": "approved"},
            result="approved",
        )
    )
    return {
        "critic_verdict": "approved",
        "critic_iteration": 0,
        "validation_status": "approved",
        "critique_log": [
            CritiqueRecord(
                agent_id="critic_evaluator",
                severity="none",
                message="Todos los criticos aprobaron los requisitos EARS",
            )
        ],
        "tool_call_history": records,
    }


def _build_structured_feedback(critiques: list[CritiqueRecord]) -> str:
    agent_messages: dict[str, list[str]] = {}
    for c in critiques:
        agent_messages.setdefault(c.agent_id, []).append(c.message)

    parts: list[str] = []
    for agent_id, messages in agent_messages.items():
        agent_label = {
            "quality_critic": "Calidad EARS",
            "style_critic": "Estilo EARS",
            "consistency_critic": "Consistencia",
        }.get(agent_id, agent_id)
        parts.append(f"[{agent_label}]: {'; '.join(messages)}")

    feedback = " | ".join(parts)
    return f"FEEDBACK_ESTRUCTURADO: {feedback[:300]}"
