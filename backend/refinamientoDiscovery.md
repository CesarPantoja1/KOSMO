# Refinamiento del Pipeline de Discovery — KOSMO Backend

## Resumen de la Sesión

Refactorización completa del pipeline multiagente de generación de Discovery y Requisitos EARS. El objetivo fue garantizar respuestas JSON limpias, documentos con formato visual profesional (markdown enriquecido), eliminación de duplicación bold+plain, corrección de tildes, y un pipeline robusto que nunca falle con error 500 incluso ante fallos del LLM.

---

## 1. Decisiones Arquitectónicas

### 1.1. "El LLM genera datos, el backend genera el formato"

**Decisión**: Separar la responsabilidad de contenido (LLM) de la responsabilidad de presentación (backend).

**Antes**: El LLM recibía instrucciones de markdown dentro de un prompt de 80 líneas. Generaba strings JSON con formato markdown embebido, lo que producía duplicación `**X**X`, falta de `\n` entre ítems, y omisión de tildes.

**Después**: Prompt compacto de ~25 líneas con reglas de formato por sección explícitas. El backend post-procesa el contenido mediante `_format_list_section()` y `clean_document_tree()` para garantizar formato correcto independientemente de la salida del LLM.

### 1.2. Pipeline de 3 capas de validación

```
LLM Output → validate_discovery_output() → validate_discovery_quality() → _format_list_section() → clean_document_tree()
              (estructural: longitud,       (semántica: tildes,          (formato: bullets,     (árbol: dedup,
               campos requeridos,            anti-duplicación,            items separados)        merge texto)
               términos prohibidos)          items por sección)
```

### 1.3. Generador nunca devuelve sin discovery

**Problema**: Cuando el LLM fallaba (API key inválida, error de red), el generador devolvía estado sin campo `discovery` → el router lanzaba `500 Internal Server Error`.

**Solución**: Todos los paths de retorno del `discovery_generator_node` incluyen un `DiscoveryDocument` mínimo con `vision` poblada desde la descripción del proyecto. La calidad añade warnings pero nunca bloquea la respuesta API.

### 1.4. MemorySaver en Windows

**Problema**: `AsyncPostgresSaver` (checkpointer de LangGraph) requiere `SelectorEventLoop`. Windows usa `ProactorEventLoop` por defecto, causando error en cada invocación del grafo.

**Solución**: En `langgraph_engine.py`, detección de plataforma: Windows usa `MemorySaver` (checkpoints volátiles), Linux/macOS usa `AsyncPostgresSaver` (checkpoints persistentes).

---

## 2. Estrategias Implementadas

### 2.1. Sanitización de Markdown

**Archivo**: `domain/sdd/llm_helpers.py`

| Función | Propósito | Conserva | Elimina |
|---|---|---|---|
| `strip_markdown_formatting()` | Features / EARS `source_statement` | Nada | Todo el formato markdown |
| `strip_llm_artifacts()` | Discovery / EARS `response` y `rationale` | `**bold**`, `*italic*`, listas, `---`, `>` | Solo `**Título:**`, `**Descripción:**` y `\\n` escapados |
| `extract_json()` | Fallback parser | JSON válido | Code fences, texto fuera de `{}`/`[]` |

### 2.2. Sanitización Selectiva por Campo (EARS)

**Archivo**: `application/orchestration/nodes/ears_generator.py`

| Campo | Función de limpieza | Razón |
|---|---|---|
| `source_statement` | `strip_markdown_formatting()` | Debe ser sintaxis EARS plana |
| `trigger` | `strip_markdown_formatting()` | Debe ser frase condicional limpia |
| `system` | `strip_markdown_formatting()` | Texto fijo "El sistema" |
| `response` | `strip_llm_artifacts()` | Admite markdown para legibilidad |
| `rationale` | `strip_llm_artifacts()` | Admite viñetas y negritas |
| `acceptance_criteria[*].description` | `strip_llm_artifacts()` | Admite negritas en verbos clave |

### 2.3. Formateo Server-Side de Secciones

**Archivo**: `application/orchestration/nodes/discovery_generator.py`

`_format_list_section()` pre-procesa cada sección antes de la conversión a markdown:

1. **Split de ítems concatenados**: `"1. ItemA 2. ItemB"` → separados con `\n`
2. **Split de bloques de scope**: `"Incluido: ... Excluido: ..."` → separados con `\n`
3. **Detección de bullets existentes**: si ya tiene `-` o `*`, se preserva
4. **Detección de ítems numerados**: si ya tiene `1.`, `2.`, se preserva
5. **Fallback a bullet**: si no tiene formato, se añade `- ` automáticamente

