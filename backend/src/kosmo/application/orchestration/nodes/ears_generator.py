from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import get_deps, validate_inputs, verify_scope
from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.ears import AcceptanceCriterion, EARSRequirement
from kosmo.contracts.sdd.feature import FeatureStatus
from kosmo.contracts.sdd.ids import RequirementId
from kosmo.contracts.sdd.state import KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced
from kosmo.domain.sdd.id_generator import IdGenerator
from kosmo.domain.sdd.llm_helpers import (
    extract_json,
    strip_llm_artifacts,
    strip_markdown_formatting,
)
from kosmo.domain.sdd.output_guardrails import validate_ears_output, validate_semantic_quality
from kosmo.domain.sdd.structured_schemas import EARSOutputSchema
from kosmo.domain.sdd.validators.ears_validator import (
    detect_implementation_leak,
    score_requirements_batch,
)

_EARS_CATEGORY_INSTRUCTIONS = """
## Categorías EARS — Perspectiva de Negocio

### 1. ubiquitous — Requisitos Ubicuos
Comportamiento que aplica SIEMPRE, sin condiciones previas. Características fundamentales del producto.
Patrón: `The <system> shall <response>`

Ejemplos:
- `The system shall identificar de forma única cada pedido mediante un número de referencia`
- `The system shall conservar el historial de transacciones del cliente durante 24 meses`

### 2. event — Requisitos Basados en Eventos
Respuesta a una acción del usuario o evento de negocio.
Patrón: `WHEN <trigger>, the <system> shall <response>`

Ejemplos:
- `WHEN el cliente confirma un pedido, the system shall reservar el inventario solicitado`
- `WHEN un usuario envía una consulta de soporte, the system shall asignar un número de seguimiento`

### 3. state — Requisitos Determinados por el Estado
Comportamiento condicionado al estado de una entidad de negocio.
Patrón: `WHILE <state>, the <system> shall <response>`

Ejemplos:
- `WHILE un pedido está en estado 'en preparación', the system shall permitir al cliente cancelarlo sin costo`
- `WHILE la cuenta del usuario está suspendida, the system shall restringir el acceso a funcionalidades de compra`

### 4. optional — Requisitos Opcionales
Comportamiento que solo aplica cuando una característica de negocio está activa.
Patrón: `WHERE <feature enabled>, the <system> shall <response>`

Ejemplos:
- `WHERE el cliente tiene suscripción premium activa, the system shall ofrecer envío gratuito en todos los pedidos`
- `WHERE la funcionalidad de notificaciones por correo está habilitada, the system shall enviar confirmación por cada transacción`

### 5. unwanted — Requisitos de Respuesta ante Fallos
Comportamiento del sistema ante situaciones no deseadas del negocio.
Patrón: `IF <condition>, THEN the <system> shall <response>`

Ejemplos:
- `IF el pago es rechazado, THEN the system shall notificar al cliente y conservar el pedido en estado 'pendiente de pago'`
- `IF el inventario es insuficiente, THEN the system shall informar al cliente y ofrecer alternativas`

### 6. complex — Requisitos Complejos
Combinación de múltiples condiciones de negocio.
Patrón: `WHEN ... AND/OR ... , WHILE ..., IF ... THEN ...`

Ejemplos:
- `WHEN el cliente solicita un reembolso AND el pedido fue entregado hace menos de 30 días, the system shall procesar el reembolso automáticamente`
"""

_TERMS_PROHIBITED = """TÉRMINOS PROHIBIDOS (causan RECHAZO AUTOMÁTICO del requisito):
NO uses: API, endpoint, REST, GraphQL, WebSocket, HTTP, JSON, XML, base de datos, tabla, columna, índice, SQL, NoSQL, PostgreSQL, MongoDB, Redis, servidor, contenedor, pod, cluster, load balancer, CDN, cloud, AWS, Azure, GCP, frontend, backend, componente, módulo, clase, método, función, controlador, middleware, framework, librería, React, Angular, Vue, Django, Flask, Spring, Express, Node, Python, Java, TypeScript, JavaScript, microservicio, ORM, Docker, Kubernetes, CI/CD, caché, Redis, JWT, OAuth, token de acceso, API key."""

