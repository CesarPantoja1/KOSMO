from __future__ import annotations

import json
from typing import Any, cast

from kosmo.contracts.memory.user_preference import UserPreference
from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_contexts import (
    DiscoveryPhaseContext,
    EARSPhaseContext,
    FeaturesPhaseContext,
    SuggestFeaturesContext,
)
from kosmo.contracts.pipeline.phase_outputs import ValidationResult
from kosmo.contracts.sdd.document import SpecPhase

_FEATURES_SYSTEM_PROMPT = (
    "Eres un analista de sistemas y gerente de producto sénior. Tu tarea consiste en descomponer "
    "un documento de descubrimiento de producto (visión de negocio) en exactamente cinco (5) "
    "características funcionales iniciales clave del sistema.\n\n"
    "Cada característica debe ser una unidad funcional coherente y debe incluir los siguientes "
    "campos:\n"
    "- 'number': Un número secuencial entero comenzando desde 1 (por ejemplo: 1, 2, 3, 4, 5).\n"
    "- 'title': Un título conciso, orientado a la acción y en español (por ejemplo: "
    "'Gestión de catálogo de productos').\n"
    "- 'description': Una descripción detallada y clara (de al menos 20 caracteres) que "
    "explique qué hace la característica.\n"
    "- 'rationale': Una justificación de negocio (de al menos 15 caracteres) explicando "
    "por qué esta característica es valiosa y necesaria.\n"
    "- 'inferred_from': Una lista de nombres de secciones del documento de descubrimiento de "
    "las cuales se infiere esta característica (por ejemplo: ['Casos de uso', "
    "'Capacidades principales']).\n\n"
    "REGLAS CRÍTICAS DE CALIDAD:\n"
    "1. NO DUPLICADOS: Las características generadas deben ser distintas entre sí y no presentar "
    "solapamiento o redundancia semántica.\n"
    "2. EVITAR DETALLES TÉCNICOS: Está terminantemente prohibido incluir términos de "
    "implementación o técnicos como: API, base de datos, backend, frontend, microservicios, "
    "servidor, docker, SQL, etc. Describe las características en lenguaje funcional de negocio.\n"
    "3. EVITAR REPETICIONES: Si se te proporciona una lista de características existentes, NO "
    "generes características redundantes con ellas.\n"
    "4. IDIOMA: Todo el contenido debe estar en español con acentuación y ortografía "
    "correctas.\n\n"
    "FORMATO DE SALIDA:\n"
    "Debes responder ÚNICAMENTE con un objeto JSON válido con la siguiente estructura, sin "
    "texto de introducción ni de conclusión:\n"
    "```json\n"
    "{\n"
    '  "features": [\n'
    "    {\n"
    '      "number": 1,\n'
    '      "title": "Nombre de la característica",\n'
    '      "description": "Descripción detallada...",\n'
    '      "rationale": "Justificación detallada...",\n'
    '      "inferred_from": ["Sección A", "Sección B"]\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "```"
)


