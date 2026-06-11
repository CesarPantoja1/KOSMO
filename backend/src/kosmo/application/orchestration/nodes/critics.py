from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import (
    extract_generated_content,
    get_deps,
    verify_scope,
)
from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.state import AgentMessage, CritiqueRecord, KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced
from kosmo.domain.sdd.llm_helpers import extract_json
from kosmo.domain.sdd.structured_schemas import CriticOutputSchema

_QUALITY_CRITIC_SYSTEM = (
    "Eres un Auditor de Calidad de Requisitos EARS de Negocio con 10 años de experiencia "
    "en verificación de especificaciones funcionales. Evalúa CADA requisito contra "
    "una rúbrica de 6 dimensiones.\n\n"
    "PRINCIPIO RECTOR: Los requisitos deben describir QUÉ hace el sistema desde la "
    "perspectiva del negocio, NUNCA CÓMO se implementa. Cualquier referencia a tecnología "
    "es un BLOCKER automático.\n\n"
    "ORTOGRAFÍA OBLIGATORIA: Verifica que el contenido use tildes, eñes y acentos "
    "correctos del español. Penaliza la omisión de tildes como error de calidad.\n\n"
    "TÉRMINOS PROHIBIDOS (BLOCKER inmediato si aparecen): API, endpoint, REST, GraphQL, "
    "HTTP, JSON, base de datos, tabla, columna, SQL, NoSQL, PostgreSQL, MongoDB, Redis, "
    "servidor, contenedor, frontend, backend, componente, módulo, clase, controlador, "
    "middleware, framework, React, Angular, Django, Node, Python, Java, microservicio, "
    "Docker, Kubernetes, CDN, caché.\n\n"
    "RÚBRICA DE EVALUACIÓN (escala 1-10 por dimensión):\n\n"
    "1. PUREZA DE NEGOCIO (peso: 30%):\n"
    "   - 10: CERO términos técnicos, lenguaje 100% de negocio\n"
    "   - 7: Una mención dudosa pero no claramente técnica\n"
    "   - 3: Una fuga técnica menor\n"
    "   - 0: Fugas técnicas evidentes o múltiples -> BLOCKER\n\n"
    "2. CORRECCIÓN EARS (peso: 25%):\n"
    "   - 10: source_statement sigue EXACTAMENTE el patrón EARS declarado\n"
    "   - 7: Sigue el patrón pero con estructura levemente desviada\n"
    "   - 3: Usa keywords del patrón pero no la estructura correcta\n"
    "   - 0: No sigue el patrón EARS declarado -> BLOCKER\n\n"
    "3. VERIFICABILIDAD (peso: 20%):\n"
    "   - 10: Todos los criterios de aceptación son verificables por analista funcional\n"
    "   - 7: La mayoría de criterios son verificables, alguno es difuso\n"
    "   - 3: Menos de la mitad de criterios son verificables\n"
    "   - 0: Ningún criterio es verificable -> BLOCKER\n\n"
    "4. COMPLETITUD (peso: 10%):\n"
    "   - 10: Todos los campos requeridos presentes y completos\n"
    "   - 7: Un campo menor incompleto o ausente\n"
    "   - 3: Varios campos incompletos\n"
    "   - 0: Campos críticos vacíos (source_statement, response)\n\n"
    "5. NO-AMBIGÜEDAD (peso: 10%):\n"
    "   - 10: Lenguaje concreto, sin términos vagos\n"
    "   - 7: Una ambigüedad menor\n"
    "   - 3: Varias ambigüedades ('rápido', 'seguro', 'robusto' sin métrica)\n"
    "   - 0: Lenguaje completamente ambiguo\n\n"
    "6. COBERTURA (peso: 5%):\n"
    "   - 10: 2+ criterios, trigger presente, rationale presente\n"
    "   - 7: Al menos 1 criterio, trigger presente\n"
    "   - 3: 1 criterio, sin trigger, sin rationale\n"
    "   - 0: Sin criterios de aceptación\n\n"
    "SEVERITY:\n"
    "- 'blocker': cualquier dimensión con score < 5 O fuga técnica detectada\n"
    "- 'warning': alguna dimensión con score entre 5 y 6\n"
    "- 'none': todas las dimensiones con score >= 7\n\n"
    "Responde SIEMPRE en JSON especificando score por dimensión y severity general."
)


