from __future__ import annotations

import structlog

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import get_deps, verify_scope
from kosmo.contracts.sdd.state import KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced


@traced("preference_feedback.execute")
async def preference_feedback_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    verify_scope(state)

    deps = get_deps(config)
    records = list(state.tool_call_history)
    log = structlog.get_logger()

    feedback_messages = state.agent_mailbox.get("preference_feedback", [])
    if not feedback_messages:
        records.append(
            ToolCallRecord(
                agent_id="preference_feedback",
                tool_name="process_feedback",
                params={"reason": "no_feedback"},
                result="skipped",
            )
        )
        return {"tool_call_history": records}

    if not deps.preference_repo:
        records.append(
            ToolCallRecord(
                agent_id="preference_feedback",
                tool_name="process_feedback",
                params={"reason": "no_preference_repo"},
                result="skipped",
            )
        )
        return {"tool_call_history": records}

    reinforced_count = 0
    violated_count = 0

    for msg in feedback_messages:
        delta = 0.0
        if msg.message_type == "preference_reinforced":
            delta = 0.1
        elif msg.message_type == "preference_violated":
            delta = -0.2
        else:
            continue

        preference_id = msg.metadata.get("preference_id", "")
        if preference_id:
            try:
                await deps.preference_repo.update_confidence(preference_id, delta)
                if delta > 0:
                    reinforced_count += 1
                else:
                    violated_count += 1
            except Exception:
                log.warning("preference_feedback.single_update_error", exc_info=True)
        else:
            try:
                prefs = await deps.preference_repo.get_by_user(
                    user_id=state.user_id,
                    project_id=state.project_id,
                    limit=100,
                )
                for p in prefs:
                    try:
                        await deps.preference_repo.update_confidence(p.id, delta)
                    except Exception:
                        pass
                if delta > 0:
                    reinforced_count += len(prefs)
                else:
                    violated_count += len(prefs)
            except Exception:
                log.warning("preference_feedback.batch_update_error", exc_info=True)

    pruned = 0
    try:
        pruned = await deps.preference_repo.delete_expired(threshold_confidence=0.1)
    except Exception:
        log.warning("preference_feedback.pruning_error", exc_info=True)

    records.append(
        ToolCallRecord(
            agent_id="preference_feedback",
            tool_name="process_feedback",
            params={"reinforced": reinforced_count, "violated": violated_count, "pruned": pruned},
            result=f"reinforced={reinforced_count},violated={violated_count},pruned={pruned}",
        )
    )

    return {"tool_call_history": records}
