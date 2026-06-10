from __future__ import annotations

import structlog

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import get_deps, verify_scope
from kosmo.contracts.sdd.state import KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced


@traced("learn_from_correction.execute")
async def learn_from_correction_node(
    state: KOSMOState, config: RunnableConfig
) -> dict[str, object]:
    """Extrae deltas de correcciones del usuario y almacena preferencias aprendidas.

    Reads: graph_deps, user_id, project_id, shared_scratchpad
    Writes: tool_call_history, errors
    """
    verify_scope(state)

    deps = get_deps(config)
    records = list(state.tool_call_history)
    log = structlog.get_logger()

    original = state.shared_scratchpad.get("correction_original")
    corrected = state.shared_scratchpad.get("correction_corrected")
    document_type = state.shared_scratchpad.get("correction_document_type", "")

    if not original and state.output_ready:
        last_output = (
            state.shared_scratchpad.get("generated_document_md")
            or state.shared_scratchpad.get("generated_content_md")
            or state.shared_scratchpad.get("refined_content")
        )
        if last_output:
            original = str(last_output)
            phase_to_doc_type = {
                "descubrimiento": "discovery",
                "caracteristicas": "features",
                "requisitos": "requirements",
            }
            document_type = document_type or phase_to_doc_type.get(
                state.phase.value, state.phase.value
            )

    if not original or not corrected or not deps.preference_repo:
        records.append(
            ToolCallRecord(
                agent_id="learn_from_correction",
                tool_name="delta_extractor",
                params={"reason": "no_correction_data"},
                result="skipped",
            )
        )
        return {"tool_call_history": records}

    from kosmo.application.memory.learn_from_correction import LearnFromCorrectionUseCase

    records.append(
        ToolCallRecord(
            agent_id="learn_from_correction",
            tool_name="learn_from_correction",
            params={
                "user_id": state.user_id,
                "project_id": state.project_id,
                "document_type": document_type,
            },
            result="invoked",
        )
    )

    try:
        learn_uc = LearnFromCorrectionUseCase(
            preference_repo=deps.preference_repo,
            llm_client=deps.llm_client,
        )
        prefs = await learn_uc.execute(
            user_id=state.user_id,
            project_id=state.project_id,
            original_document=original,
            corrected_document=corrected,
            document_type=document_type,
        )
        records[-1].result = f"stored_{len(prefs)}_preferences" if prefs else "no_rules_inferred"
    except Exception:
        log.warning(
            "learn_from_correction.error",
            user_id=state.user_id,
            project_id=state.project_id,
            exc_info=True,
        )
        records[-1].result = "failed"
        records[-1].error = "Learning pipeline failed"

    return {"tool_call_history": records}
