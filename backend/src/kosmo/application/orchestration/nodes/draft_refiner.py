from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import get_deps, validate_inputs, verify_scope
from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.state import KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced

_PROHIBITED_TERMS = {
    "api", "endpoint", "rest", "graphql", "http", "json", "xml",
    "base de datos", "tabla", "columna", "sql", "nosql", "postgresql",
    "mongodb", "redis", "servidor", "contenedor", "frontend", "backend",
    "componente", "modulo", "clase", "metodo", "funcion", "controlador",
    "middleware", "framework", "libreria", "react", "angular", "django",
    "spring", "node", "python", "java", "microservicio", "docker", "kubernetes",
}

_REFINER_FEATURE_SYSTEM = (
    "Eres un Analista de Producto Senior con 15 anos de experiencia definiendo "
    "caracteristicas de producto para equipos de ingenieria. Conviertes ideas "
    "en bruto en caracteristicas de producto PROFESIONALES y bien estructuradas.\n\n"
    "PROCESO DE REFINAMIENTO:\n"
    "1. EXTRAE LA ESENCIA: Identifica el nucleo de la idea. Que necesidad "
    "de negocio resuelve? Para que actor?\n"
    "2. FORMALIZA EL TITULO: Verbo en infinitivo + objeto de negocio especifico. "
    "Ej: 'Notificar reposicion de inventario con alertas configurables', NO "
    "'Notificaciones' ni 'Alertas'.\n"
    "3. ESTRUCTURA LA DESCRIPCION (formula de 4 partes):\n"
    "   - QUE hace la funcionalidad\n"
    "   - PARA QUIEN esta dirigida (rol de negocio)\n"
    "   - BAJO QUE CONDICION se activa o aplica\n"
    "   - QUE VALOR DE NEGOCIO aporta\n"
    "4. ENRIQUECE CON CONTEXTO: Infiere detalles del dominio que hagan la "
    "descripcion mas concreta y especifica.\n"
    "5. ELIMINA AMBIGUEDAD: Reemplaza terminos vagos como 'mejorar', "
    "'optimizar', 'gestionar' con verbos concretos y medibles.\n\n"
    "TERMINOS PROHIBIDOS (causan RECHAZO):\n"
    "NO uses: API, endpoint, REST, GraphQL, HTTP, JSON, base de datos, tabla, "
    "columna, SQL, NoSQL, PostgreSQL, MongoDB, Redis, servidor, contenedor, "
    "frontend, backend, componente, modulo, clase, metodo, funcion, controlador, "
    "middleware, framework, libreria, React, Angular, Django, Spring, Node, "
    "Python, Java, microservicio, Docker, Kubernetes.\n\n"
    "ORTOGRAFIA OBLIGATORIA: Usa tildes, enyes y acentos correctos del espanol."
)

_REFINER_DOCUMENT_SYSTEM = (
    "Eres un Editor Senior de Documentos de Negocio con 12 anos de experiencia "
    "en refinamiento de especificaciones funcionales. Aplicas mejoras QUIRURGICAS "
    "sin reescribir desde cero.\n\n"
    "PRINCIPIOS DE EDICION:\n"
    "1. PRESERVAR LA INTENCION: Mantienes las ideas, decisiones y contenido "
    "que el usuario anadio. NUNCA eliminas contenido del usuario.\n"
    "2. REFINAR, NO REESCRIBIR: Corriges estructura, completas secciones "
    "incompletas, mejoras redaccion. No generas contenido desde cero.\n"
    "3. CAPA DE NEGOCIO EXCLUSIVAMENTE: Trabajas en la perspectiva del "
    "usuario y del negocio. JAMAS anades terminos tecnicos.\n"
    "4. COMPLETAR VACIOS: Si detectas secciones con poco contenido, las "
    "enriqueces con analisis de negocio adicional.\n"
    "5. CORREGIR ESTRUCTURA: Aseguras que headings, listas y parrafos "
    "sigan una jerarquia logica.\n\n"
    "TERMINOS PROHIBIDOS (causan RECHAZO):\n"
    "NO uses: API, endpoint, REST, GraphQL, HTTP, JSON, base de datos, tabla, "
    "columna, SQL, NoSQL, PostgreSQL, MongoDB, Redis, servidor, contenedor, "
    "frontend, backend, componente, modulo, clase, metodo, funcion, controlador, "
    "middleware, framework, libreria, React, Angular, Django, Spring, Node, "
    "Python, Java, microservicio, Docker, Kubernetes.\n\n"
    "ORTOGRAFIA OBLIGATORIA: Usa tildes, enyes y acentos correctos del espanol."
)


@traced("draft_refiner.execute")
async def draft_refiner_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    verify_scope(state)

    deps = get_deps(config)

    validation_error = validate_inputs(
        state,
        ["current_draft", "improve_instruction"],
        agent_id="draft_refiner",
    )
    if validation_error:
        return validation_error

    records = list(state.tool_call_history)
    iteration = state.generation_attempts + 1
    prefs = state.shared_scratchpad.get("preference_retriever_output", {})
    preferences_prompt = prefs.get("preferences_prompt", "") if isinstance(prefs, dict) else ""

    current_content = state.shared_scratchpad.get("current_draft", "")
    improve_instruction = state.shared_scratchpad.get("improve_instruction", "")
    phase_context = state.shared_scratchpad.get("phase_context", "")

    is_feature = phase_context == "features"

    if is_feature:
        system = _REFINER_FEATURE_SYSTEM
        response_instruction = (
            "Responde con el documento completo mejorado. "
            "La primera linea DEBE ser el titulo de la caracteristica en texto plano. "
            "La segunda linea en adelante DEBE ser la descripcion de valor de negocio en texto plano. "
            "NO uses negritas (**), cursivas (*) ni prefijos como 'Titulo:' o 'Descripcion:'. "
            "Entrega el titulo y la descripcion como texto limpio sin formato."
        )
    else:
        system = _REFINER_DOCUMENT_SYSTEM
        response_instruction = "Responde con el documento completo mejorado en Markdown."

    if preferences_prompt:
        system += f"\n\n{preferences_prompt}"

    prompt = PromptTemplate(
        system_prompt=system,
        user_prompt=f"""## Instrucción de mejora
{improve_instruction}

## Documento actual
{current_content[:4000]}

## Tarea
Mejora este documento según la instrucción. Mantén el contenido del usuario.
Refina estructura, completa lo incompleto, corrige formato.
{response_instruction}""",
    )

    records.append(
        ToolCallRecord(
            agent_id="draft_refiner",
            tool_name="llm_complete",
            params={"iteration": iteration, "action": "improve", "context": phase_context},
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
            "errors": ["Draft refiner LLM call failed"],
            "validation_status": "needs_revision",
            "tool_call_history": records,
        }

    refined = response.content or ""
    prohibited = [t for t in _PROHIBITED_TERMS if t in refined.lower()]
    if prohibited:
        records[-1].result = "refined_with_warnings"
        records[-1].error = f"Prohibited terms: {', '.join(prohibited[:5])}"
    else:
        records[-1].result = "refined"

    return {
        "generation_attempts": iteration,
        "validation_status": "pending_review",
        "shared_scratchpad": {
            **state.shared_scratchpad,
            "generated_content_md": response.content,
            "refined_content": response.content,
        },
        "tool_call_history": records,
    }
