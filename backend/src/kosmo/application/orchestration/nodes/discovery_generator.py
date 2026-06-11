from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import get_deps, verify_scope
from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.state import KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced
from kosmo.domain.sdd.document_converters import clean_markdown
from kosmo.domain.sdd.output_guardrails import validate_discovery_md

_DISCOVERY_SYSTEM = """Eres un Analista de Negocio Senior. Generas contenido exclusivamente de negocio. Nunca menciones tecnología, software, bases de datos ni infraestructura.

IDIOMA Y ORTOGRAFÍA: escribes en español con todas las tildes correctas (gestión, visión, análisis, descripción, línea, mínimo, crítico, ítem, párrafo, sección, diagnóstico, tecnología). Las palabras sin tilde son rechazadas.

FORMATO DE RESPUESTA: Markdown estructurado con las siguientes secciones obligatorias. Cada sección empieza con ## (doble numeral) seguido del título exacto.

## Visión del producto
1 párrafo de 3 a 5 líneas describiendo qué hace el producto y para quién.

## Espacio del problema
1 o 2 párrafos describiendo el problema de negocio que el producto resuelve.

## Actores
Lista con viñetas. Cada línea tiene el formato "- **Rol:** descripción breve".

## Propuesta de valor
Lista con viñetas. Cada línea tiene el formato "- **Para Rol:** beneficio concreto".

## Casos de uso
Lista numerada. Cada línea tiene el formato "1. **Título breve:** descripción de la interacción usuario-sistema".

## Capacidades principales
Lista con viñetas. Cada línea tiene el formato "- **Capacidad:** descripción breve".

## Reglas de negocio
Lista numerada con reglas de negocio concretas.

## Atributos de calidad
Lista con viñetas. Cada línea tiene el formato "- **Atributo:** expectativa medible".

## Alcance
Contiene tres secciones con el formato:
**Incluido:**
- ítem 1
- ítem 2

**Excluido:**
- ítem 1
- ítem 2

**Futuro potencial:**
- ítem 1
- ítem 2

───────
IMPORTANTE: usa UN SOLO ':' como separador. NUNCA uses '::' (doble dos puntos).
Responde ÚNICAMENTE con el Markdown, sin explicaciones ni texto adicional.
───────"""


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
                system_prompt=system,
                user_prompt=user_prompt,
            ),
            temperature=0,
            max_tokens=4096,
        )
    except Exception:
        records[-1].result = "llm_error"
        records[-1].error = "LLM call failed"
        fallback = f"# Descubrimiento de Producto\n\n## Visión del producto\n\n{description or 'Sin descripción'}"
        return {
            "discovery": fallback,
            "generation_attempts": iteration,
            "errors": ["Discovery generator LLM call failed"],
            "validation_status": "needs_revision",
            "tool_call_history": records,
            "shared_scratchpad": {
                **state.shared_scratchpad,
                "generated_document_md": fallback,
            },
        }

    raw_markdown = response.content or ""
    if not raw_markdown.strip():
        records[-1].result = "empty_response"
        fallback = f"# Descubrimiento de Producto\n\n## Visión del producto\n\n{description or 'Sin descripción'}"
        return {
            "discovery": fallback,
            "generation_attempts": iteration,
            "errors": ["Discovery generation returned empty content"],
            "validation_status": "needs_revision",
            "tool_call_history": records,
            "shared_scratchpad": {
                **state.shared_scratchpad,
                "generated_document_md": fallback,
            },
        }

    markdown = clean_markdown(raw_markdown)

    guardrail_result = validate_discovery_md(markdown)
    if not guardrail_result.get("is_valid", True):
        blocker_messages = guardrail_result.get("blockers", [])
        if blocker_messages:
            records[-1].result = "guardrail_blocked"
            records[-1].error = "; ".join(blocker_messages[:3])

    has_warnings = guardrail_result.get("warning_count", 0) > 0
    if has_warnings:
        if records[-1].result not in ("guardrail_blocked",):
            records[-1].result = "generated_with_warnings"
        records[-1].error = (records[-1].error or "") + " | " + guardrail_result.get("summary", "")

    return {
        "discovery": markdown,
        "generation_attempts": iteration,
        "validation_status": "pending_review",
        "shared_scratchpad": {
            **state.shared_scratchpad,
            "generated_document_md": markdown,
        },
        "tool_call_history": records,
    }


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
        parts.append(f"## Ciclo ReAct — Iteración {iteration} — MEJORA")
        parts.append("Documento actual:")
        parts.append(current_draft[:4000])
        parts.append(
            "Instrucción: mejora manteniendo ideas del usuario. Enriquece análisis, completa secciones vacías. NO reescribas desde cero."
        )
    else:
        parts.append(f"## Ciclo ReAct — Iteración {iteration}")
        parts.append("ANÁLISIS: qué problema resuelve, para quién, qué valor aporta.")
        parts.append("PLANIFICACIÓN: distribuye en las 9 secciones con formato Markdown.")
        parts.append(
            "GENERACIÓN: responde ÚNICAMENTE con el Markdown. No incluyas explicaciones ni texto fuera del documento."
        )

    if feedback:
        parts.append(f"\n## Retroalimentación del Crítico\n{feedback}")
        if previous:
            parts.append(f"\n## Contenido previo\n{previous[:2000]}")

    parts.append(f"\n## Proyecto\n{description}")

    if context.get("domain"):
        parts.append(f"\n## Dominio\n{context['domain']}")
    if context.get("key_entities"):
        parts.append(f"\n## Entidades clave\n{', '.join(context.get('key_entities', []))}")
    if goals.get("sub_goals"):
        parts.append(f"\n## Sub-objetivos\n{', '.join(goals.get('sub_goals', []))}")

    parts.append("\nResponde ÚNICAMENTE con el Markdown del documento de descubrimiento.")

    return "\n".join(parts)
