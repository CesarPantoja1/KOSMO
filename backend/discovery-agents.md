# Discovery Agents — Flujo Completo

## Resumen

El discovery es la primera fase del pipeline SDD de KOSMO. La IA genera un documento Markdown estructurado que describe el producto desde la perspectiva del negocio. Este documento es la **única fuente de verdad** que alimenta a todos los agentes downstream (features, EARS, etc.).

---

## 1. Formato del documento

Se almacena como **Markdown canónico** en una sola columna de la base de datos. Tiene 9 secciones obligatorias, cada una encabezada con `##`:

| # | Sección | Formato |
|---|---|---|
| 1 | Visión del producto | 1 párrafo de 3-5 líneas |
| 2 | Espacio del problema | 1-2 párrafos |
| 3 | Actores | `- **Rol:** descripción` |
| 4 | Propuesta de valor | `- **Para Rol:** beneficio concreto` |
| 5 | Casos de uso | `1. **Título:** descripción` |
| 6 | Capacidades principales | `- **Capacidad:** descripción breve` |
| 7 | Reglas de negocio | Lista numerada |
| 8 | Atributos de calidad | `- **Atributo:** expectativa medible` |
| 9 | Alcance | `**Incluido:**`, `**Excluido:**`, `**Futuro potencial:**` |

---

## 2. Paso a paso del flujo

### 2.1 Entrada del usuario

```
POST /api/v1/projects/{id}/discovery/generate
```

El router (`routers/discovery.py`) crea un `KOSMOState` con:
- `project_id`: ID del proyecto
- `user_id`: sujeto autenticado
- `phase`: `DESCUBRIMIENTO`
- `raw_idea`: `RawIdea(text=project.description)`
- `max_iterations`: 10

Invoca el grafo de agentes vía `graph_engine.invoke(state)`.

### 2.2 Pipeline de agentes (LangGraph)

El grafo (`kosmo_graph.py`) ejecuta los nodos en este orden:

```
┌──────────────┐
│  supervisor   │ ← Evalúa el estado y decide la etapa
└──────┬───────┘
       │ CONTEXT
       ├────────────────────────────┐
       ▼                            ▼
┌──────────────┐ ┌──────────┐ ┌──────────────────┐
│   context    │ │   goal   │ │   preference     │ ← Paralelo (Send<3>)
│   analyzer   │ │ planner  │ │   retriever      │
└──────┬───────┘ └────┬─────┘ └────────┬─────────┘
       │               │               │
       └───────────────┼───────────────┘
                       ▼
               ┌──────────────┐
               │   context    │ ← Fusiona los 3 resultados
               │    merger    │
               └──────┬───────┘
                      │
                      ▼
               ┌──────────────┐
               │  supervisor   │ ← Decide GENERATE → discovery_generator
               └──────┬───────┘
                      │
                      ▼
               ┌──────────────────┐
               │   discovery      │ ← EL NÚCLEO: LLM genera Markdown
               │   generator      │
               └──────┬───────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌──────────────┐
    │ quality │ │  style  │ │ consistency  │ ← Paralelo (fan-out<3>)
    │ critic  │ │ critic  │ │   critic     │
    └────┬────┘ └────┬────┘ └──────┬───────┘
         │            │            │
         └────────────┼────────────┘
                      ▼
               ┌──────────────┐
               │    critic    │ ← Fusiona críticas
               │    merger    │
               └──────┬───────┘
                      │
                      ▼
               ┌──────────────────┐
               │     critic       │ ← Evalúa: ¿necesita revisión?
               │    evaluator     │──── si ──→ vuelve a discovery_generator
               └──────┬───────────┘     (máx 3 iteraciones)
                      │ no
                      ▼
               ┌──────────────────┐
               │     final        │ ← Evalúa calidad final
               │    evaluator     │──── si ──→ vuelve a supervisor
               └──────┬───────────┘     (máx 10 iteraciones totales)
                      │ no
                      ▼
               ┌──────────────────┐
               │   preference     │ ← Registra feedback del usuario
               │    feedback      │
               └──────┬───────────┘
                      ▼
               ┌──────────────────┐
               │ learn from       │ ← Aprende correcciones del usuario
               │  correction      │
               └──────┬───────────┘
                      ▼
                     END
```

### 2.3 Post-generación (router)

