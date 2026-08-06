from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from kosmo.contracts.pipeline.consistency_phase_context import ConsistencyPhaseContext
from kosmo.contracts.pipeline.orchestrator_ports import ToolDefinition
from kosmo.contracts.pipeline.phase_outputs import (
    ConsistencyReport,
    GenerationMetadata,
    ValidationResult,
)
from kosmo.contracts.sdd.document import SpecPhase

# ═══════════════════════════════════════════════════════════════════
# Bloques compartidos del builder de prompts
# ═══════════════════════════════════════════════════════════════════

_ROLE = "Eres un analista experto en trazabilidad de requisitos de software. "

_FIDELITY_RULES = (
    "## REGLAS DE ANALISIS\n\n"
    "1. LEE el documento fuente COMPLETO y cada artefacto destino.\n"
    "2. Para cada artefacto, determina una UNICA accion:\n"
    '   - "update": el cambio afecta el contenido del artefacto. '
    "DEBES sugerir el texto corregido.\n"
    '   - "delete": el concepto del que depende el artefacto fue ELIMINADO. '
    "El artefacto ya no tiene razon de existir.\n"
    '   - "keep": el artefacto NO esta relacionado con ningun cambio. '
    "NO lo incluyas en la respuesta.\n\n"
    "3. COPIA VERBATIM: 'suggested_before' debe ser una copia EXACTA y "
    "LITERAL de un fragmento del artefacto destino tal como aparece en la "
    "lista de artefactos. No parafrasees. Si el texto no existe exactamente "
    "en el artefacto, la correccion no se podra aplicar.\n"
    "4. ANALISIS SEMANTICO: no busques coincidencia literal entre el documento "
    "fuente y los artefactos. Evalua el significado.\n"
    "5. CAMBIOS COSMETICOS (ortografia, formato) que no alteran el significado "
    "NO generan impacto.\n"
    "6. Si el cambio modifica una REGLA DE NEGOCIO o ALCANCE FUNCIONAL, TODOS "
    "los artefactos que implementan esa regla estan afectados.\n"
    "7. Si el contenido contiene '[…contenido truncado…]', el texto fue "
    "recortado. Si necesitas un fragmento que no aparece, indica en la rationale "
    "que el cambio requiere revision manual.\n"
    "8. Prohibido usar el caracter guion largo. Usa punto, coma o dos puntos.\n\n"
)

_DIRECTION_DOWNSTREAM = {
    "Descubrimiento": (
        "Tu tarea es analizar CAMBIOS aplicados al documento de Descubrimiento "
        "y determinar si los artefactos de fases posteriores necesitan actualizarse "
        "para mantenerse fieles a la vision, alcance y reglas de negocio.\n\n"
    ),
    "Caracteristicas": (
        "Tu tarea es analizar CAMBIOS aplicados a las Caracteristicas y determinar "
        "si los artefactos de fases posteriores necesitan actualizarse.\n\n"
    ),
    "Requisitos": (
        "Tu tarea es analizar CAMBIOS aplicados a los Requisitos EARS y determinar "
        "si los artefactos de fases posteriores necesitan actualizarse.\n\n"
    ),
}