_BUSINESS_PRINCIPLES = """PRINCIPIOS DE NEGOCIO:
1. Describe COMPORTAMIENTO OBSERVABLE por el usuario o stakeholder, no implementación
2. Cada requisito describe UN solo comportamiento atómico
3. Usa verbos medibles: registrar, notificar, mostrar, calcular, validar, restringir, permitir, generar, asignar, actualizar
4. Los criterios de aceptación siguen Dado-Cuando-Entonces con ejemplos concretos del negocio
5. source_statement en inglés con keywords EARS; response en español descriptivo
6. SIEMPRE incluye requisitos de: happy path, estados, errores, y condiciones opcionales
7. SIEMPRE incluye rationale: por qué el negocio necesita este comportamiento"""

_QUALITY_CHECKLIST = """CHECKLIST DE CALIDAD POR REQUISITO:
- [ ] source_statement sigue EXACTAMENTE el patrón EARS de su categoría
- [ ] CERO términos técnicos o de implementación
- [ ] Describe UN solo comportamiento atómico de negocio
- [ ] Usa "El sistema" como sujeto de forma consistente
- [ ] Al menos 1 criterio de aceptación (idealmente 2-3)
- [ ] Cada criterio es verificable por un analista funcional sin conocimientos técnicos
- [ ] Lenguaje concreto, sin ambigüedades
- [ ] Incluye rationale que justifica por qué el negocio necesita este comportamiento
- [ ] La relación trigger->response es lógica y directa
- [ ] ORTOGRAFÍA: Usa tildes, eñes y acentos correctos del español"""


@traced("ears_generator.execute")
async def ears_generator_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    """Genera requisitos EARS via ciclo ReAct: Analisis -> Planificacion -> Generacion -> Auto-Validacion.

    Reads: graph_deps, discovery, shared_scratchpad, critique_log, generation_attempts
    Writes: requirements, generation_attempts, shared_scratchpad, validation_status,
            tool_call_history, errors
    """
    verify_scope(state)

    feature_status = state.shared_scratchpad.get("current_feature_status", "")
    if feature_status and feature_status != FeatureStatus.APROBADA.value:
        return {
            "validation_status": "rejected",
            "errors": [
                f"La feature debe estar Aprobada para generar requisitos. Estado actual: {feature_status}"
            ],
            "tool_call_history": list(state.tool_call_history),
        }

    deps = get_deps(config)

    validation_error = validate_inputs(
        state,
        ["current_feature_title", "current_feature_description"],
        agent_id="ears_generator",
    )
    if validation_error:
        return validation_error

    generator_action = state.shared_scratchpad.get("generator_action", "")
    current_draft = state.shared_scratchpad.get("current_draft", "")
    is_improve = generator_action == "improve" and current_draft

    records = list(state.tool_call_history)
    iteration = state.generation_attempts + 1
    prefs = state.shared_scratchpad.get("preference_retriever_output", {})
    preferences_prompt = prefs.get("preferences_prompt", "") if isinstance(prefs, dict) else ""

    feature_title = state.shared_scratchpad.get("current_feature_title", "")
    feature_description = state.shared_scratchpad.get("current_feature_description", "")

    discovery_context = _build_discovery_context(state)

    critic_feedback = ""
    if state.critique_log:
        critic_feedback = state.critique_log[-1].message

    system = _build_system_prompt(preferences_prompt)

    task = _build_task(
        iteration,
        critic_feedback,
        feature_title,
        feature_description,
        discovery_context,
        is_improve,
        current_draft,
    )

    records.append(
        ToolCallRecord(
            agent_id="ears_generator",
            tool_name="llm_complete",
            params={"iteration": iteration},
            result="invoked",
        )
    )

    try:
        response = await deps.llm_client.complete(
            prompt=PromptTemplate(
                system_prompt=system, user_prompt=task, response_schema=EARSOutputSchema
            ),
            temperature=0,
            max_tokens=8192,
        )
    except Exception:
        records[-1].result = "llm_error"
        records[-1].error = "LLM call failed"
        return {
            "generation_attempts": iteration,
            "errors": ["EARS generator LLM call failed"],
            "validation_status": "needs_revision",
            "tool_call_history": records,
        }

    if response.parsed is not None and isinstance(response.parsed, EARSOutputSchema):
        data = response.parsed.model_dump()
    else:
        data = extract_json(response.content)

    if not isinstance(data, dict):
        records[-1].result = "parse_failed"
        records[-1].error = "Invalid response format"
        return {
            "generation_attempts": iteration,
            "validation_status": "needs_revision",
            "errors": ["EARS generation returned invalid format"],
            "tool_call_history": records,
        }

    requirements = _parse_ears(data)

    if not requirements:
        records[-1].result = "empty_result"
        records[-1].error = "No requirements generated"
        return {
            "generation_attempts": iteration,
            "validation_status": "needs_revision",
            "errors": ["EARS generation returned no requirements"],
            "tool_call_history": records,
        }

    guardrail_result = validate_ears_output(data)
    if not guardrail_result.is_valid:
        blocker_messages = [v.message for v in guardrail_result.violations if v.is_blocker]
        if blocker_messages and iteration >= 3:
            records[-1].result = "guardrail_blocked"
            records[-1].error = "; ".join(blocker_messages[:3])
            return {
                "generation_attempts": iteration,
                "validation_status": "needs_revision",
                "errors": blocker_messages[:5],
                "tool_call_history": records,
            }

    semantic_violations = validate_semantic_quality(
        ears_requirements=[r.model_dump() for r in requirements],
    )
    if semantic_violations:
        guardrail_result.violations.extend(semantic_violations)

    score_card = score_requirements_batch(requirements)
    requirements = _auto_repair_leaks(requirements)

    if score_card.failed > 0:
        records[-1].result = "generated_with_warnings"
        records[
            -1
        ].error = (
            f"{score_card.failed}/{score_card.total_requirements} requisitos no pasaron validacion"
        )
    else:
        records[-1].result = "generated"

    validation_status = "pending_review"
    if score_card.passed == score_card.total_requirements and score_card.overall_score >= 7.0:
        validation_status = "approved"

    return {
        "requirements": requirements,
        "generation_attempts": iteration,
        "validation_status": validation_status,
        "shared_scratchpad": {
            **state.shared_scratchpad,
            "generated_ears": [r.model_dump() for r in requirements],
            "ears_batch_score": {
                "overall_score": score_card.overall_score,
                "passed": score_card.passed,
                "failed": score_card.failed,
                "total": score_card.total_requirements,
            },
        },
        "tool_call_history": records,
    }


