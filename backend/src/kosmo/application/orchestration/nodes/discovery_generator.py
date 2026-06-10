from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import get_deps, verify_scope
from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.discovery import DiscoveryDocument
from kosmo.contracts.sdd.state import KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced
from kosmo.domain.sdd.document_converters import (
    discovery_to_markdown,
    markdown_to_document,
)
from kosmo.domain.sdd.llm_helpers import extract_json, strip_llm_artifacts
from kosmo.domain.sdd.output_guardrails import validate_discovery_output, validate_discovery_quality
from kosmo.domain.sdd.structured_schemas import DiscoveryOutputSchema

_DISCOVERY_SYSTEM = """Eres un Analista de Negocio Senior. Generas contenido EXCLUSIVAMENTE de negocio: describe que hace el producto, para quien, por que y bajo que reglas. Nunca menciones tecnologia.

REGLAS DE ORO:
- Toda palabra con tilde DEBE llevarla. Ej: gestion -> gestión, vision -> visión.
- Cada item de lista en su propia linea con salto de linea real (\\n). Esto es CRITICO: el backend necesita \\n reales entre items, no espacios.
  CORRECTO: "1. Primer item\\n2. Segundo item\\n3. Tercer item"
  INCORRECTO: "1. Primer item 2. Segundo item 3. Tercer item"
  INCORRECTO: "Incluido: gestion Excluido: facturacion Futuro potencial: IA"
- NO dupliques: jamas escribas **X**X. Correcto: **Disponibilidad**: descripcion. Incorrecto: **Disponibilidad**Disponibilidad.

FORMATO POR SECCION:
- vision: 1 parrafo de 3-5 lineas. Comienza con "Plataforma/Sistema/Herramienta que..."
- problem_space: 1-2 parrafos de diagnostico. Menciona dolores concretos con cifras si aplica.
- actors: lista con '- **Rol**: responsabilidad (1-2 lineas)'. Minimo 3 roles. Cada rol en su propia linea con \\n.
- value_proposition: lista con '- Para el **Rol**: beneficio concreto y medible (1-2 lineas)'. Cada item con \\n.
- use_cases: lista numerada '1. Escenario: descripcion'. Minimo 3. Cada uno en su propia linea con \\n.
- core_capabilities: lista con '- **Capacidad**: descripcion (1-2 lineas)'. Minimo 5. Cada uno con \\n.
- business_rules: lista numerada '1. Regla concreta (1-2 lineas)'. Minimo 4. Cada regla con \\n.
- quality_attributes: lista con '- **Atributo**: expectativa medible (1-2 lineas)'. Minimo 4. Cada uno con \\n.
- scope: "Incluido: ...\\nExcluido: ...\\nFuturo potencial: ...". CADA bloque separado por \\n real.

FORMATO PROHIBIDO:
NO: **X**X  |  NO: juntar items en un parrafo  |  NO: omitir tildes  |  NO: items sin \\n entre ellos"""


@traced("discovery_generator.execute")
async def discovery_generator_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    verify_scope(state)

    deps = get_deps(config)

    records = list(state.tool_call_history)
    iteration = state.generation_attempts + 1
    context = state.shared_scratchpad.get("context_analyzer_output", {})
    goals = state.shared_scratchpad.get("goal_planner_output", {})
    prefs = state.shared_scratchpad.get("preference_retriever_output", {})
    preferences_prompt = prefs.get("preferences_prompt", "") if isinstance(prefs, dict) else ""

    description = ""
    if state.raw_idea:
        description = state.raw_idea.text

    previous_output = state.shared_scratchpad.get("generated_document_md", "")
    improve_instruction = state.shared_scratchpad.get("improve_instruction", "")
    current_draft = state.shared_scratchpad.get("current_draft", "")
    generator_action = state.shared_scratchpad.get("generator_action", "")
    critic_feedback = ""
    if state.critique_log:
        critic_feedback = state.critique_log[-1].message

    if improve_instruction and not critic_feedback:
        critic_feedback = improve_instruction

    is_improve = generator_action == "improve" and current_draft

    system = _DISCOVERY_SYSTEM
    if preferences_prompt:
        system += f"\n\n## Preferencias del Usuario\n{preferences_prompt}"

    user_prompt = _build_discovery_prompt(
        iteration,
        description,
        context,
        goals,
        previous_output,
        critic_feedback,
        is_improve,
        current_draft,
    )

    records.append(
        ToolCallRecord(
            agent_id="discovery_generator",
            tool_name="llm_complete",
            params={"iteration": iteration, "mode": "improve" if is_improve else "generate"},
            result="invoked",
        )
    )

    try:
        response = await deps.llm_client.complete(
            prompt=PromptTemplate(
                system_prompt=system, user_prompt=user_prompt, response_schema=DiscoveryOutputSchema
            ),
            temperature=0,
            max_tokens=4096,
        )
    except Exception:
        records[-1].result = "llm_error"
        records[-1].error = "LLM call failed"
        empty = DiscoveryDocument(vision=description or "Sin descripcion")
        return {
            "discovery": empty,
            "generation_attempts": iteration,
            "errors": ["Discovery generator LLM call failed"],
            "validation_status": "needs_revision",
            "tool_call_history": records,
            "shared_scratchpad": {
                **state.shared_scratchpad,
                "generated_document": empty.model_dump(),
                "generated_document_md": discovery_to_markdown(empty),
                "generated_document_tree": markdown_to_document(discovery_to_markdown(empty)),
            },
        }

    if response.parsed is not None and isinstance(response.parsed, DiscoveryOutputSchema):
        discovery = DiscoveryDocument(**response.parsed.model_dump())
    else:
        discovery = _parse_discovery(response.content)

    if not discovery or not discovery.vision:
        records[-1].result = "parse_failed"
        records[-1].error = "Empty vision field"
        empty = DiscoveryDocument(vision=description or "Sin descripcion")
        return {
            "discovery": empty,
            "generation_attempts": iteration,
            "errors": ["Discovery generation returned empty content"],
            "validation_status": "needs_revision",
            "tool_call_history": records,
            "shared_scratchpad": {
                **state.shared_scratchpad,
                "generated_document": empty.model_dump(),
                "generated_document_md": discovery_to_markdown(empty),
                "generated_document_tree": markdown_to_document(discovery_to_markdown(empty)),
            },
        }

    discovery = DiscoveryDocument(
        vision=strip_llm_artifacts(discovery.vision),
        problem_space=strip_llm_artifacts(discovery.problem_space),
        actors=_format_list_section(discovery.actors),
        value_proposition=_format_list_section(discovery.value_proposition),
        use_cases=_format_list_section(discovery.use_cases),
        core_capabilities=_format_list_section(discovery.core_capabilities),
        business_rules=_format_list_section(discovery.business_rules),
        quality_attributes=_format_list_section(discovery.quality_attributes),
        scope=strip_llm_artifacts(discovery.scope),
    )

    guardrail_result = validate_discovery_output(discovery.model_dump())

    if not guardrail_result.is_valid:
        blocker_messages = [v.message for v in guardrail_result.violations if v.is_blocker]
        if blocker_messages:
            records[-1].result = "guardrail_blocked"
            records[-1].error = "; ".join(blocker_messages[:3])

    quality_issues = {"blocker_count": 0, "warning_count": 0, "summary": ""}
    try:
        quality_issues = validate_discovery_quality(discovery.model_dump())
    except Exception as exc:
        quality_issues["summary"] = f"quality check error: {exc}"

    has_warnings = quality_issues.get("warning_count", 0) > 0
    if has_warnings:
        if records[-1].result not in ("guardrail_blocked",):
            records[-1].result = "generated_with_warnings"
        records[-1].error = (records[-1].error or "") + " | " + quality_issues.get("summary", "")

    markdown = discovery_to_markdown(discovery)
    document_tree = markdown_to_document(markdown)

    return {
        "discovery": discovery,
        "generation_attempts": iteration,
        "validation_status": "pending_review",
        "shared_scratchpad": {
            **state.shared_scratchpad,
            "generated_document": discovery.model_dump(),
            "generated_document_md": markdown,
            "generated_document_tree": document_tree,
        },
        "tool_call_history": records,
    }


