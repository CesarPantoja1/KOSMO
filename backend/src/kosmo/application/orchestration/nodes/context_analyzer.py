from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from kosmo.application.orchestration.helpers import get_deps, verify_scope
from kosmo.contracts.llm.ports import PromptTemplate
from kosmo.contracts.sdd.state import KOSMOState, ToolCallRecord
from kosmo.contracts.telemetry import traced
from kosmo.domain.sdd.llm_helpers import extract_json
from kosmo.contracts.sdd.schemas import ContextAnalyzerOutput


@traced("context_analyzer.execute")
async def context_analyzer_node(state: KOSMOState, config: RunnableConfig) -> dict[str, object]:
    """Extrae informacion estructurada del estado del proyecto para guiar generadores.

    Reads: graph_deps, phase, project_id, generation_attempts,
           max_iterations, discovery, features, requirements
    Writes: agent_outputs["context_analyzer"], tool_call_history
    """
    verify_scope(state)

    deps = get_deps(config)

    records = list(state.tool_call_history)
    analysis = _build_context_summary(state)

    records.append(
        ToolCallRecord(
            agent_id="context_analyzer",
            tool_name="llm_complete",
            params={"phase": state.phase.value},
            result="invoked",
        )
    )

    prompt = PromptTemplate(
        system_prompt=(
            "Eres un Arquitecto de Software Senior especializado en análisis de contexto "
            "de proyectos digitales. Tu misión es EXTRAER INFORMACIÓN ESTRUCTURADA del "
            "estado actual del proyecto para que otros agentes (generadores de discovery, "
            "features y requisitos EARS) produzcan contenido de ALTA CALIDAD y "
            "DOMAIN-SPECIFIC.\n\n"
            "METODOLOGÍA DE ANÁLISIS DE DOMINIO:\n"
            "1. IDENTIFICA EL DOMINIO: De la descripción del proyecto, extrae el sector "
            "(e-commerce, logística, salud, fintech, educación, etc.) y el subsector "
            "específico (B2B, B2C, marketplace, SaaS, etc.).\n"
            "2. IDENTIFICA ENTIDADES CLAVE: Nombra las entidades de negocio principales "
            "(no técnicas). Ej: pedido, producto, cliente, factura, proveedor, almacén.\n"
            "3. EVALÚA COMPLEJIDAD: Considera número de actores, reglas de negocio, "
            "integraciones, flujos de estado, y volumen de datos.\n"
            "4. IDENTIFICA BRECHAS: ¿Qué información falta para completar el análisis? "
            "¿Qué secciones del discovery están vacías o superficiales?\n"
            "5. RECOMIENDA FOCO: Basado en las brechas, ¿qué aspecto debe priorizar "
            "el generador en esta iteración?\n"
            "6. CONTEXT BRIEF: Resume el estado actual en 3-5 líneas para orientar "
            "a los generadores.\n\n"
            "EJEMPLOS DE ANÁLISIS DE DOMINIO:\n\n"
            "Proyecto: 'Sistema de gestión de inventario para pymes'\n"
            "ANÁLISIS CORRECTO:\n"
            "{\n"
            '  "domain": "Gestión de inventario y cadena de suministro B2B para '
            'pequeñas y medianas empresas del sector retail y distribución",\n'
            '  "key_entities": ["producto", "inventario", "almacén", "proveedor", '
            '"orden de compra", "movimiento de stock", "alerta de reabastecimiento", '
            '"reporte de rotación"],\n'
            '  "complexity_level": "medium",\n'
            '  "gaps_identified": ["Falta definir reglas de negocio para umbrales '
            'de reabastecimiento", "No se especifican los roles de usuario '
            '(administrador vs operador)", "Los casos de uso no cubren escenarios '
            'de conciliación de inventario"],\n'
            '  "recommended_focus": "Reglas de negocio y actores del sistema — '
            'sin estos, las features carecerán de contexto vinculante",\n'
            '  "context_brief": "Proyecto de gestión de inventario B2B para pymes '
            'con énfasis en control de stock en tiempo real y alertas. El discovery '
            'tiene una visión clara pero carece de reglas de negocio detalladas y '
            'definición de actores. Se recomienda priorizar la definición de '
            'umbrales de inventario y roles de usuario antes de generar '
            'características."\n'
            "}\n\n"
            "Proyecto: 'E-commerce de productos artesanales'\n"
            "ANÁLISIS CORRECTO:\n"
            "{\n"
            '  "domain": "E-commerce B2C de productos artesanales y hechos a mano '
            'con énfasis en la conexión entre artesanos y compradores",\n'
            '  "key_entities": ["producto artesanal", "artesano", "comprador", '
            '"pedido", "reseña", "categoría de producto", "pago", "envío", '
            '"devolución"],\n'
            '  "complexity_level": "high",\n'
            '  "gaps_identified": ["No se definen atributos de calidad como '
            'tiempos de respuesta esperados", "Los casos de uso no cubren '
            'el flujo de devolución", "Faltan reglas de negocio sobre '
            'comisiones y pagos a artesanos"],\n'
            '  "recommended_focus": "Reglas de negocio de pagos y atributos '
            'de calidad — críticos para la viabilidad del marketplace",\n'
            '  "context_brief": "Marketplace B2C de productos artesanales. '
            'El discovery describe bien la visión y los actores, pero las '
            'reglas de negocio sobre pagos/comisiones y los atributos de '
            'calidad están ausentes. Hay features en borrador que necesitan '
            'contexto vinculante del discovery para ser refinadas."\n'
            "}\n\n"
            "IMPORTANTE:\n"
            "- Sé ESPECÍFICO y CONCRETO. No uses términos vagos como 'varios' "
            "o 'diversos'.\n"
            "- Las entidades clave deben ser SUSTANTIVOS DE NEGOCIO, no técnicos.\n"
            "- Las brechas deben ser ACCIONABLES (el generador debe saber qué corregir).\n"
            "- El context_brief debe ser útil para orientar a los generadores.\n"
            "- Usa ortografía correcta del español: tildes, eñes, diéresis."
        ),
        user_prompt=f"""## Fase actual: {state.phase.value}
## Proyecto: {state.project_id}
## Descubrimiento: {analysis.get("discovery_summary", "No disponible")}
## Caracteristicas existentes: {analysis.get("feature_list", "Ninguna")}
## Requisitos existentes: {analysis.get("requirements_count", 0)}
## Intento actual: {state.generation_attempts + 1}/{state.max_iterations}

Produce un analisis estructurado en JSON:
```json
{{
  "domain": "dominio del proyecto en una frase",
  "key_entities": ["entidad1", "entidad2"],
  "complexity_level": "low|medium|high",
  "gaps_identified": ["brecha1"],
  "recommended_focus": "que aspecto priorizar en esta iteracion",
  "context_brief": "resumen de 3-5 lineas del estado actual"
}}
```""",
        response_schema=ContextAnalyzerOutput,
    )

    try:
        response = await deps.llm_client.complete(prompt=prompt, temperature=0, max_tokens=4096)
        if response.parsed is not None and isinstance(response.parsed, ContextAnalyzerOutput):
            data = response.parsed.model_dump()
        else:
            data = extract_json(response.content)
            if isinstance(data, list):
                data = data[0] if data else {}
        records[-1].result = "context_analyzed"
    except Exception:
        records[-1].result = "llm_error"
        records[-1].error = "LLM call failed"
        return {
            "agent_outputs": {**state.agent_outputs, "context_analyzer": {}},
            "tool_call_history": records,
            "errors": ["Context analyzer LLM call failed"],
        }

    return {
        "agent_outputs": {**state.agent_outputs, "context_analyzer": data},
        "tool_call_history": records,
    }


def _build_context_summary(state: KOSMOState) -> dict[str, object]:
    discovery_summary = ""
    if state.discovery:
        discovery_summary = state.discovery[:2000]

    feature_list = (
        "\n".join(f"- [{f.status.value}] {f.title}: {f.description[:100]}" for f in state.features)
        or "Ninguna"
    )

    return {
        "discovery_summary": discovery_summary,
        "feature_list": feature_list,
        "features_count": len(state.features),
        "requirements_count": len(state.requirements),
    }


def _empty_result(agent_name: str) -> dict[str, object]:
    return {
        "agent_outputs": {agent_name: {}},
        "tool_call_history": [],
    }