_DIRECTION_UPSTREAM = {
    "Caracteristicas": (
        "Tu tarea es analizar CAMBIOS aplicados a las Caracteristicas y determinar "
        "si contradicen la Vision, Alcance o reglas del documento de Descubrimiento. "
        "Evalua SOLO a nivel de negocio y alcance. NO documentes detalles tecnicos "
        "o de UI en el Descubrimiento. La accion 'delete' NO aplica: el Descubrimiento "
        "nunca debe eliminarse por cambios en caracteristicas.\n\n"
    ),
    "Requisitos": (
        "Tu tarea es analizar CAMBIOS aplicados a los Requisitos EARS y determinar "
        "si contradicen la Vision, Alcance o reglas del documento de Descubrimiento. "
        "Los requisitos refinan el comportamiento: solo un cambio de regla de negocio "
        "fundamental justifica modificar el Descubrimiento. NO documentes detalles "
        "tecnicos o sintaxis EARS en el Descubrimiento. La accion 'delete' NO aplica: "
        "el Descubrimiento nunca debe eliminarse por cambios en requisitos.\n\n"
    ),
    "RequisitosFeatures": (
        "Tu tarea es analizar CAMBIOS aplicados a los Requisitos EARS de una "
        "caracteristica y determinar si modifican el alcance, intencion o "
        "comportamiento esperado de la CARACTERISTICA PADRE.\n\n"
        "Para la caracteristica padre, determina una UNICA accion:\n"
        '   - "update": el cambio en los requisitos modifica el alcance, titulo '
        "o descripcion de la caracteristica (ej: un requisito agrega una "
        "funcionalidad no contemplada). DEBES sugerir el texto corregido.\n"
        '   - "keep": los cambios son detalles de implementacion que NO afectan '
        "el alcance. NO lo incluyas.\n\n"
    ),
}

_LEVEL_RULES_FEATURES = (
    "## NIVEL DE ANALISIS: Caracteristicas\n\n"
    "Las caracteristicas representan capacidades del producto. El campo 'Origen' "
    "de cada caracteristica contiene la cadena de derivacion declarada "
    "(ej: 'Se deriva de C01 y Reglas de negocio'). Usala como evidencia primaria "
    "de trazabilidad ANTES de inferir por semantica.\n\n"
)

_LEVEL_RULES_REQUIREMENTS = (
    "## NIVEL DE ANALISIS: Requisitos EARS\n\n"
    "Los requisitos representan comportamientos especificos en formato EARS. "
    "Identifica los codigos REQ-X.Y afectados e incluyelos en la rationale. "
    "Si un requisito cambia 'procesar pagos con tarjeta' por 'procesar pagos "
    "con cualquier metodo', la caracteristica padre amplio su alcance. "
    "Si el cambio solo refina criterios de aceptacion sin alterar la intencion "
    "general, la caracteristica NO esta afectada.\n\n"
)

_LEVEL_RULES_MODEL = (
    "## NIVEL DE ANALISIS: Diagramas de Actividad\n\n"
    "Los diagramas representan flujos de proceso (actores, pasos, decisiones). "
    "Analiza a nivel de flujo, no de formato PlantUML. Si cambia el numero de "
    "pasos o la logica de un proceso, el diagrama esta afectado. Si el cambio "
    "es cosmetico o solo afecta criterios de aceptacion, el diagrama NO esta "
    "afectado.\n\n"
)

_LEVEL_RULES_DISCOVERY = (
    "## NIVEL DE ANALISIS: Descubrimiento\n\n"
    "El Descubrimiento define vision, alcance y reglas de negocio. Evalua "
    "si el cambio contradice o amplia el alcance declarado. Solo 'update' "
    "es valido para este artefacto.\n\n"
)


def _output_schema(target_artifact: str) -> str:
    schemas = {
        "Feature": (
            '    {{"artifact_id": "<id exacto de la caracteristica>", '
            '"action": "update" | "delete", '
            '"rationale": "<explicacion en español>", '
            '"suggested_field": "<title o description>", '
            '"suggested_before": "<fragmento EXACTO del artefacto>", '
            '"suggested_after": "<texto sugerido>"}}'
        ),
        "EARSRequirement": (
            '    {{"artifact_id": "<id exacto de la feature, tal como aparece en la lista>", '
            '"action": "update" | "delete", '
            '"rationale": "<explicacion. Incluye codigos REQ-X.Y afectados>", '
            '"suggested_before": "<fragmento EXACTO del markdown EARS actual>", '
            '"suggested_after": "<fragmento corregido del markdown EARS>"}}'
        ),
        "ActivityDiagram": (
            '    {{"artifact_id": "<id exacto de la feature>", '
            '"action": "update" | "delete", '
            '"rationale": "<explicacion en español>", '
            '"suggested_field": "diagram_syntax", '
            '"suggested_before": "<fragmento PlantUML EXACTO del diagrama>", '
            '"suggested_after": "<fragmento PlantUML corregido>"}}'
        ),
        "DiscoveryDocument": (
            '    {{"artifact_id": "<id EXACTO del documento, tal como aparece en la lista de artefactos>", '
            '"action": "update", '
            '"rationale": "<explicacion en español>", '
            '"suggested_field": "<titulo de la seccion: ## Vision, ## Alcance, etc.>", '
            '"suggested_before": "<contenido EXACTO de la seccion a modificar>", '
            '"suggested_after": "<contenido corregido>"}}'
        ),
    }
    return schemas.get(target_artifact, schemas["Feature"])


