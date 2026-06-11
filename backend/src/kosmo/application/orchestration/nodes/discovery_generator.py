from __future__ import annotations

import re

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import get_deps, verify_scope
from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.discovery import DiscoveryDocument
from kosmo.contracts.sdd.state import KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced
from kosmo.domain.sdd.document_converters import (
    clean_markdown,
    discovery_to_markdown,
    markdown_to_document,
)
from kosmo.domain.sdd.llm_helpers import extract_json, strip_llm_artifacts
from kosmo.domain.sdd.output_guardrails import validate_discovery_output, validate_discovery_quality
from kosmo.domain.sdd.structured_schemas import DiscoveryOutputSchema

_DISCOVERY_SYSTEM = """Eres un Analista de Negocio Senior. Generas contenido exclusivamente de negocio. Nunca menciones tecnología, software, bases de datos ni infraestructura.

IDIOMA Y ORTOGRAFÍA: escribes en español con todas las tildes correctas (gestión, visión, análisis, descripción, línea, mínimo, crítico, ítem, párrafo, sección, diagnóstico, tecnología). Las palabras sin tilde son rechazadas.

FORMATO DE CADA CAMPO DEL JSON:

vision: 1 párrafo de 3 a 5 líneas describiendo qué hace el producto y para quién. Texto plano, sin formato.

problem_space: 1 o 2 párrafos describiendo el problema de negocio que el producto resuelve. Texto plano, sin formato.

actors: lista donde cada línea tiene el formato "Rol: descripción breve". Ejemplo:
"Administrador: gestiona usuarios y configura el sistema\nMentor: acepta sesiones y comparte materiales\nEstudiante: agenda sesiones y califica tutorías"

value_proposition: lista donde cada línea tiene el formato "Rol: beneficio concreto". Ejemplo:
"Para Administrador: visibilidad completa de la actividad y métricas de uso\nPara Mentor: optimización del tiempo con agenda automatizada\nPara Estudiante: acceso rápido a mentores y materiales organizados"

use_cases: lista donde cada línea tiene el formato "Título breve: descripción de la interacción usuario-sistema". Ejemplo:
"Agendar sesión: el estudiante selecciona mentor, fecha y hora, y el sistema confirma disponibilidad y envía recordatorio\nCalificar tutoría: el estudiante asigna puntuación y escribe reseña, y el sistema actualiza el perfil del mentor\nCancelar reserva: el usuario cancela antes del inicio y el sistema libera el espacio"

core_capabilities: lista donde cada línea tiene el formato "Capacidad: descripción breve". Ejemplo:
"Agenda inteligente: mentores definen disponibilidad y estudiantes reservan en tiempo real\nSistema de calificaciones: estudiantes puntúan tutorías con reseñas visibles en perfiles\nRepositorio de archivos: almacena materiales compartidos por sesión\nNotificaciones: envía recordatorios de sesiones y alertas de actividad\nPerfiles de usuario: muestra historial, calificaciones y reseñas"

business_rules: lista donde cada línea es "Regla de negocio concreta". Ejemplo:
"Un estudiante no puede agendar más de 3 sesiones con el mismo mentor por semana\nLas calificaciones solo pueden editarse dentro de las 24 horas posteriores a la sesión\nUn mentor debe tener al menos 5 reseñas para mostrar su calificación promedio"

quality_attributes: lista donde cada línea tiene el formato "Atributo: expectativa medible". Ejemplo:
"Disponibilidad: el sistema debe estar operativo el 99.5% del tiempo en horario hábil\nRendimiento: la búsqueda de mentores debe responder en menos de 2 segundos\nSeguridad: los archivos solo son accesibles para los participantes de la sesión"

scope: texto con tres secciones "Incluido: ... Excluido: ... Futuro potencial: ...". Cada sección contiene ítems separados por punto y coma. Ejemplo:
"Incluido: agendamiento de sesiones; calificación y reseñas; perfiles de usuario; notificaciones por email\nExcluido: videollamadas integradas; pagos en línea; foros de discusión\nFuturo potencial: integración con calendarios externos; recomendación de mentores; aplicación móvil"

───────
IMPORTANTE: en cada campo debes usar UN SOLO ':' como separador entre etiqueta y valor. NUNCA uses '::' (doble dos puntos). El backend formateará tu texto para darle presentación visual (negritas, viñetas, numeración).
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
                system_prompt=system, user_prompt=user_prompt, response_schema=DiscoveryOutputSchema
            ),
            temperature=0,
            max_tokens=4096,
        )
    except Exception:
        records[-1].result = "llm_error"
        records[-1].error = "LLM call failed"
        empty = DiscoveryDocument(vision=description or "Sin descripción")
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
        empty = DiscoveryDocument(vision=description or "Sin descripción")
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
        actors=_format_kv_list(strip_llm_artifacts(discovery.actors)),
        value_proposition=_format_kv_list(
            strip_llm_artifacts(discovery.value_proposition), bullet_prefix="Para "
        ),
        use_cases=_format_kv_list(strip_llm_artifacts(discovery.use_cases), ordered=True),
        core_capabilities=_format_kv_list(strip_llm_artifacts(discovery.core_capabilities)),
        business_rules=_format_plain_list(strip_llm_artifacts(discovery.business_rules)),
        quality_attributes=_format_kv_list(strip_llm_artifacts(discovery.quality_attributes)),
        scope=_format_scope(strip_llm_artifacts(discovery.scope)),
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

    markdown = clean_markdown(discovery_to_markdown(discovery))
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


# ── Formateadores (backend genera el markdown, el LLM solo entrega datos) ──


def _split_entries(text: str) -> list[str]:
    """Divide texto en entradas individuales por saltos de línea o límites de oración."""
    if not text:
        return []
    if "\n" in text:
        return [e.strip() for e in text.split("\n") if e.strip()]
    parts = re.split(r"\.\s+(?=[A-ZÁÉÍÓÚÑ])", text)
    return [p.strip().rstrip(".") for p in parts if p.strip()]


def _format_kv_list(
    text: str,
    *,
    ordered: bool = False,
    bullet_prefix: str = "",
) -> str:
    """Convierte 'Etiqueta: descripción' o 'Etiqueta:: descripción' en bullet/numbered con bold.

    ordered=True  → "1. **Etiqueta:** descripción"
    ordered=False → "- **Etiqueta:** descripción"
    bullet_prefix se antepone a la etiqueta (ej: "Para " para value_proposition).
    """
    if not text:
        return ""

    # Fix double colons – primero quitar ** para exponer :: ocultos
    text = re.sub(r"\*+", "", text)
    text = re.sub(r":{2,}", ":", text)

    entries = _split_entries(text)
    formatted: list[str] = []

    for i, entry in enumerate(entries):
        entry = re.sub(r"\*+", "", entry)
        entry = re.sub(r"^\d+[\.\)]\s*", "", entry)
        entry = re.sub(r"^[-*]\s*", "", entry)
        entry = entry.strip()

        prefix = f"{i + 1}. " if ordered else "- "

        if ":" in entry:
            colon_idx = entry.index(":")
            label = entry[:colon_idx].strip().rstrip(":")
            body = re.sub(r"^:\s*", "", entry[colon_idx + 1 :].strip()).strip()
            if body:
                formatted.append(f"{prefix}{bullet_prefix}**{label}:** {body}")
            else:
                formatted.append(f"{prefix}{bullet_prefix}**{label}**")
        else:
            formatted.append(f"{prefix}{entry}")

    result = "\n".join(formatted)
    result = re.sub(r":{2,}", ":", result)
    return result


def _format_scope(text: str) -> str:
    """Convierte el scope caótico del LLM en formato limpio con bullets.

    Maneja 'Incluido:: contenido', 'Incluido:Excluido:', '**Incluido:** contenido', etc.
    """
    if not text:
        return ""

    # Fix double colons and remove markdown chars
    # Orden: primero quitar ** para exponer :: escondidos entre marcadores markdown
    text = re.sub(r"\*+", "", text)
    text = re.sub(r":{2,}", ":", text)

    # Fix concatenated keywords: "Incluido:Excluido:" → split
    text = re.sub(r"(Incluido)\s*:\s*(Excluido)", r"\n\2", text, flags=re.IGNORECASE)
    text = re.sub(r"(Incluido)\s*:\s*(Futuro\s+potencial)", r"\n\2", text, flags=re.IGNORECASE)
    text = re.sub(r"(Excluido)\s*:\s*(Futuro\s+potencial)", r"\n\2", text, flags=re.IGNORECASE)
    text = re.sub(r"(Excluido)\s*:\s*(Incluido)", r"\n\2", text, flags=re.IGNORECASE)

    pattern = re.compile(r"(Incluido|Excluido|Futuro potencial)\s*:\s*", re.IGNORECASE)
    parts = pattern.split(text)

    result: list[str] = []
    i = 1
    while i < len(parts):
        kw = parts[i].strip()
        raw = parts[i + 1].strip() if i + 1 < len(parts) else ""
        i += 2

        kw_lower = kw.lower()
        if "incluido" in kw_lower:
            header = "Incluido"
        elif "excluido" in kw_lower:
            header = "Excluido"
        else:
            header = "Futuro potencial"

        result.append(f"**{header}:**")

        items = re.split(r"[;]", raw)
        for item in items:
            item = item.strip().strip(".").strip()
            if item and len(item) > 1:
                item = item[0].upper() + item[1:]
                result.append(f"- {item}")
        result.append("")

    return "\n".join(result).strip()


def _format_plain_list(text: str, *, ordered: bool = True) -> str:
    """Convierte texto plano en lista numerada o con viñetas."""
    if not text:
        return ""

    text = re.sub(r":{2,}", ":", text)
    entries = _split_entries(text)
    formatted: list[str] = []

    for i, entry in enumerate(entries):
        entry = re.sub(r"^\d+[\.\)]\s*", "", entry)
        entry = re.sub(r"^[-*]\s*", "", entry)
        entry = entry.strip()
        formatted.append(f"{i + 1}. {entry}" if ordered else f"- {entry}")

    return "\n".join(formatted)


# ── Prompt builder ──


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
        parts.append("PLANIFICACIÓN: distribuye en las 9 secciones.")
        parts.append(
            "GENERACIÓN: contenido con el formato 'Etiqueta: descripción' especificado en el system prompt."
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

    parts.append("""
## Formato de Respuesta (JSON exacto)
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
