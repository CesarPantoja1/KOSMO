from __future__ import annotations

from kosmo.contracts.pipeline.phase_contexts import FeatureChatContext
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.guardrails import DISCOVERY_SECTIONS, FEATURE_LEVEL_PROHIBITED_TERMS, PROHIBITED_TERMS
from kosmo.domain.pipeline.phase_modes.base_chat_mode import BaseChatMode


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
        "- Separa las ideas en parrafos cortos. Usa saltos de linea entre parrafos.\n"
        "- Usa listas con guiones (-) o numeradas (1.) para enumerar elementos.\n"
        "- Usa **negritas** para nombres de atributos y conceptos clave.\n"
        "- NO escribas toda la respuesta en un solo bloque de texto.\n"
        "- UNA SOLA INTERACCION: responde en un unico mensaje. Si el usuario pide un cambio, "
        "incluye el change_suggestion junto con tu respuesta conversacional. No preguntes "
        "'¿quieres que lo agregue?' ni esperes confirmacion. No fragmentes la respuesta.\n"
        "- Genera una sugerencia cuando el usuario solicite un cambio. El servidor evita "
        "duplicados activos al agregarla al plan; no afirmes que un cambio fue aplicado "
        "si no recibes esa confirmación explícita.\n"
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


class FeaturesChatMode(BaseChatMode):
    @property
    def phase_name(self) -> SpecPhase:
        return SpecPhase.CARACTERISTICAS

    @property
    def system_prompt(self) -> str:
        return _build_chat_system_prompt()

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
