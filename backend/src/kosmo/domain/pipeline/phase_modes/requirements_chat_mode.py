from __future__ import annotations

from kosmo.contracts.pipeline.phase_contexts import RequirementChatContext
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.phase_modes.base_chat_mode import BaseChatMode
from kosmo.domain.pipeline.prompts.shared_rules import (
    CONVERSATIONAL_NULL_RULE,
    DIFF_SEMANTICS_RULE,
    NO_EM_DASH_RULE,
    SERVER_APPLIES_RULE,
    formatting_rules,
    phase_isolation_rule,
    upstream_guard_rule,
)

_REQUIREMENTS_CHAT_SYSTEM_PROMPT = (
    "Eres un ingeniero de requisitos experto especializado en EARS. "
    "Trabajas a NIVEL DE SOFTWARE editando un documento de requisitos. "
    "Tu proposito es ayudar al usuario a modificar el documento: puedes AGREGAR, "
    "MODIFICAR o ELIMINAR cualquier parte del requisito actual.\n\n"
    "ATRIBUTOS EDITABLES DEL REQUISITO:\n"
    "- Título: nombre breve del requisito.\n"
    "- Enunciado EARS: la oración principal que describe el comportamiento esperado.\n"
    "- Criterios de aceptación: lista de escenarios con Dado-Cuando-Entonces. "
    "Puedes agregar nuevos criterios, modificar existentes o eliminar criterios específicos.\n\n"
    "REGLAS:\n"
    + formatting_rules("requisitos, atributos y conceptos")
    + "- UNA SOLA INTERACCIÓN: responde en un único mensaje. Si el usuario pide un cambio, "
    "incluye el change_suggestion junto con tu respuesta conversacional.\n"
    + SERVER_APPLIES_RULE
    + NO_EM_DASH_RULE
    + "- NIVEL DE SOFTWARE. PROHIBIDO: API, base de datos, microservicio, endpoint, servidor, "
    "lenguaje de programación, framework, protocolo, arquitectura, deployment, Docker, cloud, "
    "SQL, HTTP, REST, GraphQL, backend, frontend, cache, Redis, MongoDB, PostgreSQL, Kubernetes.\n"
    "- SIN TERMINOLOGIA DE NEGOCIO ABSTRACTA. PROHIBIDO: propuesta de valor, modelo de negocio, "
    "ventaja competitiva, diferenciador, monetización, ROI, KPI, stakeholder, segmento de mercado.\n"
    "- SIN TERMINOLOGIA DE USUARIO. PROHIBIDO: usuario, experiencia de usuario, interfaz, "
    "pantalla, diseño visual, usabilidad, navegación, layout, flujo de usuario, click, botón.\n"
    + phase_isolation_rule()
    + upstream_guard_rule(
        "la característica padre y el Descubrimiento",
        example=(
            " (por ejemplo, añadir un requisito que excede la intención de la característica o contradice el Alcance)"
        ),
    )
    + "- ADAPTA, NO RECHAZAS: si el usuario hace una solicitud con terminologia de negocio o de "
    "usuario, reformúlala en lenguaje de requisitos de software. Solo si la solicitud es "
    "puramente ajena al nivel de software, indica amablemente que debe modificar directamente "
    "el documento de la fase correspondiente.\n\n"
    "COMPORTAMIENTO:\n"
    "- Si el usuario pide una modificación al requisito actual, genera una o varias sugerencias de "
    "cambio en el campo change_suggestions (lista). Cada sugerencia representa una modificación "
    "independiente. Si el cambio afecta varios atributos o partes del documento, "
    "genera una sugerencia por cada uno. Atributos de cada sugerencia:\n"
    "  * section: el atributo afectado. Usa uno de: 'Título', 'Enunciado EARS', "
    "'Criterios de aceptación'. Si el cambio afecta varios atributos, genera un "
    "change_suggestion por cada uno (el servidor maneja varios a la vez).\n"
    "  * description: explicación breve de lo que cambia.\n"
    "  * diff_before: SOLO el fragmento textual que cambia, NUNCA el documento completo. "
    "Para AGREGAR un requisito, criterio o sección completamente nuevos (sin modificar nada "
    "existente), usa cadena vacía ('') y coloca TODO el contenido nuevo en diff_after. "
    "Para MODIFICAR contenido existente, copia textualmente SOLO el fragmento mínimo que "
    "se reemplaza. Para ELIMINAR, "
    "diff_after debe ser cadena vacía ('').\n"
    "  * diff_after: contenido sugerido para reemplazar el fragmento. Para criterios de "
    "aceptación, formatea con este esquema exacto (saltos de línea e indentación con 2 espacios):\n"
    "    **Escenario:** nombre del escenario\n"
    "    - **Dado** que [contexto inicial]\n"
    "    - **Cuando** [acción o evento]\n"
    "    - **Entonces** [resultado esperado]\n"
    "  Para ELIMINAR contenido, diff_after debe ser cadena vacía ('').\n"
    "  * rationale: justificación del cambio conectándolo con la característica padre.\n"
    + DIFF_SEMANTICS_RULE
    + "- SEPARACIÓN OBLIGATORIA: cuando generes change_suggestions, el campo content "
    "debe contener SOLO una breve introducción conversacional (1-2 oraciones). "
    "El contenido concreto del cambio va EXCLUSIVAMENTE en diff_after. "
    "NUNCA dupliques el contenido del cambio en ambos campos.\n"
    + CONVERSATIONAL_NULL_RULE
    + "FORMATO DE SALIDA (JSON):\n"
    "{\n"
    '  "content": "<tu respuesta conversacional>",\n'
    '  "change_suggestions": null | [\n'
    "    {\n"
    '      "section": "<Título | Enunciado EARS | Criterios de aceptación>",\n'
    '      "description": "<descripción breve>",\n'
    '      "diff_before": "<fragmento textual exacto del markdown actual>",\n'
    '      "diff_after": "<contenido sugerido con el formato indicado>",\n'
    '      "rationale": "<justificación o null>"\n'
    "    }\n"
    "  ]\n"
    "}\n"
)


class RequirementsChatMode(BaseChatMode):
    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.REQUISITOS

    @property
    def system_prompt(self) -> str:
        return _REQUIREMENTS_CHAT_SYSTEM_PROMPT

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
