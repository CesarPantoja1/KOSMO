from __future__ import annotations

from kosmo.contracts.sdd.state import CritiqueRecord, KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced


@traced("critic_merger.execute")
async def critic_merger_node(state: KOSMOState) -> dict[str, object]:
    """Consolida los outputs de los 3 criticos paralelos en una CritiqueRecord unificada.

    Deduplica hallazgos overlapeados, prioriza por severidad, y correlaciona
    findings entre criticos para producir recomendaciones compuestas.
    Si algun critico no produjo output, se ignora gracefully.

    Reads: agent_outputs (quality_critic, style_critic, consistency_critic)
    Writes: critique_log, critic_verdict, validation_status
    """
    merged_severity = "none"
    merged_findings: list[str] = []
    merged_messages: list[str] = []
    critic_severities: dict[str, str] = {}

    critic_names = ["quality_critic", "style_critic", "consistency_critic"]

    for name in critic_names:
        output = state.agent_outputs.get(name)
        if not isinstance(output, dict):
            continue

        severity = str(output.get("severity", "none"))
        message = str(output.get("message", ""))
        critic_severities[name] = severity

        if severity == "blocker":
            merged_severity = "blocker"
        elif severity == "warning" and merged_severity != "blocker":
            merged_severity = "warning"

        if message:
            merged_messages.append(f"[{name}] {message}")

        findings = output.get("findings", [])
        if isinstance(findings, list):
            for f in findings:
                if f is not None:
                    f_str = str(f)
                    if f_str not in merged_findings:
                        merged_findings.append(f_str)

    blocker_count = sum(1 for s in critic_severities.values() if s == "blocker")
    warning_count = sum(1 for s in critic_severities.values() if s == "warning")
    correlation = ""
    if blocker_count >= 2:
        correlation = " [CORRELACION: multiples criticos detectaron bloqueos — revision prioritaria requerida]"
    elif blocker_count == 1 and warning_count >= 1:
        correlation = " [CORRELACION: un critico bloqueo y otro advirtio — verificar ambos aspectos]"
    elif warning_count >= 2:
        correlation = " [CORRELACION: multiples criticos emitieron advertencias — mejora recomendada]"

    if merged_severity == "blocker":
        verdict = "needs_revision"
    elif merged_severity == "warning":
        verdict = "needs_revision"
    else:
        verdict = "approved"

    merged_message = "; ".join(merged_messages) if merged_messages else "All critics approved"
    merged_message += correlation

    records = list(state.tool_call_history)
    records.append(
        ToolCallRecord(
            agent_id="critic_merger",
            tool_name="merge_critics",
            params={
                "critics_processed": len(
                    [n for n in critic_names if isinstance(state.agent_outputs.get(n), dict)]
                )
            },
            result=verdict,
        )
    )

    return {
        "critique_log": [
            CritiqueRecord(
                agent_id="critic_merger",
                severity=merged_severity,
                message=merged_message[:500],
            )
        ],
        "critic_verdict": verdict,
        "validation_status": verdict,
        "tool_call_history": records,
    }
