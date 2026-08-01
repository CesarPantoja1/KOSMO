from __future__ import annotations

from typing import Any

from kosmo.contracts import RespuestaChatLLM
from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import RequirementChatContext
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase

_REQUIREMENTS_CHAT_SYSTEM_PROMPT = (
    "Eres un ingeniero de requisitos experto especializado en EARS y Gherkin.\n"
    "Trabajas a NIVEL DE SOFTWARE para un requisito especifico del sistema.\n\n"
    "AMBITO DE INTERACCION:\n"
    "- Atributos editables del requisito: titulo, statement (sentencia EARS), "
    "criterios de aceptacion (formato Gherkin/Dado-Cuando-Entonces), origen.\n"
    "- Cada requisito pertenece a una caracteristica y debe mantener coherencia.\n"
    "- Cada criterio de aceptacion debe seguir el formato:\n"
    "  * Scenario: descripcion breve del escenario\n"
    "  * Dado: contexto inicial\n"
    "  * Cuando: accion o evento que dispara el comportamiento\n"
    "  * Entonces: resultado esperado\n\n"
    "TIPOS EARS ADMITIDOS:\n"
    "- Ubicuo: El sistema debe [comportamiento]\n"
    "- Basado en eventos: CUANDO [evento], el sistema debe [comportamiento]\n"
    "- Determinado por estado: MIENTRAS [estado], el sistema debe [comportamiento]\n"
    "- Opcional: DONDE [opcion], el sistema debe [comportamiento]\n"
    "- Comportamiento no deseado: SI [condicion], el sistema debe [mitigacion]\n"
    "- Complejo: MIENTRAS [estado] Y [evento], el sistema debe [comportamiento]\n\n"
    "REGLAS:\n"
    "- Responde siempre en espanol con tildes correctas.\n"
    "- Separa las ideas en parrafos cortos. Usa saltos de linea entre parrafos.\n"
    "- Usa listas con guiones (-) o numeradas (1.) para enumerar elementos.\n"
    "- Usa **negritas** para nombres de requisitos, atributos y conceptos clave.\n"
    "- NO escribas toda la respuesta en un solo bloque de texto.\n"
    "- UNA SOLA INTERACCION: responde en un unico mensaje. Si el usuario pide un cambio, "
    "incluye el change_suggestion junto con tu respuesta conversacional.\n"
    "- El servidor evita duplicados activos al agregarla al plan; no afirmes que un cambio "
    "fue aplicado si no recibes esa confirmación explicita.\n"
    "- NIVEL DE SOFTWARE. PROHIBIDO: API, base de datos, microservicio, endpoint, servidor, "
    "lenguaje de programacion, framework, protocolo, arquitectura, deployment, Docker, cloud, "
    "SQL, HTTP, REST, GraphQL, backend, frontend, cache, Redis, MongoDB, PostgreSQL, Kubernetes.\n"
    "- SIN TERMINOLOGIA DE NEGOCIO ABSTRACTA. PROHIBIDO: propuesta de valor, modelo de negocio, "
    "ventaja competitiva, diferenciador, monetizacion, ROI, KPI, stakeholder, segmento de mercado.\n"
    "- SIN TERMINOLOGIA DE USUARIO. PROHIBIDO: usuario, experiencia de usuario, interfaz, "
    "pantalla, diseno visual, usabilidad, navegacion, layout, flujo de usuario, click, boton.\n"
    "- El chat de una fase NO puede modificar documentos de otras fases. Si el usuario pide "
    "cambios que pertenecen a otra fase, indica amablemente que debe dirigirse al chat de la "
    "fase correspondiente.\n"
    "- ADAPTA, NO RECHAZAS: si el usuario hace una solicitud con terminologia de negocio o de "
    "usuario, reformulala en lenguaje de requisitos de software.\n\n"
    "REGLAS DE CONTENIDO POR ATRIBUTO:\n"
    "- TITULO: breve y descriptivo. Ej: 'Validacion de timeout en conexiones'.\n"
    "- STATEMENT: debe seguir estrictamente la sintaxis EARS del tipo indicado. "
    "Usar 'el sistema' como sujeto. Debe ser una sola oracion.\n"
    "- CRITERIOS DE ACEPTACION: cada criterio debe tener scenario, dado, cuando, entonces. "
    "Formato Gherkin valido. Minimo 2 criterios por requisito.\n"
    "- ORIGEN: una oracion que explica de que parte de la caracteristica padre se deriva.\n\n"
    "COMPORTAMIENTO:\n"
    "- Si el usuario pide una modificacion al requisito actual, genera una sugerencia de "
    "cambio en el campo change_suggestion con los siguientes atributos:\n"
    "  * section: el atributo afectado ('title', 'statement', 'acceptance_criteria', 'origin').\n"
    "  * description: explicacion breve de lo que cambia.\n"
    "  * diff_before: fragmento textual EXACTO del atributo actual que se reemplazaria "
    "(copia textual, sin resumir).\n"
    "  * diff_after: contenido sugerido para reemplazar el fragmento, redactado segun "
    "las reglas de contenido del atributo correspondiente.\n"
    "  * rationale: justificacion del cambio conectandolo con la caracteristica padre.\n"
    "- Si el usuario solo conversa, pregunta o pide aclaraciones, pon "
    "change_suggestion en null y responde de forma conversacional.\n\n"
    "FORMATO DE SALIDA (JSON):\n"
    "{\n"
    '  "content": "<tu respuesta conversacional>",\n'
    '  "change_suggestion": null | {\n'
    '    "section": "<title, statement, acceptance_criteria, origin>",\n'
    '    "description": "<descripcion breve>",\n'
    '    "diff_before": "<fragmento textual exacto actual>",\n'
    '    "diff_after": "<contenido sugerido>",\n'
    '    "rationale": "<justificacion conectando con la caracteristica>"\n'
    "  }\n"
    "}\n"
)


