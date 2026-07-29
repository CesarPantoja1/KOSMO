from __future__ import annotations

from typing import Any

from kosmo.contracts import RespuestaChatLLM
from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import FeatureChatContext
from kosmo.contracts.pipeline.phase_outputs import (
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase

_FEATURES_CHAT_SYSTEM_PROMPT = (
    "Eres un asistente conversacional especializado en Características de producto.\n"
    "Trabajas a NIVEL DE USUARIO para una característica específica del producto.\n\n"
    "ÁMBITO DE INTERACCIÓN:\n"
    "- Expresas lo que el usuario desea lograr con el producto.\n"
    "- Atributos editables de la característica: Título, Descripción, Origen.\n"
    "- Cada cambio propuesto debe conservar trazabilidad con las secciones del Descubrimiento.\n\n"
    "REGLAS:\n"
    "- Responde siempre en español con tildes correctas.\n"
    "- Mantén el análisis a NIVEL DE USUARIO. PROHIBIDO: API, base de datos, "
    "microservicios, endpoints, servidores, lenguajes de programación, frameworks, "
    "protocolos, arquitectura, deployment, Docker, cloud, SQL, HTTP, REST, GraphQL, "
    "backend, frontend, cache, Redis, MongoDB, PostgreSQL, Kubernetes, AWS, GCP, "
    "Azure, plataforma, sistema informático, aplicación web.\n"
    "- Evita terminología de negocio abstracta (ROI, KPI, monetización, propuesta de valor).\n"
    "- El chat de una fase NO puede modificar documentos de otras fases. Si el usuario pide "
    "cambios que pertenecen a otra fase (ej. modificar el Descubrimiento), indica amablemente "
    "que debe dirigirse al chat de la fase correspondiente.\n\n"
    "COMPORTAMIENTO:\n"
    "- Si el usuario pide una modificación a la característica actual, genera una sugerencia de "
    "cambio en el campo change_suggestion con los siguientes atributos:\n"
    "  * section: el atributo afectado de la característica ('Título', 'Descripción', 'Origen').\n"
    "  * description: explicación breve de lo que cambia.\n"
    "  * diff_before: fragmento textual EXACTO del atributo actual que se reemplazaría.\n"
    "  * diff_after: contenido sugerido para reemplazar el fragmento.\n"
    "  * rationale: justificación del cambio conectándolo con la sección relevante del Descubrimiento.\n"
    "- Si el usuario solo conversa, pregunta o pide aclaraciones, pon "
    "change_suggestion en null y responde de forma conversacional.\n\n"
    "FORMATO DE SALIDA (JSON):\n"
    "{\n"
    '  "content": "<tu respuesta conversacional>",\n'
    '  "change_suggestion": null | {\n'
    '    "section": "<atributo afectado: Título, Descripción u Origen>",\n'
    '    "description": "<descripción breve>",\n'
    '    "diff_before": "<fragmento textual exacto actual>",\n'
    '    "diff_after": "<contenido sugerido>",\n'
    '    "rationale": "<justificación conectando con la sección del Descubrimiento>"\n'
    "  }\n"
    "}\n"
)


class FeaturesChatMode:
    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.CARACTERISTICAS

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
        return _FEATURES_CHAT_SYSTEM_PROMPT

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return []

    def build_user_prompt(self, context: FeatureChatContext) -> str:
        from kosmo.domain.sdd.document_converters import document_to_markdown

        discovery_md = document_to_markdown(context.discovery_document)
        f = context.feature

        parts = [
            f"## Característica actual ({f.display_id})\n",
            f"- **Título**: {f.title}",
            f"- **Descripción**: {f.description}",
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
                errors.append("El campo content no puede estar vacío.")
            if output.change_suggestion is not None:
                cs = output.change_suggestion
                if not cs.section or not cs.section.strip():
                    errors.append("El campo section no puede estar vacío.")
                if not cs.description or not cs.description.strip():
                    errors.append("El campo description no puede estar vacío.")
                if not cs.diff_before or not cs.diff_before.strip():
                    errors.append("El campo diff_before no puede estar vacío.")
                if not cs.diff_after or not cs.diff_after.strip():
                    errors.append("El campo diff_after no puede estar vacío.")
                if cs.diff_before.strip() == cs.diff_after.strip():
                    errors.append("diff_before y diff_after son idénticos; la sugerencia no propone cambios reales.")
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
            "## Feedback de validación\n\n"
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
