# ExArq.md — Arquitectura de Orquestación Multiagente de KOSMO

> **Autor:** Arquitectura de Software Principal  
> **Versión:** 2.1  
> **Fecha:** 9 de junio de 2026 — Análisis funcional corregido con inspección de código real  
> **Alcance:** Backend — Análisis exhaustivo de la orquestación de agentes con LangGraph sobre Arquitectura Hexagonal

---

## Tabla de Contenido

1. [Visión General del Proyecto](#1-visión-general-del-proyecto)
2. [Stack Tecnológico](#2-stack-tecnológico)
3. [Arquitectura Hexagonal — Estructura de Capas](#3-arquitectura-hexagonal--estructura-de-capas)
4. [El Corazón del Sistema: Orquestación con LangGraph](#4-el-corazón-del-sistema-orquestación-con-langgraph)
5. [Catálogo Completo de Agentes](#5-catálogo-completo-de-agentes)
6. [Diagramas de Flujo y Topología](#6-diagramas-de-flujo-y-topología)
7. [Estado Global — KOSMOState](#7-estado-global--kosmostate)
8. [Mecanismo de Aprendizaje (Learning Pipeline)](#8-mecanismo-de-aprendizaje-learning-pipeline)
9. [Persistencia: Checkpointing, Memoria y Documentos Duales](#9-persistencia-checkpointing-memoria-y-documentos-duales)
10. [Guardrails y Verificación Determinista](#10-guardrails-y-verificación-determinista)
11. [Análisis Final: ¿Orquestación Multiagente o Secuencia de Prompts?](#11-análisis-final-orquestación-multiagente-o-secuencia-de-prompts)
12. [Probar el Flujo Completo](#12-probar-el-flujo-completo)

---

## 1. Visión General del Proyecto

KOSMO es una herramienta de co-creación enfocada en **Negocio y Experiencia de Usuario**. Su propósito es transformar ideas abstractas en **Especificaciones de Diseño Técnico (SDD)** siguiendo un flujo secuencial rígido:

```
[Descubrimiento] → [Características] → [Requisitos] → [Modelo] → [Implementación]
```

Cada fase está controlada por un **Wizard** (Supervisor) que orquesta agentes especializados. Los agentes deben actuar como ingenieros de requisitos expertos, adaptándose, comunicándose y aprendiendo de las interacciones previas con el usuario.

### Flujo de Negocio (Wizard de 5 Pantallas)

| Fase | Pantalla | Objetivo | Agente Generador |
|------|----------|----------|-----------------|
| **Descubrimiento** | 3 | Documento de 9 secciones: Visión, Problema, Actores, Propuesta de Valor, Casos de Uso, Capacidades, Reglas de Negocio, Atributos de Calidad, Alcance | `discovery_generator` |
| **Características** | 4 (Opción A: Generar, Opción B: Sugerir) | Descomponer el discovery en features concretas con título y descripción de valor de negocio | `features_generator` / `draft_refiner` |
| **Requisitos** | 5 | Derivar requisitos EARS (Easy Approach to Requirements Syntax) clasificados en 6 categorías | `ears_generator` |
| **Modelo** | N/A | No implementado aún en el pipeline actual | Pendiente |
| **Implementación** | N/A | No implementado aún en el pipeline actual | Pendiente |

---

## 2. Stack Tecnológico

### Runtime y Framework

| Tecnología | Rol |
|------------|-----|
| **Python 3.13** | Lenguaje de programación |
| **FastAPI 0.136+** | Framework web asíncrono |
| **Uvicorn** | Servidor ASGI |
| **Pydantic v2** | Validación de datos, serialización, schemas |
| **Pydantic Settings** | Carga de configuración desde `.env` |

### Persistencia

| Tecnología | Rol |
|------------|-----|
| **PostgreSQL + asyncpg** | Base de datos relacional principal (SQLAlchemy asíncrono 2.0) |
| **Redis 7.4+** | Token store, rate limiting, PKCE authorization codes, login attempts |
| **pgvector** | Embeddings vectoriales para búsqueda semántica (stub) |
| **MongoDB (motor)** | Almacenamiento de documentos (stub) |
| **Python-ULID** | Generación de IDs con prefijos tipados (`prj_`, `feat_`, `spec_`, `tsk_`, `usr_`, `apk_`, `aud_`, `pref_`, `req_`) |

### Orquestación de IA

| Tecnología | Rol |
|------------|-----|
| **LangGraph 1.1.9+** | Motor de grafos con checkpointing para orquestación de agentes |
| **langgraph-checkpoint-postgres 3.0+** | Persistencia de estado del grafo en PostgreSQL |
| **LiteLLM 1.80+** | Proxy unificado para múltiples proveedores LLM |
| **pydantic-ai 1.86+** | Structured output y tool calling tipado |
| **DeepSeek** | Proveedor LLM alternativo (vía API directa) |
| **LangSmith** | Trazabilidad y monitoreo de ejecuciones del grafo |

### Seguridad

| Tecnología | Rol |
|------------|-----|
| **Argon2id** | Hashing de contraseñas |
| **RS256 JWT (python-jose)** | Firma y verificación de tokens |
| **Fernet (cryptography)** | Cifrado simétrico de secretos y API keys |
| **PKCE (RFC 7636)** | Flujo de autorización con código + challenge |

### Observabilidad

| Tecnología | Rol |
|------------|-----|
| **Logfire** | Exportación OTEL con integración nativa FastAPI + SQLAlchemy + Redis |
| **structlog** | Logging estructurado |
| **@traced** | Decorador de telemetría en casos de uso |

### Gestión de Dependencias

| Tecnología | Rol |
|------------|-----|
| **uv** | Gestor de dependencias y entornos virtuales |
| **Alembic** | Migraciones de base de datos |
| **Ruff** | Linting y formateo |
| **Pyright** | Type checking estricto |
| **import-linter** | Validación de arquitectura por capas |

---

## 3. Arquitectura Hexagonal — Estructura de Capas

KOSMO implementa una **Arquitectura Hexagonal (Ports & Adapters)** estricta con cuatro capas, cuyo orden de dependencia está forzado por `import-linter`:

```
┌─────────────────────────────────────────────────────────┐
│                  infrastructure/                         │
│  FastAPI routers, SQLAlchemy/Redis, LangGraph engine,   │
│  Fernet cipher, Argon2 hasher, DeepSeek/LiteLLM adapter │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │                 application/                      │  │
│  │  Use Cases: CreateFeature, GenerateDiscovery,     │  │
│  │  Orchestration nodes (graph agents), learning     │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │               domain/                       │  │  │
│  │  │  Pure Algorithms: EARS validator,           │  │  │
│  │  │  document_converters, id_generator,         │  │  │
│  │  │  context_compressor, guardrails             │  │  │
│  │  │                                             │  │  │
│  │  │  ┌───────────────────────────────────────┐  │  │  │
│  │  │  │            contracts/                 │  │  │  │
│  │  │  │  Entities, Error Types, Port         │  │  │  │
│  │  │  │  Interfaces (Protocol classes),      │  │  │  │
│  │  │  │  Pydantic models                     │  │  │  │
│  │  │  └───────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 3.1. Capa `contracts/` (Kernel)

Define entidades, tipos de error y **puertos** (interfaces `Protocol`). No tiene dependencias externas. Es el **contrato sagrado** que todas las demás capas deben respetar.

Subdirectorios clave:
- `sdd/` — Entidades de dominio: `Feature`, `Project`, `DiscoveryDocument`, `EARSRequirement`, `KOSMOState`, `GuardrailResult`, `SuggestedFeature`, `ProblemDetail` (RFC 7807)
- `llm/` — Puerto `LLMClient` con `PromptTemplate` y `LLMResponse`
- `orchestration/` — Puertos `GraphEngine` y `ToolRegistry`
- `memory/` — Puerto `UserPreferenceRepository` y entidad `UserPreference`
- `storage/` — Puerto `BlobStorage`
- `auth/` — Puertos de autenticación

### 3.2. Capa `domain/` (Algoritmos Puros)

**Sin I/O, sin relojes, sin aleatoriedad, sin globales.** Contiene lógica de negocio pura:

- `domain/sdd/id_generator.py` — `IdGenerator.generate("feature")` → `feat_01KT...`
- `domain/sdd/document_converters.py` — Conversión TipTap ↔ Markdown, `extract_discovery_from_document()`, `discovery_to_markdown()`, `requirements_document_to_markdown()`
- `domain/sdd/validators/` — `ears_validator.py` (scoring de requisitos EARS en 6 dimensiones), `task_dag_validator.py` (detección de ciclos), `domain_model_validator.py`
- `domain/sdd/output_guardrails.py` — Validación determinista post-LLM para discovery, features y EARS
- `domain/sdd/structured_schemas.py` — Schemas Pydantic para structured output del LLM
- `domain/agents/learning/` — `delta_extractor()`, `rule_inferencer()`, `preference_store()`, `conflict_resolver()`
- `domain/agents/context_compressor.py` — Compresión de contexto cuando el historial excede 8000 tokens

### 3.3. Capa `application/` (Casos de Uso)

Orquesta la lógica de dominio a través de puertos. No conoce implementaciones concretas:

- `application/features/` — `CreateFeatureUseCase`, `ListFeaturesUseCase`, `ToggleFeatureStatusUseCase`, `SaveSelectedSuggestionsUseCase`, etc.
- `application/sdd/` — `GetDiscoveryDocumentUseCase`, `SaveDiscoveryDocumentUseCase`
- `application/orchestration/` — **El corazón de la IA**: nodos del grafo LangGraph (agentes), `kosmo_graph.py` (construcción del StateGraph), `helpers.py` (utilidades de inyección de dependencias)

### 3.4. Capa `infrastructure/` (Adaptadores)

Implementaciones concretas de los puertos definidos en `contracts/`:

- `infrastructure/api/` — FastAPI routers, `composition.py` (wiring central), `main.py` (lifespan)
- `infrastructure/persistence/postgres/` — Modelos SQLAlchemy, repositorios, `document_repo.py` (persistencia dual)
- `infrastructure/persistence/redis/` — Token store, authorization codes, login attempts
- `infrastructure/orchestration/langgraph_engine.py` — Adaptador concreto del puerto `GraphEngine`
- `infrastructure/llm/` — `DeepSeekClient`, `LiteLLMClient`, `NoopLLMClient`
- `infrastructure/security/` — Argon2id, RS256 JWT, Fernet cipher

### 3.5. Composición Central (Wiring)

Toda la inyección de dependencias se realiza en **un único punto**: `infrastructure/api/composition.py`. Durante el lifespan de FastAPI se instancian `AuthComponents` y `SDDComponents`, y se montan en `app.state`:

```python
# composition.py — fragmento clave
spec_repo = SqlAlchemySpecRepository(session_factory)
project_repo = SqlAlchemyProjectRepository(session_factory)
feature_repo = SqlAlchemyFeatureRepository(session_factory)
preference_repo = SqlAlchemyUserPreferenceRepository(session_factory)
document_repo = SqlAlchemyDocumentRepository(session_factory)

graph_engine = LangGraphEngine(settings)
graph_engine.configure_deps(llm_client, preference_repo)
```

---

## 4. El Corazón del Sistema: Orquestación con LangGraph

### 4.1. ¿Qué es LangGraph?

LangGraph es un framework de **StateGraph** (grafo de estados) que permite construir pipelines de agentes como grafos dirigidos con:
- **Nodos**: funciones asíncronas que transforman un estado compartido
- **Aristas**: conexiones fijas o **condicionales** (ruteo dinámico basado en el estado)
- **Checkpointing**: persistencia del estado después de cada paso (super-step)
- **Interrupciones**: capacidad de pausar el grafo y esperar input humano (`interrupt()`)
- **Ejecución paralela**: mediante `Send()` a múltiples nodos simultáneamente

### 4.2. Topología del Grafo KOSMO

El grafo completo se construye en `application/orchestration/kosmo_graph.py:build_kosmo_graph()` y contiene **17 nodos** organizados en 4 etapas:

```
       ┌──────────┐
       │ ENTRY    │
       └────┬─────┘
            │
       ┌────▼─────┐
       │supervisor│◄────────────────────────────────────────┐
       └────┬─────┘                                         │
            │                                               │
     ┌──────┼──────┬──────────────┐                         │
     │      │      │              │                         │
     ▼      ▼      ▼              │                         │
┌────────┐┌─────┐┌──────────┐    │                         │
│context ││goal ││preference │    │                         │
│analyzer││plan-││retriever  │    │                         │
│        ││ner  ││           │    │                         │
└───┬────┘└──┬──┘└─────┬─────┘    │                         │
    │        │          │          │                         │
    └────────┼──────────┘          │                         │
             │                     │                         │
        ┌────▼─────┐               │                         │
        │ context  │               │                         │
        │ merger   │───────────────┘                         │
        └──────────┘                                         │
                                                             │
    ┌────────────────────────────────────────────────────┐   │
    │            STAGE: GENERATE                         │   │
    │                                                    │   │
    │  ┌───────────────┐  ┌───────────────┐  ┌────────┐  │   │
    │  │discovery_gen  │  │features_gen   │  │ears_gen│  │   │
    │  └───────┬───────┘  └───────┬───────┘  └───┬────┘  │   │
    │          │                  │               │       │   │
    │          └──────────────────┼───┬───────────┘       │   │
    │                             │   │                    │   │
    │              ┌──────────────┼───┼──────────────┐    │   │
    │              ▼              ▼   ▼              │    │   │
    │        ┌──────────┐ ┌───────────┐ ┌──────────┐│    │   │
    │        │ quality  │ │  style   │ │consistency││    │   │
    │        │ critic   │ │ critic   │ │ critic   ││    │   │
    │        └────┬─────┘ └─────┬─────┘ └────┬─────┘│    │   │
    │             │              │             │      │    │   │
    │             └──────────────┼─────────────┘      │    │   │
    │                            ▼                     │    │   │
    │                   ┌────────────────┐             │    │   │
    │                   │ critic_merger  │             │    │   │
    │                   └───────┬────────┘             │    │   │
    │                           │                      │    │   │
    │                   ┌───────▼────────┐             │    │   │
    │                   │critic_evaluator│─────────────┼────┼──► (loop si blocked)
    │                   └───────┬────────┘             │    │   │
    └───────────────────────────┼──────────────────────┘    │   │
                                  │                           │
                          ┌───────▼────────┐                  │
                          │final_evaluator │──────────────────┘
                          └───────┬────────┘
                                  │
                          ┌───────▼────────┐
                          │learn_from_corr │
                          └───────┬────────┘
                                  │
                               ┌──▼──┐
                               │ END │
                               └─────┘
```

### 4.3. Máquina de Estados del Supervisor

El `supervisor_node` implementa una **máquina de estados de 4 etapas**:

| Etapa (`SupervisorStage`) | Propósito | Transición |
|---|---|---|
| `CONTEXT` | Dispara 3 agentes en **paralelo** (`context_analyzer`, `goal_planner`, `preference_retriever`) → mergean en `context_merger` → vuelven al supervisor | → `GENERATE` |
| `GENERATE` | Rutea al generador específico según `phase` (descubrimiento → `discovery_generator`, características → `features_generator` o `draft_refiner`, requisitos → `ears_generator`) | → Cadena de críticos |
| `EVALUATE` | Evalúa el resultado de la cadena de críticos: si `needs_revision`, reenvía al generador; si `approved`, pasa al evaluador final | → `GENERATE` o `DONE` |
| `DONE` | Pipeline completado | → `END` |

### 4.4. Ciclo ReAct en los Generadores

Cada nodo generador implementa un patrón **ReAct (Reasoning + Acting)**:

```
┌─────────────────────────────────────────────────────┐
│                 CICLO ReAct                         │
│                                                     │
│  1. THOUGHT (Análisis)                              │
│     └─ Identifica actores, flujos, reglas de negocio│
│                                                     │
│  2. OBSERVATION (Feedback)                          │
│     └─ Incorpora critique_log de iteraciones previas│
│                                                     │
│  3. ACTION PLAN (Planificación)                     │
│     └─ Distribuye entre categorías/secciones        │
│                                                     │
│  4. ACTION (Generación)                             │
│     └─ Invoca LLM con contexto estructurado         │
│                                                     │
│  5. GUARDRAIL (Validación determinista) ← NUEVO     │
│     └─ validate_*_output() verifica contratos       │
└─────────────────────────────────────────────────────┘
```

### 4.5. Inyección de Dependencias en el Grafo

Las dependencias del grafo (`LLMClient`, `UserPreferenceRepository`, `FeatureRepository`) se inyectan mediante el patrón **global mutable** en `helpers.py`:

```python
# helpers.py
_current_deps: GraphDependencies | None = None

def set_current_deps(deps: GraphDependencies) -> None:
    global _current_deps
    _current_deps = deps

def get_deps() -> GraphDependencies | None:
    return _current_deps
```

Cada nodo llama `get_deps()` para obtener el `LLMClient` y los repositorios. **Nota:** Este es un anti-patrón conocido que se abordará en un sprint futuro de refactorización (mover deps a `KOSMOState.deps` o `configurable`).

---

## 5. Catálogo Completo de Agentes

### 5.1. Agentes de Contexto (Ejecución Paralela)

Estos tres agentes se ejecutan **simultáneamente** al inicio de cada invocación del grafo:

#### `context_analyzer` (Analizador de Contexto)
- **Archivo:** `context_analyzer.py:12`
- **Rol:** Extrae información estructurada del estado actual del proyecto
- **Input:** `discovery`, `features`, `requirements`, `generation_attempts`
- **Output:** `{"domain": "e-commerce B2B", "key_entities": ["pedido", "producto"], "complexity_level": "medium", "gaps_identified": [...], "recommended_focus": "...", "context_brief": "..."}`
- **LLM:** Sí (invoca `llm_client.complete()` con prompt analítico)
- **Determinismo:** Bajo — depende de la interpretación del LLM

#### `goal_planner` (Planificador de Objetivos)
- **Archivo:** `goal_planner.py:11`
- **Rol:** Descompone la fase actual en sub-objetivos accionables y medibles
- **Input:** `phase`, `context_analyzer_output`
- **Output:** `{"sub_goals": [...], "success_criteria": [...], "dependencies": [...], "parallelizable_tasks": [...], "estimated_sections": 5}`
- **LLM:** Sí (invoca `llm_client.complete()`)

#### `preference_retriever` (Recuperador de Preferencias)
- **Archivo:** `preference_retriever.py:11`
- **Rol:** Recupera preferencias del usuario desde la base de datos y las formatea para inyección en prompts
- **Input:** `user_id`, `project_id`
- **Output:** `{"preferences_prompt": "## Preferencias del Usuario\n1. Prefiere listas numeradas...", "retrieval_error": null}`
- **LLM:** No — es determinista, consulta BD directamente
- **Post-acción:** Incrementa `usage_count` de las preferencias recuperadas

#### `context_merger` (Fusionador de Contexto)
- **Archivo:** `context_merger.py:9`
- **Rol:** Consolida los outputs de analyzer, planner y retriever en `shared_scratchpad`
- **Input:** `agent_outputs`
- **Output:** `shared_scratchpad` actualizado con las 3 claves fusionadas
- **LLM:** No — merge determinista con política de resolución de conflictos

### 5.2. Agentes Generadores

#### `discovery_generator` (Generador de Descubrimiento)
- **Archivo:** `discovery_generator.py:42`
- **Fase:** `DESCUBRIMIENTO`
- **Rol:** Genera un documento de descubrimiento con 9 secciones de análisis de negocio
- **Ciclo ReAct:** Implementado — Thought → Action Plan → Action con feedback de críticos
- **LLM:** Sí — `llm_client.complete()` con `temperature=0`
- **Modo mejora:** Si `generator_action == "improve"`, refina documento existente sin reescribir desde cero
- **Guardrail post-LLM:** `validate_discovery_output()` — verifica 9 secciones, mínimo 50 caracteres/sección, términos prohibidos
- **Output al estado:** `discovery`, `generated_document`, `generated_document_md`, `generated_document_tree`
- **Prompt del sistema:** 45 líneas con principios de negocio, términos prohibidos, regla anti-trivialidad y ejemplo de inferencia rica

#### `features_generator` (Generador de Características)
- **Archivo:** `features_generator.py:72`
- **Fase:** `CARACTERISTICAS`
- **Rol:** Infiere características ricas y específicas del dominio a partir del discovery
- **Ciclo ReAct:** Implementado — con feedback de críticos y guardrails post-LLM
- **LLM:** Sí — `llm_client.complete()` con `temperature=0.3`
- **Anti-trivialidad:** Recibe lista de títulos existentes como **sección PROHIBIDA** con ejemplos de paráfrasis negativas
- **Contexto vinculante:** Se inyectan secciones del discovery (Visión, Actores, Propuesta de Valor, Reglas de Negocio, Casos de Uso, Capacidades) como contexto obligatorio para inferencia
- **Few-Shot:** Ejemplo completo de 3 sugerencias correctas vs sugerencias triviales incorrectas
- **Guardrail post-LLM:** `validate_features_output()` — exactamente 3 sugerencias, título >= 3 chars, descripción >= 20 chars, rationale >= 10 chars, deduplicación contra existentes, detección de paráfrasis
- **Output al estado:** `features`, `generated_features`, `existing_feature_titles`, `existing_feature_ids`

#### `ears_generator` (Generador de Requisitos EARS)
- **Archivo:** `ears_generator.py:94`
- **Fase:** `REQUISITOS`
- **Rol:** Transforma features aprobadas en requisitos EARS de negocio clasificados en 6 categorías
- **Ciclo ReAct:** Implementado — Análisis → Corrección → Planificación → Generación → Auto-Validación
- **LLM:** Sí — `llm_client.complete()` con `temperature=0`, `max_tokens=8192`
- **Validación de estado:** Bloquea la generación si `current_feature_status != "aprobada"`
- **Guardrail post-LLM:** `validate_ears_output()` — 6 categorías presentes, source_statement >= 10 chars, response >= 5 chars, términos prohibidos, mínimo 3 requisitos totales, trigger obligatorio según patrón
- **Auto-reparación:** `_auto_repair_leaks()` — reemplaza términos de implementación detectados por `[comportamiento de negocio]`
- **Scoring:** `score_requirements_batch()` — evaluá en 6 dimensiones (pureza_negocio 30%, correccion_ears 25%, verificabilidad 20%, completitud 10%, no_ambiguedad 10%, cobertura 5%)
- **Output al estado:** `requirements`, `generated_ears`, `ears_batch_score`

#### `draft_refiner` (Refinador de Borradores)
- **Archivo:** `draft_refiner.py:10`
- **Fase:** Cualquier fase en modo `improve`
- **Rol:** Mejora documentos existentes aplicando correcciones quirúrgicas sin reescribir desde cero
- **Modo dual:** Si `phase_context == "features"`, actúa como Analista de Producto; si no, como Editor de Documentos de Negocio
- **LLM:** Sí — `llm_client.complete()` con `temperature=0.3`
- **Output al estado:** `generated_content_md`, `refined_content`

### 5.3. Agentes Críticos (Cadena de Evaluación)

Tres críticos en **ejecución paralela** que evalúan la salida del generador activo, consolidados por `critic_merger`:

#### `quality_critic` (Crítico de Calidad EARS)
- **Archivo:** `critics.py:114`
- **Rol:** Auditor de calidad — evalúa cada requisito contra una rúbrica de 6 dimensiones con escala 1-10
- **Dimensiones evaluadas:**
  1. **Pureza de Negocio** (30%) — CERO términos técnicos
  2. **Corrección EARS** (25%) — source_statement sigue el patrón exacto
  3. **Verificabilidad** (20%) — criterios verificables por analista funcional
  4. **Completitud** (10%) — todos los campos requeridos presentes
  5. **No-Ambigüedad** (10%) — lenguaje concreto sin términos vagos
  6. **Cobertura** (5%) — 2+ criterios, trigger, rationale
- **Severity:** `blocker` (score < 5 o fuga técnica), `warning` (score 5-6), `none` (score >= 7)
- **LLM:** Sí — evalúa contenido generado contra la rúbrica

#### `style_critic` (Crítico de Estilo EARS)
- **Archivo:** `critics.py:289`
- **Rol:** Editor de estilo — verifica sintaxis EARS, nomenclatura, uso correcto de shall/should/may, formato Dado-Cuando-Entonces, lenguaje de negocio y ortografía
- **Condición de activación:** Solo se ejecuta si hay preferencias de usuario recuperadas
- **LLM:** Sí — verifica contra preferencias del usuario

#### `consistency_critic` (Crítico de Consistencia)
- **Archivo:** `critics.py:214`
- **Rol:** Guardián de consistencia — detecta 5 tipos de problemas estructurales:
  1. Requisitos duplicados
  2. Requisitos contradictorios
  3. Terminología inconsistente
  4. Vacíos de cobertura (categorías EARS vacías)
  5. Dependencias no declaradas
- **LLM:** Sí — analiza el conjunto completo de requisitos

### 5.4. Agentes de Evaluación y Aprendizaje

#### `critic_evaluator` (Evaluador de Críticos)
- **Archivo:** `critic_evaluator.py:9`
- **Rol:** Gate obligatorio post-críticos. Decide si reenviar al generador o pasar al evaluador final
- **Lógica:** Si hay blockers → reenvía al generador con feedback estructurado. Si hay warnings y `critic_iteration < max_critic_iterations` → reenvía. Si todo approved → pasa a final_evaluator
- **LLM:** No — lógica booleana determinista
- **Max critic iterations:** 3

#### `final_evaluator` (Evaluador Final)
- **Archivo:** `final_evaluator.py:41`
- **Rol:** Última línea de defensa antes de entregar al usuario. Evalúa contra 5 criterios:
  1. Pureza de Negocio (1-10)
  2. Cobertura EARS (1-10)
  3. Verificabilidad Funcional (1-10)
  4. Densidad de Criterios (1-10)
  5. Ortografía (1-10)
- **Veredicto:** `approved` (todos >= 6, sin blockers), `needs_revision` (algún < 6 o hay blockers)
- **Interrupción humana:** Si se agotan `max_iterations`, usa `langgraph.types.interrupt()` para solicitar decisión humana (accept / edit / abort)
- **LLM:** Sí

#### `learn_from_correction` (Aprendizaje por Corrección)
- **Archivo:** `learn_from_correction.py:11`
- **Rol:** Extrae deltas de correcciones del usuario y almacena preferencias aprendidas
- **Pipeline de aprendizaje:**
  1. `delta_extractor()` — diff unificado entre documento original (IA) y corregido (usuario)
  2. `rule_inferencer()` — LLM identifica patrones de edición → infiere reglas
  3. `conflict_resolver()` — detecta duplicados contra preferencias existentes
  4. `preference_store()` — persiste nuevas reglas en `user_preferences`
- **LLM:** Sí — `rule_inferencer` usa LLM para inferir reglas desde el diff
- **Ejecución:** Nodo terminal — se ejecuta al final del grafo si hay datos de corrección

---

## 6. Diagramas de Flujo y Topología

### 6.1. Diagrama de Máquina de Estados del Supervisor

```mermaid
stateDiagram-v2
    [*] --> CONTEXT: Inicio de pipeline
    
    state CONTEXT {
        [*] --> context_analyzer
        [*] --> goal_planner
        [*] --> preference_retriever
        context_analyzer --> context_merger: merge
        goal_planner --> context_merger: merge
        preference_retriever --> context_merger: merge
        context_merger --> [*]: vuelve a supervisor
    }
    
    CONTEXT --> GENERATE: dispatch_context()
    
    state GENERATE {
        [*] --> SelectorFase
        SelectorFase --> discovery_generator: phase=DESCUBRIMIENTO
        SelectorFase --> features_generator: phase=CARACTERISTICAS
        SelectorFase --> ears_generator: phase=REQUISITOS
        SelectorFase --> draft_refiner: action=improve
    }
    
    GENERATE --> CRITICS: generación completada
    
    state CRITICS {
        [*] --> quality_critic
        [*] --> style_critic
        [*] --> consistency_critic
        quality_critic --> critic_merger: merge
        style_critic --> critic_merger: merge
        consistency_critic --> critic_merger: merge
        critic_merger --> critic_evaluator: evalúa
    }
    
    CRITICS --> GENERATE: needs_revision && iteration < max
    
    state EVALUATE {
        critic_evaluator --> final_evaluator: approved
    }
    
    CRITICS --> EVALUATE: approved
    
    EVALUATE --> GENERATE: needs_revision && attempt < max
    EVALUATE --> DONE: output_ready || rejected
    EVALUATE --> HUMAN_REVIEW: max_iterations alcanzado
    
    state HUMAN_REVIEW {
        [*] --> EsperaInput
        EsperaInput --> accept_as_is
        EsperaInput --> edit_and_retry
        EsperaInput --> abort
        accept_as_is --> [*]
        edit_and_retry --> GENERATE: reenvía con feedback
        abort --> [*]
    }
    
    DONE --> learn_from_correction
    learn_from_correction --> [*]: END
    HUMAN_REVIEW --> learn_from_correction: accept / abort
```

### 6.2. Diagrama de Secuencia: Flujo Completo de una Generación

```mermaid
sequenceDiagram
    actor Usuario
    participant Router as FastAPI Router
    participant Engine as LangGraphEngine
    participant Supervisor as supervisor_node
    participant Analyzer as context_analyzer
    participant Planner as goal_planner
    participant Prefs as preference_retriever
    participant Merger as context_merger
    participant Generator as *_generator
    participant QCritic as quality_critic
    participant SCritic as style_critic
    participant CCritic as consistency_critic
    participant CEval as critic_evaluator
    participant Final as final_evaluator
    participant Learn as learn_from_correction
    participant LLM as LLMClient (DeepSeek/LiteLLM)
    participant DB as PostgreSQL + Redis
    
    Usuario->>Router: POST /features/generate
    Router->>DB: get project, existing features
    Router->>Engine: invoke(KOSMOState)
    Engine->>Engine: set_current_deps(llm, prefs)
    
    Note over Engine,Supervisor: STAGE: CONTEXT
    
    Engine->>Supervisor: state (supervisor_stage=CONTEXT)
    Supervisor->>Supervisor: dispatch: current_subtask = "features_generator"
    Supervisor->>Supervisor: check compress_context (token threshold)
    Supervisor-->>Engine: stage → GENERATE
    
    par Ejecución Paralela (Send)
        Engine->>Analyzer: context_analyzer_node(state)
        Analyzer->>LLM: complete() — extraer dominio, entidades, gaps
        LLM-->>Analyzer: JSON estructurado
        Analyzer-->>Engine: agent_outputs["context_analyzer"]
    and
        Engine->>Planner: goal_planner_node(state)
        Planner->>LLM: complete() — descomponer en sub-objetivos
        LLM-->>Planner: JSON con sub_goals
        Planner-->>Engine: agent_outputs["goal_planner"]
    and
        Engine->>Prefs: preference_retriever_node(state)
        Prefs->>DB: get_by_user(user_id, project_id)
        DB-->>Prefs: [UserPreference, ...]
        Prefs->>DB: increment_usage(pref_ids)
        Prefs-->>Engine: agent_outputs["preference_retriever"]
    end
    
    Engine->>Merger: context_merger_node(state)
    Merger->>Merger: merge analyzer + planner + prefs → shared_scratchpad
    Merger-->>Engine: scratchpad actualizado
    
    Note over Engine,Generator: STAGE: GENERATE
    
    Engine->>Supervisor: vuelve al supervisor
    Supervisor->>Supervisor: route_to_generator → "features_generator"
    Engine->>Generator: features_generator_node(state)
    Generator->>Generator: build system prompt + Few-Shot
    Generator->>Generator: inject discovery context + denied titles
    Generator->>LLM: complete() — generate 3 features
    LLM-->>Generator: JSON con suggestions
    Generator->>Generator: validate_features_output() ← GUARDRAIL
    Generator-->>Engine: features + scratchpad
    
    Note over Engine,Final: STAGE: EVALUATE (cadena de críticos en PARALELO)
    
    par Ejecución Paralela de Críticos
        Engine->>QCritic: quality_critic_node(state)
        QCritic->>LLM: complete() — evaluar rúbrica 6 dimensiones
        LLM-->>QCritic: severity + dimension_scores
        QCritic-->>Engine: critique_log
    and
        Engine->>SCritic: style_critic_node(state)
        SCritic->>LLM: complete() — verificar sintaxis EARS + estilo
        LLM-->>SCritic: severity + findings
        SCritic-->>Engine: critique_log + agent_mailbox feedback
    and
        Engine->>CCritic: consistency_critic_node(state)
        CCritic->>LLM: complete() — detectar duplicados, gaps
        LLM-->>CCritic: severity + findings
        CCritic-->>Engine: critique_log
    end
    
    Engine->>Engine: critic_merger_node(state) — consolida 3 críticos
    Engine->>CEval: critic_evaluator_node(state)
    CEval->>CEval: lógica: blockers? warnings? approved?
    alt needs_revision && iteration < max_critic
        CEval-->>Engine: reenvía a Generator
        Note over Generator: Ciclo de mejora (max 3 iteraciones)
    else approved
        CEval-->>Engine: pasa a final_evaluator
    end
    
    Engine->>Final: final_evaluator_node(state)
    Final->>LLM: complete() — 5 criterios finales
    LLM-->>Final: overall_verdict + scores
    alt approved
        Final-->>Engine: output_ready = True
    else needs_revision && attempt < max
        Final-->>Engine: reenvía a supervisor
    else max_iterations alcanzado
        Final->>Usuario: interrupt() — human_review_required
        Usuario-->>Final: accept / edit / abort
    end
    
    Engine->>Learn: learn_from_correction_node(state)
    Learn->>Learn: delta_extractor (diff original vs corregido)
    Learn->>LLM: rule_inferencer — identificar patrones
    LLM-->>Learn: reglas inferidas
    Learn->>DB: preference_store(reglas)
    
    Engine-->>Router: KOSMOState final
    Router->>DB: persist features
    Router-->>Usuario: FeaturesListResponse
```

### 6.3. Diagrama de Componentes y Conexiones

```mermaid
graph TD
    subgraph "Infrastructure"
        FR[FastAPI Routers]
        LGE[LangGraphEngine]
        PG[PostgreSQL + pgvector]
        RD[Redis]
        DS[DeepSeek Adapter]
        LL[LiteLLM Adapter]
        NOOP[NoopLLMClient]
    end
    
    subgraph "Application"
        UC[Use Cases]
        SG[StateGraph build_kosmo_graph]
        SUP[supervisor_node]
        CTX[context_analyzer]
        GP[goal_planner]
        PR[preference_retriever]
        CM[context_merger]
        DG[discovery_generator]
        FG[features_generator]
        EG[ears_generator]
        DR[draft_refiner]
        QC[quality_critic]
        SC[style_critic]
        CC[consistency_critic]
        CE[critic_evaluator]
        FE[final_evaluator]
        LC[learn_from_correction]
    end
    
    subgraph "Domain"
        GRD[output_guardrails]
        EARS_V[ears_validator]
        DC[document_converters]
        ID[IdGenerator]
        CCMP[context_compressor]
        LRN[learning nodes]
    end
    
    subgraph "Contracts"
        ST[KOSMOState]
        LLMP[LLMClient Protocol]
        GEP[GraphEngine Protocol]
        REPOS[Repository Protocols]
        GR[GuardrailResult]
    end
    
    FR --> UC
    FR --> LGE
    LGE --> SG
    LGE --> PG
    LGE --> DS
    LGE --> LL
    LGE --> NOOP
    
    SG --> SUP
    SG --> CTX
    SG --> GP
    SG --> PR
    SG --> CM
    SG --> DG
    SG --> FG
    SG --> EG
    SG --> DR
    SG --> QC
    SG --> SC
    SG --> CC
    SG --> CE
    SG --> FE
    SG --> LC
    
    CTX --> LLMP
    GP --> LLMP
    DG --> LLMP
    FG --> LLMP
    EG --> LLMP
    DR --> LLMP
    QC --> LLMP
    SC --> LLMP
    CC --> LLMP
    FE --> LLMP
    LC --> LLMP
    SUP --> CCMP
    
    DG --> GRD
    FG --> GRD
    EG --> GRD
    EG --> EARS_V
    EG --> ID
    
    PR --> REPOS
    LC --> REPOS
    UC --> REPOS
    
    SG --> ST
    SUP --> ST
```

---

## 7. Estado Global — KOSMOState

```python
class KOSMOState(BaseModel):
    # Identidad
    project_id: str
    user_id: str

    # Artefactos de dominio
    raw_idea: RawIdea | None = None
    discovery: DiscoveryDocument | None = None       # 9 secciones de negocio
    features: list[Feature] = []                      # Características generadas
    requirements: list[EARSRequirement] = []           # Requisitos EARS

    # Fase actual del pipeline
    phase: SpecPhase = SpecPhase.DESCUBRIMIENTO       # 5 fases

    # Comunicación entre agentes
    shared_scratchpad: dict[str, object] = {}          # Memoria compartida (legacy)
    agent_outputs: dict[str, object] = {}              # Outputs por agente
    scratchpad: Scratchpad = Field(...)                # Memoria tipeada (NUEVO)

    # Contexto de features existentes (NUEVO)
    existing_feature_titles: list[str] = []            # Para anti-trivialidad
    existing_feature_ids: list[str] = []               # Para deduplicación

    # Auditoría
    critique_log: list[CritiqueRecord] = []            # Feedback de críticos
    tool_call_history: list[ToolCallRecord] = []       # Trazabilidad de invocaciones

    # Control de flujo
    max_iterations: int = 10                           # Límite global de reintentos
    generation_attempts: int = 0                       # Contador de intentos
    critic_iteration: int = 0                          # Contador de ciclo crítico
    max_critic_iterations: int = 3                     # Límite de reintentos post-crítico

    # Veredictos
    validation_status: str | None = None               # approved | pending_review | needs_revision | rejected
    critic_verdict: str | None = None                  # approved | needs_revision

    # Navegación
    current_subtask: str | None = None                 # Nombre del nodo generador activo
    supervisor_stage: SupervisorStage = CONTEXT        # Máquina de estados

    # Interacción humana
    human_input_pending: bool = False                  # Flag para interrupt()
    human_prompt: str | None = None                    # Mensaje para el usuario
    output_ready: bool = False                         # Flag de salida final
    evaluation_summary: dict[str, object] = {}         # Resumen del evaluador final

    # Errores
    errors: list[str] = []                             # Acumulador de errores
```

### 7.1. Flujo de Transformación del Estado

```
Invocación inicial (desde Router)
│
│  state = KOSMOState(
│      project_id="prj_01KT...",
│      user_id="usr_01KT...",
│      phase=SpecPhase.CARACTERISTICAS,
│      discovery=DiscoveryDocument(...),
│      existing_feature_titles=["Dashboard de ventas", ...],
│      existing_feature_ids=["feat_...", ...],
│  )
│
▼
supervisor_node(state)  →  stage=CONTEXT → dispatch
│
▼
[context_analyzer + goal_planner + preference_retriever]  ← PARALELO
│
▼
context_merger → shared_scratchpad actualizado
│
▼
supervisor_node(state)  →  stage=GENERATE → "features_generator"
│
▼
features_generator(state)  →  features + generated_features + guardrail
│
▼
[quality_critic → style_critic → consistency_critic]
│
▼
critic_evaluator(state)  →  needs_revision? → (loop: vuelve a generator)
                         →  approved?       → final_evaluator
│
▼
final_evaluator(state)   →  approved? → output_ready=True, validation_status="approved"
                         →  rejected? → output_ready=False, validation_status="rejected"
                         →  max?      → interrupt() → human decision
│
▼
learn_from_correction(state) ← NODO FINAL
│
▼
END → LangGraphEngine.invoke() retorna KOSMOState final → Router persiste
```

---

## 8. Mecanismo de Aprendizaje (Learning Pipeline)

### 8.1. Flujo de Aprendizaje Completo

```
Usuario edita documento generado por IA
│
▼
Router detecta diff: original_document != corrected_document
│
▼
save_discovery_document / save_requirements_document
│
├─► LearnFromCorrectionUseCase.execute()
│   │
│   ├─► 1. delta_extractor(original, corrected)
│   │      └─ Convierte ambos a Markdown
│   │      └─ Aplica difflib.unified_diff()
│   │      └─ Retorna: {diff_text, original_md, corrected_md, added_lines, removed_lines}
│   │
│   ├─► 2. rule_inferencer(delta, document_type, llm_client)
│   │      └─ Si added_lines == 0 y removed_lines == 0 → skip
│   │      └─ Prompt con ambos documentos (truncados a 3000 chars)
│   │      └─ LLM identifica patrones de edición → infiere reglas
│   │      └─ Output: [{rule_text, corpus, context_snippet}, ...]
│   │
│   ├─► 3. conflict_resolver(new_rules, user_id, project_id, repo)
│   │      └─ Carga preferencias existentes del usuario
│   │      └─ Compara rule_text.lower() para detectar duplicados
│   │      └─ Marca duplicados con flag "duplicate: true"
│   │
│   └─► 4. preference_store(rules, user_id, project_id, doc_type, repo)
│          └─ Genera ULID con prefijo "pref_"
│          └─ Crea UserPreference con rule_text, corpus, context_snippet
│          └─ Persiste en user_preferences (PostgreSQL)
│
▼
Próxima invocación del grafo
│
├─► preference_retriever_node
│      └─ get_by_user(user_id, project_id, limit=20)
│      └─ Formatea: "## Preferencias del Usuario\n1. {rule_text}\n..."
│      └─ Inyecta en system_prompt de generadores
│      └─ increment_usage(pref_ids)
```

### 8.2. Ejemplo de Inferencia de Reglas

| Documento Original (IA) | Documento Corregido (Usuario) | Regla Inferida |
|---|---|---|
| "El sistema permitirá crear, leer, actualizar y eliminar tareas" | "El sistema permitirá **gestionar el ciclo de vida completo de las tareas**: registro, asignación, seguimiento, notificación y cierre" | "El usuario prefiere descripciones de negocio que cubran el ciclo de vida completo con verbos de dominio" |
| Usa bullets con `-` | Usa bullets con `1.`, `2.` | "El usuario prefiere listas numeradas para pasos secuenciales" |

---

## 9. Persistencia: Checkpointing, Memoria y Documentos Duales

### 9.1. Checkpointing de LangGraph

El `LangGraphEngine` utiliza `AsyncPostgresSaver` como checkpointer. Esto significa que **después de cada super-step** del grafo, el estado completo (`KOSMOState`) se serializa y persiste en PostgreSQL.

```python
# langgraph_engine.py
self._checkpointer = await AsyncPostgresSaver.from_conn_string(db_url)
self._compiled = self._graph.compile(checkpointer=self._checkpointer)
```

**Implicaciones:**
- Si el grafo se interrumpe (error, timeout, `interrupt()`), puede **reanudarse** desde el último checkpoint
- El `thread_id` identifica una sesión de ejecución
- Actualmente los `thread_id` varían por endpoint (`str(pid)`, `f"{pid}_suggest"`, `f"{fid}"`, etc.), lo que significa que no hay persistencia cross-invocación para el mismo proyecto

### 9.2. Memoria de Usuario (User Preferences)

| Entidad | Ubicación | Propósito |
|---|---|---|
| `UserPreference` | PostgreSQL (`user_preferences`) | Almacena reglas de estilo inferidas de correcciones |
| `preference_retriever_node` | Nodo del grafo | Recupera preferencias y las inyecta en prompts |
| `learn_from_correction_node` | Nodo del grafo | Infiere y persiste nuevas preferencias |
| `rule_inferencer` → `LLM` | Domain + LLM | Identifica patrones de edición |
| `conflict_resolver` | Domain | Evita duplicados en preferencias |

### 9.3. Dualidad de Documentos (Vista vs Limpio)

Para resolver el problema de contaminación de contexto, se implementa una **persistencia dual**:

| Columna | Contenido | Consumidor |
|---|---|---|
| `discovery_document` (JSON) | Árbol TipTap/ProseMirror completo — editable por el usuario en el editor rico | Frontend (editor) |
| `discovery_clean` (JSON) | `DiscoveryDocument` con 9 strings — sin markup decorativo | Agentes de IA (input exclusivo) |
| `requirements_document` (JSON) | Árbol TipTap/ProseMirror completo | Frontend (editor) |
| `requirements_clean` (JSON) | `RequirementsDocument` con listas EARS tipeadas | Agentes de IA (input exclusivo) |

**Puerto:** `contracts/sdd/document_repository.py` → `DocumentRepository (Protocol)`
**Adaptador:** `infrastructure/persistence/postgres/repositories/document_repo.py` → `SqlAlchemyDocumentRepository`

---

## 10. Guardrails y Verificación Determinista

### 10.1. Arquitectura de Guardrails

```
LLM Response (string)
│
▼
extract_json(content)  →  dict
│
▼
┌─────────────────────────────────────┐
│   DOMAIN/SDD/OUTPUT_GUARDRAILS.PY   │  ← CAPA PURA (sin I/O)
│                                     │
│  validate_discovery_output(data)    │
│  ├─ 9 secciones presentes?          │
│  ├─ ≥ 50 caracteres por sección?    │
│  ├─ Términos prohibidos?            │
│  └─ → GuardrailResult               │
│                                     │
│  validate_features_output(data,     │
│      existing_titles)               │
│  ├─ Exactamente 3 sugerencias?      │
│  ├─ title ≥ 3 chars?               │
│  ├─ description ≥ 20 chars?        │
│  ├─ rationale ≥ 10 chars?          │
│  ├─ Duplicado de existente?         │
│  ├─ Paráfrasis de existente?        │
│  ├─ Términos prohibidos?            │
│  └─ → GuardrailResult               │
│                                     │
│  validate_ears_output(data)         │
│  ├─ 6 categorías presentes?         │
│  ├─ source_statement ≥ 10 chars?   │
│  ├─ response ≥ 5 chars?            │
│  ├─ trigger en patrones que lo      │
│  │   requieren (event, state, etc)? │
│  ├─ ≥ 1 acceptance_criterion?      │
│  ├─ ≥ 3 requisitos totales?        │
│  ├─ Términos prohibidos?            │
│  └─ → GuardrailResult               │
└─────────────────────────────────────┘
│
▼
GuardrailResult
├─ is_valid: bool
├─ violations: list[GuardrailViolation]
│   ├─ field: str
│   ├─ message: str
│   └─ severity: "blocker" | "warning"
└─ sanitized: dict | list | None
```

### 10.2. Ciclo de Reintento con Guardrails

```
generator → LLM → parse → GUARDRAIL
                              │
                    ┌─────────┴──────────┐
                    │                    │
               is_valid=True        is_valid=False
                    │                    │
                    ▼                    ▼
             continúa normal      ¿iteration < 3?
                                       │
                              ┌────────┴────────┐
                              │                  │
                             YES                NO
                              │                  │
                              ▼                  ▼
                      reintenta generator    retorna error
                      con feedback de       al endpoint
                      guardrail violations
```

---

## 11. Análisis Funcional: ¿Orquestación Multiagente o Secuencia de Prompts?

> **Nota metodológica:** Este análisis se basa en el código real implementado en `src/kosmo/application/orchestration/` a fecha de junio 2026. Cada afirmación está respaldada por inspección directa del grafo (`kosmo_graph.py`, 159 líneas) y los 16 nodos que lo componen.

### 11.1. Inventario Real de Agentes (Inspección de Código)

Se registraron **16 nodos** en `build_kosmo_graph()`. De ellos, **15 constituyen agentes con responsabilidades distintas** y 1 (`critic_merger`) es un nodo utilitario de consolidación. La tabla siguiente documenta la presencia real de cada agente en el grafo, si invoca LLM, y si usa herramientas externas:

| # | Nodo | Invoca LLM? | Usa herramientas? | Prompt del sistema verificado | Integrado en grafo |
|---|---|---|---|---|---|
| 1 | `supervisor` | No | No | Lógica de máquina de estados (pura) | `set_entry_point` |
| 2 | `context_analyzer` | **Sí** (L76) | No | "analista de contexto experto en ingeniería de software" (L39) | `Send` paralelo |
| 3 | `goal_planner` | **Sí** | No | Prompt simple de planificación | `Send` paralelo |
| 4 | `preference_retriever` | No | Consulta BD (preference_repo) | N/A — determinista | `Send` paralelo |
| 5 | `context_merger` | No | No | Merge determinista de 3 outputs | Arista directa → supervisor |
| 6 | `discovery_generator` | **Sí** (L113) | No | "Analista de Negocio Senior con 15 años" (L15) | `add_node` + `add_edge` → críticos |
| 7 | `features_generator` | **Sí** (L212) | **Sí** — `tool_registry.invoke("search_features")` (L84-98) | "Arquitecto de Producto Senior con 15 años" + Few-Shot (L17-72) | `add_node` + `add_edge` → críticos |
| 8 | `ears_generator` | **Sí** (L166) | No | "Ingeniero de Requisitos de Negocio Senior" (L291) | `add_node` + `add_edge` → críticos |
| 9 | `draft_refiner` | **Sí** | No | Dual: Analista de Producto / Editor de Negocio | `add_node` + `add_edge` → críticos |
| 10 | `quality_critic` | **Sí** (L163) | No | "Auditor de Calidad EARS" — rúbrica 6 dimensiones (L16-66) | `add_node` + `add_edge` → critic_merger |
| 11 | `style_critic` | **Sí** (solo si hay prefs, L310) | No | "Editor de Estilo EARS" — 6 criterios (L92-113) | `add_node` + `add_edge` → critic_merger |
| 12 | `consistency_critic` | **Sí** (L264) | No | "Guardián de Consistencia" — 5 tipos de problemas (L69-89) | `add_node` + `add_edge` → critic_merger |
| 13 | `critic_merger` | No | No | Deduplica hallazgos overlapeados, prioriza por severidad (L7-80) | `add_node` + `add_edge` → critic_evaluator |
| 14 | `critic_evaluator` | No | No | Gate booleano: blockers → reenvío; warnings → reenvío si < max; approved → final (L8-132) | `add_conditional_edges` |
| 15 | `final_evaluator` | **Sí** (L87) | No | "Evaluador Final — ÚLTIMA LÍNEA DE DEFENSA" — 5 criterios (L17-38) | `add_node` + `add_conditional_edges` |
| 16 | `preference_feedback` | No | Consulta BD (preference_repo) | Refuerzo de confianza de preferencias (L12-98) | `add_node` + `add_edge` → learn_from_correction |
| 17 | `learn_from_correction` | Delega a `LearnFromCorrectionUseCase` (LLM interno) | No | Pipeline de aprendizaje: delta → reglas → persistencia (L12-96) | `add_node` + `add_edge` → END |

**Hallazgo:** De 16 nodos, 8 invocan LLM directamente, 2 consultan base de datos con lógica determinista, 5 son lógica pura (sin I/O), y 1 (`features_generator`) intenta usar tool_registry.

### 11.2. Topología Real del Grafo (Verificada en Código)

```python
# kosmo_graph.py — flujo verificado línea por línea

# ENTRY: supervisor (stage machine)
builder.set_entry_point("supervisor")

# STAGE CONTEXT: 3 agentes en PARALELO vía Send() (L49-53)
# → context_analyzer, goal_planner, preference_retriever
# Se mergean en context_merger → vuelve a supervisor

# STAGE GENERATE: supervisor rutea a 1 de 4 generadores
# → discovery_generator | features_generator | ears_generator | draft_refiner
# Cada generador emite a los 3 críticos en PARALELO (L116-131)
builder.add_edge("discovery_generator", "quality_critic")
builder.add_edge("discovery_generator", "style_critic")
builder.add_edge("discovery_generator", "consistency_critic")
# (mismo patrón para los otros 3 generadores)

# CRITICS: 3 críticos en PARALELO → critic_merger → critic_evaluator (L129-133)
builder.add_edge("quality_critic", "critic_merger")
builder.add_edge("style_critic", "critic_merger")
builder.add_edge("consistency_critic", "critic_merger")
builder.add_edge("critic_merger", "critic_evaluator")

# GATE: critic_evaluator → (loop: generador) o (forward: final_evaluator) (L135-144)
builder.add_conditional_edges("critic_evaluator", route_after_critic_evaluator, {
    "discovery_generator": "discovery_generator",  # loop
    ...
    "final_evaluator": "final_evaluator",          # forward
})

# FINAL: final_evaluator → (loop: supervisor) o (forward: preference_feedback) (L147-153)
builder.add_conditional_edges("final_evaluator", route_after_evaluator, {
    "supervisor": "supervisor",       # loop global
    END: "preference_feedback",       # forward
})

# LEARNING: preference_feedback → learn_from_correction → END (L156-157)
builder.add_edge("preference_feedback", "learn_from_correction")
builder.add_edge("learn_from_correction", END)
```

**Hallazgo crítico corregido:** Los 3 críticos (`quality`, `style`, `consistency`) se ejecutan **en paralelo**, no secuencialmente como afirmaba la versión anterior de este documento. Cada generador emite aristas hacia los 3 críticos simultáneamente, y el nodo `critic_merger` los consolida. Esto duplica el paralelismo del grafo (antes solo en CONTEXT, ahora también en CRITICS).

### 11.3. Criterios de Evaluación

| Criterio | Definición | Peso |
|---|---|---|
| **A. Especialización de Roles** | Cada agente tiene personalidad, prompt del sistema y responsabilidad inconfundibles | 20% |
| **B. Estado Compartido con Transformación** | Los agentes leen y escriben un estado común que evoluciona | 20% |
| **C. Ejecución Paralela** | Múltiples agentes se ejecutan simultáneamente | 15% |
| **D. Ciclos de Retroalimentación** | Agentes revisan, critican y reenvían el trabajo de otros agentes | 20% |
| **E. Ruteo Condicional Dinámico** | El flujo no es fijo; depende del estado y decisiones runtime | 15% |
| **F. Memoria y Aprendizaje** | El sistema recuerda interacciones previas y adapta su comportamiento | 10% |

### 11.4. Evaluación de KOSMO (Basada en Código Real)

#### A. Especialización de Roles — **CUMPLE (19/20)**

**Verificación en código:** Cada nodo tiene su propio archivo con un `system_prompt` distinto y no trivial:

| Agente | Prompt verificado | Longitud | Técnica |
|---|---|---|---|
| `discovery_generator` | `_DISCOVERY_SYSTEM` — 9 principios de negocio, términos prohibidos, regla anti-trivialidad, ejemplo de inferencia rica vs trivial | 56 líneas | Few-shot negativo + guardrails |
| `features_generator` | `_SUGGESTION_SYSTEM` + `_SUGGESTION_FEW_SHOT` — ejemplo completo de 3 sugerencias correctas vs 3 triviales incorrectas | 72 líneas | Few-shot con ejemplos positivos y negativos |
| `ears_generator` | `_EARS_CATEGORY_INSTRUCTIONS` (70 líneas) + `_BUSINESS_PRINCIPLES` + `_TERMS_PROHIBITED` (72 términos) + `_QUALITY_CHECKLIST` (10 puntos) | ~200 líneas de prompt | Instrucción exhaustiva + checklist |
| `quality_critic` | `_QUALITY_CRITIC_SYSTEM` — rúbrica de 6 dimensiones con escala numérica, severidad blocker/warning/none | 66 líneas | Rúbrica cuantitativa |
| `consistency_critic` | `_CONSISTENCY_CRITIC_SYSTEM` — 5 tipos de problemas estructurales | 24 líneas | Taxonomía de errores |
| `style_critic` | `_STYLE_CRITIC_SYSTEM` — 6 criterios de estilo EARS | 22 líneas | Checklist de convenciones |

**Conclusión:** 15 agentes con roles diferenciados, prompts del sistema únicos y verificables. No son el mismo prompt con parámetros distintos. La especificidad de los prompts (especialmente `ears_generator` con ~200 líneas de instrucciones y `features_generator` con técnica few-shot negativa) demuestra especialización profunda.

#### B. Estado Compartido con Transformación — **CUMPLE PARCIALMENTE (15/20)**

**Verificación en código:**

- **Fortaleza:** `KOSMOState` es un `BaseModel` compartido por los 16 nodos. Campos clave verificados:
  - `shared_scratchpad: dict[str, object]` — pizarra común (usado en todos los generadores)
  - `agent_outputs: dict[str, object]` — outputs por agente (usado por `critic_merger` L23-45, `learn_from_correction`)
  - `agent_mailbox: dict[str, list[AgentMessage]]` — **NUEVO**: mensajería inter-agente tipeada (usado por `features_generator` L293-303 → `consistency_critic` L226-236, y `style_critic` L389 → `preference_feedback` L20)
  - `critique_log: list[CritiqueRecord]` — historial de críticas (usado por todos los generadores L81-82 y `critic_evaluator` L17, L120)
  - `tool_call_history: list[ToolCallRecord]` — trazabilidad de invocaciones (usado en TODOS los nodos)

- **Fortaleza:** `agent_mailbox` implementa comunicación dirigida entre agentes:
  ```python
  # features_generator → consistency_critic
  "agent_mailbox": {
      "consistency_critic": [
          AgentMessage(
              from_agent="features_generator",
              to_agent="consistency_critic",
              message_type="request_review",
              content="Verifica que las features no solapan",
              priority="high",
          )
      ],
  }
  ```

- **Debilidad:** `shared_scratchpad` sigue usando `dict[str, object]` sin tipado fuerte. Las claves son strings mágicas (`"context_analyzer_output"`, `"generated_ears"`, `"generated_document_md"`, `"current_feature_title"`, `"correction_original"`, etc.) sin contrato formal. Esto causa acoplamiento implícito entre nodos.

- **Debilidad:** El `Scratchpad` tipeado existe en `contracts/` pero ningún nodo lo usa aún — todos operan sobre `shared_scratchpad` genérico.

**Conclusión:** El estado compartido es real y rico, con 7 campos que evolucionan a través de los nodos. La adición de `agent_mailbox` con mensajería tipeada es una mejora significativa sobre la versión anterior. La falta de tipado en `shared_scratchpad` sigue siendo la principal debilidad.

#### C. Ejecución Paralela — **CUMPLE (13/15)**

**Verificación en código:** El paralelismo está implementado en **dos puntos** del grafo, no solo uno:

1. **CONTEXT:** 3 agentes en paralelo vía `Send()`:
   ```python
   # kosmo_graph.py L49-53
   return [
       Send("context_analyzer", {}),
       Send("goal_planner", {}),
       Send("preference_retriever", {}),
   ]
   ```

2. **CRITICS:** 3 críticos en paralelo desde cada generador:
   ```python
   # kosmo_graph.py L116-131
   builder.add_edge("discovery_generator", "quality_critic")
   builder.add_edge("discovery_generator", "style_critic")
   builder.add_edge("discovery_generator", "consistency_critic")
   builder.add_edge("quality_critic", "critic_merger")
   builder.add_edge("style_critic", "critic_merger")
   builder.add_edge("consistency_critic", "critic_merger")
   ```
   LangGraph ejecuta los 3 críticos concurrentemente porque todos dependen del mismo nodo origen y convergen en `critic_merger`.

- **Debilidad:** Los generadores son mutuamente excluyentes — solo uno se ejecuta por fase.
- **Debilidad:** No hay paralelismo cross-fase (ej. generar discovery + features simultáneamente).

**Conclusión:** El paralelismo es **significativamente mayor** de lo documentado anteriormente. Con 2 puntos de ejecución paralela (CONTEXT + CRITICS), KOSMO aprovecha mejor el motor de LangGraph. La mejora de 10/15 a 13/15 refleja el paralelismo en críticos que se había omitido en la versión anterior.

#### D. Ciclos de Retroalimentación — **CUMPLE (19/20)**

**Verificación en código:** Existen **cuatro niveles** de ciclos de feedback (no tres):

1. **Ciclo Generador → Críticos → Generador (inner loop):**
   ```python
   # critic_evaluator.py L119-124
   if state.critic_verdict == "needs_revision" and state.critic_iteration < state.max_critic_iterations:
       return state.current_subtask or "discovery_generator"  # reenvía al generador
   ```
   Feedback estructurado por agente crítico (`critic_evaluator._build_structured_feedback()`, L118-132). Máximo 3 iteraciones.

2. **Ciclo Evaluador Final → Supervisor → Generador (outer loop):**
   ```python
   # final_evaluator.py L166-181 y supervisor.py L106-116
   # Si needs_revision y generation_attempts < max_iterations:
   # → supervisor_stage = GENERATE → vuelve al generador
   ```

3. **Ciclo Humano → Generador (interrupt loop):**
   ```python
   # final_evaluator.py L109-121
   human_decision = interrupt({...})  # pausa el grafo, espera input
   # Opciones: accept_as_is, edit_and_retry, abort
   # edit_and_retry → inyecta feedback humano → vuelve al generador
   ```

4. **Ciclo Preferencias → Style Critic → Preference Feedback (reinforcement loop):**
   ```python
   # style_critic L389 → preference_feedback L20 → preference_repo.update_confidence()
   # Si style_critic APRUEBA: confianza +0.1 (refuerzo positivo)
   # Si style_critic RECHAZA: confianza -0.2 (castigo)
   # Además: preference_feedback.delete_expired(threshold=0.1) — poda automática
   ```

**Conclusión:** Cuatro niveles de ciclos de feedback anidados, incluyendo un ciclo de refuerzo automático de preferencias que no existía en la documentación anterior. El `preference_feedback` cierra parcialmente el loop de aprendizaje al ajustar confianza de reglas basado en el veredicto del `style_critic`.

#### E. Ruteo Condicional Dinámico — **CUMPLE (14/15)**

**Verificación en código:** Tres funciones de ruteo condicional, todas inspeccionadas:

1. `route_after_supervisor()` (L43-59): 6 rutas posibles — `Send` paralelo (CONTEXT) o string (GENERATE→generador específico, EVALUATE→final_evaluator, DONE→END)

2. `route_after_critic_evaluator()` (L119-124): 5 rutas — reenvía al generador activo (`current_subtask`) si `needs_revision`, o avanza a `final_evaluator` si `approved`

3. `route_after_evaluator()` (L62-65): 2 rutas — loop a `supervisor` si `needs_revision`, o `END` (que conecta a `preference_feedback`)

- **Fortaleza:** `_route_to_generator()` (L73-103) selecciona dinámicamente entre 4 generadores según `phase` + `generator_action` (ej. `CARACTERISTICAS` + `improve` → `draft_refiner` en vez de `features_generator`)
- **Fortaleza:** Manejo explícito de fases no implementadas (MODELO, IMPLEMENTACION) con `human_input_pending=True` (L84-92)

**Conclusión:** Ruteo condicional completo con 3 funciones de routing y selección dinámica de generador. Las aristas condicionales cubren todos los casos de negocio.

#### F. Memoria y Aprendizaje — **CUMPLE PARCIALMENTE (8/10)**

**Verificación en código:** El sistema de aprendizaje es más completo de lo documentado:

- **Fortaleza:** `preference_retriever` recupera preferencias y las inyecta en prompts de generadores + `style_critic` (L308 en style_critic)
- **Fortaleza:** `learn_from_correction` → `LearnFromCorrectionUseCase.execute()` pipeline completo:
  1. `delta_extractor` — diff unificado
  2. `rule_inferencer` — LLM infiere reglas desde el diff
  3. `conflict_resolver` — evita duplicados
  4. `preference_store` — persiste en PostgreSQL
- **Fortaleza:** `preference_feedback` — **NUEVO**: ciclo de refuerzo automático que ajusta `confidence` de preferencias (+0.1 por acierto, -0.2 por violación) y poda reglas con confianza < 0.1
- **Fortaleza:** `context_compressor` — comprime historial cuando excede umbral de tokens
- **Debilidad:** Las preferencias se inyectan en generadores y `style_critic`, pero no modifican el comportamiento de `quality_critic`, `consistency_critic`, ni `final_evaluator`
- **Debilidad:** `thread_id` de checkpointing varía por endpoint → no hay persistencia cross-invocación para el mismo proyecto
- **Debilidad:** `InMemoryToolRegistry` está definida y `features_generator` intenta invocar `search_features`, pero en `composition.py` no se registra ninguna herramienta → `deps.tool_registry` es siempre `None` en producción

**Conclusión:** El mecanismo de aprendizaje es sustancialmente más completo que en la versión anterior (pasa de 6/10 a 8/10). El ciclo `preference_feedback` cierra parcialmente el loop de aprendizaje. La principal debilidad es que `ToolRegistry` está cableada pero sin herramientas registradas.

### 11.5. Veredicto Final

| Criterio | Peso | Anterior | **Actual** | Ponderada |
|---|---|---|---|---|
| A. Especialización de Roles | 20% | 18/20 | **19/20** | 3.8 |
| B. Estado Compartido | 20% | 14/20 | **15/20** | 3.0 |
| C. Ejecución Paralela | 15% | 10/15 | **13/15** | 1.95 |
| D. Ciclos de Retroalimentación | 20% | 19/20 | **19/20** | 3.8 |
| E. Ruteo Condicional | 15% | 14/15 | **14/15** | 2.8 |
| F. Memoria y Aprendizaje | 10% | 6/10 | **8/10** | 1.6 |
| **TOTAL** | **100%** | **16.2** | **17.0** | **16.95 / 20** |

### 11.6. Clasificación Final

```
Puntuación 0-5   → Secuencia de Prompts Simple
Puntuación 5-10  → Pipeline de Agentes con Orquestación Básica
Puntuación 10-15 → Orquestación Multiagente Moderada
Puntuación 15-20 → Orquestación Multiagente Avanzada ← KOSMO: 17.0 (+0.8 vs análisis anterior)
```

**KOSMO implementa una Orquestación Multiagente Avanzada (Nivel 4 de 5), habiendo mejorado +0.8 puntos respecto al análisis anterior gracias a correcciones basadas en inspección real del código.**

### 11.7. Correcciones Respecto al Análisis Anterior

| Aspecto | Análisis anterior (erróneo) | Realidad (código) | Impacto |
|---|---|---|---|
| Críticos | Secuenciales (quality → style → consistency) | **Paralelos** (3 aristas desde generador → critic_merger) | +3 pts en C |
| Nº de agentes | 13 | **15** (añadidos `critic_merger` y `preference_feedback`) | +1 pt en A |
| Mensajería inter-agente | No documentada | **`agent_mailbox`** con `AgentMessage` tipeado (features_generator → consistency_critic, style_critic → preference_feedback) | +1 pt en B |
| Ciclo de refuerzo | No documentado | **`preference_feedback`** ajusta confianza ±0.1/0.2 y poda reglas <0.1 | +2 pts en F |
| Inyección de dependencias | Global mutable `_current_deps` | **`RunnableConfig`** con `configurable={"deps": ...}` | Mejora arquitectónica (no afecta puntuación) |
| Tool calling | "No integrado" | **Parcialmente integrado**: `features_generator` invoca `tool_registry` pero composition.py no registra herramientas | Sin cambio (sigue sin ser funcional) |

### 11.8. Justificación Detallada

**Lo que SÍ es multiagente (verificado en código):**
- 15 agentes con roles especializados, prompts del sistema únicos y no triviales (algunos de 200+ líneas)
- Estado compartido (`KOSMOState`) que evoluciona a través de 16 nodos con 7 campos de comunicación
- **Dos puntos de ejecución paralela real**: 3 agentes en CONTEXT + 3 críticos en EVALUATE
- **Cuatro niveles de ciclos de retroalimentación**: crítico (3 iter), evaluador final (10 iter), humano (ilimitado), y refuerzo de preferencias (automático)
- Ruteo condicional dinámico con 3 funciones de routing y selección de generador por fase + acción
- `agent_mailbox` con mensajería inter-agente tipeada (comunicación dirigida, no solo broadcast)
- Mecanismo de aprendizaje con 4 etapas (delta → reglas → conflictos → persistencia) + refuerzo automático
- Compresión de contexto adaptativa (`should_compress` en supervisor)
- Guardrails deterministas (`output_guardrails.py`, 449 líneas, 3 validadores completos)
- Human-in-the-loop real vía `langgraph.types.interrupt()` con 3 opciones
- Checkpointing en PostgreSQL (`AsyncPostgresSaver`)

**Lo que NO es multiagente (aún):**
- Los agentes no negocian entre sí — la comunicación es mediada por el estado, no hay diálogo directo multi-turno
- No hay delegación autónoma — el supervisor asigna tareas; los agentes no pueden delegar sub-tareas
- `ToolRegistry` está cableada en `GraphDependencies` pero sin herramientas registradas → `deps.tool_registry` es `None` en producción
- El aprendizaje no cierra el ciclo hacia los críticos (solo `style_critic` consulta preferencias; `quality_critic` y `consistency_critic` no)
- Dos fases del Wizard (Modelo e Implementación) no están implementadas — devuelven `human_input_pending`
- `shared_scratchpad` sin tipado fuerte — acoplamiento implícito entre nodos vía strings mágicas

### 11.9. Comparación con Arquitecturas de Referencia

| Característica | Simple Prompt Chain | LangChain LCEL | **KOSMO** | AutoGen | CrewAI |
|---|---|---|---|---|---|
| Agentes especializados | No | No | **Sí (15)** | Sí | Sí |
| Estado compartido | No | Parcial | **Sí (KOSMOState + mailbox)** | Sí | Sí |
| Ejecución paralela | No | No | **Sí (2 puntos: Send + fan-out)** | Sí | Sí |
| Ciclos feedback | No | No | **Sí (4 niveles)** | Sí | Sí |
| Ruteo condicional | No | No | **Sí (StateGraph, 3 routers)** | Sí | Limitado |
| Mensajería inter-agente | No | No | **Sí (AgentMailbox)** | Sí | No |
| Tool calling | No | Sí | **Parcial (cableado, sin tools)** | Sí | Sí |
| Aprendizaje | No | No | **Sí (4-stage pipeline + refuerzo)** | Limitado | No |
| Human-in-the-loop | No | No | **Sí (interrupt con 3 opciones)** | Sí | No |
| Checkpointing | No | No | **Sí (Postgres)** | No | No |

---

## Apéndice A: Resumen de Archivos Clave

| Archivo | Líneas | Capa | Rol |
|---|---|---|---|
| `contracts/sdd/state.py` | 93 | Contracts | `KOSMOState` — estado global del grafo con `agent_mailbox` |
| `contracts/orchestration/graph_deps.py` | 12 | Contracts | `GraphDependencies` — llm_client, preference_repo, tool_registry |
| `application/orchestration/kosmo_graph.py` | 159 | Application | Construcción del StateGraph con 16 nodos y 2 puntos de paralelismo |
| `application/orchestration/helpers.py` | 149 | Application | Inyección de deps vía `RunnableConfig`, verify_scope, extract_generated_content |
| `application/orchestration/nodes/supervisor.py` | 125 | Application | Máquina de estados CONTEXT→GENERATE→EVALUATE→DONE + compresión de contexto |
| `application/orchestration/nodes/context_analyzer.py` | 111 | Application | Analizador de contexto (ejecución paralela con LLM) |
| `application/orchestration/nodes/goal_planner.py` | 77 | Application | Planificador de objetivos (ejecución paralela con LLM) |
| `application/orchestration/nodes/preference_retriever.py` | 80 | Application | Recuperador de preferencias (ejecución paralela, determinista) |
| `application/orchestration/nodes/context_merger.py` | 33 | Application | Fusionador de outputs de contexto (determinista) |
| `application/orchestration/nodes/discovery_generator.py` | 260 | Application | Generador de documento de descubrimiento (9 secciones, guardrails, ReAct) |
| `application/orchestration/nodes/features_generator.py` | 305 | Application | Generador de características (Few-Shot, anti-trivialidad, agent_mailbox, intento de tool_registry) |
| `application/orchestration/nodes/ears_generator.py` | 489 | Application | Generador de requisitos EARS (6 categorías, auto-reparación de leaks, scoring) |
| `application/orchestration/nodes/draft_refiner.py` | 111 | Application | Refinador de borradores (modo mejora dual) |
| `application/orchestration/nodes/critics.py` | 437 | Application | 3 críticos en **paralelo** (quality, style, consistency) + agent_mailbox feedback |
| `application/orchestration/nodes/critic_merger.py` | 81 | Application | **NUEVO** — Deduplica hallazgos de 3 críticos paralelos, prioriza por severidad |
| `application/orchestration/nodes/critic_evaluator.py` | 133 | Application | Gate post-críticos (decisión booleana con feedback estructurado) |
| `application/orchestration/nodes/final_evaluator.py` | 197 | Application | Evaluador final + `interrupt()` humano con 3 opciones |
| `application/orchestration/nodes/preference_feedback.py` | 99 | Application | **NUEVO** — Ciclo de refuerzo de preferencias (+0.1/-0.2) + poda automática |
| `application/orchestration/nodes/learn_from_correction.py` | 97 | Application | Aprendizaje por corrección del usuario (4-stage pipeline) |
| `domain/sdd/output_guardrails.py` | 449 | Domain | Validación determinista post-LLM (3 validadores: discovery, features, EARS) |
| `domain/sdd/structured_schemas.py` | 103 | Domain | Schemas Pydantic para structured output (integrado en todos los generadores) |
| `domain/sdd/validators/ears_validator.py` | 495 | Domain | Scoring EARS en 6 dimensiones + detección de leaks de implementación |
| `domain/agents/learning/nodes.py` | 139 | Domain | delta_extractor, rule_inferencer, preference_store, conflict_resolver |
| `domain/agents/context_compressor.py` | 67 | Domain | Compresión de contexto (token threshold 8000) |
| `infrastructure/orchestration/langgraph_engine.py` | 86 | Infrastructure | Adaptador GraphEngine con Postgres checkpointing + ToolRegistry wiring |
| `infrastructure/api/composition.py` | 250 | Infrastructure | Wiring central de todos los componentes |

---

## Apéndice B: Glosario de Términos

| Término | Definición |
|---|---|
| **EARS** | Easy Approach to Requirements Syntax — taxonomía de requisitos con 6 patrones: Ubiquitous, Event-driven, State-driven, Optional, Unwanted, Complex |
| **StateGraph** | Grafo dirigido donde cada nodo recibe y retorna un estado compartido — núcleo de LangGraph |
| **Checkpointing** | Persistencia del estado después de cada super-step, permitiendo reanudación y auditoría |
| **Send()** | Mecanismo de LangGraph para ejecución paralela de nodos |
| **ReAct** | Ciclo Reasoning + Acting: Thought → Action → Observation → (repeat) |
| **interrupt()** | Pausa el grafo y espera input humano antes de continuar |
| **Guardrail** | Validación determinista post-LLM que intercepta la respuesta antes de inyectarla en el estado |
| **Few-Shot Prompting** | Técnica de prompt engineering que incluye ejemplos concretos en el prompt para guiar al LLM |
| **Scratchpad** | Memoria compartida entre agentes dentro de una ejecución del grafo |
| **RFC 7807** | Estándar para respuestas de error HTTP con `Content-Type: application/problem+json` |
| **PKCE** | Proof Key for Code Exchange — RFC 7636, flujo de autorización segura |
| **Hexagonal Architecture** | Arquitectura de Puertos y Adaptadores con dependencias unidireccionales contracts→domain→application→infrastructure |

---

## 12. Probar el Flujo Completo

### 12.1. Requisitos Previos

| Requisito | Versión | Verificación |
|---|---|---|
| Docker + Docker Compose | 24+ / v2+ | `docker compose version` |
| Python | 3.13 | `python --version` |
| uv (gestor de dependencias) | 0.7+ | `uv --version` |
| Git | 2.x | `git --version` |

**Servicios externos (vía Docker):**
- PostgreSQL 17 con pgvector
- Redis 7 Alpine
- MongoDB 7 (opcional, stub)

### 12.2. Configuración del Entorno

#### 12.2.1. Archivo `.env`

Copiar `.env.example` a `.env` y configurar las variables:

```bash
cd backend
cp .env.example .env
```

Variables críticas a revisar:

```ini
# LLM: noop (mock) para pruebas sin API key, deepseek/otros para generación real
LLM_PROVIDER=noop
LLM_MODEL=deepseek-chat
# LLM_API_KEY=sk-...        # solo si usas deepseek

# Base de datos
DATABASE_URL=postgresql+asyncpg://kosmo:kosmo@localhost:5432/kosmo_dev

# JWT — si no existen, se generan automáticamente con:
# openssl genpkey -algorithm RSA -out .secrets/jwt_private.pem -pkeyopt rsa_keygen_bits:2048
# openssl rsa -in .secrets/jwt_private.pem -pubout -out .secrets/jwt_public.pem
JWT_PRIVATE_KEY_PATH=./.secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=./.secrets/jwt_public.pem
```

#### 12.2.2. Generar Claves JWT (si no existen)

```bash
mkdir -p .secrets
openssl genpkey -algorithm RSA -out .secrets/jwt_private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -in .secrets/jwt_private.pem -pubout -out .secrets/jwt_public.pem
```

#### 12.2.3. Instalar Dependencias

```bash
uv sync --all-groups
```

### 12.3. Levantar la Infraestructura

#### Opción A: Docker Compose (recomendado)

```bash
# Desde la raíz del proyecto (C:\projects\KOSMO)
docker compose build backend
docker compose up -d postgres redis mongodb backend

# Verificar que todo está healthy
docker compose ps

# Ver logs del backend
docker compose logs backend -f
```

El `entrypoint.sh` del contenedor ejecuta `alembic upgrade head` automáticamente al iniciar. Si necesitas correr migraciones manualmente desde local:

```bash
uv run alembic upgrade head
```

#### Opción B: Solo DBs en Docker, backend en local

```bash
docker compose up -d postgres redis mongodb
uv run alembic upgrade head
uv run uvicorn kosmo.infrastructure.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 12.4. Seed de Usuario de Desarrollo

```bash
uv run python -m kosmo.infrastructure.scripts.seed_dev_user
```

Esto crea el usuario `dev@kosmo.dev` / `dev-password-12345`. Es idempotente — si ya existe, muestra `already-exists`.

### 12.5. Verificación Inicial

```bash
curl http://localhost:8000/health
# {"status": "ok"}

curl http://localhost:8000/api/v1/schemas
# Lista de DTOs disponibles
```

### 12.6. Flujo End-to-End Completo

El flujo completo de negocio sigue el Wizard de 5 pantallas. Aquí se documenta con `curl`, asumiendo `base=http://localhost:8000`.

#### Paso 1 — Auth (PKCE S256)

```bash
# 1.1 Registrar usuario (idempotente — 201 o 409)
curl -s -X POST "$base/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@kosmo.dev","password":"dev-password-12345"}'

# 1.2 PKCE: generar code_verifier y code_challenge
CODE_VERIFIER=$(python -c "import secrets,base64,hashlib; v=secrets.token_bytes(48); print(base64.urlsafe_b64encode(v).decode().rstrip('='))")
CODE_CHALLENGE=$(echo -n "$CODE_VERIFIER" | python -c "import sys,base64,hashlib; v=sys.stdin.read().encode(); print(base64.urlsafe_b64encode(hashlib.sha256(v).digest()).decode().rstrip('='))")

# 1.3 Autorizar (obtener authorization_code)
AUTH_RESP=$(curl -s -X POST "$base/api/v1/auth/authorize" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"dev@kosmo.dev\",\"password\":\"dev-password-12345\",\"code_challenge\":\"$CODE_CHALLENGE\",\"code_challenge_method\":\"S256\",\"scopes\":[\"agent:run\",\"profile:read\"]}")
AUTH_CODE=$(echo "$AUTH_RESP" | python -c "import sys,json; print(json.load(sys.stdin)['authorization_code'])")

# 1.4 Intercambiar por tokens JWT
TOKEN_RESP=$(curl -s -X POST "$base/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"grant_type\":\"authorization_code\",\"code\":\"$AUTH_CODE\",\"code_verifier\":\"$CODE_VERIFIER\"}")
ACCESS_TOKEN=$(echo "$TOKEN_RESP" | python -c "import sys,json; print(json.load(sys.stdin)['access']['token'])")
REFRESH_TOKEN=$(echo "$TOKEN_RESP" | python -c "import sys,json; print(json.load(sys.stdin)['refresh']['token'])")

echo "ACCESS_TOKEN: $ACCESS_TOKEN"
```

#### Paso 2 — Crear Proyecto

```bash
PROJECT_RESP=$(curl -s -X POST "$base/api/v1/projects" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"name":"Sistema de Gestión de Inventario","description":"Sistema para pequeñas empresas que permite gestionar inventario en tiempo real, controlar stock, generar reportes y recibir alertas de bajo inventario."}')
PROJECT_ID=$(echo "$PROJECT_RESP" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "PROJECT_ID: $PROJECT_ID"

# Ver estado del wizard
curl -s "$base/api/v1/projects/$PROJECT_ID/status" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool
```

#### Paso 3 — Discovery (Fase 1: Descubrimiento)

```bash
# Generar documento de descubrimiento con IA
curl -s -X POST "$base/api/v1/projects/$PROJECT_ID/discovery/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool

# Obtener el documento generado (con índice de navegación)
curl -s "$base/api/v1/projects/$PROJECT_ID/discovery" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool

# Editar manualmente (dispara el pipeline de aprendizaje si hay diff)
curl -s -X PUT "$base/api/v1/projects/$PROJECT_ID/discovery" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"document":{"type":"doc","content":[...]}}'
```

#### Paso 4 — Features (Fase 2: Características)

```bash
# Generar features iniciales con IA (persiste 5)
FEATURES_RESP=$(curl -s -X POST "$base/api/v1/projects/$PROJECT_ID/features/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN")
FEATURE_ID=$(echo "$FEATURES_RESP" | python -c "import sys,json; print(json.load(sys.stdin)['features'][0]['id'])")
echo "FEATURE_ID: $FEATURE_ID"

# Listar features del proyecto
curl -s "$base/api/v1/projects/$PROJECT_ID/features" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool

# Sugerir alternativas (IA, no persiste)
curl -s -X POST "$base/api/v1/projects/$PROJECT_ID/features/suggest" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool

# Aprobar feature (Borrador → Aprobada)
curl -s -X PATCH "$base/api/v1/projects/$PROJECT_ID/features/$FEATURE_ID/status" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"status":"aprobada"}' | python -m json.tool
```

#### Paso 5 — Requisitos EARS (Fase 3)

```bash
# Generar requisitos EARS con IA (feature debe estar Aprobada)
curl -s -X POST "$base/api/v1/projects/$PROJECT_ID/features/$FEATURE_ID/requirements/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool

# Obtener requisitos
curl -s "$base/api/v1/projects/$PROJECT_ID/features/$FEATURE_ID/requirements" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool

# Editar manualmente (dispara aprendizaje)
curl -s -X PUT "$base/api/v1/projects/$PROJECT_ID/features/$FEATURE_ID/requirements" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"document":{"type":"doc","content":[...]}}'

# Regenerar con IA
curl -s -X POST "$base/api/v1/projects/$PROJECT_ID/features/$FEATURE_ID/requirements/regenerate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool
```

#### Paso 6 — Preferencias de Usuario (Aprendizaje)

```bash
USER_ID=$(echo "$TOKEN_RESP" | python -c "import sys,json; print(json.load(sys.stdin)['subject'])")

# Listar preferencias aprendidas
curl -s "$base/api/v1/users/$USER_ID/preferences?project_id=$PROJECT_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool

# Ajustar confianza de una preferencia
curl -s -X PATCH "$base/api/v1/users/$USER_ID/preferences/$PREF_ID/confidence" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"delta":0.2}'

# Eliminar preferencia
curl -s -X DELETE "$base/api/v1/users/$USER_ID/preferences/$PREF_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

#### Paso 7 — Refresh y Logout

```bash
# Refresh de tokens (rotación)
REFRESH_RESP=$(curl -s -X POST "$base/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"grant_type\":\"refresh_token\",\"refresh_token\":\"$REFRESH_TOKEN\"}")
ACCESS_TOKEN=$(echo "$REFRESH_RESP" | python -c "import sys,json; print(json.load(sys.stdin)['access']['token'])")

# Verificar token actual
curl -s "$base/api/v1/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool

# Logout (revoca access + refresh)
curl -s -X POST "$base/api/v1/auth/logout" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}"
```

### 12.7. Colección Postman

Para pruebas interactivas, importar la colección `postman/KOSMO_API_v3_Complete.postman_collection.json` en Postman. La colección incluye:

- **30 endpoints** organizados en 8 carpetas, sin duplicados
- Variables de colección con auto-propagation (`access_token`, `project_id`, `feature_id`, etc.)
- Pre-request scripts para PKCE S256 (generación de `code_verifier` y `code_challenge`)
- Tests automáticos de validación de status codes y extracción de variables

**Orden de ejecución:** Health → Auth → Proyectos → Discovery → Features → Requisitos → Preferencias → Utilidades.

### 12.8. Troubleshooting

| Problema | Causa probable | Solución |
|---|---|---|
| `docker compose up backend` falla con `PermissionError: 'data'` | El directorio `data/blobs` no está montado | Asegurar volumen en docker-compose.yml: `- ./backend/data/blobs:/app/data/blobs` |
| 401 en cualquier endpoint | Token expirado o no enviado | Ejecutar paso 1.4 (Token) o paso 7 (Refresh) |
| 409 en generate de requisitos | Feature no está Aprobada | Ejecutar paso 4 (Aprobar feature) |
| 404 en cualquier endpoint | ID incorrecto | Verificar que `PROJECT_ID` y `FEATURE_ID` se capturaron correctamente |
| LLM no genera contenido | `LLM_PROVIDER=noop` | Noop es mock para desarrollo. Cambiar a `deepseek` con API key |
| `alembic` no encuentra la BD | DATABASE_URL incorrecto o DB no accesible | Verificar `docker compose ps` y que postgres está healthy |
| Logfire errores en logs | `LOGFIRE_TOKEN` vacío | Normal en local dev — Logfire se degrada gracefulmente |