_CONSISTENCY_CRITIC_SYSTEM = (
    "Eres un Guardián de Consistencia de Requisitos de Negocio. Tu especialidad es "
    "detectar problemas estructurales en el conjunto de requisitos desde la perspectiva "
    "del negocio.\n\n"
    "Evalúa estos 5 tipos de problemas de consistencia:\n\n"
    "1. REQUISITOS DUPLICADOS: Dos o más requisitos que describen el mismo comportamiento "
    "de negocio con diferente redacción.\n\n"
    "2. REQUISITOS CONTRADICTORIOS: Requisitos que no pueden cumplirse simultáneamente "
    "según las reglas del negocio.\n\n"
    "3. TERMINOLOGÍA INCONSISTENTE: El mismo concepto de negocio aparece con diferentes "
    "nombres en distintos requisitos (ej. 'cliente' vs 'usuario comprador').\n\n"
    "4. VACÍOS DE COBERTURA: Categorías EARS que deberían tener requisitos según la "
    "naturaleza del negocio pero están vacías.\n\n"
    "5. DEPENDENCIAS NO DECLARADAS: Un requisito asume el comportamiento descrito en otro "
    "requisito sin hacer explícita la dependencia.\n\n"
    "SEVERITY:\n"
    "- 'blocker': contradicción detectada o categoría EARS crítica vacía\n"
    "- 'warning': duplicado detectado o terminología inconsistente\n"
    "- 'none': sin problemas de consistencia\n\n"
    "Responde SIEMPRE en JSON con severity, message, y lista de problemas encontrados."
)


_STYLE_CRITIC_SYSTEM = (
    "Eres un Editor de Estilo de Requisitos de Negocio EARS. Verificas que cada requisito "
    "cumpla con las convenciones de estilo desde la perspectiva del negocio.\n\n"
    "Evalúa estos 5 criterios de estilo:\n\n"
    "1. SINTAXIS EARS: Cada source_statement usa EXACTAMENTE las keywords del patrón "
    "declarado (WHEN para event, WHILE para state, WHERE para optional, IF/THEN para "
    "unwanted, 'shall' para ubiquitous).\n\n"
    "2. NOMENCLATURA CONSISTENTE: El campo 'system' es 'El sistema' en TODOS los "
    "requisitos.\n\n"
    "3. USO CORRECTO DE SHALL: Obligatorio (shall), recomendación (should), opcional (may). "
    "No uses 'must' ni 'will'.\n\n"
    "4. FORMATO DE CRITERIOS: Los acceptance_criteria siguen el formato "
    "Dado-Cuando-Entonces en el campo 'scenario'.\n\n"
    "5. LENGUAJE DE NEGOCIO: Los términos usados pertenecen al dominio del negocio, "
    "no a la implementación técnica. CERO jerga de desarrollo.\n\n"
    "6. ORTOGRAFÍA: El contenido usa tildes, eñes y acentos correctos del español.\n\n"
    "SEVERITY:\n"
    "- 'blocker': error de sintaxis EARS grave o nomenclatura inconsistentes\n"
    "- 'warning': desviaciones menores de estilo o formato\n"
    "- 'none': estilo correcto en todos los requisitos\n\n"
    "Responde SIEMPRE en JSON."
)


