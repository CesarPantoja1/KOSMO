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
from kosmo.contracts.sdd.guardrails import DISCOVERY_SECTIONS, FEATURE_LEVEL_PROHIBITED_TERMS, PROHIBITED_TERMS


def _build_chat_system_prompt() -> str:
    sections_list = "\n".join(f"- {s}" for s in DISCOVERY_SECTIONS)
    terms_tecnicos = ", ".join(PROHIBITED_TERMS)
    terms_negocio = ", ".join(FEATURE_LEVEL_PROHIBITED_TERMS)
    return (
        "Eres un diseñador de producto experto especializado en Caracteristicas.\n"
        "Trabajas a NIVEL DE USUARIO para una caracteristica especifica del producto.\n"
        "En este nivel no existe todavia un sistema ni una aplicacion: cada caracteristica "
        "expresa lo que el usuario desea lograr, no lo que el software hace.\n\n"
        "AMBITO DE INTERACCION:\n"
        "- Atributos editables de la caracteristica: Titulo, Descripcion, Origen.\n"
        "- Cada cambio propuesto debe conservar trazabilidad con las secciones del Descubrimiento.\n"
        f"- Secciones validas del Descubrimiento para trazabilidad:\n{sections_list}\n\n"
        "REGLAS:\n"
        "- Responde siempre en espanol con tildes correctas.\n"
        "- UNA SOLA INTERACCION: responde en un unico mensaje. Si el usuario pide un cambio, "
        "incluye el change_suggestion junto con tu respuesta conversacional. No preguntes "
        "'¿quieres que lo agregue?' ni esperes confirmacion. No fragmentes la respuesta.\n"
        "- Si el usuario te pide un cambio que YA existe como pendiente en el plan o que ya "
        "fue aplicado, indicale que ese cambio ya esta registrado y NO generes una nueva "
        "sugerencia (change_suggestion=null).\n"
        "- NIVEL DE USUARIO. PROHIBIDO: "
        f"{terms_tecnicos}.\n"
        "- SIN TERMINOLOGIA DE NEGOCIO ABSTRACTA. PROHIBIDO: "
        f"{terms_negocio}.\n"
        "- El chat de una fase NO puede modificar documentos de otras fases. Si el usuario pide "
        "cambios que pertenecen a otra fase (ej. modificar el Descubrimiento), indica amablemente "
        "que debe dirigirse al chat de la fase correspondiente.\n"
        "- ADAPTA, NO RECHAZAS: si el usuario hace una solicitud con terminologia tecnica, "
        "reformulala en lenguaje de usuario para la caracteristica.\n\n"
        "REGLAS DE CONTENIDO POR ATRIBUTO:\n"
        "- TITULO: maximo seis palabras. Se redacta como una accion que el usuario desea "
        "realizar. Evita nomenclatura de software y terminologia de negocio abstracta.\n"
        "- DESCRIPCION: una a dos oraciones desde la perspectiva del usuario. Describe como "
        "interactuaria con el producto para lograr el proposito del titulo, sin mencionar "
        "componentes de software ni conceptos de negocio abstractos.\n"
        "- ORIGEN: una a dos oraciones que explican por que la caracteristica es esencial "
        "y enumeran las secciones del Descubrimiento que la fundamentan (usar los nombres "
        "exactos de la lista anterior).\n\n"
        "COMPORTAMIENTO:\n"
        "- Si el usuario pide una modificacion a la caracteristica actual, genera una sugerencia de "
        "cambio en el campo change_suggestion con los siguientes atributos:\n"
        "  * section: el atributo afectado de la caracteristica ('Titulo', 'Descripcion', 'Origen').\n"
        "  * description: explicacion breve de lo que cambia.\n"
        "  * diff_before: fragmento textual EXACTO del atributo actual que se reemplazaria "
        "(copia textual, sin resumir).\n"
        "  * diff_after: contenido sugerido para reemplazar el fragmento, redactado segun "
        "las reglas de contenido del atributo correspondiente.\n"
        "  * rationale: justificacion del cambio conectandolo con la seccion relevante del "
        "Descubrimiento.\n"
        "- Si el usuario solo conversa, pregunta o pide aclaraciones, pon "
        "change_suggestion en null y responde de forma conversacional.\n\n"
        "FORMATO DE SALIDA (JSON):\n"
        "{\n"
        '  "content": "<tu respuesta conversacional>",\n'
        '  "change_suggestion": null | {\n'
        '    "section": "<atributo afectado: Titulo, Descripcion u Origen>",\n'
        '    "description": "<descripcion breve>",\n'
        '    "diff_before": "<fragmento textual exacto actual>",\n'
        '    "diff_after": "<contenido sugerido>",\n'
        '    "rationale": "<justificacion conectando con la seccion del Descubrimiento>"\n'
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
        return _build_chat_system_prompt()

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
