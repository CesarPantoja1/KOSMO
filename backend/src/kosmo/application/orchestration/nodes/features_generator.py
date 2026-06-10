from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import get_deps, verify_scope
from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId
from kosmo.contracts.sdd.state import AgentMessage, KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced
from kosmo.domain.sdd.document_converters import discovery_to_markdown
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.domain.sdd.llm_helpers import extract_json, strip_markdown_formatting
from kosmo.domain.sdd.output_guardrails import (
    validate_features_output,
    validate_generate_features_output,
    validate_semantic_quality,
)
from kosmo.domain.sdd.structured_schemas import FeaturesOutputSchema, GenerateFeaturesOutputSchema

_SUGGESTION_SYSTEM = (
    "Eres un Arquitecto de Producto Senior con 15 anos disenando funcionalidades de software.\n"
    "Tu trabajo es INFERIR caracteristicas ricas y especificas a partir del contexto de negocio.\n\n"
    "REGLA ANTI-TRIVIALIDAD (CRITICA):\n"
    "- Si el input es breve como 'Gestion de productos', NO respondas lo mismo o parafreas como "
    "'Administrar productos' o 'Manejo de productos'.\n"
    "- DEBES cruzar con el Discovery para inferir: que tipo de productos? para que actores? "
    "bajo que reglas? que valor aporta?\n"
    "- Cada title DEBE ser VERBO EN INFINITIVO + OBJETO DE NEGOCIO ESPECIFICO.\n"
    "- Cada description DEBE contener: (1) QUE hace, (2) PARA QUIEN, (3) BAJO QUE CONDICION, "
    "(4) QUE VALOR APORTA.\n"
    "- Cada rationale DEBE explicar por que esta caracteristica es relevante dado el dominio.\n"
    "- Cada inferred_from DEBE listar las secciones de Discovery de las que se deriva.\n\n"
    "ORTOGRAFIA OBLIGATORIA: tildes, enyes y acentos correctos del espanol.\n\n"
    "TERMINOS PROHIBIDOS (causan RECHAZO AUTOMATICO del requisito):\n"
    "NO uses: API, endpoint, REST, GraphQL, HTTP, JSON, XML, base de datos, tabla, columna, "
    "SQL, NoSQL, PostgreSQL, MongoDB, Redis, servidor, contenedor, frontend, backend, "
    "componente, modulo, clase, metodo, funcion, controlador, middleware, framework, libreria, "
    "React, Angular, Django, Spring, Node, Python, Java, microservicio, Docker, Kubernetes.\n"
)

_SUGGESTION_FEW_SHOT = """
## Ejemplo de inferencia rica (CORRECTO):

Contexto Discovery: E-commerce con actores administrador/cliente, regla de inventario minimo de 48h.

Input: "Gestion de productos"

Sugerencias CORRECTAS:
1. {
     "title": "Catalogar productos con categorizacion jerarquica por atributos de negocio",
     "description": "El administrador puede clasificar productos en categorias y subcategorias con atributos personalizables (talla, color, material), cumpliendo la regla de negocio de trazabilidad y permitiendo al cliente filtrar y encontrar productos segun sus preferencias.",
     "rationale": "Derivado de la necesidad de trazabilidad del discovery y los casos de uso de busqueda del cliente",
     "inferred_from": ["use_cases", "business_rules", "core_capabilities"],
     "category": "gestion"
   }
2. {
     "title": "Gestionar umbrales de inventario con notificacion proactiva al equipo de compras",
     "description": "Cuando el stock de un producto cae por debajo del minimo configurado, el sistema notifica al comprador responsable segun la regla de reposicion de 48 horas, evitando roturas de stock que impactan la disponibilidad del catalogo.",
     "rationale": "Derivado de la regla de negocio de inventario minimo y el actor administrador",
     "inferred_from": ["business_rules", "actors"],
     "category": "operacion"
   }
3. {
     "title": "Publicar y despublicar productos con control de visibilidad por canal de venta",
     "description": "El administrador controla que productos son visibles en cada canal (web, movil, marketplace) segun la regla de negocio de exclusividad por convenio, permitiendo estrategias de venta diferenciadas sin duplicar catalogo.",
     "rationale": "Derivado de la propuesta de valor de centralizacion y las reglas de negocio de exclusividad",
     "inferred_from": ["value_proposition", "business_rules"],
     "category": "comunicacion"
   }

Sugerencias INCORRECTAS (TRIVIALES):
- "Gestion de productos" -> Repite el input
- "Administrar productos" -> Parafrasis del input
- "Gestion del catalogo" -> Variante generica sin inferencia
"""