def _format_list_section(text: str) -> str:
    if not text:
        return ""

    import re

    text = re.sub(r"(\d+)\.\s+(?=[A-Z])", r"\n\1. ", text)
    text = re.sub(r"\b(Incluido:|Excluido:|Futuro potencial:)", r"\n\1", text)

    lines = text.strip().split("\n")
    formatted: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            formatted.append(stripped)
            continue

        if _looks_like_numbered_item(stripped):
            formatted.append(stripped)
            continue

        needs_bullet = not formatted and not stripped.startswith("- ")
        if needs_bullet:
            formatted.append(f"- {stripped}")
        else:
            formatted.append(stripped)

    return "\n".join(formatted)


def _looks_like_numbered_item(text: str) -> bool:
    import re
    return bool(re.match(r"^\d+[\.\)]\s+", text))


def _build_discovery_prompt(
    iteration: int,
    description: str,
    context: dict[str, object],
    goals: dict[str, object],
    previous: str,
    feedback: str,
    is_improve: bool,
    current_draft: str,
) -> str:
    parts: list[str] = []

    if is_improve:
        parts.append(f"## Ciclo ReAct — Iteracion {iteration} — MEJORA")
        parts.append("Documento actual:")
        parts.append(current_draft[:4000])
        parts.append("Instruccion: mejora manteniendo ideas del usuario. Enriquece analisis, completa secciones vacias. NO reescribas desde cero.")
    else:
        parts.append(f"## Ciclo ReAct — Iteracion {iteration}")
        parts.append("ANALISIS: que problema resuelve, para quien, que valor aporta.")
        parts.append("PLANIFICACION: distribuye en las 9 secciones.")
        parts.append("GENERACION: contenido sustancial con ortografia correcta.")

    if feedback:
        parts.append(f"\n## Retroalimentacion del Critico\n{feedback}")
        if previous:
            parts.append(f"\n## Contenido previo\n{previous[:2000]}")

    parts.append(f"\n## Proyecto\n{description}")

    if context.get("domain"):
        parts.append(f"\n## Dominio\n{context['domain']}")
    if context.get("key_entities"):
        parts.append(f"\n## Entidades clave\n{', '.join(context.get('key_entities', []))}")
    if goals.get("sub_goals"):
        parts.append(f"\n## Sub-objetivos\n{', '.join(goals.get('sub_goals', []))}")

    parts.append("""
## Formato de Respuesta (JSON exacto, usa estos nombres de campo)
```json
{
  "vision": "...",
  "problem_space": "...",
  "actors": "...",
  "value_proposition": "...",
  "use_cases": "...",
  "core_capabilities": "...",
  "business_rules": "...",
  "quality_attributes": "...",
  "scope": "..."
}
```""")

    return "\n".join(parts)


def _parse_discovery(raw: str) -> DiscoveryDocument | None:
    data = extract_json(raw)
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        return None
    try:
        return DiscoveryDocument(**data)
    except (TypeError, ValueError):
        return None
