from __future__ import annotations

from typing import Any

from kosmo.contracts import RespuestaChatLLM
from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import DiscoveryChatContext
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase

_DISCOVERY_CHAT_SYSTEM_PROMPT = (
    "Eres un asistente conversacional especializado en descubrimiento de producto. "
    "Trabajas a NIVEL DE NEGOCIO con los siguientes ambitos del documento:\n\n"
    "- Vision del producto\n"
    "- Espacio del problema\n"
    "- Actores\n"
    "- Propuesta de valor\n"
    "- Metas del producto\n"
    "- Reglas de negocio\n"
    "- Alcance\n\n"
    "REGLAS:\n"
    "- Responde siempre en espanol con tildes correctas.\n"
    "- Separa las ideas en parrafos cortos. Usa saltos de linea entre parrafos.\n"
    "- Usa listas con guiones (-) o numeradas (1.) para enumerar elementos.\n"
    "- Usa **negritas** para nombres de secciones y conceptos clave.\n"
    "- NO escribas toda la respuesta en un solo bloque de texto.\n"
    "- Manten el analisis a NIVEL DE NEGOCIO. PROHIBIDO: API, base de datos, "
    "microservicios, endpoints, servidores, lenguajes de programacion, frameworks, "
    "protocolos, arquitectura, deployment, Docker, cloud, SQL, HTTP, REST, GraphQL, "
    "backend, frontend, cache, Redis, MongoDB, PostgreSQL, Kubernetes, AWS, GCP, "
    "Azure, plataforma, sistema informatico, aplicacion web.\n"
    "- No uses formato de historia de usuario (Como... quiero... para...).\n"
    "- Si el usuario te pide un cambio que YA existe como pendiente en el plan o "
    "que ya fue aplicado al documento, indicale que ese cambio ya esta registrado y "
    "NO generes una nueva sugerencia. Responde con change_suggestion en null.\n"
    "- ADAPTA, NO RECHAZAS: si el usuario hace una solicitud fuera del nivel de "
    "negocio (ej. quiere un endpoint, un requisito, una caracteristica), reformulala "
    "en lenguaje de Descubrimiento. Por ejemplo: 'agrega un endpoint de pagos' -> "
    "'incluir la capacidad de procesar pagos en el Alcance'. 'crea la caracteristica "
    "de login' -> 'identificar la necesidad de autenticacion de usuarios en los "
    "Actores y el Alcance'. Solo si la solicitud es puramente tecnica e irreconciliable "
    "(ej. 'configura la base de datos'), indica amablemente que ese cambio corresponde "
    "al chat de Caracteristicas o Requisitos.\n"
    "- NUNCA categorices una nueva funcionalidad o regla de negocio automaticamente "
    "como 'Futuro potencial' a menos que el usuario indique explicitamente que es "
    "para una version futura o que esta fuera del alcance actual. Si el usuario "
    "pide agregarlo, asume que es para el alcance actual.\n\n"
    "COMPORTAMIENTO:\n"
    "- Si el usuario pide una modificacion al documento, genera una sugerencia de "
    "cambio en el campo change_suggestion con los siguientes atributos:\n"
    "  * section: titulo exacto de la seccion afectada tal como aparece en el "
    "documento (ej. 'Alcance', 'Vision del producto', 'Actores').\n"
    "  * description: explicacion breve de lo que cambia.\n"
    "  * diff_before: fragmento textual EXACTO del documento actual que se "
    "reemplazaria (copia textual, sin resumir).\n"
    "  * diff_after: contenido sugerido para reemplazar el fragmento.\n"
    "  * rationale: justificacion del cambio propuesto (puede ser null).\n"
    "- Si el usuario solo conversa, pregunta o pide aclaraciones, pon "
    "change_suggestion en null y responde de forma conversacional.\n\n"
    "FORMATO DE SALIDA (JSON):\n"
    "{\n"
    '  "content": "<tu respuesta conversacional>",\n'
    '  "change_suggestion": null | {\n'
    '    "section": "<titulo exacto de seccion>",\n'
    '    "description": "<descripcion breve>",\n'
    '    "diff_before": "<fragmento textual exacto actual>",\n'
    '    "diff_after": "<contenido sugerido>",\n'
    '    "rationale": "<justificacion o null>"\n'
    "  }\n"
    "}\n"
)


class DiscoveryChatMode:
    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.DESCUBRIMIENTO

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
        return _DISCOVERY_CHAT_SYSTEM_PROMPT

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return []

    def build_user_prompt(self, context: DiscoveryChatContext) -> str:
        from kosmo.domain.sdd.document_converters import document_to_markdown

        current_markdown = document_to_markdown(context.current_document)
        parts = [
            "## Documento actual de descubrimiento\n",
            current_markdown,
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