_EMPTY_FALLBACK = (
    "Si ningun artefacto esta afectado, devuelve: "
    '{"actions": [], "overall_rationale": "Ningun artefacto requiere cambios."}'
)


def build_consistency_prompt(
    direction: str,
    source_label: str,
    target_artifact: str,
    extra_rules: str = "",
) -> str:
    if direction == "downstream":
        task = _DIRECTION_DOWNSTREAM.get(source_label, _DIRECTION_DOWNSTREAM["Descubrimiento"])
    elif direction == "upstream_features":
        task = _DIRECTION_UPSTREAM.get("Caracteristicas", "")
    elif direction == "upstream_requirements":
        task = _DIRECTION_UPSTREAM.get("Requisitos", "")
    elif direction == "upstream_requirements_features":
        task = _DIRECTION_UPSTREAM.get("RequisitosFeatures", "")
    else:
        task = ""
    schema = _output_schema(target_artifact)
    return (
        _ROLE
        + task
        + _FIDELITY_RULES
        + extra_rules
        + "## FORMATO DE SALIDA (JSON estricto)\n\n"
        + "Responde UNICAMENTE con el siguiente JSON, sin markdown ni texto adicional:\n"
        + "{\n"
        + '  "actions": [\n'
        + schema
        + "\n"
        + "  ],\n"
        + '  "overall_rationale": "<resumen general del analisis en español>"\n'
        + "}\n\n"
        + _EMPTY_FALLBACK
    )


# ═══════════════════════════════════════════════════════════════════
# Prompts generados por el builder (1 variable por skill registrado)
# ═══════════════════════════════════════════════════════════════════

_DISCOVERY_EXAMPLES = (
    "## EJEMPLOS\n\n"
    "Ejemplo 1 — Cambio de unidad:\n"
    '  Cambio: "peso en kilogramos" → "peso en libras"\n'
    '  Feature "Calculo de peso total" → accion: "update", '
    'razon: "La unidad de medida cambio de kg a lb, la feature debe reflejar libras."\n\n'
    "Ejemplo 2 — Eliminacion de concepto:\n"
    '  Cambio: se elimina la seccion "Gestion de Inventario" del documento fuente\n'
    '  Feature "Control de stock" → accion: "delete", '
    'razon: "El concepto de inventario ya no existe en el descubrimiento."\n\n'
    "Ejemplo 3 — Cambio cosmetico:\n"
    '  Cambio: se corrige una tilde en "Vision"\n'
    '  Feature "Dashboard de metricas" → NO incluir (accion "keep" implicita).\n\n'
)

_CONSISTENCY_SYSTEM_PROMPT = build_consistency_prompt(
    direction="downstream",
    source_label="Descubrimiento",
    target_artifact="Feature",
    extra_rules=_DISCOVERY_EXAMPLES,
)

CONSISTENCY_UPSTREAM_SYSTEM_PROMPT = build_consistency_prompt(
    direction="upstream_features",
    source_label="Caracteristicas",
    target_artifact="DiscoveryDocument",
    extra_rules="El artifact_id del documento de Descubrimiento es EXACTAMENTE "
    "el que aparece en la lista de artefactos. Copialo literalmente.\n\n",
)

