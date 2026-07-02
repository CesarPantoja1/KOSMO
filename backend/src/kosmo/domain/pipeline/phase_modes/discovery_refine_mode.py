from __future__ import annotations

from typing import Any

from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import DiscoveryRefinePhaseContext
from kosmo.contracts.pipeline.phase_outputs import (
    DiscoveryPhaseOutput,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase

_DISCOVERY_REFINE_SYSTEM_PROMPT = (
    "Eres un analista de negocio sénior. Recibís un documento de descubrimiento de "
    "producto YA EXISTENTE y una instrucción de refinamiento del usuario.\n"
    "Tu tarea es reescribir el documento aplicando EXACTAMENTE lo que pide la "
    "instrucción: puede agregar, modificar o eliminar contenido o secciones.\n\n"
    "REGLAS DE REFINAMIENTO:\n"
    "- Parte del documento actual tal como está; respeta su estructura vigente.\n"
    "- Aplica únicamente los cambios solicitados; conserva intacto el resto del "
    "contenido.\n"
    "- NO reincorpores secciones que el usuario haya eliminado.\n"
    "- NO agregues secciones nuevas salvo que la instrucción lo pida de forma "
    "explícita.\n"
    "- Mantén todo a NIVEL DE NEGOCIO. PROHIBIDO: API, base de datos, "
    "microservicios, endpoints, servidores, lenguajes, frameworks, protocolos, "
    "arquitectura, deployment, Docker, cloud, SQL, HTTP, REST, GraphQL, backend, "
    "frontend, cache, Redis, MongoDB, PostgreSQL, Kubernetes, AWS, GCP, Azure.\n"
    "- No uses formato de historia de usuario (Como... quiero... para...).\n"
    "- Todo en español con tildes correctas.\n"
    "- Devuelve ÚNICAMENTE el documento completo en Markdown, sin texto introductorio "
    "ni explicaciones sobre los cambios realizados.\n"
)


class DiscoveryRefineMode:
    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.DESCUBRIMIENTO

    @property
    def system_prompt(self) -> str:
        return _DISCOVERY_REFINE_SYSTEM_PROMPT

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="validate_business_level",
                description="Verifica que el documento refinado se mantenga a nivel de "
                "negocio, sin jerga técnica ni de implementación",
                parameters={
                    "type": "object",
                    "properties": {
                        "document": {
                            "type": "string",
                            "description": ("El documento de descubrimiento refinado en formato markdown"),
                        }
                    },
                    "required": ["document"],
                },
            ),
        ]

    def build_user_prompt(self, context: DiscoveryRefinePhaseContext) -> str:
        from kosmo.domain.sdd.document_converters import document_to_markdown

        current_markdown = document_to_markdown(context.current_document)
        parts = [
            "## Documento actual de descubrimiento\n",
            current_markdown,
            "\n## Instrucción de refinamiento del usuario\n",
            context.user_instructions,
        ]
        if context.user_preferences:
            prefs = "\n".join(f"- {p.rule_text}" for p in context.user_preferences)
            parts.append(f"\n## Preferencias del usuario\n\n{prefs}")
        return "\n".join(parts)

    def validate_output(self, output: Any) -> ValidationResult:
        from kosmo.domain.pipeline.phase_validators.discovery_refine_validator import (
            validate_business_level,
        )
        from kosmo.domain.sdd.document_converters import markdown_to_document
        from kosmo.domain.sdd.output_guardrails import auto_repair_technical_terms

        raw_text: str = ""
        if isinstance(output, dict) and "document" in output:
            raw_text = str(output["document"])  # type: ignore[reportUnknownArgumentType]
        elif isinstance(output, dict) and "raw_text" in output:
            raw_text = str(output["raw_text"])  # type: ignore[reportUnknownArgumentType]
        elif isinstance(output, str):
            raw_text = output
        else:
            return ValidationResult(
                is_valid=False,
                errors=["Formato de salida no reconocido"],
            )

        raw_text = auto_repair_technical_terms(raw_text)
        doc = markdown_to_document(raw_text)
        return validate_business_level(doc)

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
            f"El documento refinado tiene los siguientes problemas:\n\n"
            f"{error_list}\n\n"
            f"Corrige estos problemas manteniendo el documento a nivel de negocio, sin "
            f"jerga técnica, y devuelve el documento completo en Markdown sin texto "
            f"introductorio."
        )

    def build_output(
        self,
        raw_output: Any,
        validation_result: ValidationResult,
        metadata: GenerationMetadata,
    ) -> DiscoveryPhaseOutput:
        from kosmo.domain.sdd.document_converters import (
            coerce_markdown_output,
            markdown_to_document,
        )

        doc = markdown_to_document(coerce_markdown_output(raw_output))
        return DiscoveryPhaseOutput(
            discovery_document=doc,
            validation_result=validation_result,
            generation_metadata=metadata,
        )