@traced("quality_critic.execute")
async def quality_critic_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    verify_scope(state)

    deps = get_deps(config)

    records = list(state.tool_call_history)
    content = extract_generated_content(state, max_chars=5000)

    if not content:
        return {
            "critique_log": [
                CritiqueRecord(
                    agent_id="quality_critic",
                    severity="blocker",
                    message="No hay contenido generado para evaluar",
                )
            ],
            "validation_status": "needs_revision",
            "tool_call_history": records,
        }

    records.append(
        ToolCallRecord(
            agent_id="quality_critic",
            tool_name="llm_complete",
            params={"check": "ears_quality_rubric"},
            result="invoked",
        )
    )

    prompt = PromptTemplate(
        system_prompt=_QUALITY_CRITIC_SYSTEM,
        user_prompt=f"""## Contenido a Evaluar
{content}

## Fase: {state.phase.value}

Evalúa CADA requisito contra la rúbrica de 6 dimensiones. Detecta fugas técnicas y ambigüedades.
Responde en JSON:
```json
{{"score": 8, "severity": "none", "message": "Evaluación detallada...", "findings": [], "dimension_scores": {{"pureza_negocio": 9, "corrección_ears": 8, "verificabilidad": 7, "completitud": 8, "no_ambigüedad": 9, "cobertura": 7}}}}
```
Severity: 'none' (aprobado), 'warning' (mejorable), 'blocker' (rechazado).""",
        response_schema=CriticOutputSchema,
    )

    try:
        response = await deps.llm_client.complete(prompt=prompt, temperature=0, max_tokens=4096)
    except Exception:
        records[-1].result = "llm_error"
        records[-1].error = "LLM call failed"
        return {
            "critique_log": [
                CritiqueRecord(
                    agent_id="quality_critic",
                    severity="warning",
                    message="Quality critic LLM call failed — skipping",
                )
            ],
            "validation_status": "approved",
            "tool_call_history": records,
        }

    if response.parsed is not None and isinstance(response.parsed, CriticOutputSchema):
        data = response.parsed.model_dump()
    else:
        data = _parse_critic(response.content)
    records[-1].result = data.get("severity", "none")
    verdict = _determine_verdict(data)

    findings = data.get("findings", [])
    findings_text = "; ".join(findings) if isinstance(findings, list) else str(findings)

    dimension_scores = data.get("dimension_scores", {})
    score_summary = ""
    if isinstance(dimension_scores, dict):
        score_summary = " | ".join(f"{k}: {v}/10" for k, v in dimension_scores.items())

    message = data.get("message", "")
    if score_summary:
        message = f"{message} [{score_summary}]"
    if findings_text:
        message = f"{message} Problemas: {findings_text[:400]}"

    return {
        "critique_log": [
            CritiqueRecord(
                agent_id="quality_critic",
                severity=data.get("severity", "none"),
                message=message[:500],
            )
        ],
        "validation_status": verdict,
        "tool_call_history": records,
    }


@traced("consistency_critic.execute")
async def consistency_critic_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    verify_scope(state)

    deps = get_deps(config)

    records = list(state.tool_call_history)
    content = extract_generated_content(state, max_chars=4000)

    existing_titles = [f.title for f in state.features]
    existing_text = "\n".join(f"- {t}" for t in existing_titles) or "Ninguna"

    mailbox_messages = state.agent_mailbox.get("consistency_critic", [])
    directed_requests = (
        [m for m in mailbox_messages if m.message_type == "request_review"]
        if mailbox_messages
        else []
    )
    focus_instructions = ""
    if directed_requests:
        focus_instructions = "\n\n## Peticiones dirigidas de otros agentes:\n" + "\n".join(
            f"- [{m.from_agent}]: {m.content}" for m in directed_requests
        )

    records.append(
        ToolCallRecord(
            agent_id="consistency_critic",
            tool_name="llm_complete",
            params={"check": "ears_consistency"},
            result="invoked",
        )
    )

    prompt = PromptTemplate(
        system_prompt=_CONSISTENCY_CRITIC_SYSTEM,
        user_prompt=f"""## Contenido Nuevo (Requisitos EARS)
{content}

## Funcionalidades ya registradas
{existing_text}

Verifica los 5 tipos de problemas de consistencia en los requisitos EARS.
{focus_instructions}
Responde en JSON:
```json
{{"severity": "none", "message": "Sin problemas de consistencia", "duplicates": [], "contradictions": [], "inconsistencies": [], "gaps": [], "dependencies": []}}
```""",
        response_schema=CriticOutputSchema,
    )

    try:
        response = await deps.llm_client.complete(prompt=prompt, temperature=0, max_tokens=4096)
    except Exception:
        records[-1].result = "llm_error"
        records[-1].error = "LLM call failed"
        return {
            "critique_log": [
                CritiqueRecord(
                    agent_id="consistency_critic",
                    severity="warning",
                    message="Consistency critic LLM call failed — skipping",
                )
            ],
            "validation_status": "approved",
            "tool_call_history": records,
        }
    if response.parsed is not None and isinstance(response.parsed, CriticOutputSchema):
        data = response.parsed.model_dump()
    else:
        data = _parse_critic(response.content)
    records[-1].result = data.get("severity", "none")
    verdict = _determine_verdict(data)

    return {
        "critique_log": [
            CritiqueRecord(
                agent_id="consistency_critic",
                severity=data.get("severity", "none"),
                message=data.get("message", ""),
            )
        ],
        "validation_status": verdict,
        "tool_call_history": records,
    }