def _build_discovery_context(state: KOSMOState) -> str:
    if not state.discovery:
        return ""

    d = state.discovery
    parts: list[str] = []

    if d.vision:
        parts.append(f"### Vision del Producto\n{d.vision}")
    if d.problem_space:
        parts.append(f"### Espacio de Problema\n{d.problem_space}")
    if d.actors:
        parts.append(f"### Actores y Stakeholders\n{d.actors}")
    if d.value_proposition:
        parts.append(f"### Propuesta de Valor\n{d.value_proposition}")
    if d.business_rules:
        parts.append(
            f"### Reglas de Negocio (CRITICAS — derivar requisitos de estas reglas)\n{d.business_rules}"
        )
    if d.use_cases:
        parts.append(f"### Casos de Uso Principales\n{d.use_cases}")
    if d.core_capabilities:
        parts.append(f"### Capacidades Principales\n{d.core_capabilities}")
    if d.scope:
        parts.append(f"### Alcance del Producto\n{d.scope}")
    if d.quality_attributes:
        parts.append(f"### Atributos de Calidad\n{d.quality_attributes}")

    return "\n\n".join(parts)


def _build_system_prompt(preferences_prompt: str) -> str:
    system = (
        "Eres un Ingeniero de Requisitos de Negocio Senior con 15 años de experiencia "
        "en levantamiento de requerimientos funcionales para stakeholders no técnicos.\n\n"
        "Trabajas EXCLUSIVAMENTE en capa de NEGOCIO. Todo lo que produces describe "
        "QUÉ debe hacer el sistema desde la perspectiva del usuario o stakeholder, "
        "NUNCA CÓMO se implementa. Eres completamente agnóstico a la tecnología.\n\n"
        f"{_BUSINESS_PRINCIPLES}\n\n"
        "FORMATO DE RESPUESTA:\n"
        "- source_statement: texto plano con sintaxis EARS exacta. SIN markdown.\n"
        "- response: texto enriquecido en Markdown. Usa **negritas** para "
        "conceptos clave. Formato correcto: **Concepto**: descripcion. "
        "JAMAS dupliques: **Concepto**Concepto es INCORRECTO. "
        "Usa - viñetas para enumerar comportamientos, *cursivas* para "
        "ejemplos, '---' para separar subsecciones. Maximo 2-3 parrafos.\n"
        "- rationale: texto enriquecido en Markdown con viñetas si enumera razones.\n"
        "- acceptance_criteria.description: admite **negritas** para verbos clave.\n"
        "- Cada item de lista DEBE ir en su propia linea con salto de linea real.\n"
        "- PROHIBIDO omitir tildes. Toda palabra que lleve tilde DEBE llevarla.\n\n"
        f"{_TERMS_PROHIBITED}\n\n"
        f"{_EARS_CATEGORY_INSTRUCTIONS}\n\n"
        f"{_QUALITY_CHECKLIST}\n\n"
        "ORTOGRAFÍA OBLIGATORIA: Todo el contenido generado DEBE usar ortografía "
        "correcta del español: tildes (acción, generación, descripción), eñes (diseño, "
        "año), y diéresis donde corresponda. Está PROHIBIDO omitir tildes o acentos."
    )
    if preferences_prompt:
        system += f"\n\n## Preferencias del Usuario\n{preferences_prompt}"
    return system


