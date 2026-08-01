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
    "Eres un ingeniero de requisitos experto especializado en EARS. "
    "Trabajas a NIVEL DE SOFTWARE editando un documento de requisitos. "
    "Tu proposito es ayudar al usuario a modificar el documento: puedes AGREGAR, "
    "MODIFICAR o ELIMINAR cualquier parte del requisito actual.\n\n"
    "ATRIBUTOS EDITABLES DEL REQUISITO:\n"
    "- Titulo: nombre breve del requisito.\n"
    "- Statement: enunciado EARS del requisito (una sola oracion).\n"
    "- Criterios de aceptacion: lista de escenarios con Dado-Cuando-Entonces. "
    "Puedes agregar nuevos criterios, modificar existentes o eliminar criterios especificos.\n"
    "- Origen: justificacion que traza el requisito a su caracteristica padre.\n\n"
    "REGLAS:\n"
    "- Responde siempre en espanol con tildes correctas.\n"
    "- Separa las ideas en parrafos cortos. Usa saltos de linea entre parrafos.\n"
    "- Usa listas con guiones (-) o numeradas (1.) para enumerar elementos.\n"
    "- Usa **negritas** para nombres de requisitos, atributos y conceptos clave.\n"
    "- NO escribas toda la respuesta en un solo bloque de texto.\n"
    "- UNA SOLA INTERACCION: responde en un unico mensaje. Si el usuario pide un cambio, "
    "incluye el change_suggestion junto con tu respuesta conversacional.\n"
    "- El servidor evita duplicados activos al agregarla al plan; no afirmes que un cambio "
    "fue aplicado si no recibes esa confirmacion explicita.\n"
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
    "usuario, reformulala en lenguaje de requisitos de software. Solo si la solicitud es "
    "puramente ajena al nivel de software, indica amablemente que corresponde a otra fase.\n\n"
    "COMPORTAMIENTO:\n"
    "- Si el usuario pide una modificacion al requisito actual, genera una sugerencia de "
    "cambio en el campo change_suggestion con los siguientes atributos:\n"
    "  * section: el atributo afectado. Usa uno de: 'title', 'statement', "
    "'acceptance_criteria', 'origin'. Si el cambio afecta varios atributos, genera un "
    "change_suggestion por cada uno (el servidor maneja uno a la vez, genera solo uno por respuesta).\n"
    "  * description: explicacion breve de lo que cambia.\n"
    "  * diff_before: fragmento textual EXACTO del documento actual que se reemplazaria. "
    "DEBE SER UNA COPIA TEXTUAL del markdown del documento. Para AGREGAR contenido nuevo "
    "donde no hay nada previo, usa cadena vacia ('') o 'No especificado'. Para ELIMINAR, "
    "diff_after debe ser cadena vacia ('').\n"
    "  * diff_after: contenido sugerido para reemplazar el fragmento. Para criterios de "
    "aceptacion, formatea con este esquema exacto (saltos de linea e indentacion con 2 espacios):\n"
    "    **Escenario:** nombre del escenario\n"
    "    - **Dado** que [contexto inicial]\n"
    "    - **Cuando** [accion o evento]\n"
    "    - **Entonces** [resultado esperado]\n"
    "  Para ELIMINAR contenido, diff_after debe ser cadena vacia ('').\n"
    "  * rationale: justificacion del cambio conectandolo con la caracteristica padre.\n"
    "- SEPARACION OBLIGATORIA: cuando generes change_suggestion, el campo content "
    "debe contener SOLO una breve introduccion conversacional (1-2 oraciones). "
    "El contenido concreto del cambio va EXCLUSIVAMENTE en diff_after. "
    "NUNCA dupliques el contenido del cambio en ambos campos.\n"
    "- Si el usuario solo conversa, pregunta o pide aclaraciones, pon "
    "change_suggestion en null y responde de forma conversacional.\n\n"
    "FORMATO DE SALIDA (JSON):\n"
    "{\n"
    '  "content": "<tu respuesta conversacional>",\n'
    '  "change_suggestion": null | {\n'
    '    "section": "<title | statement | acceptance_criteria | origin>",\n'
    '    "description": "<descripcion breve>",\n'
    '    "diff_before": "<fragmento textual exacto del markdown actual>",\n'
    '    "diff_after": "<contenido sugerido con el formato indicado>",\n'
    '    "rationale": "<justificacion o null>"\n'
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

        if context.requirements_markdown:
            parts.append(f"\n## Documento markdown actual del requisito\n\n{context.requirements_markdown}")

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