### 2.4. Validación de Calidad Semántica

**Archivo**: `domain/sdd/output_guardrails.py`

`validate_discovery_quality()` ejecuta 3 chequeos post-generación:

| Chequeo | Severidad | Umbral |
|---|---|---|
| **Ortografía (tildes)** | Blocker | <80% de tildes esperadas presentes |
| **Anti-duplicación** `**X**X` | Blocker | Cualquier ocurrencia del patrón |
| **Items por sección** | Warning | <2 ítems visibles en secciones de lista |

Diccionario de 80+ palabras con tilde esperada: `gestión`, `crítico`, `descripción`, `información`, `configuración`, etc.

### 2.5. Limpieza de Árbol ProseMirror

**Archivo**: `domain/sdd/document_converters.py`

`clean_document_tree()` recorre recursivamente el árbol ProseMirror y aplica `_dedup_bold_and_merge()` en nodos de tipo `paragraph` y `heading`:

1. **Deduplicación bold+plain**: Si un nodo bold contiene "Gerente" y el siguiente nodo plain también empieza con "Gerente", se elimina el prefijo duplicado del nodo plain.
2. **Merge de texto adyacente**: Nodos plain consecutivos se unen con espacio.
3. **Preservación de bold**: Los nodos bold se conservan intactos.

### 2.6. Sistema de Tildes en Visión

**Archivo**: `domain/sdd/document_converters.py`

Corrección hardcodeada: `"Visión del producto"` (antes `"Vision del producto"`). Los títulos de sección en `discovery_to_markdown()` se generan con tildes correctas desde el backend.

---

## 3. Archivos Modificados — Mapa Completo

| Archivo | Cambios Clave |
|---|---|
| `src/kosmo/__init__.py` | `WindowsSelectorEventLoopPolicy` para Windows |
| `src/kosmo/domain/sdd/llm_helpers.py` | `strip_markdown_formatting()`, `strip_llm_artifacts()`, `extract_json()` |
| `src/kosmo/domain/sdd/document_converters.py` | `clean_document_tree()`, `_dedup_bold_and_merge()`, `_clean_content_nodes()`, tilde en "Visión" |
| `src/kosmo/domain/sdd/output_guardrails.py` | `validate_discovery_quality()` con diccionario de 80+ tildes, `validate_semantic_quality()` |
| `src/kosmo/application/orchestration/nodes/discovery_generator.py` | Prompt compacto 25 líneas, `_format_list_section()`, fallback LLM siempre emite discovery |
| `src/kosmo/application/orchestration/nodes/ears_generator.py` | Sanitización selectiva por campo (`strip_llm_artifacts` vs `strip_markdown_formatting`) |
| `src/kosmo/application/orchestration/nodes/features_generator.py` | `strip_markdown_formatting()` en título y descripción |
| `src/kosmo/application/orchestration/nodes/draft_refiner.py` | Prompt sin `**Título:**` ni `**Descripción:**` |
| `src/kosmo/infrastructure/orchestration/langgraph_engine.py` | `MemorySaver` en Windows, `AsyncPostgresSaver` en Linux/macOS |
| `src/kosmo/infrastructure/api/routers/discovery.py` | Try/except con logging en `graph_engine.invoke()`, `clean_document_tree` en generate y regenerate |
| `src/kosmo/infrastructure/api/routers/requirements.py` | `clean_document_tree` en generate y regenerate, fix `get_uc` no definido |
| `src/kosmo/infrastructure/api/routers/features.py` | `strip_markdown_formatting()` en `suggest-from-idea` |
| `src/kosmo/infrastructure/llm/noop_adapter.py` | Match `"analista" + "negocio"` para nuevo prompt |
| `src/kosmo/infrastructure/api/main.py` | Static mount para `discovery-viewer.html` |
| `static/discovery-viewer.html` | Visor/editor 3-panel con renderizado ProseMirror, TOC, CSS para hr/blockquote |
| `postman/KOSMO_API_v3_Complete.postman_collection.json` | Body en `toggle_status` (`{"status": "aprobada"}`) |

---

## 4. Pipeline de Orquestación Multiagente — Flujo Discovery