def _build_task(
    iteration: int,
    critic_feedback: str,
    feature_title: str,
    feature_description: str,
    discovery_context: str,
    is_improve: bool = False,
    current_draft: str = "",
) -> str:
    parts: list[str] = []

    if is_improve:
        parts.append(f"## Ciclo ReAct — Iteracion {iteration} — MODO MEJORA")
        parts.append("")
        parts.append("### Documento Actual (modificado por el usuario):")
        parts.append(current_draft[:4000])
        parts.append("")
        parts.append("### Instruccion:")
        parts.append(
            "Mejora este documento de requisitos manteniendo las ideas del usuario. "
            "Refina la estructura EARS, completa requisitos incompletos, corrige "
            "errores de formato y mejora la redaccion. NO elimines requisitos que "
            "el usuario anadio ni cambies su intencion."
        )
        parts.append("")
    else:
        parts.append(f"## Ciclo ReAct — Iteracion {iteration}")
        parts.append("")
        parts.append("### 1. ANALISIS (Thought)")
        parts.append("Analiza la funcionalidad desde la perspectiva del negocio:")
        parts.append("- Identifica los actores principales y sus objetivos")
        parts.append("- Identifica los flujos principales (happy path)")
        parts.append("- Identifica estados posibles de las entidades de negocio")
        parts.append("- Identifica condiciones de error o casos excepcionales")
        parts.append("- Identifica funcionalidades opcionales o condicionales")
        parts.append("- Identifica reglas de negocio que generan restricciones")
        parts.append("")
        if critic_feedback:
            parts.append("### 2. CORRECCION (Observation de iteracion anterior)")
            parts.append(f"Feedback del revisor: {critic_feedback}")
            parts.append("")
        parts.append("### 3. PLANIFICACION (Action Plan)")
        parts.append("Distribuye los requisitos entre las categorias EARS que apliquen.")
        parts.append("")
        parts.append("### 4. GENERACION (Action)")
        parts.append("Genera los requisitos en formato JSON estructurado por categoria EARS.")
        parts.append("")

    parts.append("## Datos de la Funcionalidad")
    parts.append(f"**Titulo:** {feature_title}")
    parts.append(f"**Descripcion:** {feature_description}")
    parts.append("")

    if discovery_context:
        parts.append("## Contexto del Producto (Discovery)")
        parts.append(discovery_context)
        parts.append("")

    parts.append("## Instrucciones Finales")
    if not is_improve:
        parts.append(
            "Genera entre 3 y 15 requisitos distribuidos en las categorias EARS que apliquen."
        )
        parts.append("Cada requisito debe ser ATOMICO: un solo comportamiento de negocio.")
    parts.append("Cada requisito debe tener al menos 1 criterio de aceptacion (idealmente 2-3).")
    parts.append(
        "Los criterios de aceptacion deben incluir scenario (Dado-Cuando-Entonces) y expected_result."
    )
    parts.append("El campo system debe ser 'El sistema' de forma consistente.")
    parts.append("NO incluyas el campo 'id'.")
    parts.append(
        "SIEMPRE incluye rationale que justifique por que el negocio necesita este requisito."
    )
    parts.append("")
    parts.append("## Autoevaluacion de Calidad")
    parts.append("Antes de responder, verifica:")
    parts.append("- [ ] ¿Cada requisito describe UN solo comportamiento atomico de negocio?")
    parts.append("- [ ] ¿Hay requisitos en al menos 4 de las 6 categorias EARS?")
    parts.append("- [ ] ¿Los criterios de aceptacion son verificables por un analista funcional sin conocimientos tecnicos?")
    parts.append("- [ ] ¿CERO terminos tecnicos o de implementacion en todo el contenido?")
    parts.append("- [ ] ¿Se cubren los flujos: happy path, estados, errores y condiciones opcionales?")
    parts.append("- [ ] ¿Cada source_statement sigue EXACTAMENTE el patron EARS de su categoria?")
    parts.append("")
    parts.append("Responde SOLO con JSON:")
    parts.append("""```json
{
  "ubiquitous": [
    {
      "pattern": "ubiquitous",
      "trigger": null,
      "system": "El sistema",
      "response": "identifica de forma unica cada pedido",
      "acceptance_criteria": [
        {
          "description": "Cada pedido recibe un identificador unico",
          "scenario": "Dado que se crea un pedido, cuando el sistema lo registra, entonces asigna un ID",
          "expected_result": "El pedido tiene un ID que no se repite",
          "verified_by": "prueba funcional"
        }
      ],
      "source_statement": "The system shall identificar de forma unica cada pedido",
      "rationale": "Trazabilidad requerida por el negocio",
      "traceability": ["feature: {{FEATURE}}"]
    }
  ],
  "event": [],
  "state": [],
  "optional": [],
  "unwanted": [],
  "complex": []
}
```""")

    return "\n".join(parts)


