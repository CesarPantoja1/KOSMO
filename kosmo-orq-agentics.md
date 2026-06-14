# KOSMO — Orquestación Multiagente: Análisis Completo

## Tabla de Contenidos

1. [¿Qué es la orquestación multiagente de KOSMO?](#1-qué-es-la-orquestación-multiagente-de-kosmo)
2. [Arquitectura general](#2-arquitectura-general)
3. [El grafo de ejecución](#3-el-grafo-de-ejecución)
4. [Los 17 agentes — Qué hace cada uno](#4-los-17-agentes--qué-hace-cada-uno)
5. [Flujo de pipeline paso a paso](#5-flujo-de-pipeline-paso-a-paso)
6. [Mecanismo de memoria y aprendizaje](#6-mecanismo-de-memoria-y-aprendizaje)
7. [Herramientas (Tools) disponibles](#7-herramientas-tools-disponibles)
8. [Capacidades de cada agente](#8-capacidades-de-cada-agente)
9. [Escalabilidad de la arquitectura](#9-escalabilidad-de-la-arquitectura)
10. [Capa por capa — División hexagonal](#10-capa-por-capa--división-hexagonal)
11. [¿Los agentes consultan bases de datos por sí mismos?](#11-los-agentes-consultan-bases-de-datos-por-sí-mismos)
12. [¿Piensan? ¿Aprenden?](#12-piensan-aprenden)
13. [Proveedores de LLM](#13-proveedores-de-llm)
14. [API y exposición al exterior](#14-api-y-exposición-al-exterior)
15. [Manejo de estado concurrente](#15-manejo-de-estado-concurrente)
16. [Observabilidad y telemetría](#16-observabilidad-y-telemetría)
17. [Resumen de patrones arquitectónicos](#17-resumen-de-patrones-arquitectónicos)
18. [Referencia rápida de archivos clave](#18-referencia-rápida-de-archivos-clave)

---

## 1. ¿Qué es la orquestación multiagente de KOSMO?

KOSMO implementa un sistema de **17 agentes especializados** orquestados mediante **LangGraph (StateGraph)** que colaboran para producir documentos de especificación de software (SDD — Software Design Document) de alta calidad. El sistema sigue el patrón **Supervisor-Worker** con ciclos de **Crítico-Refinamiento** y un pipeline de **aprendizaje desde correcciones del usuario**.

Cada "agente" es una **función async de Python** (un nodo del grafo) que:
- Lee el estado global compartido (`KOSMOState`)
- Ejecuta su lógica especializada (análisis, generación, crítica, etc.)
- Escribe sus resultados de vuelta en el estado compartido
- Registra toda su actividad en un historial de auditoría (`ToolCallRecord`)

**No son agentes autónomos con iniciativa propia**: son workers especializados que reciben tareas del Supervisor y ejecutan su función asignada dentro de un pipeline determinista.

---

## 2. Arquitectura general

### Arquitectura Hexagonal (Ports & Adapters)

```
contratos/  →  dominio/  →  aplicación/  →  infraestructura/
(kernel)       (algoritmos) (casos de uso)   (FastAPI, DBs, LLMs)
```

Cada capa tiene dependencias estrictamente hacia adentro (enforcement via `.importlinter`).

### Las 4 capas

| Capa | Directorio | Responsabilidad |
|------|-----------|-----------------|
| **Contratos** | `src/kosmo/contracts/` | Entidades, puertos (interfaces), errores. Sin dependencias externas. |
| **Dominio** | `src/kosmo/domain/` | Algoritmos puros. Sin I/O, sin clock, sin randomness. |
| **Aplicación** | `src/kosmo/application/` | Casos de uso que orquestan lógica de dominio usando puertos. |
| **Infraestructura** | `src/kosmo/infrastructure/` | Adaptadores concretos: FastAPI, SQLAlchemy, Redis, LLM clients. |

### Composición Root

Toda la inyección de dependencias ocurre en `infrastructure/api/composition.py` durante el lifespan de FastAPI. El `LangGraphEngine` recibe `LLMClient`, `UserPreferenceRepository`, y repositorios de features/proyectos/specs. Estos se inyectan como `GraphDependencies` en cada ejecución del grafo via `config["configurable"]["deps"]`.

---

## 3. El grafo de ejecución

### Construcción del grafo

Archivo: `application/orchestration/kosmo_graph.py`

```python
def build_kosmo_graph() -> StateGraph:
    builder = StateGraph(KOSMOState)
    builder.set_entry_point("supervisor")
    # ... 17 nodos + edges + conditional edges
    return builder
```

### Nodos del grafo (17)

```
┌──────────────────────────────────────────────────────────────┐
│  ORQUESTADOR CENTRAL                                         │
│  ┌──────────────┐                                            │
│  │  supervisor  │ ← stage machine (CONTEXT→GENERATE→EVAL)    │
│  └──────┬───────┘                                            │
│         │                                                    │
│   ┌─────┴───── CONTEXT (fan-out Send<3> paralelo)            │
│   │                                                          │
│   ├── context_analyzer ─────┐                                │
│   ├── goal_planner ─────────┼──► context_merger ──► back     │
│   └── preference_retriever ─┘                                │
│                                                              │
│   ├────── GENERATE (rutea a 1 de 4)                          │
│   │                                                          │
│   ├── discovery_generator ───┐                               │
│   ├── features_generator ────┤                               │
│   ├── ears_generator ────────┤                               │
│   └── draft_refiner ─────────┤                               │
│                              │                               │
│              ┌───────────────┘                               │
│              │  fan-out paralelo a 3 críticos                │
│              ▼                                               │
│       ┌──────┬──────┬──────┐                                │
│       │quality│style │consis│                                │
│       │critic │critic│critic│                                │
│       └───┬───┴──┬───┴──┬───┘                               │
│           └──────┼──────┘                                    │
│                  ▼                                            │
│           critic_merger                                       │
│                  │                                            │
│           critic_evaluator (gate)                             │
│              ├─ "needs_revision" + iter < 3 → loop gen       │
│              └─ "approved" → final_evaluator                  │
│                                                              │
│   ├────── EVALUATE                                           │
│   │                                                          │
│   └── final_evaluator (no bloqueante, informativo)            │
│                                                              │
│   ├────── POST-PIPELINE (secuencial)                         │
│   │                                                          │
│   ├── preference_feedback → refuerzo/violación confianza      │
│   └── learn_from_correction → extracción de reglas           │
│                                                              │
│   └── END                                                    │
└──────────────────────────────────────────────────────────────┘
```

### Tipos de routing en el grafo

1. **`Send()` fan-out**: El supervisor despacha 3 nodos en paralelo durante la etapa CONTEXT (`Send("context_analyzer", {})`, etc.)
2. **Edges paralelas**: Los 4 generadores envían a los 3 críticos simultáneamente (12 edges en total)
3. **Conditional edges**: 
   - `route_after_supervisor`: decide si ir a CONTEXT (fan-out), GENERATE (1 nodo), EVALUATE (1 nodo), o END
   - `route_after_critic_evaluator`: decide si loop back al generador o seguir a final_evaluator
   - `route_after_evaluator`: decide END o volver a supervisor

---

## 4. Los 17 agentes — Qué hace cada uno

### ETAPA CONTEXT (3 agentes en paralelo + 1 merger)

| # | Agente | Archivo | Rol | ¿Usa LLM? |
|---|--------|---------|-----|-----------|
| 0 | **supervisor** | `nodes/supervisor.py` | Stage machine. Lee `supervisor_stage`, decide transiciones, aplica context compression si >8000 tokens. | No |
| 1 | **context_analyzer** | `nodes/context_analyzer.py` | Extrae dominio, entidades clave, nivel de complejidad, brechas, foco recomendado y un context_brief desde el estado del proyecto. | **Sí** (LLM con `ContextAnalyzerOutput` schema) |
| 2 | **goal_planner** | `nodes/goal_planner.py` | Descompone la fase actual en sub-objetivos SMART, criterios de éxito medibles, dependencias y tareas paralelizables. | **Sí** (LLM con `GoalPlannerOutput` schema) |
| 3 | **preference_retriever** | `nodes/preference_retriever.py` | Lee `UserPreferenceRepository` de PostgreSQL, obtiene hasta 20 preferencias del usuario, formatea prompt de inyección, incrementa `usage_count`. | **No** (DB read) |
| 4 | **context_merger** | `nodes/context_merger.py` | Merge determinista de outputs de los 3 agentes anteriores en `shared_scratchpad`. Política: `preference_retriever` > `goal_planner` > `context_analyzer`. | **No** (merge) |

### ETAPA GENERATE (4 generadores, 1 solo se ejecuta según la fase)

| # | Agente | Archivo | Rol | ¿Usa LLM? | ¿Usa Tools? |
|---|--------|---------|-----|-----------|-------------|
| 5 | **discovery_generator** | `nodes/discovery_generator.py` | Genera documento Markdown de 9 secciones (visión, problema, actores, propuesta de valor, casos de uso, capacidades, reglas, atributos, alcance). Soporta modo mejora (improve). | **Sí** | No (solo `llm_complete`) |
| 6 | **features_generator** | `nodes/features_generator.py` | Genera features (3 sugerencias o 5 en modo generate). Implementa anti-trivialidad, anti-paráfrasis, guardrails estructurales y semánticos. Envía mensaje a `consistency_critic`. | **Sí** | **Sí** (`search_features`, `search_discovery`) |
| 7 | **ears_generator** | `nodes/ears_generator.py` | Genera requisitos EARS en 6 categorías (ubiquitous, event, state, optional, unwanted, complex). Ciclo ReAct completo: Análisis→Corrección→Planificación→Generación→Auto-validación. Auto-repara fugas técnicas. Scoring batch. | **Sí** | No (solo `llm_complete`) |
| 8 | **draft_refiner** | `nodes/draft_refiner.py` | Refina contenido existente (discovery o features). Modo mejora: preserva intención del usuario, completa secciones, corrige estructura. Detecta términos prohibidos. | **Sí** | No (solo `llm_complete`) |

### ETAPA CRITICS (3 críticos en paralelo + merger + evaluator)

| # | Agente | Archivo | Rol | ¿Usa LLM? |
|---|--------|---------|-----|-----------|
| 9 | **quality_critic** | `nodes/critics.py` | Audita calidad EARS contra rúbrica de 6 dimensiones: pureza de negocio (30%), corrección EARS (25%), verificabilidad (20%), completitud (10%), no-ambigüedad (10%), cobertura (5%). Bloquea si score < 5 en cualquier dimensión o fuga técnica. | **Sí** |
| 10 | **style_critic** | `nodes/critics.py` | Verifica 6 criterios de estilo: sintaxis EARS, nomenclatura consistente, uso de "shall", formato Dado-Cuando-Entonces, lenguaje de negocio, ortografía española. Envía feedback a `preference_feedback` vía mailbox. Saltea si no hay preferencias. | **Sí** |
| 11 | **consistency_critic** | `nodes/critics.py` | Detecta 5 problemas estructurales: duplicados, contradicciones, terminología inconsistente, vacíos de cobertura entre categorías EARS, dependencias no declaradas. Recibe `request_review` de `features_generator` vía mailbox. | **Sí** |
| 12 | **critic_merger** | `nodes/critic_merger.py` | Consolida los 3 outputs de críticos. Agrupa por severidad (`blocker` > `warning` > `none`). Prioriza blockers. | **No** (merge) |
| 13 | **critic_evaluator** | `nodes/critic_evaluator.py` | **Gate obligatorio**. Analiza últimos 3 `CritiqueRecord`. Si hay `blocker` → `needs_revision`. Si hay `warning` + iter < 3 → `needs_revision`. Si todo ok → `approved`. Construye feedback estructurado para el generador. | **No** (reglas) |

### ETAPA EVALUATE

| # | Agente | Archivo | Rol | ¿Usa LLM? |
|---|--------|---------|-----|-----------|
| 14 | **final_evaluator** | `nodes/final_evaluator.py` | Evaluación **no bloqueante** de 5 criterios: pureza de negocio, cobertura, verificabilidad, densidad, ortografía (escala 1-10). Veredicto informativo: `approved` o `needs_improvement` con recomendaciones. El contenido SIEMPRE se entrega. | **Sí** |

### ETAPA POST-PIPELINE

| # | Agente | Archivo | Rol | ¿Usa LLM? | ¿Usa DB? |
|---|--------|---------|-----|-----------|----------|
| 15 | **preference_feedback** | `nodes/preference_feedback.py` | Procesa mensajes del mailbox de `style_critic`. Aplica delta de confianza: +0.1 si preferencia fue seguida (reinforced), -0.2 si fue violada. Poda preferencias con `confidence < 0.1`. | **No** | **Sí** (update_confidence, delete_expired) |
| 16 | **learn_from_correction** | `nodes/learn_from_correction.py` | Ejecuta el pipeline completo de aprendizaje: extrae deltas (`difflib.unified_diff`), infiere reglas (LLM), resuelve conflictos con preferencias existentes, almacena nuevas preferencias en PostgreSQL. | **Sí** | **Sí** (preference_repo.add) |

---

## 5. Flujo de pipeline paso a paso

### 1. Entrada al pipeline

Un endpoint de la API (ej. `POST /api/v1/projects/{id}/discovery/generate`) construye un `KOSMOState` inicial y llama:

```python
result_state = await graph_engine.invoke(state, config)
```

### 2. Supervisor — Stage Machine

```
supervisor_node()  →  lee supervisor_stage = CONTEXT
  ├─ Si generation_attempts >= max_iterations (10) → DONE + human_input_pending
  ├─ Si human_input_pending → pausa, espera Command(resume=...)
  ├─ Si stage == CONTEXT:
  │    └─ Determina current_subtask según phase + generator_action
  │       (descubrimiento → discovery_generator,
  │        caracteristicas → features_generator,
  │        requisitos → ears_generator,
  │        improve → draft_refiner)
  │    └─ Chequea context compression (>8000 tokens)
  │    └─ Transiciona: CONTEXT → GENERATE
  └─ Retorna → route_after_supervisor() despacha Send a 3 nodos
```

### 3. Context phase — 3 agentes en paralelo

Los 3 agentes se ejecutan simultáneamente:
- `context_analyzer` extrae dominio, entidades, gaps, foco
- `goal_planner` define sub-objetivos SMART con criterios de éxito
- `preference_retriever` carga preferencias del usuario desde PostgreSQL

Cada uno escribe en `agent_outputs`. El state usa reducer `_dict_merge` para evitar condiciones de carrera.

### 4. context_merger — Unificación

Consolida los 3 outputs en `shared_scratchpad`:
```
shared_scratchpad = {
  "context_analyzer_output": {...},
  "goal_planner_output": {...},
  "preference_retriever_output": {...},
}
```

Retorna al supervisor (edge `context_merger → supervisor`).

### 5. Supervisor → Generator

El supervisor recibe el estado con `supervisor_stage=GENERATE`. `_route_to_generator()` retorna `current_subtask`.
`route_after_supervisor()` retorna el string del nodo generador (no más `Send`).

### 6. Generator → 3 Critics (fan-out paralelo)

El generador produce contenido. Luego, automáticamente (edges directas), los 3 críticos se ejecutan en paralelo:

- `quality_critic`: rúbrica de 6 dimensiones (0-10 por dimensión)
- `style_critic`: estilo EARS y preferencias de usuario
- `consistency_critic`: duplicados, contradicciones, gaps

### 7. critic_merger → critic_evaluator

El merger consolida. El evaluator (gate) decide:

```
Si hay blocker → needs_revision → loop back al generador
Si hay warning + critic_iteration < 3 → needs_revision → loop back
Si todo approved → final_evaluator
```

**Máximo 3 iteraciones del loop generador-crítico** (`max_critic_iterations = 3`).

### 8. final_evaluator

Evaluación no bloqueante. Siempre aprueba el contenido (`output_ready = True`). Genera un score informativo y recomendaciones para el usuario.

### 9. Post-pipeline

- `preference_feedback`: ajusta confianza de preferencias (±0.1, ±0.2)
- `learn_from_correction`: si hay deltas de corrección, extrae reglas y las persiste

---

## 6. Mecanismo de memoria y aprendizaje

### Modelo de preferencias

Cada preferencia de usuario (`UserPreference`) contiene:

| Campo | Descripción |
|-------|-------------|
| `id` | ULID con prefijo (`pref_`) |
| `rule_text` | Regla en lenguaje natural (ej: "El usuario prefiere listas numeradas para instrucciones") |
| `corpus` | Palabras clave del dominio |
| `context_snippet` | Fragmento original que fue modificado |
| `confidence` | Float 0.0–1.0, ajustado dinámicamente |
| `usage_count` | Veces que fue recuperada e inyectada en prompts |

### Ciclo de Feedback (preference_feedback)

```
style_critic → mailbox (AgentMessage) → preference_feedback node
   ├─ message_type == "preference_reinforced" → confidence += 0.1
   └─ message_type == "preference_violated"   → confidence -= 0.2

Luego: delete_expired(threshold_confidence = 0.1) → poda preferencias débiles
```

Si no hay `preference_id` específico, aplica el delta a **todas** las preferencias del usuario.

### Ciclo de Aprendizaje (learn_from_correction)

Pipeline de 4 pasos:

1. **delta_extractor** (`domain/agents/learning/nodes.py`): Usa `difflib.unified_diff` para comparar documento original (IA) vs corregido (usuario). Cuenta líneas añadidas/eliminadas.

2. **rule_inferencer**: Envía el diff al LLM pidiendo identificar patrones de edición que revelen preferencias. Extrae reglas accionables.

3. **conflict_resolver**: Verifica reglas nuevas contra existentes en PostgreSQL (por `rule_text` normalizado). Marca duplicados.

4. **preference_store**: Persiste reglas no duplicadas en PostgreSQL via `UserPreferenceRepository.add()`.

### Inyección en prompts

Las preferencias se formatean como:

```
## Preferencias del Usuario (aprendidas de correcciones anteriores)
1. [rule_text_1]
2. [rule_text_2]

Aplica estas preferencias al generar contenido.
Si dos preferencias entran en conflicto, prioriza la mas reciente.
```

Se inyectan en los system prompts de **todos los generadores** (discovery, features, EARS, draft_refiner) y en el **style_critic**.

### Context Compression

Cuando el historial acumulado supera **8,000 tokens** (estimados como `len(text) // 4`), el supervisor dispara `compress_context()`. Este compresor:
- Resume críticas, errores, tool calls, contenido generado y preferencias
- Usa LLM para producir un resumen de ≤500 tokens
- Preserva decisiones tomadas, errores y preferencias del usuario
- Descarta ruido y repeticiones

---

## 7. Herramientas (Tools) disponibles

### ToolRegistry

Implementado como `InMemoryToolRegistry` en `domain/agents/tool_registry.py`. Es un diccionario `{nombre: (ToolDefinition, handler_async)}`. Métodos: `register()`, `invoke()`, `list_tools()`.

### Las 4 herramientas registradas

| Herramienta | Handler | Parámetros | Retorna | Usada por |
|-------------|---------|------------|---------|-----------|
| **`search_discovery`** | `search_discovery_handler` | `query`, `project_id` | Secciones del discovery que coinciden con query (búsqueda por keyword) | `features_generator` |
| **`search_features`** | `search_features_handler` | `query`, `project_id` | Features existentes cuyo título/descripción contengan query (verifica solapamiento) | `features_generator` |
| **`get_project_context`** | `get_project_context_handler` | `project_id` | Nombre, descripción, fase actual del proyecto | (registrada, disponible) |
| **`count_features`** | `count_features_handler` | `project_id` | Total, aprobadas, en borrador | (registrada, disponible) |

### Cómo se invocan

Los handlers reciben repositorios via `functools.partial` en el wiring (`build_sdd_tools()`). El `features_generator` invoca:

```python
search_result = await deps.tool_registry.invoke("search_features", {
    "project_id": state.project_id,
    "query": "...",
})
```

Cada invocación se registra en `tool_call_history` como `ToolCallRecord` con `duration_ms`.

### El pseudo-tool `llm_complete`

Todos los agentes que usan LLM registran un `ToolCallRecord` con `tool_name="llm_complete"` para trazabilidad. No es una herramienta real, es un marcador de auditoría.

---

## 8. Capacidades de cada agente

### Capacidades detalladas por agente

#### Supervisor
- **Orquestación**: Stage machine (CONTEXT → GENERATE → EVALUATE → DONE)
- **Límites**: `max_iterations=10`, `max_critic_iterations=3`
- **Human-in-the-Loop**: Pausa y espera `Command(resume=...)` cuando `human_input_pending=True`
- **Compresión de contexto**: Dispara `compress_context()` si >8000 tokens acumulados
- **Routing por fase**: Mapea `SpecPhase` → generador correcto (`descubrimiento`, `caracteristicas`, `requisitos`)
- **Phases no implementadas**: `modelo` e `implementacion` notifican al usuario que requieren trabajo manual

#### Context Analyzer
- **Análisis de dominio**: Identifica sector (e-commerce, fintech, salud...) y subsector (B2B, B2C...)
- **Entidades clave**: Nombra entidades de negocio principales (no técnicas)
- **Evaluación de complejidad**: `low`, `medium`, `high` basado en actores, reglas, flujos
- **Identificación de brechas**: Qué información falta para completar el análisis
- **Foco recomendado**: Qué aspecto priorizar en esta iteración
- **Context brief**: Resumen de 3-5 líneas para orientar generadores
- **Capacidad LLM**: Structured output via `ContextAnalyzerOutput` schema

#### Goal Planner
- **SMART goals**: Specific, Measurable, Achievable, Relevant, Time-bound
- **Fase-específico**: Diferentes instrucciones para descubrimiento (9 secciones), características (4 Ws), requisitos (6 categorías EARS)
- **Criterios de éxito medibles**: Incluye números, thresholds
- **Dependencias**: Orden lógico de generación (ej: actores antes que casos de uso)
- **Tareas paralelizables**: Identifica qué se puede generar simultáneamente
- **Capacidad LLM**: Structured output via `GoalPlannerOutput` schema

#### Preference Retriever
- **DB Read**: Consulta PostgreSQL via `UserPreferenceRepository.get_by_user()`
- **Formateo**: Convierte preferencias en prompt de inyección
- **Incremento de uso**: Llama `increment_usage()` para tracking
- **Graceful degradation**: Si la DB falla, loguea warning y continúa sin preferencias

#### Context Merger
- **Merge determinista**: Orden de prioridad: `preference_retriever` > `goal_planner` > `context_analyzer`
- **Escribe en shared_scratchpad** para que generadores lean contexto unificado

#### Discovery Generator
- **Generación Markdown**: 9 secciones obligatorias con formato estricto
- **Modo generate**: Desde cero, con descripción del proyecto
- **Modo improve**: Mejora documento existente preservando ideas del usuario
- **Guardrails**: `validate_discovery_md()` detecta problemas estructurales
- **Términos prohibidos**: Bloquea vocabulario técnico (API, endpoint, SQL, etc.)
- **Idioma**: Español con tildes correctas obligatorias
- **Feedback del crítico**: Incorpora críticas previas en prompts de iteraciones siguientes
- **Capacidad LLM**: `temperature=0`, `max_tokens=4096`

#### Features Generator
- **Anti-trivialidad**: No repite ni parafrasea features existentes. Inferencia rica desde discovery.
- **Estructura 4W**: QUÉ hace, PARA QUIÉN, BAJO QUÉ CONDICIÓN, QUÉ VALOR
- **Modo suggest (3)** vs **modo generate (5)**: Diferentes schemas y guardrails
- **Validación semántica**: `validate_semantic_quality()` detecta problemas de contenido
- **Guardrails estructurales**: `validate_features_output()` / `validate_generate_features_output()`
- **Mailbox**: Envía `request_review` a `consistency_critic` para verificar no solapamiento
- **Herramientas**: Invoca `search_features` para verificar solapamiento con existentes
- **Capacidad LLM**: `temperature=0.3`, `max_tokens=4096`, structured output

#### EARS Generator
- **6 categorías EARS**: ubiquitous, event, state, optional, unwanted, complex
- **ReAct Cycle**: Thought (análisis) → Observation (corrección de feedback) → Action Plan → Action (generación) → Self-validation (checklist)
- **Checklist de autoevaluación**: 10 puntos de verificación antes de entregar
- **Detección de fugas técnicas**: `detect_implementation_leak()` escanea términos prohibidos
- **Auto-reparación**: `_auto_repair_leaks()` reemplaza fugas con placeholder
- **Scoring batch**: `score_requirements_batch()` puntúa todos los requisitos
- **Validación EARS**: `validate_ears_output()` con guardrails
- **3-15 requisitos por feature**, al menos 4 categorías EARS, al menos 1 criterio por requisito
- **Capacidad LLM**: `temperature=0`, `max_tokens=8192`, structured output

#### Draft Refiner
- **Mejora quirúrgica**: Refina sin reescribir, preserva intención del usuario
- **Dos modos**: Feature (título + descripción) y Document (Markdown)
- **Detección de términos prohibidos**: Escanea output contra diccionario de ~30 términos
- **Graceful degradation**: Si detecta términos prohibidos, marca warning en vez de bloquear
- **Capacidad LLM**: `temperature=0.3`, `max_tokens=4096`

#### Quality Critic
- **Rúbrica 6D** (ponderada): Pureza (30%), Corrección EARS (25%), Verificabilidad (20%), Completitud (10%), No-ambigüedad (10%), Cobertura (5%)
- **Severity**: `blocker` (score<5 o fuga técnica), `warning` (score 5-6), `none` (score≥7)
- **Términos prohibidos**: Lista de ~30 términos técnicos que causan blocker automático
- **Evalúa CADA requisito individualmente**
- **Capacidad LLM**: `temperature=0`, `max_tokens=4096`, structured output

#### Style Critic
- **6 criterios**: Sintaxis EARS exacta, nomenclatura consistente, shall correcto, formato criterios, lenguaje negocio, ortografía española
- **Preferencias del usuario**: Verifica contra preferencias inyectadas en prompt
- **Mailbox a preference_feedback**: `preference_reinforced` o `preference_violated`
- **Saltea si no hay preferencias**: No ejecuta LLM si `preferences_prompt` está vacío
- **Capacidad LLM**: `temperature=0`, `max_tokens=4096`

#### Consistency Critic
- **5 tipos de problemas**: Duplicados, contradicciones, terminología inconsistente, vacíos de cobertura, dependencias no declaradas
- **Recibe mensajes de otros agentes**: Procesa `request_review` del mailbox
- **Contexto de features existentes**: Compara contra `state.features`
- **Capacidad LLM**: `temperature=0`, `max_tokens=4096`

#### Critic Merger
- **Consolidación determinista** de 3 críticos paralelos
- **Priorización**: Blockers > Warnings > None
- **Agrupa por agente** con etiquetas (Calidad EARS, Estilo EARS, Consistencia)

#### Critic Evaluator (Gate)
- **Últimos 3 CritiqueRecord** del `critique_log`
- **Lógica de decisión**:
  - Si hay `blocker` → `needs_revision` (siempre)
  - Si hay `warning` + `critic_iteration < max_critic_iterations` → `needs_revision`
  - Si todo `approved` → `approved`
- **Feedback estructurado**: Por agente con mensajes concatenados
- **No usa LLM**: Reglas deterministas

#### Final Evaluator
- **No bloqueante**: Siempre aprueba, siempre entrega contenido
- **5 criterios** (1-10): Pureza de negocio, cobertura, verificabilidad, densidad, ortografía
- **Veredicto informativo**: `approved` o `needs_improvement` con summary de recomendaciones
- **Incluye historial de críticas** en el prompt para contexto
- **Resetea contadores**: `critic_iteration=0`, `generation_attempts=0`
- **Capacidad LLM**: `temperature=0`, `max_tokens=4096`

#### Preference Feedback
- **Procesa mailbox**: Lee mensajes de `style_critic` dirigidos a `preference_feedback`
- **Refuerzo**: +0.1 a confidence si preferencia fue seguida
- **Violación**: -0.2 a confidence si preferencia fue violada
- **Batch update**: Si no hay `preference_id`, aplica delta a todas las preferencias
- **Pruning**: Elimina preferencias con `confidence < 0.1`

#### Learn From Correction
- **Pipeline completo de aprendizaje**: delta → inferencia → conflictos → persistencia
- **Graceful degradation**: Si faltan datos, loguea y continúa
- **Determinación automática de document_type** según `phase`
- **Delegate al UseCase**: `LearnFromCorrectionUseCase` (aplicación/memory)

---

## 9. Escalabilidad de la arquitectura

### Escalabilidad horizontal

| Dimensión | Estrategia | Límites |
|-----------|-----------|---------|
| **Nodos del grafo** | Agregar nuevos agentes es cuestión de `builder.add_node()` + edges. El state es extensible (Pydantic). | Sin límite duro |
| **Nuevas fases** | `SpecPhase` es un enum. Agregar `MODELO`, `IMPLEMENTACION` requiere nuevos generadores + routing. | Enum extensible |
| **Nuevas herramientas** | `InMemoryToolRegistry.register()` + handler en `build_sdd_tools()`. | Sin límite |
| **Nuevos críticos** | Fan-out automático. Agregar nodo + edges al grafo. | Sin límite |
| **Nuevos LLM providers** | Solo requiere nuevo adapter que implemente `LLMClient` protocol. | Sin límite |

### Escalabilidad vertical (rendimiento)

| Mecanismo | Descripción |
|-----------|-------------|
| **Paralelismo real** | 3 agentes en CONTEXT y 3 críticos se ejecutan en paralelo (LangGraph fan-out) |
| **Reducers concurrentes** | `_dict_merge`, `_list_merge` (cap 200), `_last_wins` previenen race conditions |
| **Context compression** | A 8000 tokens, comprime historial para no exceder ventana de contexto |
| **Límites de iteración** | `max_iterations=10`, `max_critic_iterations=3` previenen loops infinitos |
| **Capped lists** | `critique_log` y `tool_call_history` capados a 200 entradas (sin crecimiento infinito) |
| **Graceful degradation** | Si LLM falla, todos los nodos tienen fallback (contenido mínimo, skip, warning) |

### Patrones de resiliencia

- **Human-in-the-loop**: Si `generation_attempts >= max_iterations`, pausa y pide revisión humana
- **Checkpointing**: `AsyncPostgresSaver` persiste el estado completo entre cada nodo. Permite `resume()` tras pausa.
- **Fallback en generadores**: Si LLM falla, retorna contenido mínimo en vez de crashear
- **Fallback en críticos**: Si LLM falla, marcan `approved` y continúan (no bloquean el pipeline)
- **Preference repo opcional**: Si no hay `preference_repo`, los nodos saltan gracefully

### Limitaciones actuales

- Fases `modelo` e `implementacion` no implementadas (devuelven `human_input_pending`)
- `MongoDB` tiene stub pero no se usa en el pipeline de agentes
- Las herramientas son invocadas manualmente (no son "tool-calling" automático tipo function calling del LLM)
- Los críticos evalúan contenido como texto plano, no tienen acceso a la estructura de la DB

---

## 10. Capa por capa — División hexagonal

### Contracts (`src/kosmo/contracts/`)

El kernel de la aplicación. Define QUÉ, no CÓMO.

| Subdirectorio | Contenido | Archivos clave |
|---------------|-----------|----------------|
| `sdd/` | Entidades: `KOSMOState`, `Feature`, `EARSRequirement`, `SpecDocument`, `RawIdea`, `SpecPhase`, `SupervisorStage` | `state.py` (129 líneas), `schemas.py` |
| `orchestration/` | Puertos: `GraphEngine`, `GraphDependencies`, `ToolRegistry`, `ToolDefinition`, `ToolResult` | `graph_deps.py`, `tools.py`, `graph_engine.py` |
| `llm/` | Puerto: `LLMClient` protocol, `PromptTemplate`, `LLMResponse`, `LLMUsage` | `ports.py` |
| `memory/` | Entidad: `UserPreference`, Puerto: `UserPreferenceRepository` | `user_preference.py`, `repositories.py` |
| `auth/` | Entidades de autenticación, tokens, PKCE | Varios archivos |
| `storage/` | Puerto: `BlobStorage` | Interfaz |

### Domain (`src/kosmo/domain/`)

Algoritmos puros. Sin I/O, sin side effects.

| Subdirectorio | Contenido | Archivos clave |
|---------------|-----------|----------------|
| `agents/` | `InMemoryToolRegistry`, `context_compressor`, learning pipeline (`delta_extractor`, `rule_inferencer`, `conflict_resolver`, `preference_store`), `memory_agent/injection_preparer` | `tool_registry.py`, `context_compressor.py`, `learning/nodes.py` |
| `sdd/` | Validadores EARS (`ears_validator.py`), guardrails (`output_guardrails.py`), convertidores (`document_converters.py`), helpers LLM (`llm_helpers.py`), generador de IDs (`id_generator.py`), schemas estructurados (`structured_schemas.py`) | 6+ archivos |
| `auth/` | PKCE (RFC 7636) | Lógica pura |
| `features/` | Transiciones de estado de features | Máquina de estados |

### Application (`src/kosmo/application/`)

Casos de uso. Orquestan dominio usando puertos.

| Subdirectorio | Contenido | Archivos clave |
|---------------|-----------|----------------|
| `orchestration/` | **CORAZÓN DEL SISTEMA**: `kosmo_graph.py` (definición del grafo), `nodes/` (17 nodos) | `kosmo_graph.py`, `nodes/*.py` (17 archivos), `helpers.py` |
| `auth/` | Casos de uso: Register, Authorize, Exchange, Refresh, Revoke | 6+ archivos |
| `sdd/` | Casos de uso: Save/Load Discovery, Features CRUD, Generate, Improve | 4+ archivos |
| `features/` | CRUD, Generate, Improve, Suggest features | Varios archivos |
| `projects/` | Create, List, Get project | 3 archivos |
| `memory/` | `LearnFromCorrectionUseCase`, `InjectPreferences` | Casos de uso de aprendizaje |

### Infrastructure (`src/kosmo/infrastructure/`)

Adaptadores concretos. Implementan los puertos.

| Subdirectorio | Contenido | Archivos clave |
|---------------|-----------|----------------|
| `api/` | FastAPI app, routers (auth, projects, discovery, features, requirements, specs, preferences), WebSocket, `composition.py` (wiring) | `main.py`, `routers/*.py`, `composition.py` |
| `orchestration/` | `LangGraphEngine` (compila, invoca, streamea, resume), `tool_handlers.py` (4 handlers + builder) | `langgraph_engine.py`, `tool_handlers.py` |
| `llm/` | Adapters: `DeepSeekClient`, `LiteLLMClient` (multi-provider), `NoopLLMClient` | `deepseek_adapter.py`, `litellm_adapter.py`, `noop_adapter.py` |
| `persistence/` | PostgreSQL (SQLAlchemy async), Redis (token store, rate limiter), MongoDB (stub) | `postgres/repositories/*.py`, `redis/*.py` |
| `security/` | Argon2id, JOSE/JWT RS256, Fernet, API Key Vault | `password_hasher.py`, `jwt.py`, `fernet.py`, `key_vault.py` |
| `storage/` | `FileSystemBlobStorage` | `filesystem_blob_storage.py` |
| `telemetry/` | Structlog + Logfire/OpenTelemetry | Configuración |

---

## 11. ¿Los agentes consultan bases de datos por sí mismos?

**Sí, pero con restricciones.** Dos agentes consultan la base de datos directamente:

### preference_retriever
- **DB**: PostgreSQL
- **Operación**: `UserPreferenceRepository.get_by_user(user_id, project_id, limit=20)`
- **Propósito**: Obtener preferencias aprendidas del usuario para inyectar en prompts
- **Side effect**: `increment_usage([pref_ids])` — tracking de uso
- **Graceful degradation**: Si la DB falla, loguea warning y continúa sin preferencias

### preference_feedback
- **DB**: PostgreSQL
- **Operaciones**: `update_confidence(pref_id, delta)`, `get_by_user()`, `delete_expired(threshold=0.1)`
- **Propósito**: Ajustar scores de confianza y podar preferencias obsoletas

### learn_from_correction
- **DB**: PostgreSQL
- **Operación**: `preference_repo.add(user_preference)` — inserta nuevas preferencias
- **Propósito**: Persistir reglas inferidas desde correcciones del usuario

### features_generator (indirectamente, vía herramientas)
- **DB**: PostgreSQL (a través de handlers de herramientas)
- **Operación**: `search_features` → `feature_repo.list_by_project()`
- **Propósito**: Verificar que features nuevas no solapen con existentes

**Los demás agentes (generadores, críticos, evaluadores) NO acceden a la base de datos.** Solo leen el `KOSMOState` compartido y hacen llamadas LLM.

---

## 12. ¿Piensan? ¿Aprenden?

### ¿Piensan?

Los agentes **no tienen razonamiento autónomo persistente**. "Piensan" en el sentido de que:

1. **Los generadores implementan ReAct** (Reasoning + Acting): Analizan el contexto (Thought), procesan feedback previo (Observation), planifican (Action Plan), y generan (Action). Este razonamiento es **intra-llamada**: ocurre dentro de un solo prompt del LLM y no persiste entre iteraciones.

2. **El supervisor implementa razonamiento determinista**: Evalúa condiciones (intentos, fase, human_input_pending) y decide transiciones. No usa LLM.

3. **El critic_evaluator implementa razonamiento basado en reglas**: Clasifica severidades y decide si reenviar o aprobar.

4. **Los críticos delegan el razonamiento al LLM**: Reciben contenido, aplican rúbricas, y emiten veredictos estructurados.

**No hay "pensamiento" persistente entre ejecuciones**: Cada nodo parte del `KOSMOState` actual y ejecuta su función. El estado es el único mecanismo de continuidad.

### ¿Aprenden?

**Sí, el sistema aprende de las correcciones del usuario.** El aprendizaje no es automático ni continuo, sino **activado por correcciones explícitas**:

1. **¿Qué aprende?** Reglas de estilo y preferencias implícitas del usuario (ej: "prefiere listas numeradas", "evita jerga técnica en secciones X").

2. **¿Cómo aprende?**
   - El usuario corrige un documento generado por la IA
   - `learn_from_correction` calcula el `unified_diff` entre original y corregido
   - Envía el diff al LLM para que identifique patrones de edición
   - Extrae reglas en lenguaje natural
   - Verifica duplicados contra preferencias existentes
   - Almacena nuevas reglas en PostgreSQL

3. **¿Cómo aplica lo aprendido?**
   - `preference_retriever` carga preferencias al inicio del pipeline
   - Se inyectan en los system prompts de todos los generadores
   - `style_critic` verifica que el contenido cumpla las preferencias
   - `preference_feedback` refuerza (+0.1) o penaliza (-0.2) la confianza

4. **¿Qué no aprende?**
   - No hay fine-tuning de modelos
   - No hay embeddings ni búsqueda semántica
   - No hay RAG (Retrieval-Augmented Generation)
   - No hay memoria episódica entre sesiones (solo preferencias)

---

## 13. Proveedores de LLM

### Protocolo unificado

Todos los agentes usan `LLMClient` protocol (`contracts/llm/ports.py`):

```python
class LLMClient(Protocol):
    async def complete(prompt, response_schema?, temperature, max_tokens) -> LLMResponse
    async def stream(prompt, temperature, max_tokens) -> ...
```

### Adapters disponibles

| Adapter | Proveedor | Modelo default | Configuración |
|---------|-----------|----------------|---------------|
| `DeepSeekClient` | DeepSeek API | `deepseek-chat` | `LLM_PROVIDER=deepseek` + `LLM_API_KEY` |
| `LiteLLMClient` | Multi-proveedor (Anthropic, OpenAI, Gemini) | Configurable | `LLM_PROVIDER=anthropic/openai/gemini` |
| `NoopLLMClient` | Mock | N/A | `LLM_PROVIDER=noop` (testing) |

### Structured Output

Los agentes usan `response_schema` en `PromptTemplate` para forzar salidas JSON estructuradas. Los schemas están definidos en `domain/sdd/structured_schemas.py`:
- `ContextAnalyzerOutput`
- `GoalPlannerOutput`
- `FeaturesOutputSchema`
- `GenerateFeaturesOutputSchema`
- `EARSOutputSchema`
- `CriticOutputSchema`
- `EvaluationOutputSchema`

Si `response.parsed` es válido, se usa directamente. Si no, se aplica `extract_json()` como fallback.

---

## 14. API y exposición al exterior

### REST Endpoints

| Router | Prefijo | Endpoints clave |
|--------|---------|-----------------|
| `auth.py` | `/api/v1/auth` | register, authorize (PKCE), token, refresh, me, logout |
| `projects.py` | `/api/v1/projects` | Create, List, Get (por ID o slug) |
| `discovery.py` | `/api/v1/projects/{id}/discovery` | Generate, Get, Save, Regenerate |
| `features.py` | `/api/v1/features/...` | CRUD, Generate (5), Suggest (3), Improve, Status |
| `requirements.py` | `/api/v1/features/{id}/requirements/...` | Get, Save, Generate, Regenerate |
| `specs.py` | `/api/v1/specs/{id}` | Get, advance phases |
| `preferences.py` | `/api/v1/preferences` | User preference CRUD |

### WebSocket

`/api/v1/specs/{spec_id}/events` — Eventos en tiempo real del pipeline:
- `NodeStarted` / `NodeCompleted`
- `ArtifactProduced`
- `ValidationFailed` / `ValidationRetry`
- `RegenerationTriggered`
- `PhaseTransition`

### Flujo de invocación del grafo desde API

```
1. Cliente → POST /api/v1/projects/{id}/discovery/generate
2. Router → crea KOSMOState(project_id, user_id, phase, raw_idea)
3. Router → await graph_engine.invoke(state, config)
4. LangGraphEngine → compila grafo → ejecuta todos los nodos → retorna KOSMOState final
5. Router → extrae result_state.discovery → persiste en PostgreSQL
6. Router → retorna JSON con discovery generado
```

---

## 15. Manejo de estado concurrente

### Reducers en KOSMOState

El `KOSMOState` usa `Annotated` con reducers para permitir escritura concurrente segura desde nodos paralelos:

| Tipo | Reducer | Campos |
|------|---------|--------|
| `dict` | `_dict_merge` (shallow merge, último prevalece) | `shared_scratchpad`, `agent_outputs`, `agent_mailbox` |
| `list` | `_list_merge` (concatena, cap 200) | `critique_log`, `tool_call_history`, `errors` |
| `scalar` | `_last_wins` (último valor escrito prevalece) | `validation_status`, `critic_verdict` |

Esto permite que **3 agentes en CONTEXT y 3 críticos** escriban simultáneamente sin condiciones de carrera.

### Checkpointing

- **Producción (Linux)**: `AsyncPostgresSaver` persiste cada estado intermedio en PostgreSQL
- **Desarrollo (Windows)**: `MemorySaver` guarda en memoria
- **Resume**: `graph_engine.resume(checkpoint_id, human_input)` permite continuar un grafo pausado

---

## 16. Observabilidad y telemetría

### Trazabilidad

- **`@traced` decorator**: Cada nodo del grafo está decorado (ej. `@traced("quality_critic.execute")`)
- **`ToolCallRecord`**: Cada invocación de LLM y herramienta registra `agent_id`, `tool_name`, `params`, `result`, `error`, `duration_ms`, `timestamp`
- **`CritiqueRecord`**: Cada crítica registra `agent_id`, `severity`, `message`, `timestamp`
- **`AgentMessage`**: Comunicación inter-agente registrada con `from_agent`, `to_agent`, `message_type`, `priority`

### Stack de observabilidad

- **structlog**: Logging estructurado en todo el código
- **OpenTelemetry**: Auto-instrumentación de FastAPI, SQLAlchemy, HTTPX
- **Logfire**: Export de telemetría a plataforma de observabilidad (producción)
- **LangSmith**: Tracing de LangGraph (opcional, via `langchain_tracing_v2`)

### Configuración de observabilidad

```python
# config.py
logfire_token: SecretStr | None
otel_service_name: str = "kosmo-backend"
langchain_tracing_v2: bool = False
langchain_api_key: SecretStr | None
langchain_project: str = "kosmo-backend"
```

---

## 17. Resumen de patrones arquitectónicos

| Patrón | Implementación |
|--------|---------------|
| **Hexagonal (Ports & Adapters)** | 4 capas con dependencias hacia adentro. Enforced por `.importlinter`. |
| **Supervisor-Worker** | Supervisor rutea a workers especializados según fase y etapa |
| **Fan-out / Map-Reduce** | 3 agentes en paralelo (CONTEXT), 3 críticos en paralelo, merge posterior |
| **Critic-Refine Loop** | Generator → 3 Critics → Critic Merger → Critic Evaluator → (loop o proceed) |
| **ReAct** | Generadores implementan Thought → Action → Observation dentro de prompts |
| **Human-in-the-Loop** | Supervisor pausa y espera `resume()` cuando `human_input_pending=True` |
| **State Machine** | `SupervisorStage`: CONTEXT → GENERATE → EVALUATE → DONE |
| **Dependency Injection** | `GraphDependencies` via `config["configurable"]["deps"]` |
| **Event Sourcing Lite** | `ToolCallRecord` + `CritiqueRecord` construyen audit trail completo |
| **Reinforcement Learning Simple** | ±0.1/±0.2 a `UserPreference.confidence` + pruning |
| **Graceful Degradation** | Fallbacks en todos los nodos: LLM fails → contenido mínimo, DB fails → skip |

---

## 18. Referencia rápida de archivos clave

### Orquestación (corazón del sistema)

| Archivo | Líneas | Función |
|---------|--------|---------|
| `application/orchestration/kosmo_graph.py` | 157 | Construcción del StateGraph con 17 nodos + edges |
| `application/orchestration/nodes/supervisor.py` | 119 | Stage machine, routing, context compression |
| `application/orchestration/nodes/critics.py` | 437 | 3 críticos LLM (quality, style, consistency) |
| `application/orchestration/nodes/critic_evaluator.py` | 133 | Gate post-críticos, lógica de reenvío |
| `application/orchestration/nodes/critic_merger.py` | 33 | Merge determinista de críticos |
| `application/orchestration/nodes/final_evaluator.py` | 110 | Evaluación informativa no bloqueante |
| `application/orchestration/nodes/context_analyzer.py` | 177 | Análisis de dominio con LLM |
| `application/orchestration/nodes/goal_planner.py` | 144 | Planificación SMART con LLM |
| `application/orchestration/nodes/preference_retriever.py` | 82 | Carga preferencias desde PostgreSQL |
| `application/orchestration/nodes/context_merger.py` | 33 | Merge determinista de contexto |
| `application/orchestration/nodes/discovery_generator.py` | 227 | Generador de documento discovery (9 secciones) |
| `application/orchestration/nodes/features_generator.py` | 340 | Generador de features con anti-trivialidad |
| `application/orchestration/nodes/ears_generator.py` | 501 | Generador EARS (6 categorías, ReAct, auto-repair) |
| `application/orchestration/nodes/draft_refiner.py` | 165 | Refinamiento de contenido existente |
| `application/orchestration/nodes/learn_from_correction.py` | 97 | Pipeline de aprendizaje desde correcciones |
| `application/orchestration/nodes/preference_feedback.py` | 99 | Ajuste de confianza de preferencias |
| `application/orchestration/helpers.py` | 149 | Utilidades compartidas (get_deps, verify_scope, etc.) |

### Estado y contratos

| Archivo | Líneas | Función |
|---------|--------|---------|
| `contracts/sdd/state.py` | 129 | `KOSMOState` con todos los campos y reducers |
| `contracts/orchestration/graph_deps.py` | 12 | `GraphDependencies` dataclass |
| `contracts/orchestration/tools.py` | 46 | `ToolDefinition`, `ToolResult`, `ToolRegistry` protocol |
| `contracts/llm/ports.py` | 44 | `LLMClient` protocol, `PromptTemplate`, `LLMResponse` |

### Infraestructura de orquestación

| Archivo | Líneas | Función |
|---------|--------|---------|
| `infrastructure/orchestration/langgraph_engine.py` | 101 | Compila grafo, checkpointing, invoke/stream/resume |
| `infrastructure/orchestration/tool_handlers.py` | 184 | 4 handlers de herramientas + builder |
| `infrastructure/api/composition.py` | 259 | Composition root: wiring de todos los componentes |

### Dominio

| Archivo | Líneas | Función |
|---------|--------|---------|
| `domain/agents/learning/nodes.py` | 139 | delta_extractor, rule_inferencer, preference_store, conflict_resolver |
| `domain/agents/context_compressor.py` | 73 | Compresión de contexto >8000 tokens |
| `domain/agents/memory_agent/__init__.py` | 18 | Formateador de preferencias para inyección en prompts |
| `domain/agents/tool_registry.py` | 39 | `InMemoryToolRegistry` |
| `domain/sdd/output_guardrails.py` | — | 6 validadores guardrail |
| `domain/sdd/validators/ears_validator.py` | — | Scoring EARS, detección de fugas |

### Configuración

| Archivo | Líneas | Función |
|---------|--------|---------|
| `config.py` | 97 | Pydantic Settings: providers, modelos, conexiones, feature flags |

---

## Resumen ejecutivo

KOSMO implementa una arquitectura multiagente basada en **LangGraph** con **17 agentes especializados** que colaboran en un pipeline de **4 etapas** (CONTEXT → GENERATE → EVALUATE → DONE). El sistema utiliza:

- **3 agentes de contexto** que analizan el dominio, planifican objetivos y recuperan preferencias del usuario en paralelo
- **4 generadores** especializados por fase SDD (descubrimiento, características, requisitos EARS, refinamiento)
- **3 críticos** que evalúan calidad, estilo y consistencia en paralelo con rúbricas detalladas
- **1 gate evaluator** que decide si reenviar al generador o proceder
- **1 evaluador final** no bloqueante que proporciona scoring informativo
- **2 agentes de aprendizaje** que ajustan confianza de preferencias y extraen reglas desde correcciones del usuario

La arquitectura es **hexagonal** (Ports & Adapters), con **inyección de dependencias** en el composition root, **estado compartido con reducers concurrentes**, **checkpointing en PostgreSQL**, y **graceful degradation** en todos los nodos. Soporta múltiples proveedores de LLM (DeepSeek, OpenAI, Anthropic, Gemini) vía un protocolo unificado.

El sistema **aprende de correcciones del usuario** mediante un pipeline de 4 pasos (delta → inferencia → conflictos → persistencia) y **refuerza/penaliza preferencias** con un sistema simple de confidence scoring (±0.1/±0.2). No utiliza embeddings, RAG, ni fine-tuning.