CONSISTENCY_REQUIREMENTS_DOWNSTREAM_SYSTEM_PROMPT = build_consistency_prompt(
    direction="upstream_requirements_features",
    source_label="Requisitos",
    target_artifact="Feature",
    extra_rules=_LEVEL_RULES_REQUIREMENTS,
)

CONSISTENCY_REQUIREMENTS_UPSTREAM_SYSTEM_PROMPT = build_consistency_prompt(
    direction="upstream_requirements",
    source_label="Requisitos",
    target_artifact="DiscoveryDocument",
    extra_rules="El artifact_id del documento de Descubrimiento es EXACTAMENTE "
    "el que aparece en la lista de artefactos. Copialo literalmente.\n\n",
)

CONSISTENCY_FEATURES_DOWNSTREAM_SYSTEM_PROMPT = build_consistency_prompt(
    direction="downstream",
    source_label="Caracteristicas",
    target_artifact="EARSRequirement",
    extra_rules=_LEVEL_RULES_FEATURES,
)

CONSISTENCY_REQUIREMENTS_MODEL_SYSTEM_PROMPT = build_consistency_prompt(
    direction="downstream",
    source_label="Requisitos",
    target_artifact="ActivityDiagram",
    extra_rules=_LEVEL_RULES_MODEL,
)

CONSISTENCY_DISCOVERY_REQUIREMENTS_PROMPT = build_consistency_prompt(
    direction="downstream",
    source_label="Descubrimiento",
    target_artifact="EARSRequirement",
    extra_rules=_LEVEL_RULES_REQUIREMENTS + _DISCOVERY_EXAMPLES,
)

CONSISTENCY_DISCOVERY_MODEL_PROMPT = build_consistency_prompt(
    direction="downstream",
    source_label="Descubrimiento",
    target_artifact="ActivityDiagram",
    extra_rules=_LEVEL_RULES_MODEL,
)

CONSISTENCY_FEATURES_MODEL_PROMPT = build_consistency_prompt(
    direction="downstream",
    source_label="Caracteristicas",
    target_artifact="ActivityDiagram",
    extra_rules=_LEVEL_RULES_MODEL,
)

CONSISTENCY_VALIDATE_CREATE_FEATURE_PROMPT = (
    "Eres un analista de trazabilidad de software.\n"
    "Tu tarea es analizar un documento de Descubrimiento completo y una nueva "
    "caracteristica propuesta, realizando DOS tareas en una sola respuesta:\n\n"
    "1. DERIVA EL ORIGEN: identifica las secciones del Descubrimiento que "
    "fundamentan esta caracteristica. Recorre todas las secciones del documento "
    "(Vision, Espacio del problema, Actores, Propuesta de valor, Metas del "
    "producto, Alcance, Reglas de negocio y cualquier otra presente). "
    "Devuelve una cadena de trazabilidad en el campo 'origin' con el formato:\n"
    '   "Derivado de [seccion(es)] del descubrimiento."\n'
    "   Si la caracteristica no se relaciona claramente con ninguna seccion, usa:\n"
    '   "Sin relacion directa con las secciones del descubrimiento."\n\n'
    "2. VERIFICA COHERENCIA: determina si la caracteristica es consistente con "
    "el contenido de TODAS las secciones del Descubrimiento. Si la caracteristica "
    "contradice explicitamente la vision, el alcance declarado, los actores "
    "identificados, las metas definidas o cualquier regla de negocio, indica "
    "is_consistent=false y explica el motivo en el campo 'reason'.\n\n"
    "Responde UNICAMENTE con el siguiente JSON, sin markdown ni texto adicional:\n"
    "{\n"
    '  "origin": "<cadena de trazabilidad derivada>",\n'
    '  "is_consistent": true,\n'
    '  "reason": ""\n'
    "}\n\n"
    "Si la caracteristica NO es consistente:\n"
    "{\n"
    '  "origin": "<cadena de trazabilidad derivada>",\n'
    '  "is_consistent": false,\n'
    '  "reason": "<explicacion clara de la contradiccion, en español>"\n'
    "}\n\n"
    "IMPORTANTE: Siempre incluye el campo origin. No uses el caracter guion largo (—)."
)