def _parse_ears(data: dict[str, object]) -> list[EARSRequirement]:
    requirements: list[EARSRequirement] = []
    for pattern_key in ["ubiquitous", "event", "state", "optional", "unwanted", "complex"]:
        items = data.get(pattern_key, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            criteria = _parse_acceptance_criteria(item.get("acceptance_criteria", []))
            requirements.append(
                EARSRequirement(
                    id=RequirementId(IdGenerator.generate("requirement")),
                    pattern=pattern_key,
                    trigger=strip_markdown_formatting(item.get("trigger", "") or ""),
                    system=strip_markdown_formatting(item.get("system", "El sistema")),
                    response=strip_llm_artifacts(item.get("response", "")),
                    acceptance_criteria=criteria,
                    source_statement=strip_markdown_formatting(item.get("source_statement", "")),
                    rationale=strip_llm_artifacts(item.get("rationale", "")),
                    traceability=item.get("traceability", []),
                )
            )
    return requirements


def _parse_acceptance_criteria(raw: object) -> list[AcceptanceCriterion]:
    if not isinstance(raw, list):
        return []
    result: list[AcceptanceCriterion] = []
    for c in raw:
        if isinstance(c, dict):
            result.append(
                AcceptanceCriterion(
                    description=strip_llm_artifacts(c.get("description", "")),
                    scenario=strip_llm_artifacts(c.get("scenario", "")),
                    expected_result=strip_llm_artifacts(c.get("expected_result", "")),
                    verified_by=c.get("verified_by", ""),
                )
            )
        elif isinstance(c, str):
            result.append(AcceptanceCriterion(description=strip_llm_artifacts(c)))
    return result


def _auto_repair_leaks(requirements: list[EARSRequirement]) -> list[EARSRequirement]:
    repaired: list[EARSRequirement] = []
    for req in requirements:
        leaks = detect_implementation_leak(req.source_statement)
        if leaks:
            cleaned_statement = req.source_statement
            for leak in leaks:
                cleaned_statement = cleaned_statement.replace(
                    leak.matched_text, f"[termino tecnico '{leak.matched_text}' eliminado — expresar en lenguaje de negocio]"
                )
            req = req.model_copy(update={"source_statement": cleaned_statement})

        if req.acceptance_criteria:
            cleaned_criteria: list[AcceptanceCriterion] = []
            for ac in req.acceptance_criteria:
                ac_leaks = detect_implementation_leak(ac.description)
                if ac_leaks:
                    cleaned_desc = ac.description
                    for leak in ac_leaks:
                        cleaned_desc = cleaned_desc.replace(
                            leak.matched_text, "[termino tecnico eliminado]"
                        )
                    ac = ac.model_copy(update={"description": cleaned_desc})
                cleaned_criteria.append(ac)
            req = req.model_copy(update={"acceptance_criteria": cleaned_criteria})

        repaired.append(req)
    return repaired
