from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import get_deps, verify_scope
from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.state import KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced
from kosmo.domain.sdd.llm_helpers import extract_json
from kosmo.contracts.sdd.schemas import GoalPlannerOutput


@traced("goal_planner.execute")
async def goal_planner_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    """Descompone la fase actual en sub-objetivos accionables y medibles.

    Reads: graph_deps, phase, shared_scratchpad
    Writes: agent_outputs["goal_planner"], tool_call_history
    """
    verify_scope(state)

    deps = get_deps(config)

    records = list(state.tool_call_history)
    context = state.shared_scratchpad.get("context_analyzer_output", {})
    if not isinstance(context, dict):
        context = {}

    records.append(
        ToolCallRecord(
            agent_id="goal_planner",
            tool_name="llm_complete",
            params={"phase": state.phase.value},
            result="invoked",
        )
    )

    prompt = PromptTemplate(
        system_prompt=(
            "Eres un Planificador de Objetivos de Ingeniería de Software con 12 años "
            "de experiencia en descomposición de proyectos complejos. Tu misión es "
            "DESCOMPONER LA FASE ACTUAL en sub-objetivos SMART (Specific, Measurable, "
            "Achievable, Relevant, Time-bound) que guíen a los generadores de IA.\n\n"
            "METODOLOGÍA DE PLANIFICACIÓN POR FASE:\n\n"
            "FASE DESCUBRIMIENTO:\n"
            "- Sub-objetivos deben cubrir: visión del producto, análisis del problema, "
            "identificación de actores, propuesta de valor, casos de uso, capacidades "
            "clave, reglas de negocio, atributos de calidad, alcance.\n"
            "- Success criteria: cada sección debe tener al menos 2-3 párrafos "
            "sustanciales con análisis de negocio profundo, cero terminología técnica.\n\n"
            "FASE CARACTERÍSTICAS:\n"
            "- Sub-objetivos: inferir features desde el discovery, asegurar que cada "
            "feature tenga título accionable (verbo+objeto), descripción con las 4 W "
            "(Qué, Para Quién, Bajo Qué Condición, Qué Valor), y rationale que vincule "
            "con secciones del discovery.\n"
            "- Success criteria: todas las features son NO triviales, no parafrasean "
            "existentes, y están inferidas del contexto de negocio.\n\n"
            "FASE REQUISITOS:\n"
            "- Sub-objetivos: cubrir las 6 categorías EARS (ubiquitous, event, state, "
            "optional, unwanted, complex), asegurar atomicidad (un solo comportamiento "
            "por requisito), incluir criterios de aceptación Dado-Cuando-Entonces.\n"
            "- Success criteria: cero fugas técnicas, puntuación >= 7 en scoring EARS, "
            "al menos 3 requisitos por feature.\n\n"
            "EJEMPLOS DE PLANIFICACIÓN:\n\n"
            "Fase: descubrimiento | Dominio: Gestión de inventario B2B\n"
            "PLAN CORRECTO:\n"
            "{\n"
            '  "sub_goals": [\n'
            '    "Definir la visión del producto en 2-3 párrafos que describan el '
            'propósito fundamental y el impacto esperado en el negocio",\n'
            '    "Identificar al menos 4 actores de negocio con sus responsabilidades '
            'y objetivos",\n'
            '    "Documentar las reglas de negocio de inventario: umbrales mínimos, '
            'políticas de reabastecimiento, trazabilidad de movimientos",\n'
            '    "Describir 5-7 casos de uso principales con flujos de negocio '
            'completos",\n'
            '    "Definir atributos de calidad: disponibilidad, consistencia de '
            'datos, tiempo de respuesta para consultas de stock",\n'
            '    "Establecer el alcance: qué está incluido (gestión de inventario, '
            'alertas, reportes) y qué está fuera (contabilidad, facturación)"\n'
            '  ],\n'
            '  "success_criteria": [\n'
            '    "Cada sección del discovery tiene al menos 150 caracteres de '
            'contenido sustancial de negocio",\n'
            '    "CERO términos técnicos en todo el documento",\n'
            '    "Los actores aparecen referenciados en los casos de uso",\n'
            '    "Las reglas de negocio se reflejan en las capacidades principales"\n'
            '  ],\n'
            '  "dependencies": [\n'
            '    "Los actores deben definirse antes que los casos de uso",\n'
            '    "Las reglas de negocio deben definirse antes que las capacidades"\n'
            '  ],\n'
            '  "parallelizable_tasks": [\n'
            '    "Visión, actores y propuesta de valor pueden generarse en paralelo",\n'
            '    "Atributos de calidad y alcance pueden generarse en paralelo"\n'
            '  ],\n'
            '  "estimated_sections": 9\n'
            "}\n\n"
            "IMPORTANTE:\n"
            "- Los sub-objetivos deben ser CONCRETOS y CONTEXTUALIZADOS al dominio.\n"
            "- Los success criteria deben ser MEDIBLES (incluir números, thresholds).\n"
            "- Las dependencias deben reflejar el ORDEN LÓGICO de generación.\n"
            "- Usa ortografía correcta del español: tildes, eñes, diéresis."
        ),
        user_prompt=f"""## Fase: {state.phase.value}
## Contexto: {context.get("context_brief", "No disponible")}
## Dominio: {context.get("domain", "No disponible")}
## Brechas: {context.get("gaps_identified", [])}

Define sub-objetivos para esta fase. Responde en JSON:
```json
{{
  "sub_goals": ["objetivo 1", "objetivo 2"],
  "success_criteria": ["criterio 1"],
  "dependencies": [],
  "parallelizable_tasks": [],
  "estimated_sections": 5
}}
```""",
        response_schema=GoalPlannerOutput,
    )

    try:
        response = await deps.llm_client.complete(prompt=prompt, temperature=0, max_tokens=4096)
        if response.parsed is not None and isinstance(response.parsed, GoalPlannerOutput):
            data = response.parsed.model_dump()
        else:
            data = extract_json(response.content)
            if isinstance(data, list):
                data = data[0] if data else {}
        records[-1].result = "goals_planned"
    except Exception:
        records[-1].result = "llm_error"
        records[-1].error = "LLM call failed"
        return {
            "agent_outputs": {**state.agent_outputs, "goal_planner": {}},
            "tool_call_history": records,
            "errors": ["Goal planner LLM call failed"],
        }

    return {
        "agent_outputs": {**state.agent_outputs, "goal_planner": data},
        "tool_call_history": records,
    }
