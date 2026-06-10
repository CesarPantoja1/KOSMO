from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import (
    extract_generated_content,
    get_deps,
    verify_scope,
)
from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.state import CritiqueRecord, KOSMOState
from kosmo.contracts.telemetry import traced
from kosmo.domain.sdd.llm_helpers import extract_json
from kosmo.domain.sdd.structured_schemas import EvaluationOutputSchema

_FINAL_EVALUATOR_SYSTEM = (
    "Eres un Evaluador de Calidad de contenido generado por IA para un producto digital. "
    "Tu rol es PROVEER RETROALIMENTACION CONSTRUCTIVA sobre la calidad del contenido, "
    "NO bloquear ni rechazar. El contenido SIEMPRE se entrega al usuario.\n\n"
    "Evalua estos 5 criterios de calidad de negocio (escala 1-10):\n\n"
    "1. PUREZA DE NEGOCIO (1-10): CERO fugas de implementacion. El contenido describe "
    "comportamiento del negocio sin mencionar tecnologia, bases de datos, APIs, frameworks.\n\n"
    "2. COBERTURA (1-10): El contenido cubre todas las secciones o categorias esperadas.\n\n"
    "3. VERIFICABILIDAD (1-10): Los elementos son verificables por un analista funcional "
    "sin conocimientos tecnicos.\n\n"
    "4. DENSIDAD (1-10): Cada elemento tiene suficiente profundidad y detalle de negocio.\n\n"
    "5. ORTOGRAFIA (1-10): El contenido usa tildes, enyes y acentos correctos del espanol.\n\n"
    "Tu veredicto (overall_verdict) es INFORMATIVO, no bloqueante:\n"
    "- 'approved': calidad aceptable\n"
    "- 'needs_improvement': recomendaciones de mejora incluidas en summary\n\n"
    "Incluye un summary con recomendaciones accionables para el usuario.\n"
    "Responde SIEMPRE en JSON."
)


@traced("final_evaluator.execute")
async def final_evaluator_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    verify_scope(state)

    deps = get_deps(config)

    critic_log_entries = [f"[{c.agent_id}] {c.severity}: {c.message}" for c in state.critique_log]
    critic_summary = "\n".join(critic_log_entries) if critic_log_entries else "Sin criticas previas"

    content = extract_generated_content(state, max_chars=6000)
    next_attempt = state.generation_attempts

    prompt = PromptTemplate(
        system_prompt=_FINAL_EVALUATOR_SYSTEM,
        user_prompt=f"""## Contenido generado
{content}

## Resumen de Criticas Previas
{critic_summary}

## Fase: {state.phase.value}
## Intento: {next_attempt}/{state.max_iterations}

Evalua los 5 criterios de calidad de negocio.
El veredicto es INFORMATIVO, no bloqueante.
Incluye recomendaciones accionables en el summary.

Responde en JSON:
```json
{{
  "pureza_negocio": 8,
  "cobertura": 7,
  "verificabilidad": 8,
  "densidad": 7,
  "ortografia": 9,
  "blockers": [],
  "overall_verdict": "approved",
  "summary": "Recomendaciones para mejorar..."
}}
```""",
        response_schema=EvaluationOutputSchema,
    )

    try:
        response = await deps.llm_client.complete(prompt=prompt, temperature=0, max_tokens=4096)
        if response.parsed is not None and isinstance(response.parsed, EvaluationOutputSchema):
            data = response.parsed.model_dump()
        else:
            data = extract_json(response.content)
            if isinstance(data, list):
                data = data[0] if data else {}
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {
            "overall_verdict": "approved",
            "summary": "Evaluacion automatica no disponible. Contenido entregado sin revision.",
            "blockers": [],
        }

    return {
        "output_ready": True,
        "validation_status": "approved",
        "evaluation_summary": data,
        "critique_log": [
            *state.critique_log,
            CritiqueRecord(
                agent_id="final_evaluator",
                severity="none",
                message=data.get("summary", "Evaluacion completada"),
            ),
        ],
        "critic_iteration": 0,
        "generation_attempts": 0,
    }