class FeaturesMode:
    def __init__(self) -> None:
        self._existing_titles: list[str] = []

    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.CARACTERISTICAS

    @property
    def system_prompt(self) -> str:
        return _FEATURES_SYSTEM_PROMPT

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="validate_feature_structure",
                description="Verifica que las características tengan todos los campos y formatos "
                "correctos",
            ),
            ToolDefinition(
                name="validate_feature_uniqueness",
                description="Verifica que no existan redundancias ni duplicados entre "
                "características",
            ),
        ]

    def build_user_prompt(
        self,
        context: DiscoveryPhaseContext
        | FeaturesPhaseContext
        | EARSPhaseContext
        | SuggestFeaturesContext,
    ) -> str:
        from kosmo.domain.sdd.document_converters import document_to_markdown

        # Limpiar títulos cacheados
        self._existing_titles = []

        discovery_md = ""
        existing_titles_list: list[str] = []
        user_prefs: list[Any] = []

        if isinstance(context, (FeaturesPhaseContext, SuggestFeaturesContext)):
            discovery_md = document_to_markdown(context.discovery_document)
            existing_titles_list = context.existing_feature_titles
            user_prefs = context.user_preferences
        elif isinstance(context, EARSPhaseContext):
            discovery_md = document_to_markdown(context.discovery_document)
            user_prefs = context.user_preferences
        else:
            user_prefs = context.user_preferences

        parts = [
            "## Documento de Descubrimiento de Producto\n",
            discovery_md,
        ]

        if existing_titles_list:
            self._existing_titles = list(existing_titles_list)
            existing_list = "\n".join(f"- {title}" for title in self._existing_titles)
            parts.append(
                "\n## Características Existentes (NO DUPLICAR NI REPETIR ESTAS "
                f"CARACTERÍSTICAS):\n\n{existing_list}"
            )

        if user_prefs:
            pref_strings: list[str] = []
            for p in user_prefs:
                if isinstance(p, UserPreference):
                    pref_strings.append(p.rule_text)
            if pref_strings:
                prefs = "\n".join(f"- {text}" for text in pref_strings)
                parts.append(f"\n## Preferencias del usuario:\n\n{prefs}")

        return "\n".join(parts)

    def validate_output(self, output: Any) -> ValidationResult:
        from kosmo.domain.pipeline.phase_validators.features_validator import (
            validate_feature_structure,
            validate_feature_uniqueness,
        )

        features_list: list[dict[str, Any]] = []

        if isinstance(output, dict):
            output_dict = cast(dict[str, object], output)
            if "features" in output_dict:
                raw_features = output_dict["features"]
                if isinstance(raw_features, list):
                    for item in cast(list[object], raw_features):
                        if isinstance(item, dict):
                            feat_dict: dict[str, Any] = {}
                            for k, v in cast(dict[object, object], item).items():
                                if isinstance(k, str):
                                    feat_dict[k] = v
                            features_list.append(feat_dict)
            elif "raw_text" in output_dict:
                try:
                    text = str(output_dict["raw_text"])
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0].strip()
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        parsed_dict = cast(dict[str, object], parsed)
                        if "features" in parsed_dict:
                            raw_features = parsed_dict["features"]
                            if isinstance(raw_features, list):
                                for item in cast(list[object], raw_features):
                                    if isinstance(item, dict):
                                        feat_dict: dict[str, Any] = {}
                                        for k, v in cast(dict[object, object], item).items():
                                            if isinstance(k, str):
                                                feat_dict[k] = v
                                        features_list.append(feat_dict)
                    elif isinstance(parsed, list):
                        for item in cast(list[object], parsed):
                            if isinstance(item, dict):
                                feat_dict: dict[str, Any] = {}
                                for k, v in cast(dict[object, object], item).items():
                                    if isinstance(k, str):
                                        feat_dict[k] = v
                                features_list.append(feat_dict)
                except Exception:
                    return ValidationResult(
                        is_valid=False,
                        errors=[
                            "El formato de salida no es un JSON válido con la clave 'features'."
                        ],
                    )
            else:
                return ValidationResult(
                    is_valid=False,
                    errors=["El formato de salida no contiene la clave 'features'."],
                )
        elif isinstance(output, list):
            for item in cast(list[object], output):
                if isinstance(item, dict):
                    feat_dict: dict[str, Any] = {}
                    for k, v in cast(dict[object, object], item).items():
                        if isinstance(k, str):
                            feat_dict[k] = v
                    features_list.append(feat_dict)
        else:
            return ValidationResult(
                is_valid=False,
                errors=["El formato de salida debe ser un JSON válido."],
            )

        struct_result = validate_feature_structure(features_list)
        uniq_result = validate_feature_uniqueness(features_list, self._existing_titles)

        all_errors = struct_result.errors + uniq_result.errors
        all_warnings = struct_result.warnings + uniq_result.warnings

        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
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
            f"La generación de características tiene los siguientes problemas:\n\n"
            f"{error_list}\n\n"
            f"Corrige estos problemas y vuelve a generar la lista completa de características "
            f"en formato JSON válido matching el esquema indicado."
        )