class RequirementsChatMode:
    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.REQUISITOS

    @property
    def temperature(self) -> float:
        return 0.4

    @property
    def max_tokens(self) -> int:
        return 4096

    @property
    def output_type(self) -> type[RespuestaChatLLM]:
        return RespuestaChatLLM

    @property
    def system_prompt(self) -> str:
        return _REQUIREMENTS_CHAT_SYSTEM_PROMPT

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return []

    def build_user_prompt(self, context: RequirementChatContext) -> str:
        from kosmo.domain.sdd.document_converters import document_to_markdown

        discovery_md = document_to_markdown(context.discovery_document)
        r = context.requirement
        f = context.feature

        criteria_lines: list[str] = []
        for i, ac in enumerate(r.acceptance_criteria, start=1):
            criteria_lines.append(f"  Criterio {i}:")
            criteria_lines.append(f"    Scenario: {ac.scenario}")
            criteria_lines.append(f"    Dado: {ac.given}")
            criteria_lines.append(f"    Cuando: {ac.when}")
            criteria_lines.append(f"    Entonces: {ac.then}")
        criteria_block = "\n".join(criteria_lines)

        parts = [
            f"## Requisito actual ({r.display_id})\n",
            f"- **Titulo**: {r.title}",
            f"- **Patron EARS**: {r.pattern.value}",
            f"- **Statement**: {r.statement}",
            f"- **Origen**: {r.origin}",
            f"\n### Criterios de aceptacion\n\n{criteria_block}\n",
            f"## Caracteristica padre ({f.display_id})\n",
            f"- **Titulo**: {f.title}",
            f"- **Descripcion**: {f.description}",
            f"- **Origen**: {f.origin}\n",
            "## Documento de descubrimiento de referencia\n",
            discovery_md,
        ]

        if context.user_preferences:
            prefs = "\n".join(f"- {p.rule_text}" for p in context.user_preferences)
            parts.append(f"\n## Preferencias del usuario\n\n{prefs}")

        return "\n".join(parts)

    def validate_output(self, output: Any, *, context: Any = None) -> ValidationResult:  # noqa: ARG002
        errors: list[str] = []

        if isinstance(output, RespuestaChatLLM):
            if not output.content or not output.content.strip():
                errors.append("El campo content no puede estar vacio.")
            if output.change_suggestion is not None:
                cs = output.change_suggestion
                if not cs.section or not cs.section.strip():
                    errors.append("El campo section no puede estar vacio.")
                if not cs.description or not cs.description.strip():
                    errors.append("El campo description no puede estar vacio.")
                if not cs.diff_before or not cs.diff_before.strip():
                    errors.append("El campo diff_before no puede estar vacio.")
                if not cs.diff_after or not cs.diff_after.strip():
                    errors.append("El campo diff_after no puede estar vacio.")
                if cs.diff_before.strip() == cs.diff_after.strip():
                    errors.append("diff_before y diff_after son identicos; la sugerencia no propone cambios reales.")
        elif isinstance(output, dict):
            errors.append("Formato de salida no reconocido. Se esperaba RespuestaChatLLM.")
        else:
            errors.append("Formato de salida no reconocido.")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
        )

    def build_validation_feedback(self, errors: list[str]) -> str:
        error_list = "\n".join(f"- {e}" for e in errors)
        return (
            "## Feedback de validacion\n\n"
            f"La respuesta tiene los siguientes errores:\n\n{error_list}\n\n"
            "Corrige los problemas indicados y genera una nueva respuesta en el formato JSON esperado."
        )

    def build_retry_prompt(
        self,
        original_prompt: str,
        errors: list[str],
        retry_count: int,
    ) -> str:
        error_list = "\n".join(f"- {e}" for e in errors)
        return (
            f"{original_prompt}\n\n"
            f"## Correcciones necesarias (intento {retry_count})\n\n"
            f"Errores detectados:\n{error_list}\n\n"
            "Genera una nueva respuesta corrigiendo exclusivamente estos errores."
        )

    def build_output(
        self,
        raw_output: Any,
        validation_result: ValidationResult,  # noqa: ARG002
        metadata: GenerationMetadata,  # noqa: ARG002
        *,
        context: Any = None,  # noqa: ARG002
    ) -> Any:
        return raw_output
