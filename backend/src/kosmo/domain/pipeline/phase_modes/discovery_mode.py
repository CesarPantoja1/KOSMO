from __future__ import annotations

import json
from typing import Any

from kosmo.contracts.pipeline.orchestrator_ports import (
    PhaseMode,
    ToolDefinition,
)
from kosmo.contracts.pipeline.phase_contexts import (
    DiscoveryPhaseContext,
    EARSPhaseContext,
    FeaturesPhaseContext,
    SuggestFeaturesContext,
)
from kosmo.contracts.pipeline.phase_outputs import (
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.guardrails import (
    DISCOVERY_SECTIONS,
)
from kosmo.domain.sdd.output_guardrails import (
    detect_technical_terms,
)


class DiscoveryMode(PhaseMode):
    """Modo de fase para la etapa de Descubrimiento del pipeline KOSMO.

    Define las instrucciones que guían a la IA para generar un documento
    de visión de producto estructurado con 8 secciones obligatorias,
    reglas de formato, prohibiciones de contenido técnico y criterios
    mínimos de completitud.
    """

    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.DESCUBRIMIENTO

    @property
    def system_prompt(self) -> str:
        sections_desc = "\n".join(
            f"{i}. **{s}** — desarrollá esta sección con al menos 2 o 3 oraciones sustantivas."
            for i, s in enumerate(DISCOVERY_SECTIONS, 1)
        )
        return (
            "Eres un analista de negocio experto y estratega de producto.\n\n"
            "Tu tarea es generar un Documento de Visión de Producto estructurado "
            "en formato Markdown, basado en el nombre y la descripción del proyecto "
            "que el usuario te proporcionará.\n\n"
            "## Reglas de contenido\n\n"
            "- Usá exclusivamente **lenguaje de negocio**, centrado en el valor "
            "para el usuario, los objetivos comerciales y el dominio del problema.\n"
            "- **PROHIBIDO** mencionar tecnologías, bases de datos, lenguajes de "
            "programación, frameworks, protocolos, infraestructura, arquitectura "
            "de software o cualquier término técnico de implementación.\n"
            "- Cada sección debe contener al menos **2 o 3 oraciones** con "
            "información sustantiva y específica del proyecto, no genérica.\n"
            "- Redactá en **español** profesional.\n"
            "- Evitá listas genéricas sin contexto; cada afirmación debe estar "
            "anclada en el dominio del proyecto.\n\n"
            "## Estructura obligatoria\n\n"
            "El documento debe incluir exactamente estas 8 secciones con "
            "títulos de nivel 2 (##):\n\n"
            f"{sections_desc}\n\n"
            "## Formato de salida\n\n"
            "Respondé **ÚNICAMENTE** con un objeto JSON válido con esta "
            "estructura exacta:\n\n"
            '```json\n'
            '{"document": "## Visión\\n...\\n\\n'
            '## Espacio de problema\\n...\\n\\n'
            '## Actores\\n...\\n\\n'
            '## Propuesta de Valor\\n...\\n\\n'
            '## Casos de Uso\\n...\\n\\n'
            '## Capacidades Principales\\n...\\n\\n'
            '## Reglas de Negocio\\n...\\n\\n'
            '## Atributos de Calidad\\n..."}\n'
            '```\n\n'
            "El campo `document` debe contener el Markdown completo del "
            "documento. No incluyas texto fuera del JSON."
        )

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return []

    def build_user_prompt(
        self,
        context: (
            DiscoveryPhaseContext
            | FeaturesPhaseContext
            | EARSPhaseContext
            | SuggestFeaturesContext
        ),
    ) -> str:
        if isinstance(context, DiscoveryPhaseContext):
            return (
                f"Nombre del Proyecto: {context.project_name}\n"
                f"Descripción: {context.project_description}\n\n"
                "Generá el Documento de Visión de Producto completo "
                "siguiendo las instrucciones del sistema."
            )
        return (
            "Generá el Documento de Visión de Producto completo "
            "siguiendo las instrucciones del sistema."
        )

    def validate_output(self, output: Any) -> ValidationResult:
        text = self._extract_text(output)
        errors: list[str] = []
        warnings: list[str] = []

        if not text.strip():
            return ValidationResult(
                is_valid=False,
                errors=["El documento generado está vacío."],
            )

        for section in DISCOVERY_SECTIONS:
            if not self._has_section(text, section):
                errors.append(f"Falta la sección obligatoria: '{section}'.")
            else:
                section_content = self._extract_section_content(text, section)
                if len(section_content.split()) < 10:
                    warnings.append(
                        f"La sección '{section}' tiene menos de 10 palabras; "
                        "posiblemente no cumple con el mínimo de completitud."
                    )

        guardrail_result = detect_technical_terms(text)
        if not guardrail_result.passed:
            for v in guardrail_result.violations:
                errors.append(v.message)

        quality_score = 1.0 - (len(errors) * 0.15 + len(warnings) * 0.05)
        quality_score = max(0.0, min(1.0, quality_score))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            quality_score=quality_score,
        )

    def build_retry_prompt(
        self,
        original_prompt: str,
        errors: list[str],
        retry_count: int,
    ) -> str:
        errors_text = "\n".join(f"  - {e}" for e in errors)
        return (
            f"⚠️ INTENTO DE CORRECCIÓN #{retry_count + 1}\n\n"
            f"El documento generado anteriormente NO pasó la validación. "
            f"Errores encontrados:\n\n"
            f"{errors_text}\n\n"
            f"{original_prompt}\n\n"
            "Corregí todos los errores listados arriba y generá nuevamente "
            "el documento completo. Respondé solo con el JSON."
        )

    @staticmethod
    def _extract_text(output: object) -> str:
        if isinstance(output, str):
            return output
        if isinstance(output, dict):
            raw: dict[str, Any] = output  # type: ignore[assignment]
            for key in ("document", "raw_text"):
                value = raw.get(key)
                if isinstance(value, str) and value.strip():
                    return value
            try:
                return json.dumps(raw)
            except (TypeError, ValueError):
                return str(raw)
        return str(output)

    @staticmethod
    def _has_section(text: str, section_name: str) -> bool:
        import re

        pattern = rf"##\s+{re.escape(section_name)}\b"
        return bool(re.search(pattern, text, re.IGNORECASE))

    @staticmethod
    def _extract_section_content(text: str, section_name: str) -> str:
        import re

        pattern = rf"##\s+{re.escape(section_name)}\b(.*?)(?=##\s+\S|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match is None:
            return ""
        return match.group(1).strip()