@traced("features_generator.execute")
async def features_generator_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    verify_scope(state)

    deps = get_deps(config)

    records = list(state.tool_call_history)
    iteration = state.generation_attempts + 1

    if deps.tool_registry:
        search_result = await deps.tool_registry.invoke(
            "search_features",
            {
                "project_id": state.project_id,
                "query": " ".join(t for t in [f.title for f in state.features[:5]]),
            },
        )
        records.append(
            ToolCallRecord(
                agent_id="features_generator",
                tool_name="search_features",
                params={"project_id": state.project_id},
                result="found" if search_result.success else "skipped",
            )
        )
    prefs = state.shared_scratchpad.get("preference_retriever_output", {})
    preferences_prompt = prefs.get("preferences_prompt", "") if isinstance(prefs, dict) else ""
    context = state.shared_scratchpad.get("context_analyzer_output", {})

    discovery_md = ""
    if state.discovery:
        discovery_md = discovery_to_markdown(state.discovery)

    existing_titles = [f.title for f in state.features]
    existing_ids = [f.id for f in state.features]
    critic_feedback = ""
    if state.critique_log:
        critic_feedback = state.critique_log[-1].message

    existing_text = "\n".join(f"- {t}" for t in existing_titles) or "Ninguna"

    system = _SUGGESTION_SYSTEM
    if preferences_prompt:
        system += f"\n\n## Preferencias del Usuario\n{preferences_prompt}"

    denied_section = (
        f"\n## CARACTERISTICAS EXISTENTES — PROHIBIDO sugerir cualquiera de estas o parafrasis:\n"
        f"{existing_text}\n\n"
        f"Ejemplos de parafrasis PROHIBIDAS:\n"
    )
    for title in existing_titles[:5]:
        denied_section += f"- '{title}' → cualquier variante como 'Administrar {title.lower()}', 'Manejo de {title.lower()}' esta PROHIBIDO\n"

    generation_mode = state.shared_scratchpad.get("generation_mode", "suggest")
    if generation_mode == "generate":
        target_count = 5
        response_schema = GenerateFeaturesOutputSchema
        guardrail_fn = validate_generate_features_output
    else:
        target_count = 3
        response_schema = FeaturesOutputSchema
        guardrail_fn = validate_features_output

    task = (
        f"Genera exactamente {target_count} caracteristicas NUEVAS, RICAS y ESPECIFICAS del dominio. "
        "NINGUNA debe ser parafrasis o variacion de las existentes. "
        "Cada caracteristica debe inferir riqueza contextual del Discovery."
    )
    if critic_feedback and iteration > 1:
        task = f"Corrige las caracteristicas previas. Feedback: {critic_feedback}"

    discovery_context = ""
    if state.discovery:
        d = state.discovery
        sections: list[str] = []
        if d.vision:
            sections.append(f"### Vision del Producto\n{d.vision}")
        if d.actors:
            sections.append(f"### Actores\n{d.actors}")
        if d.value_proposition:
            sections.append(f"### Propuesta de Valor\n{d.value_proposition}")
        if d.business_rules:
            sections.append(f"### Reglas de Negocio (DERIVAR de estas)\n{d.business_rules}")
        if d.use_cases:
            sections.append(f"### Casos de Uso\n{d.use_cases}")
        if d.core_capabilities:
            sections.append(f"### Capacidades Principales\n{d.core_capabilities}")
        discovery_context = "\n\n".join(sections)

    domain_info = (
        context.get("domain", "No disponible") if isinstance(context, dict) else "No disponible"
    )

    user_prompt = f"""{_SUGGESTION_FEW_SHOT}

## Documento de Descubrimiento
{discovery_md[:4000]}

## Contexto de Negocio Vinculado (OBLIGATORIO — cruzar con cada sugerencia)
{discovery_context[:3000] if discovery_context else "No disponible"}

## Dominio inferido: {domain_info}

{denied_section}

## Ciclo ReAct — Iteracion {iteration}

### 1. ANALISIS (Thought)
Analiza el discovery desde la perspectiva de producto:
- Que actores tienen necesidades no cubiertas?
- Que reglas de negocio generan oportunidades de funcionalidad?
- Que capacidades faltan para completar la propuesta de valor?
- Que patrones de uso sugieren los casos de uso descritos?

### 2. OBSERVACION (Feedback){' ' + critic_feedback if critic_feedback and iteration > 1 else ' (primera iteracion, sin feedback previo)'}

### 3. PLANIFICACION (Action Plan)
Distribuye las caracteristicas entre aspectos del negocio:
gestion de entidades, operacion, comunicacion, analisis, integracion.

### 4. GENERACION (Action)

{task}

## Autoevaluacion de Calidad
Antes de responder, verifica:
- [ ] ¿Cada feature tiene un titulo con VERBO EN INFINITIVO + OBJETO DE NEGOCIO ESPECIFICO?
- [ ] ¿Ninguna feature es parafrasis de las existentes?
- [ ] ¿Cada descripcion cubre las 4 partes: QUE, PARA QUIEN, BAJO QUE CONDICION, QUE VALOR?
- [ ] ¿Los rationale vinculan cada feature con secciones concretas del discovery?
- [ ] ¿Hay al menos una feature por cada area: gestion de entidades, operacion, comunicacion/notificacion, analisis/reporte?

Si alguna respuesta es negativa, REFUERZA esas features antes de entregar el JSON.

Cada feature DEBE tener:
- title: verbo en infinitivo + objeto de negocio especifico (min 3 car.)
- description: QUE hace, PARA QUIEN, BAJO QUE CONDICION, QUE VALOR APORTA (min 20 car.)
- rationale: por que es relevante dado el dominio (min 10 car.)
- inferred_from: secciones de discovery que motivan esta sugerencia
- category: categoria de negocio inferida

Responde SOLO con JSON:
```json
{{
  "suggestions": [
    {{
      "title": "...",
      "description": "...",
      "rationale": "...",
      "inferred_from": ["business_rules", "use_cases"],
      "category": "gestion"
    }}
  ],
  "excluded_titles": {existing_titles!r},
  "domain_inferred": "..."
}}
```"""

    prompt = PromptTemplate(
        system_prompt=system,
        user_prompt=user_prompt,
        response_schema=response_schema,
    )

    records.append(
        ToolCallRecord(
            agent_id="features_generator",
            tool_name="llm_complete",
            params={"iteration": iteration, "mode": generation_mode},
            result="invoked",
        )
    )

    try:
        response = await deps.llm_client.complete(prompt=prompt, temperature=0.3, max_tokens=4096)
    except Exception:
        records[-1].result = "llm_error"
        records[-1].error = "LLM call failed"
        return {
            "generation_attempts": iteration,
            "errors": ["Features generator LLM call failed"],
            "validation_status": "needs_revision",
            "tool_call_history": records,
        }

    if response.parsed is not None and isinstance(response.parsed, (FeaturesOutputSchema, GenerateFeaturesOutputSchema)):
        data = response.parsed.model_dump()
    else:
        data = extract_json(response.content)

    if not isinstance(data, dict):
        records[-1].result = "parse_failed"
        records[-1].error = "Invalid response format"
        return {
            "generation_attempts": iteration,
            "validation_status": "needs_revision",
            "errors": ["Features generation returned invalid format"],
            "tool_call_history": records,
        }

    suggestions_data = data.get("suggestions", data.get("features", []))
    if not isinstance(suggestions_data, list):
        suggestions_data = []

    guardrail_result = guardrail_fn(suggestions_data, existing_titles)

    if not guardrail_result.is_valid:
        blocker_messages = [v.message for v in guardrail_result.violations if v.is_blocker]
        records[-1].result = "guardrail_blocked"
        records[-1].error = "; ".join(blocker_messages[:3])
        if iteration >= 3:
            return {
                "generation_attempts": iteration,
                "validation_status": "needs_revision",
                "errors": blocker_messages[:5],
                "tool_call_history": records,
            }
    else:
        records[-1].result = "generated"

    valid_suggestions = (
        guardrail_result.sanitized if guardrail_result.sanitized else suggestions_data
    )

    existing_titles_lower = {t.strip().lower() for t in existing_titles}

    features = []
    for item in valid_suggestions[:target_count]:
        if isinstance(item, dict) and item.get("title") and item.get("description"):
            title_norm = item["title"].strip().lower()
            if title_norm not in existing_titles_lower:
                features.append(
                    Feature(
                        id=FeatureId(IdGenerator.generate("feature")),
                        project_id=state.project_id,
                        title=strip_markdown_formatting(item["title"]),
                        description=strip_markdown_formatting(item["description"]),
                    ).model_dump()
                )

    records[-1].result = "generated" if features else "empty_result"

    for f in features:
        semantic_violations = validate_semantic_quality(feature_title=f.get("title", ""))
        if semantic_violations:
            if records[-1].result == "generated":
                records[-1].result = "generated_with_warnings"
            records[-1].error = "; ".join(v.message for v in semantic_violations[:2])

    existing_feature_titles = existing_titles[:]
    existing_feature_ids = existing_ids[:]

    return {
        "features": state.features + [Feature(**f) for f in features],
        "generation_attempts": iteration,
        "validation_status": "pending_review" if features else "needs_revision",
        "shared_scratchpad": {
            **state.shared_scratchpad,
            "generated_features": features,
        },
        "existing_feature_titles": existing_feature_titles,
        "existing_feature_ids": existing_feature_ids,
        "tool_call_history": records,
        "agent_mailbox": {
            **state.agent_mailbox,
            "consistency_critic": [
                AgentMessage(
                    from_agent="features_generator",
                    to_agent="consistency_critic",
                    message_type="request_review",
                    content=f"Verifica que las {len(features)} features nuevas no solapan con las {len(existing_titles)} existentes",
                    priority="high",
                )
            ],
        },
    }
