from __future__ import annotations

import time
from typing import TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

if TYPE_CHECKING:
    from kosmo.contracts.orchestration.graph_deps import GraphDependencies
    from kosmo.contracts.sdd.state import KOSMOState

from kosmo.contracts.orchestration.graph_deps import GraphDependencies


def get_deps(config: RunnableConfig) -> GraphDependencies:
    deps = config.get("configurable", {}).get("deps")
    if deps is None:
        raise RuntimeError(
            "GraphDependencies not found in config. "
            "Did you forget to pass configurable={'deps': ...} to the graph?"
        )
    return deps


def verify_scope(state: KOSMOState) -> None:
    assert state.project_id, "project_id requerido"
    assert state.user_id, "user_id requerido"


def validate_inputs(
    state: KOSMOState,
    required_fields: list[str],
    agent_id: str = "",
) -> dict[str, object] | None:
    missing: list[str] = []
    for field in required_fields:
        value = state.shared_scratchpad.get(field, "")
        if not value:
            missing.append(field)
    if missing:
        return {
            "validation_status": "needs_revision",
            "errors": [f"{agent_id}: campos requeridos ausentes: {', '.join(missing)}"],
        }
    return None


def extract_generated_content(state: KOSMOState, max_chars: int = 4000) -> str:
    generated_ears = state.shared_scratchpad.get("generated_ears")
    if generated_ears and isinstance(generated_ears, list):
        return _format_ears_for_critics(generated_ears, max_chars)

    generated_document = state.shared_scratchpad.get("generated_document")
    if generated_document and isinstance(generated_document, dict):
        return _format_discovery_for_critics(generated_document, max_chars)

    for key in ["generated_document_md", "generated_content_md", "refined_content"]:
        content = state.shared_scratchpad.get(key, "")
        if content:
            return str(content)[:max_chars]

    return ""


def _format_ears_for_critics(ears: list, max_chars: int) -> str:
    parts: list[str] = []
    total_chars = 0
    for req in ears:
        if not isinstance(req, dict):
            continue
        block_parts: list[str] = []
        pattern = req.get("pattern", "")
        block_parts.append(f"[Categoria: {pattern}]")
        block_parts.append(f"source_statement: {req.get('source_statement', '')}")
        if req.get("trigger"):
            block_parts.append(f"trigger: {req['trigger']}")
        block_parts.append(f"system: {req.get('system', '')}")
        block_parts.append(f"response: {req.get('response', '')}")
        ac_list = req.get("acceptance_criteria", [])
        if ac_list:
            block_parts.append("acceptance_criteria:")
            for ac in ac_list:
                if isinstance(ac, dict):
                    block_parts.append(f"  - {ac.get('description', '')}")
                    if ac.get("expected_result"):
                        block_parts.append(f"    expected: {ac['expected_result']}")
        block = "\n".join(block_parts)
        if total_chars + len(block) > max_chars:
            break
        parts.append(block)
        total_chars += len(block) + 2
    return "\n\n".join(parts)


def _format_discovery_for_critics(doc: dict, max_chars: int) -> str:
    parts: list[str] = []
    total_chars = 0
    section_keys = [
        ("vision", "[Vision del producto]"),
        ("problem_space", "[Espacio del problema]"),
        ("actors", "[Actores]"),
        ("value_proposition", "[Propuesta de valor]"),
        ("use_cases", "[Casos de uso]"),
        ("core_capabilities", "[Capacidades principales]"),
        ("business_rules", "[Reglas de negocio]"),
        ("quality_attributes", "[Atributos de calidad]"),
        ("scope", "[Alcance]"),
    ]
    for key, label in section_keys:
        content = doc.get(key, "")
        if content and isinstance(content, str) and content.strip():
            block = f"{label}\n{content.strip()}"
            if total_chars + len(block) > max_chars:
                break
            parts.append(block)
            total_chars += len(block) + 2
    return "\n\n".join(parts)


def noop_result(errors: list[str] | None = None) -> dict[str, object]:
    return {
        "validation_status": "needs_revision",
        "errors": errors or ["Graph dependencies not available"],
    }


def build_llm_prompt_record(
    agent_id: str, params: dict[str, object] | None = None
) -> dict[str, object]:
    from kosmo.contracts.sdd.state import ToolCallRecord

    record = ToolCallRecord(
        agent_id=agent_id,
        tool_name="llm_complete",
        params=params or {},
        result="invoked",
    )
    start = time.perf_counter()
    return {"record": record, "start": start}


def finalize_llm_prompt_record(
    record_payload: dict[str, object], result: str, error: str | None = None
) -> None:
    record = record_payload["record"]
    start = record_payload["start"]
    record.result = result
    record.error = error
    record.duration_ms = int((time.perf_counter() - start) * 1000)