class ConsistencyEvaluationMode:
    def __init__(
        self,
        phase_name: SpecPhase = SpecPhase.DESCUBRIMIENTO,
        system_prompt: str | None = None,
    ) -> None:
        self._phase_name = phase_name
        self._system_prompt = system_prompt or _CONSISTENCY_SYSTEM_PROMPT

    @property
    def phase_name(self) -> SpecPhase:
        return self._phase_name

    @property
    def temperature(self) -> float:
        return 0.2

    @property
    def max_tokens(self) -> int:
        return 16384

    @property
    def output_type(self) -> type[BaseModel]:
        return ConsistencyReport

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def available_tools(self) -> list[ToolDefinition]:
        return []

    def build_user_prompt(self, context: ConsistencyPhaseContext) -> str:
        changes_text = "\n".join(
            f"### Cambio en '{c.section}'\n"
            f"**Descripcion:** {c.description}\n"
            f"**Antes:**\n{c.diff.before[:15000]}{'[…truncado…]' if len(c.diff.before) > 15000 else ''}\n"
            f"**Despues:**\n{c.diff.after[:15000]}{'[…truncado…]' if len(c.diff.after) > 15000 else ''}\n"
            for c in context.applied_changes
        )
        artifacts_text = "\n".join(
            f'- [{a.artifact_type}] id={a.artifact_id}, titulo="{a.title}", '
            f'descripcion="{a.description[:12000]}'
            f'{"[…truncado…]" if len(a.description) > 12000 else ""}"'
            for a in context.downstream_artifacts
        )
        src = context.source_content
        truncated = "\n[…contenido truncado…]" if len(src) > 30000 else ""
        source_doc = (src[:30000] + truncated) if src else "(no disponible)"

        return (
            f"## Fase origen: {context.source_phase.value}\n"
            f"## Fase destino: {context.target_phase.value}\n\n"
            f"### Documento fuente actual:\n{source_doc}\n\n"
            f"### Cambios aplicados:\n{changes_text}\n\n"
            f"### Artefactos actuales en la fase destino:\n{artifacts_text}\n\n"
            "## Instrucciones\n\n"
            "Analiza cada artefacto contra los cambios aplicados y el documento fuente actual. "
            "Determina que accion requiere cada uno (update, delete, o keep). "
            "Para acciones 'update', incluye el texto sugerido.\n\n"
            "**IMPORTANTE:** El valor de 'suggested_before' debe ser una copia "
            "EXACTA y LITERAL de un fragmento del artefacto destino, tal como "
            "aparece en la lista de arriba. No lo parafrasees ni lo resumas. "
            "Si el texto no existe exactamente en el artefacto, la correccion "
            "no se podra aplicar.\n\n"
            "Responde UNICAMENTE en el formato JSON especificado."
        )

    def validate_output(self, output: Any, *, context: Any = None) -> ValidationResult:  # noqa: ARG002
        errors: list[str] = []
        if not isinstance(output, ConsistencyReport):
            errors.append("El output debe ser un ConsistencyReport.")
            return ValidationResult(is_valid=False, errors=errors)
        if output.actions:
            for idx, action in enumerate(output.actions):
                if not action.artifact_id:
                    errors.append(f"actions[{idx}] falta 'artifact_id'.")
                if not action.rationale:
                    errors.append(f"actions[{idx}] falta 'rationale'.")
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def build_validation_feedback(self, errors: list[str]) -> str:
        error_list = "\n".join(f"- {e}" for e in errors)
        return f"## Errores de validacion\n\n{error_list}\n\nCorrige los errores y genera una nueva respuesta."

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
            "Genera una nueva respuesta en el formato JSON especificado."
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