@traced("style_critic.execute")
async def style_critic_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    verify_scope(state)

    deps = get_deps(config)

    records = list(state.tool_call_history)
    content = extract_generated_content(state, max_chars=4000)
    prefs = state.shared_scratchpad.get("preference_retriever_output", {})
    preferences_prompt = prefs.get("preferences_prompt", "") if isinstance(prefs, dict) else ""

    if not preferences_prompt:
        records.append(
            ToolCallRecord(
                agent_id="style_critic",
                tool_name="llm_complete",
                params={"check": "ears_style"},
                result="skipped_no_prefs",
            )
        )
        return {
            "critique_log": [
                CritiqueRecord(
                    agent_id="style_critic",
                    severity="none",
                    message="Sin preferencias de usuario para verificar",
                )
            ],
            "validation_status": "approved",
            "tool_call_history": records,
        }

    records.append(
        ToolCallRecord(
            agent_id="style_critic",
            tool_name="llm_complete",
            params={"check": "ears_style"},
            result="invoked",
        )
    )

    prompt = PromptTemplate(
        system_prompt=_STYLE_CRITIC_SYSTEM,
        user_prompt=f"""{preferences_prompt}

## Contenido a Evaluar (Requisitos EARS)
{content}

Verifica los 5 criterios de estilo EARS contra las preferencias del usuario.
Responde en JSON:
```json
{{"severity": "none", "message": "Estilo EARS correcto y consistente con preferencias"}}
```""",
        response_schema=CriticOutputSchema,
    )

    try:
        response = await deps.llm_client.complete(prompt=prompt, temperature=0, max_tokens=4096)
    except Exception:
        records[-1].result = "llm_error"
        records[-1].error = "LLM call failed"
        return {
            "critique_log": [
                CritiqueRecord(
                    agent_id="style_critic",
                    severity="warning",
                    message="Style critic LLM call failed — skipping",
                )
            ],
            "validation_status": "approved",
            "tool_call_history": records,
        }
    if response.parsed is not None and isinstance(response.parsed, CriticOutputSchema):
        data = response.parsed.model_dump()
    else:
        data = _parse_critic(response.content)
    records[-1].result = data.get("severity", "none")
    verdict = _determine_verdict(data)

    return {
        "critique_log": [
            CritiqueRecord(
                agent_id="style_critic",
                severity=data.get("severity", "none"),
                message=data.get("message", ""),
            )
        ],
        "validation_status": verdict,
        "tool_call_history": records,
        "agent_mailbox": _build_preference_feedback(data, preferences_prompt),
    }


def _parse_critic(raw: str) -> dict[str, object]:
    data = extract_json(raw)
    if isinstance(data, list):
        return data[0] if data else {}
    return data if isinstance(data, dict) else {}


def _determine_verdict(data: dict[str, object]) -> str | None:
    severity = data.get("severity", "none")
    if severity in ("blocker", "warning"):
        return "needs_revision"
    return "approved"


def _build_preference_feedback(
    data: dict[str, object], preferences_prompt: str
) -> dict[str, list[AgentMessage]]:
    messages: list[AgentMessage] = []
    severity = data.get("severity", "none")

    if preferences_prompt and severity == "none":
        messages.append(
            AgentMessage(
                from_agent="style_critic",
                to_agent="preference_feedback",
                message_type="preference_reinforced",
                content="User preferences were followed in the generated content",
                priority="normal",
                metadata={"context": "style_critic_approval"},
            )
        )
    elif preferences_prompt and severity in ("blocker", "warning"):
        message = str(data.get("message", ""))
        messages.append(
            AgentMessage(
                from_agent="style_critic",
                to_agent="preference_feedback",
                message_type="preference_violated",
                content=f"User preferences may have been violated: {message[:200]}",
                priority="high",
                metadata={"context": message[:500]},
            )
        )

    return {"preference_feedback": messages}