```
API Router (POST /discovery/generate)
  │
  ├─ KOSMOState(phase=DESCUBRIMIENTO, raw_idea=project.description)
  │
  └─ graph_engine.invoke(state, config)
       │
       ├─ supervisor_node → dispatch_context()
       │
       ├─ [context_analyzer ‖ goal_planner ‖ preference_retriever] (paralelo, Send<3>)
       │
       ├─ context_merger → supervisor → route to discovery_generator
       │
       ├─ discovery_generator_node:
       │   1. Build prompt (_DISCOVERY_SYSTEM + _build_discovery_prompt)
       │   2. LLM complete (DeepSeek, structured output con DiscoveryOutputSchema)
       │   3. Parse: response.parsed (Pydantic) ‖ extract_json (fallback)
       │   4. strip_llm_artifacts() + _format_list_section()
       │   5. validate_discovery_output() → guardrail estructural
       │   6. validate_discovery_quality() → tildes, anti-dup, items
       │   7. discovery_to_markdown() → markdown
       │   8. markdown_to_document() → árbol ProseMirror
       │   9. clean_document_tree() → _dedup_bold_and_merge()
       │
       ├─ [quality_critic ‖ style_critic ‖ consistency_critic] (paralelo, fan-out<3)
       │
       ├─ critic_merger → critic_evaluator (loop si needs_revision, máx 3)
       │
       ├─ final_evaluator (loop si needs_revision, máx 10)
       │
       └─ preference_feedback → learn_from_correction → END
  │
  └─ API Router: persiste document_tree, devuelve DiscoveryDocumentResponse
```

---

## 5. Decisiones Clave y Por Qué

| Decisión | Alternativa rechazada | Razón |
|---|---|---|
| `MemorySaver` en Windows | Forzar `SelectorEventLoop` global | `uvicorn` crea el loop antes de que el código de usuario pueda cambiar la policy |
| `_format_list_section()` server-side | Pedir al LLM formato perfecto | DeepSeek es inconsistente con `\n` entre ítems; el backend garantiza el formato |
| Prompt de 25 líneas | Prompt de 80 líneas con ejemplos largos | El LLM perdía atención en reglas de formato; prompt compacto = mejor adherencia |
| `strip_llm_artifacts()` (conserva markdown) | `strip_markdown_formatting()` (elimina todo) | Discovery y EARS `response` necesitan markdown para legibilidad visual |
| Quality warnings, nunca blockers | Bloquear respuesta si calidad < umbral | El usuario siempre debe recibir contenido; las advertencias informan sin bloquear |
| Fallback discovery mínimo en error LLM | Devolver 500 | El frontend siempre recibe un documento renderizable, aunque sea básico |

---

## 6. Lecciones Aprendidas

1. **DeepSeek y `response_format: json_object`**: DeepSeek soporta `json_object` pero NO garantiza que use los nombres de campo del schema Pydantic. Es necesario incluir el formato JSON esperado explícitamente en el prompt.

2. **DeepSeek y tildes**: El modelo frecuentemente omite tildes incluso cuando el prompt lo pide explícitamente. La única defensa efectiva es la validación post-generación con diccionario de palabras esperadas.

3. **DeepSeek y `\n` entre ítems**: El modelo tiende a concatenar ítems con espacios en vez de usar saltos de línea reales. El split server-side con regex es necesario como safety net.

4. **Windows + psycopg + LangGraph**: La combinación `ProactorEventLoop` + `AsyncPostgresSaver` no funciona en Windows. `MemorySaver` es una alternativa válida para desarrollo local.

5. **Prompt compacto > Prompt extenso**: Un prompt de 25 líneas con reglas explícitas y ejemplos de formato correcto/incorrecto produce mejor adherencia que uno de 80 líneas con ejemplos narrativos largos.

---

## 7. Estado Actual

- **Backend**: Apagado. Listo para `uv run uvicorn kosmo.infrastructure.api.main:app --host 0.0.0.0 --port 8000`
- **PostgreSQL 17**: Limpio, 4 migraciones aplicadas, usuario seed `dev@kosmo.dev / dev-password-12345`
- **Redis 7**: Limpio
- **MongoDB 7**: Limpio
- **LLM**: DeepSeek (`deepseek-chat`), API key configurada en `.env`
- **Visor Discovery**: `http://localhost:8000/static/discovery-viewer.html`
- **Postman Collection**: `backend/postman/KOSMO_API_v3_Complete.postman_collection.json`