Al terminar el grafo, el router:

1. **Toma** `result_state.discovery` (string Markdown)
2. **Guarda** el Markdown en `projects.discovery_md` (vía `document_repo.save_discovery_md()`)
3. **Devuelve** `{ document: markdown_string }` al frontend

---

## 3. Agentes del grafo

### 3.1 Nodo central: `discovery_generator`

**Archivo:** `application/orchestration/nodes/discovery_generator.py`

**Qué hace:** Genera el documento de descubrimiento. El LLM (DeepSeek) recibe un system prompt con las 9 secciones y sus formatos, y responde **directamente en Markdown** — sin JSON intermedio.

**Entrada:**
- `state.raw_idea` → descripción del proyecto
- `state.shared_scratchpad["context_analyzer_output"]` → análisis de dominio
- `state.shared_scratchpad["goal_planner_output"]` → sub-objetivos
- `state.shared_scratchpad["preference_retriever_output"]` → preferencias del usuario
- `state.shared_scratchpad["current_draft"]` → documento actual (modo mejora)
- `state.critique_log` → feedback de críticos (iteraciones previas)
- `state.generation_attempts` → número de iteración actual

**Salida:**
- `state.discovery` → string Markdown (ej: `"# Descubrimiento de Producto\n\n## Visión del producto\n\n..."`)
- `state.shared_scratchpad["generated_document_md"]` → mismo Markdown

**Validaciones internas:**
- `clean_markdown()` → elimina dobles dos puntos `::`
- `validate_discovery_md()` → verifica que las 9 secciones `##` estén presentes + sin términos prohibidos + ortografía

### 3.2 Nodos de contexto (fase CONTEXT)

**`context_analyzer`** — Analiza el dominio del proyecto. Extrae sector, entidades clave, nivel de complejidad, brechas en el discovery, y recomendaciones. Produce `shared_scratchpad["context_analyzer_output"]`.

**`goal_planner`** — Define sub-objetivos para la generación. Produce `shared_scratchpad["goal_planner_output"]`.

**`preference_retriever`** — Recupera preferencias y estilos del usuario desde el repositorio de memoria. Produce `shared_scratchpad["preference_retriever_output"]`.

**`context_merger`** — Fusiona los 3 resultados de contexto en un solo bloque para el supervisor.

### 3.3 Nodos críticos (fase CRITICS)

Se ejecutan en paralelo tras cada generación. Evalúan la calidad del discovery:

**`quality_critic`** — Evalúa calidad funcional: ¿están todas las secciones? ¿el contenido es sustancial? ¿hay términos prohibidos?

**`style_critic`** — Evalúa estilo: ortografía, tildes, eñes, formato de bullets, uso correcto de `:`.

**`consistency_critic`** — Evalúa consistencia: ¿los actores coinciden con los casos de uso? ¿las capacidades cubren las reglas de negocio?

**`critic_merger`** — Fusiona las 3 críticas.

**`critic_evaluator`** — Si el veredicto es `needs_revision`, reenvía al `discovery_generator` para otra iteración. Máximo 3 iteraciones en este loop.

### 3.4 Nodos finales

**`final_evaluator`** — Evalúa el documento completo con rúbrica: pureza de negocio, cobertura, verificabilidad, ortografía. Si `needs_revision`, reenvía al supervisor. Máximo 10 iteraciones totales.

**`preference_feedback`** — Registra las preferencias inferidas del resultado.

**`learn_from_correction`** — Cuando el usuario edita manualmente el documento, este nodo aprende el delta para mejorar futuras generaciones.

---

## 4. Qué se persiste

| Qué | Dónde | Tipo | Cuándo |
|---|---|---|---|
| **Markdown del discovery** | `projects.discovery_md` | `TEXT` | Al finalizar `generate`, `regenerate`, o `PUT /save` |
| Preferencias de usuario | `user_preferences` (Redis/DB) | varios | `learn_from_correction` |
| Estado del grafo | LangGraph checkpointer | memoria/langgraph | Durante la ejecución |

**No se persiste:**
- El `KOSMOState` completo (es efímero, vive durante la ejecución del grafo)
- Árboles ProseMirror/TipTap (eliminados en la refactorización)
- `DiscoveryDocument` como JSON (eliminado — ahora es Markdown directo)

---

## 5. Qué se utiliza para el siguiente agente

### 5.1 Discovery → Features

Cuando se invoca `POST /projects/{id}/features/generate`:

1. El router lee `projects.discovery_md`
2. Lo asigna a `state.discovery` (string Markdown)
3. El `features_generator_node` recibe `state.discovery` directamente
4. Lo pasa al LLM como contexto en el user prompt:

```
## Documento de Descubrimiento
{state.discovery[:6000]}
```

El LLM infiere características a partir del discovery, prestando especial atención a actores, reglas de negocio, casos de uso, propuesta de valor y capacidades principales.

### 5.2 Discovery → EARS (requisitos)

Cuando se invoca `POST /features/{id}/requirements/generate`:

1. El router lee `projects.discovery_md` del proyecto padre
2. Lo asigna a `state.discovery` (string Markdown)
3. El `ears_generator_node` recibe `state.discovery` directamente
4. Lo pasa al LLM como contexto:

```
## Contexto del Producto (Discovery)
{state.discovery}
```

El LLM deriva requisitos EARS cruzando la feature actual con el discovery completo.

### 5.3 Discovery → Regeneración

Cuando se invoca `POST /projects/{id}/discovery/regenerate`:

1. Se lee `projects.discovery_md` actual
2. Se carga en `state.shared_scratchpad["current_draft"]`
3. Se activa `generator_action = "improve"`
4. El `discovery_generator` recibe el documento actual y lo mejora

---

## 6. Diagrama de persistencia

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────────┐
│   Usuario    │     │   LangGraph      │     │     PostgreSQL          │
│   (API)      │     │   (agentes)      │     │                         │
└──────┬──────┘     └────────┬─────────┘     └────────────┬────────────┘
       │                     │                            │
       │ POST /generate      │                            │
       ├────────────────────>│                            │
       │                     │                            │
       │                     │ discovery_generator        │
       │                     │ (LLM → Markdown)           │
       │                     │         │                  │
       │                     │    critics + evaluator     │
       │                     │         │                  │
       │                     │    state.discovery = md    │
       │                     │         │                  │
       │<─── result_state ───│         │                  │
       │                     │         │                  │
       │ save_discovery_md() │         │                  │
       ├─────────────────────┼─────────┼─────────────────>│
       │                     │         │  INSERT/UPDATE   │
       │                     │         │  discovery_md    │
       │                     │         │                  │
       │                     │         │                  │
       │ POST /features/generate                          │
       ├─────────────────────┼───────────────────────────>│
       │                     │         │  SELECT          │
       │                     │         │  discovery_md    │
       │<────────────────────┼─────────┼──────────────────│
       │                     │         │                  │
       │ state.discovery = md│         │                  │
       ├────────────────────>│         │                  │
       │                     │         │                  │
       │                     │ features_generator         │
       │                     │ (LLM ← discovery md)       │
       │                     │         │                  │
       │<─── features ───────│         │                  │
```

---

## 7. Archivos clave

| Archivo | Rol |
|---|---|
| `contracts/sdd/discovery.py` | `RawIdea` — entrada del usuario |
| `contracts/sdd/state.py` | `KOSMOState` — estado del grafo, `discovery: str = ""` |
| `application/orchestration/kosmo_graph.py` | Construcción del grafo LangGraph |
| `application/orchestration/nodes/discovery_generator.py` | Nodo generador principal |
| `application/orchestration/nodes/supervisor.py` | Orquestador de etapas |
| `application/orchestration/nodes/critics.py` | Críticos: quality, style, consistency |
| `application/orchestration/nodes/critic_evaluator.py` | Evalúa si reintentar generación |
| `application/orchestration/nodes/final_evaluator.py` | Evalúa calidad final |
| `domain/sdd/output_guardrails.py` | `validate_discovery_md()` — validación post-LLM |
| `domain/sdd/document_converters.py` | `clean_markdown()` — limpieza de `::` |
| `domain/sdd/rules/discovery_format.md` | Guía de formato de las 9 secciones |
| `infrastructure/api/routers/discovery.py` | Endpoints REST: GET, PUT, generate, regenerate |
| `infrastructure/persistence/postgres/models/project.py` | `ProjectModel.discovery_md` — columna DB |
| `infrastructure/persistence/postgres/repositories/document_repo.py` | `save_discovery_md()` / `get_discovery_md()` |
