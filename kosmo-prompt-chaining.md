# KOSMO Backend — Análisis Arquitectónico Completo

## 1. ¿Qué es KOSMO?

KOSMO es una plataforma de **Spec-Driven Development (SDD)** asistida por IA. El backend toma una idea de proyecto en lenguaje natural y la transforma progresivamente, usando LLMs, en:

1. **Documento de Descubrimiento** (visión, actores, casos de uso, capacidades, reglas de negocio, QAs)
2. **Características (Features)** descompuestas del descubrimiento
3. **Requisitos EARS** (Easy Approach to Requirements Syntax) por feature
4. **Modelo de Dominio UML** (clases, relaciones, boundaries DDD)
5. **Tareas (Tasks)** descompuestas del modelo de dominio, con DAG de dependencias

Todo esto se persiste en PostgreSQL, se expone via REST + WebSocket, y se visualiza en un frontend Next.js con canvas de modelado visual (@xyflow/react).

---

## 2. Inventario Completo: ¿Qué Nomás Hay en el Backend?

### 2.1 Estructura de Directorios

```
backend/
├── pyproject.toml                 # Python 3.13 + dependencias (FastAPI, LangGraph, LiteLLM, pydantic-ai, SQLAlchemy...)
├── Dockerfile                     # Multi-stage (uv builder → python runtime)
├── entrypoint.sh                  # Alembic migrations + Uvicorn
├── alembic.ini                    # Configuración de migraciones
├── alembic/
│   ├── env.py                     # Entorno de migraciones
│   └── versions/
│       └── 0001_init.py           # Migración inicial (9+ tablas)
├── .importlinter                  # Enforcement de arquitectura hexagonal
├── data/blobs/                    # Almacenamiento de archivos (blobs en filesystem)
├── src/kosmo/                     # Paquete principal (hexagonal)
│   ├── config.py                  # Pydantic Settings (.env → configuración tipada)
│   ├── contracts/                 # Capa 1: Entidades + Puertos (interfaces)
│   ├── domain/                    # Capa 2: Algoritmos puros + Agentes IA
│   ├── application/               # Capa 3: Casos de uso (orquestación)
│   └── infrastructure/            # Capa 4: Adaptadores (FastAPI, SQLAlchemy, Redis, LLMs, seguridad)
└── tests/                         # unit, integration, contract, e2e, property-based
```

### 2.2 Dependencias Clave (pyproject.toml)

| Dependencia | Rol |
|---|---|
| `fastapi` + `uvicorn` | Servidor HTTP REST |
| `langgraph` + `langgraph-checkpoint-postgres` | Pipeline SDD con persistencia de estado |
| `litellm` | Cliente multi-proveedor LLM (Anthropic, OpenAI, Gemini) |
| `pydantic-ai` | Agentes IA con structured output (dependencia declarada, uso emergente) |
| `sqlalchemy[asyncio]` + `asyncpg` | ORM asíncrono para PostgreSQL |
| `redis[hiredis]` | Token store, rate limiting, PKCE codes, login attempts |
| `motor` | Cliente async MongoDB (stub para memoria de agentes) |
| `python-jose[cryptography]` | JWT RS256 |
| `argon2-cffi` | Password hashing Argon2id (OWASP 2025) |
| `cryptography` (Fernet) | Cifrado de secretos y API keys |
| `jinja2` | Templates de prompts para LLMs |
| `structlog` | Logging estructurado |
| `pgvector` | Búsqueda vectorial en PostgreSQL (infraestructura lista, código stub) |
| `ulid` | Identificadores únicos con prefijo tipado |

### 2.3 Bases de Datos

| Base | Motor | Propósito | Estado |
|---|---|---|---|
| **PostgreSQL** | `pgvector/pgvector:pg17` | Almacén primario (proyectos, specs, features, requisitos, tareas, usuarios, auditoría, pipeline events, API keys cifradas, artifactos) | **Activo** |
| **Redis** | `redis:7-alpine` | Revocación de tokens JWT, authorization codes PKCE, rate limiting, login attempts | **Activo** |
| **MongoDB** | `mongo:7` | Memoria de agentes IA (document store) | **Stub** (configurado en docker-compose pero sin código real) |

---

## 3. Arquitectura: Hexagonal (Ports & Adapters)

### 3.1 Las 4 Capas

El backend sigue **estrictamente** arquitectura hexagonal con 4 capas, forzada por `.importlinter`:

```
┌─────────────────────────────────────────────────────────┐
│  infrastructure/    ← FastAPI, SQLAlchemy, Redis, LLMs  │  Capa 4 (exterior)
│  application/       ← Casos de uso (orquestación)       │  Capa 3
│  domain/            ← Algoritmos puros + Agentes IA     │  Capa 2
│  contracts/         ← Entidades + Puertos (interfaces)  │  Capa 1 (kernel)
└─────────────────────────────────────────────────────────┘

Dependencias: contracts ← domain ← application ← infrastructure
(NUNCA al revés)
```

### 3.2 Qué Hay en Cada Capa

#### `contracts/` — El Kernel (Entidades + Puertos)

Define **QUÉ** existe y **QUÉ** se puede hacer, sin **CÓMO**:

| Subdirectorio | Contenido |
|---|---|
| `contracts/sdd/` | Entidades de dominio SDD: `SpecDocument`, `DiscoveryDocument`, `Feature`, `EARSRequirement`, `DomainModel`, `Task`, `Constitution`, `Project`, `SDDState`, `SpecPhase` (enum con 6 fases), `PipelineEvent` |
| `contracts/sdd/repositories.py` | Puertos (Protocol): `SpecRepository`, `FeatureRepository`, `ProjectRepository` — interfaces abstractas para persistencia |
| `contracts/sdd/errors.py` | Errores tipados: `FeatureNotApprovedError`, `FeatureNotFoundError`, `DocumentValidationError`, `SpecNotFoundError`, `ProjectNotFoundError`, `MarkdownParseError` |
| `contracts/sdd/ids.py` | NewTypes: `SpecId`, `ProjectId`, `FeatureId`, `RequirementId`, `TaskId`, `UserId`, `BoundaryName` |
| `contracts/sdd/events.py` | Eventos del pipeline: `NodeStarted`, `NodeCompleted`, `ArtifactProduced` |
| `contracts/auth/` | Entidades auth: `User`, `Principal`, `TokenPair`, `PKCEParams`, `EncryptedSecret`. Puertos: `UserRepository`, `PasswordHasher`, `LoginAttemptStore`, `SecretCipher` |
| `contracts/llm/ports.py` | Puerto `LLMClient` (Protocol con `complete()` y `stream()`), `PromptTemplate`, `LLMResponse`, `LLMUsage` |
| `contracts/storage/` | Puerto `BlobStorage` para archivos binarios |
| `contracts/audit/` | Puerto `AuditEventSink` para eventos de auditoría |
| `contracts/telemetry.py` | Decorador `@traced` para observabilidad de casos de uso |

#### `domain/` — Algoritmos Puros + Servicios de Agentes IA

Define **CÓMO** se transforman los datos, sin I/O externo (solo reciben `LLMClient` por inyección):

| Subdirectorio | Responsabilidad |
|---|---|
| `domain/agents/spec_capture/` | `capture()` — Captura inicial SDD: recibe `RawIdea`, llama LLM con template `discovery.j2`, produce `DiscoveryDocument` |
| `domain/agents/discovery_writer/` | `generate_discovery()` — Genera/regenera documento de descubrimiento desde descripción del proyecto |
| `domain/agents/analyzer/` | `generate_requirements()` — Genera requisitos EARS desde el `DiscoveryDocument`. **Con reintento**: máximo 3 intentos si `ears_validator` encuentra errores |
| `domain/agents/architect/` | `generate_design()` — Genera `DomainModel` (UML classes + relationships + DDD boundaries) desde requisitos. Serializa a PlantUML y XMI |
| `domain/agents/planner/` | `decompose_tasks()` — Descompone el `DomainModel` en `Task[]` con DAG de dependencias. Valida con `task_dag_validator` |
| `domain/agents/feature_generator/` | `generate_features_from_discovery()` (5 features), `improve_feature_description()`, `suggest_feature_from_idea()`, `suggest_alternative_features()` (3 sugerencias, no persiste) |
| `domain/agents/requirements_generator/` | `generate_feature_requirements()` — Requisitos EARS por feature (taxonomía: ubiquitous, event, state, optional, unwanted, complex). Con reintento hasta 3x |
| `domain/agents/canvas_sync/` | `apply_canvas_edit()` — Sincroniza ediciones del canvas visual con el `DomainModel` |
| `domain/sdd/validators/` | Validadores puros: `ears_validator.py` (corrección estructural EARS), `task_dag_validator.py` (consistencia del DAG), `domain_model_validator.py`, `xmi_validator.py` |
| `domain/sdd/serializers/` | `plantuml_serializer.py` (DomainModel → PlantUML), `xmi_serializer.py` (DomainModel → XMI) |
| `domain/sdd/document_converters.py` | Conversión Markdown ↔ RichTextDocument (árbol ProseMirror/TipTap), `slugify_spanish()` |
| `domain/sdd/id_generator.py` | `IdGenerator.generate("entity")` → ULID con prefijo (`prj_`, `feat_`, `spec_`, `tsk_`, `usr_`, `apk_`, `aud_`) |
| `domain/sdd/llm_helpers.py` | `extract_json()` — Extrae JSON de respuestas LLM (soporta code fences y raw JSON) |
| `domain/sdd/few_shot/` | Ejemplos few-shot: `customer_support_rag_backend_en/` y `photo_albums_en/` (research, requirements, design, tasks, spec.json completos) |
| `domain/sdd/templates/` | Templates Markdown skeleton por fase + steering (product.md, tech.md, structure.md) |
| `domain/auth/pkce.py` | PKCE: `generate_code_verifier()`, `compute_code_challenge()` (SHA-256) |
| `domain/features/status_transitions.py` | Máquina de estados: `BORRADOR ↔ APROBADA` |

#### `application/` — Casos de Uso (Orquestación)

Cada caso de uso es una **clase con `execute()`** que recibe puertos por constructor (Dependency Inversion):

| Subdirectorio | Casos de Uso |
|---|---|
| `application/sdd/capture.py` | `CaptureDiscoveryUseCase` — Orquesta spec_capture agent + persistencia |
| `application/sdd/requirements.py` | `GenerateRequirementsUseCase` — Orquesta analyzer agent + valida fase previa |
| `application/sdd/design.py` | `GenerateDesignUseCase` — Orquesta architect agent |
| `application/sdd/tasks.py` | `DecomposeTasksUseCase` — Orquesta planner agent |
| `application/sdd/canvas.py` | `SyncCanvasEditUseCase` — Sincronización canvas ↔ domain model |
| `application/sdd/context_assembler.py` | `ContextAssembler` — Construye `PromptTemplate` con contexto (actualmente subutilizado, los agentes construyen sus propios prompts) |
| `application/features/` | `CreateFeature`, `GenerateFeatures`, `ImproveFeature`, `SuggestAlternatives`, `SuggestFromIdea`, `ToggleFeatureStatus`, `GenerateRequirements`, `RegenerateRequirements`, `SaveRequirementsDocument`, etc. |
| `application/auth/` | `RegisterUser`, `AuthorizeWithPkce`, `ExchangeAuthorizationCode`, `IssueTokenPair`, `VerifyAccessToken`, `RefreshTokenPair`, `RevokeSession` |
| `application/projects/` | `CreateProject`, `GetProject`, `ListProjects` |
| `application/orchestration/sdd_graph.py` | **LangGraph StateGraph** — Pipeline de 4 nodos secuenciales. Ver sección 5. |

#### `infrastructure/` — Adaptadores (Implementaciones Concretas)

| Subdirectorio | Adaptadores |
|---|---|
| `infrastructure/api/main.py` | **FastAPI app** — lifespan, CORS, middleware, routers, OpenAPI, exception handlers |
| `infrastructure/api/composition.py` | **Composition Root** — `build_auth_components()` + `build_sdd_components()`: cablea TODO |
| `infrastructure/api/routers/` | Routers REST: `auth`, `projects`, `discovery`, `features`, `requirements`, `specs`, `schemas` |
| `infrastructure/api/websocket/specs.py` | WebSocket para broadcast de eventos de spec en tiempo real |
| `infrastructure/api/middlewares/logging.py` | `RequestLoggingMiddleware` — structured logging + trace IDs |
| `infrastructure/api/dependencies/` | `get_principal()` (JWT auth), `IpRateLimiter` (rate limiting) |
| `infrastructure/api/errors.py` | Exception handlers: `SpecError` → RFC 7807, `Exception` → 500 |
| `infrastructure/api/schemas*.py` | DTOs de API (AuthorizeRequest, RegisterRequest, TokenPairResponse, etc.) |
| `infrastructure/persistence/postgres/` | **Implementaciones reales**: `SqlAlchemySpecRepository`, `SqlAlchemyFeatureRepository`, `SqlAlchemyProjectRepository`, `SqlAlchemyUserRepository`, `SqlAlchemyAuditEventSink` + modelos ORM |
| `infrastructure/persistence/redis/` | `RedisAuthorizationCodeStore`, `RedisTokenRevocationStore`, `RedisLoginAttemptStore` |
| `infrastructure/llm/` | `LiteLLMClient` (Anthropic/OpenAI/Gemini via litellm), `DeepSeekClient` (HTTP directo), `NoopLLMClient` (mock/testing) |
| `infrastructure/security/` | `Argon2idPasswordHasher`, `JoseJwtIssuer`/`JoseJwtVerifier` (RS256), `FernetSecretCipher`, `FernetApiKeyVault` |
| `infrastructure/storage/filesystem_blob_storage.py` | Blob storage en filesystem local |
| `infrastructure/telemetry/bootstrap.py` | OpenTelemetry + Logfire |

---

## 4. Cómo se Conecta Todo: Composition Root

Toda la inyección de dependencias ocurre en **UN solo punto**: `infrastructure/api/composition.py` durante el `lifespan` de FastAPI (`main.py:230-264`).

### Flujo de Wiring

```
main.py (lifespan)
  │
  ├─ build_auth_components(settings)
  │   ├─ Crea Redis (token store, PKCE codes, login attempts)
  │   ├─ Crea PostgreSQL engine + session factory
  │   ├─ Crea JoseJwtIssuer + JoseJwtVerifier (RS256)
  │   ├─ Crea Argon2idPasswordHasher
  │   ├─ Crea FernetSecretCipher
  │   ├─ Instancia SqlAlchemyUserRepository, SqlAlchemyAuditEventSink
  │   └─ Instancia TODOS los casos de uso auth:
  │       RegisterUser, AuthorizeWithPkce, ExchangeAuthorizationCode,
  │       IssueTokenPair, VerifyAccessToken, RefreshTokenPair, RevokeSession
  │
  ├─ build_sdd_components(settings, session_factory)
  │   ├─ Crea SqlAlchemySpecRepository, SqlAlchemyProjectRepository, SqlAlchemyFeatureRepository
  │   ├─ Selecciona LLMClient según LLM_PROVIDER:
  │   │   ├─ "deepseek"  → DeepSeekClient (HTTP a api.deepseek.com)
  │   │   ├─ "noop"      → NoopLLMClient (respuestas mock)
  │   │   └─ (default)   → LiteLLMClient (Anthropic Claude, OpenAI, Gemini)
  │   ├─ Crea FileSystemBlobStorage
  │   └─ Crea FernetApiKeyVault
  │
  └─ Guarda todo en app.state (FastAPI state):
      app.state.spec_repo, app.state.project_repo, app.state.feature_repo,
      app.state.llm_client, app.state.verify_access_token, etc.
```

Los routers acceden a las dependencias via `request.app.state.*` y **crean los casos de uso en cada request** (no son singletons pre-cableados para los casos de uso SDD — ver sección 9.2):

```python
# Patrón en routers/specs.py (y otros routers SDD):
uc = CaptureDiscoveryUseCase(
    spec_repo=request.app.state.spec_repo,
    project_repo=request.app.state.project_repo,
    llm_client=request.app.state.llm_client,
)
spec = await uc.execute(...)
```

---

## 5. Flujos del Backend: ¿Qué Nomás Hace?

Existen **DOS flujos principales** que coexisten:

### 5.1 Flujo SDD Clásico (Pipeline Secuencial con LangGraph)

Es la ruta "completa" de principio a fin. Sigue las 6 fases de `SpecPhase`:

```
DESCUBRIMIENTO → CARACTERISTICAS → REQUISITOS → MODELO → PROTOTIPO → IMPLEMENTACION
```

#### Endpoints REST (paso a paso):

```
POST /api/v1/projects/{id}/specs                  # Fase 1: Captura inicial
  └─ POST {raw_idea: {text, optional_context}}
     └─ CaptureDiscoveryUseCase
        └─ spec_capture agent → DiscoveryDocument
        └─ Persiste SpecDocument (phase=descubrimiento)
        └─ Persiste discovery_document en proyecto (árbol ProseMirror)

POST /specs/{spec_id}/advance/requirements         # Fase 2: Requisitos
  └─ GenerateRequirementsUseCase
     └─ analyzer agent → EARSRequirement[]
     └─ Valida cada requisito con ears_validator (reintento 3x)
     └─ Actualiza SpecDocument (phase=requisitos)

POST /specs/{spec_id}/advance/design               # Fase 3: Modelo de Dominio
  └─ GenerateDesignUseCase
     └─ architect agent → DomainModel (UML + PlantUML + XMI)
     └─ Actualiza SpecDocument (phase=modelo)

POST /specs/{spec_id}/advance/tasks                # Fase 4: Tareas
  └─ DecomposeTasksUseCase
     └─ planner agent → Task[] con DAG de dependencias
     └─ Valida DAG con task_dag_validator
     └─ Actualiza SpecDocument (phase=prototipo)
```

#### Pipeline Interno con LangGraph

`application/orchestration/sdd_graph.py` define un `StateGraph` con **4 nodos secuenciales**:

```
┌──────────────┐     ┌──────────┐     ┌───────────┐     ┌─────────┐
│ spec_capture │ ──► │ analyzer │ ──► │ architect │ ──► │ planner │ ──► END
└──────────────┘     └──────────┘     └───────────┘     └─────────┘
```

El estado compartido es `SDDState` (Pydantic model):

```python
class SDDState(BaseModel):
    spec_id: str | None
    raw_idea: RawIdea | None
    discovery: DiscoveryDocument | None
    roadmap: ProjectRoadmap | None
    features: list[Feature] = []
    requirements: list[EARSRequirement] = []
    design: DomainModel | None
    tasks: list[Task] = []
    phase: SpecPhase
    errors: list[str] = []
    event_cursor: int = 0
```

**Nota importante**: Los nodos en `sdd_graph.py` están actualmente como **stubs** (solo cambian la fase, no ejecutan lógica real). La implementación real del pipeline se expone via REST endpoints individuales. LangGraph + `langgraph-checkpoint-postgres` está preparado para orquestación con persistencia pero no está completamente integrado con los casos de uso actuales.

### 5.2 Flujo Feature-Céntrico (Más Flexible, Paso a Paso)

Camino alternativo que trabaja a nivel de features individuales:

```
POST /api/v1/projects                                  # Crear proyecto

POST /api/v1/projects/{id}/discovery/generate          # IA genera discovery
  └─ discovery_writer agent → DiscoveryDocument (9 secciones Markdown)

GET  /api/v1/projects/{id}/discovery                   # Leer/editar discovery

POST /api/v1/projects/{id}/features/generate           # IA genera 5 features
  └─ feature_generator agent → Feature[] (status=BORRADOR)

GET  /api/v1/projects/{id}/features                    # Listar features

POST /api/v1/projects/{id}/features/suggest            # IA sugiere 3 alternativas
  └─ No persiste (solo preview)

POST /api/v1/projects/{id}/features/suggest-from-idea  # IA formaliza una idea suelta

PATCH /api/v1/features/{id}/status                     # Aprobar feature
  └─ BORRADOR → APROBADA (máquina de estados)

POST /api/v1/features/{id}/requirements/generate       # IA genera requisitos EARS
  └─ requirements_generator agent → RequirementsDocument
     └─ Taxonomía: ubiquitous, event, state, optional, unwanted, complex
     └─ Reintento 3x por requisito si ears_validator falla

PUT  /api/v1/features/{id}/requirements                # Guardar ediciones manuales

POST /api/v1/features/{id}/requirements/regenerate     # IA regenera requisitos
```

### 5.3 Flujo de Canvas Visual

```
POST /specs/{spec_id}/canvas                           # Sincronizar canvas
  └─ SyncCanvasEditUseCase
     └─ canvas_sync agent → ChangeDelta
     └─ Aplica ediciones del canvas visual al DomainModel
```

### 5.4 Flujo de Autenticación (PKCE + OAuth 2.0)

```
POST /api/v1/auth/register                             # Registro de usuario
  └─ Argon2id hashing de password
  └─ Persiste en PostgreSQL

POST /api/v1/auth/authorize                            # Inicio de sesión (PKCE)
  └─ Verifica email + password (Argon2id)
  └─ Rate limiting: 10 fallos en 15 min → lockout
  └─ Genera authorization code (Redis, TTL corto)

POST /api/v1/auth/token                                # Intercambia code → JWT pair
  └─ ExchangeAuthorizationCode
     └─ Verifica PKCE code_verifier (SHA-256 challenge)
     └─ Emite Access Token (RS256, TTL configurable) + Refresh Token
     └─ Registra JTI en Redis para posible revocación

POST /api/v1/auth/refresh                              # Refrescar token
  └─ RefreshTokenPair
     └─ Rota tokens: nuevo par, viejo revocado inmediatamente

POST /api/v1/auth/logout                               # Cerrar sesión
  └─ Revoca el JTI actual en Redis

GET  /api/v1/auth/me                                   # Perfil del usuario autenticado
```

---

## 6. ¿Agentes o Encadenamiento de Prompts?

### Respuesta: **Encadenamiento de Prompts, No Agentes Autónomos**

KOSMO **NO utiliza agentes autónomos** (no hay agent loops, no hay tool-calling autónomo, no hay memoria de agente real). Lo que existe es un **encadenamiento determinista de prompts** donde cada "agente" es en realidad:

1. Un **servicio de dominio** (`domain/agents/*/service.py`) que:
   - Carga un template Jinja2 (`prompts/*.j2`)
   - Lo renderiza con datos del dominio (discovery, constitution, requirements, etc.)
   - Construye un `PromptTemplate` (system_prompt + user_prompt)
   - Llama a `llm_client.complete()` (temperature 0-0.7)
   - Extrae y parsea JSON de la respuesta
   - Valida con validadores puros (ears_validator, task_dag_validator)
   - **Reintenta hasta 3 veces** si la validación falla
   - Retorna objetos de dominio tipados

2. Un **caso de uso** (`application/`) que:
   - Recibe los puertos por constructor
   - Llama al servicio de dominio
   - Persiste el resultado via repositorios
   - Actualiza el estado (fase, etc.)

### Arquitectura de Llamadas de un "Agente"

```
Router (infrastructure/api/routers/specs.py)
  │
  ├─ Crea caso de uso con dependencias de app.state
  │
  ▼
Caso de Uso (application/sdd/requirements.py)
  │
  ├─ Verifica precondiciones (fase previa completada)
  ├─ Obtiene datos del repositorio
  │
  ▼
Agente Service (domain/agents/analyzer/service.py)
  │
  ├─ Carga template Jinja2 (prompts/requirements.j2)
  ├─ Renderiza con datos del dominio
  ├─ Construye PromptTemplate
  ├─ Llama a LLMClient.complete(prompt, temperature=0)
  ├─ Extrae JSON (extract_json)
  ├─ Parsea a Pydantic (EARSRequirement.model_validate)
  ├─ Valida cada requisito (ears_validator)
  │   └─ Si error: reintenta hasta 3x con prompt de corrección
  ├─ Si aún hay errores tras 3 intentos: lanza Exception
  └─ Retorna list[EARSRequirement] validado
  │
  ▼
Caso de Uso
  │
  ├─ Asigna resultado a spec.requirements
  ├─ Actualiza spec.phase
  └─ Persiste via spec_repo.update(spec)
```

### Los "Agentes" NO Tienen:

- **Memoria persistente** — MongoDB está configurado pero no hay código que lo use
- **Tool calling / function calling** — el LLM solo devuelve JSON estructurado
- **Bucles autónomos de decisión** — el flujo es determinista: siempre spec_capture → analyzer → architect → planner
- **Planificación autónoma** — las tareas son generadas por el planner agent, pero la ejecución de esas tareas no está automatizada
- **Aprendizaje** — `domain/agents/learning/` es un stub vacío

### ¿Por Qué No Son Agentes?

Un agente de IA típicamente tiene:
1. Un goal/objetivo
2. Capacidad de planificar pasos
3. Herramientas (tools) que puede invocar
4. Un bucle de observación → pensamiento → acción
5. Memoria de corto y largo plazo

Los "agentes" de KOSMO son **funciones puras de transformación de datos via LLM**. Cada uno hace UNA cosa (generar requisitos, generar diseño, etc.) y retorna. No hay bucle agéntico. Es **prompt chaining determinista**.

Los stubs `learning/`, `memory_agent/`, y `mcp/` sugieren que hubo (o hay) intención de evolucionar hacia agentes reales, pero actualmente no están implementados.

---

## 7. Análisis de Cohesión y Acoplamiento

### 7.1 Cohesión — ALTA

| Aspecto | Evaluación |
|---|---|
| **Cohesión por capa** | **Muy alta**. Cada capa tiene una responsabilidad única y clara: contracts define QUÉ, domain define CÓMO (algoritmos), application ORQUESTA, infrastructure IMPLEMENTA. |
| **Cohesión por módulo** | **Alta**. Los agentes están aislados: `analyzer/` solo genera requisitos, `architect/` solo genera diseño, `planner/` solo genera tareas. Cada uno tiene su template, schema y service. |
| **Cohesión funcional** | **Alta**. Cada caso de uso (`GenerateRequirementsUseCase`, `GenerateDesignUseCase`, etc.) tiene UN solo propósito. |
| **Cohesión de datos** | **Alta**. `SpecDocument` agrupa todo el estado de una especificación SDD. `RequirementsDocument` agrupa requisitos por taxonomía EARS. |

**Puntos de mejora**:
- `context_assembler.py` está subutilizado: los agentes construyen sus propios prompts en vez de delegar en el assembler, duplicando lógica de construcción de prompts.
- Los routers SDD instancian casos de uso manualmente en cada endpoint (no usan FastAPI dependency injection), lo que dispersa la creación de dependencias.

### 7.2 Acoplamiento — BAJO (pero con matices)

| Aspecto | Evaluación |
|---|---|
| **Acoplamiento entre capas** | **Muy bajo**. Forzado por `.importlinter`: infrastructure depende de application, application depende de domain, domain depende de contracts. NUNCA al revés. |
| **Acoplamiento a infraestructura** | **Bajo**. Los casos de uso dependen de abstracciones (Protocols en contracts/), no de implementaciones concretas. Ej: `GenerateRequirementsUseCase` recibe `SpecRepository` (Protocol), no `SqlAlchemySpecRepository`. |
| **Acoplamiento temporal** | **Bajo-moderalo**. El pipeline SDD es secuencial por diseño (no puedes generar diseño sin requisitos), pero esto es una restricción de dominio, no un acoplamiento accidental. |
| **Acoplamiento a proveedores LLM** | **Bajo**. Strategy Pattern: `LLMClient` es un Protocol con 3 implementaciones intercambiables (DeepSeek, LiteLLM, Noop). Cambiar de proveedor es cambiar una variable de entorno. |
| **Acoplamiento de datos** | **Moderado**. `SDDState` y `SpecDocument` comparten estructura similar pero son entidades separadas (duplicación de campos). |

**Puntos de mejora**:
- `_resolve_project_identifier()` está duplicada en varios lugares (specs.py, features.py).
- No hay un mecanismo centralizado de eventos cross-module (aunque existe `contracts/sdd/events.py` con tipos de eventos y `broadcast_event` vía WebSocket, no están integrados con los casos de uso de forma transversal).
- MongoDB, pgvector, outbox, sandbox, mcp y git están como stubs — infraestructura declarada pero sin código.

---

## 8. Cómo Logra el Flujo SDD

### 8.1 Mecanismo de Avance de Fases

El avance está **protegido por precondiciones explícitas** en cada caso de uso:

```python
# En GenerateRequirementsUseCase:
if spec.discovery is None:
    raise Exception("La especificación no tiene un Descubrimiento generado")

# En GenerateDesignUseCase:
if not spec.requirements:
    raise Exception("La especificación no tiene requisitos generados")

# En DecomposeTasksUseCase:
if spec.design is None:
    raise Exception("La especificación no tiene diseño generado")
```

Cada fase actualiza `spec.phase` al completarse:

```
DESCUBRIMIENTO (inicial) → REQUISITOS → MODELO → PROTOTIPO
```

Las fases `CARACTERISTICAS` e `IMPLEMENTACION` están definidas en el enum pero no tienen endpoints de avance automático implementados todavía.

### 8.2 Persistencia del Pipeline

- **LangGraph checkpoint**: Configurado con `langgraph-checkpoint-postgres` para persistir el estado del grafo en PostgreSQL (preparado para ejecución asíncrona con reintentos).
- **Pipeline Events**: La tabla `pipeline_events` (modelo ORM) almacena eventos `NodeStarted`, `NodeCompleted`, `ArtifactProduced` por spec. La infraestructura de eventos existe pero no está completamente integrada con los casos de uso actuales.
- **WebSocket**: `broadcast_event` emite eventos en tiempo real a clientes conectados para feedback del progreso del pipeline.

### 8.3 Diagrama de Secuencia del Flujo Completo

```
Cliente (Frontend)          FastAPI Router         Caso de Uso           Agente Service        LLM Client
      │                         │                      │                      │                    │
      │ POST /specs/{id}/       │                      │                      │                    │
      │   advance/requirements  │                      │                      │                    │
      │────────────────────────►│                      │                      │                    │
      │                         │ new GenerateRequirementsUseCase(...)         │                    │
      │                         │─────────────────────►│                      │                    │
      │                         │                      │ spec_repo.get(id)    │                    │
      │                         │                      │──► PostgreSQL         │                    │
      │                         │                      │◄── SpecDocument      │                    │
      │                         │                      │                      │                    │
      │                         │                      │ generate_requirements(discovery, ...)         │
      │                         │                      │─────────────────────►│                    │
      │                         │                      │                      │ _load_template()   │
      │                         │                      │                      │ jinja.render(...)  │
      │                         │                      │                      │ llm.complete(...)  │
      │                         │                      │                      │───────────────────►│
      │                         │                      │                      │◄─── LLMResponse ───│
      │                         │                      │                      │                    │
      │                         │                      │                      │ extract_json()     │
      │                         │                      │                      │ EARSRequirement    │
      │                         │                      │                      │   .model_validate()│
      │                         │                      │                      │                    │
      │                         │                      │                      │ validate_requirement(req)  │
      │                         │                      │                      │ ¿errores? → retry │
      │                         │                      │                      │   (max 3x) → llm  │
      │                         │                      │                      │───────────────────►│
      │                         │                      │                      │◄─── corrección ───│
      │                         │                      │                      │                    │
      │                         │                      │◄── list[EARSRequirement] ──────────────────│
      │                         │                      │                      │                    │
      │                         │                      │ spec.requirements = reqs                   │
      │                         │                      │ spec.phase = REQUISITOS                    │
      │                         │                      │ spec_repo.update(spec)                     │
      │                         │                      │──► PostgreSQL                              │
      │                         │                      │◄── OK                                      │
      │                         │                      │                      │                    │
      │                         │◄── SpecDocument ────│                      │                    │
      │◄── 200 JSON ──────────│                      │                      │                    │
```

---

## 9. Detalles de Implementación Relevantes

### 9.1 Sistema de IDs

Todos los IDs son **ULID con prefijo tipado** (NO UUID):

```python
# domain/sdd/id_generator.py
IdGenerator.generate("project")   → "prj_01KT07HCKMM..."
IdGenerator.generate("feature")   → "feat_01KT0CDV84..."
IdGenerator.generate("spec")      → "spec_01KT06W284..."
IdGenerator.generate("task")      → "tsk_01KT08ABC0..."
IdGenerator.generate("user")      → "usr_01KT05JRA7..."
IdGenerator.generate("api_key")   → "apk_..."
IdGenerator.generate("audit")     → "aud_..."
```

Ventajas: URL-safe, ordenables temporalmente (los primeros 10 chars son timestamp), prefijo semántico para debugging y routing.

### 9.2 Patrón de Creación de Casos de Uso

Los casos de uso **NO** son singletons pre-cableados. Se instancian en cada request:

```python
# En los routers SDD (specs.py, features.py, discovery.py):
uc = CaptureDiscoveryUseCase(
    spec_repo=request.app.state.spec_repo,
    project_repo=request.app.state.project_repo,
    llm_client=request.app.state.llm_client,
)
```

Los servicios de dominio son **funciones puras** (no clases), inyectando `llm_client` como parámetro:

```python
# domain/agents/analyzer/service.py
async def generate_requirements(
    discovery: DiscoveryDocument,
    constitution: Constitution | None,
    llm_client: LLMClient,  # Inyectado
) -> list[EARSRequirement]:
```

### 9.3 Sistema de Validación con Reintentos

El validador EARS es el mecanismo de calidad más robusto:

1. El LLM genera requisitos en JSON
2. Se parsean a `EARSRequirement` (Pydantic)
3. `validate_requirement(req)` verifica:
   - Que el `source_statement` contenga las keywords del patrón (WHEN, IF, WHILE, WHERE)
   - Que `system` y `response` no estén vacíos
   - Que `acceptance_criteria` no esté vacío
4. Si hay errores: se envía el requisito erróneo + los mensajes de error de vuelta al LLM para que lo corrija
5. Máximo 3 reintentos por requisito

### 9.4 Documentos Enriquecidos (ProseMirror/TipTap)

Discovery y Requirements no son strings planos. Son **árboles JSON tipados**:

```python
class RichTextDocument(BaseModel):
    version: int = 1
    content: list[DocumentNode]  # Árbol de nodos (heading, paragraph, bulletList, etc.)
    sections: list[SectionHeading]  # Índice de navegación extraído de headings
```

Esto permite integración directa con editores WYSIWYG en el frontend (ProseMirror/TipTap).

### 9.5 Manejo de Errores — RFC 7807

TODOS los errores usan `Content-Type: application/problem+json`:

```json
{
  "type": "urn:kosmo:features:not-approved",
  "title": "Feature no aprobada",
  "status": 409,
  "detail": "La feature feat_01HT... debe estar Aprobada para generar requisitos",
  "instance": "/api/v1/features/feat_01HT/requirements/generate",
  "trace_id": "01KT05JRA7466PPYQXYTX",
  "violations": []
}
```

Cada `type` es una URN única que permite al frontend hacer `switch` para manejo específico.

---

## 10. Proveedores LLM Soportados

| Proveedor | Adapter | Modelo por Defecto | Configuración |
|---|---|---|---|
| **Anthropic** | `LiteLLMClient` | `claude-sonnet-4-20250514` | `LLM_PROVIDER` no seteado (default) |
| **OpenAI** | `LiteLLMClient` | Configurable | `LLM_PROVIDER=openai` |
| **Google Gemini** | `LiteLLMClient` | Configurable | `LLM_PROVIDER=gemini` |
| **DeepSeek** | `DeepSeekClient` | `deepseek-chat` | `LLM_PROVIDER=deepseek` |
| **Noop (Mock)** | `NoopLLMClient` | N/A | `LLM_PROVIDER=noop` (testing) |

El API key se almacena **cifrado con Fernet** en PostgreSQL (tabla `encrypted_api_keys`), o se lee de `LLM_API_KEY` en `.env` durante el wiring.

---

## 11. Lo Que Falta / Stubs

| Stub | Estado | Descripción |
|---|---|---|
| `domain/agents/learning/` | Solo `__pycache__` | Agente de aprendizaje (planeado, no implementado) |
| `domain/agents/memory_agent/` | Solo `__pycache__` | Agente de memoria (planeado, no implementado) |
| `infrastructure/mcp/` | Carpeta vacía | Model Context Protocol (planeado) |
| `infrastructure/sandbox/` | Carpeta vacía | Sandbox de ejecución de código (planeado) |
| `infrastructure/git/` | Carpeta vacía | Integración con Git (planeado) |
| `infrastructure/outbox/` | Carpeta vacía | Patrón Outbox para eventos (planeado) |
| `infrastructure/persistence/mongodb/` | Carpeta vacía | Memoria de agentes en MongoDB (planeado, motor instalado) |
| `infrastructure/persistence/postgres/vector/` | Stub | Búsqueda vectorial pgvector (infra lista, código pendiente) |
| LangGraph nodes reales | Stubs | Los nodos en `sdd_graph.py` solo cambian fase, no ejecutan agentes reales |
| Fase CARACTERISTICAS | No implementada en pipeline | Definida en enum pero sin endpoint de avance |
| Fase IMPLEMENTACION | No implementada | Definida en enum pero sin lógica |

---

## 12. Resumen Ejecutivo

| Dimensión | Valoración |
|---|---|
| **Arquitectura** | Hexagonal (Ports & Adapters) — 4 capas con enforcement automático |
| **Paradigma IA** | **Encadenamiento de prompts**, NO agentes autónomos |
| **Cohesión** | **Alta** — cada módulo tiene una responsabilidad única y clara |
| **Acoplamiento** | **Bajo** — inyección de dependencias, abstracciones (Protocols), Strategy Pattern para LLMs |
| **Estado** | **Funcional** con stubs para features planeadas (memoria, aprendizaje, MCP, sandbox) |
| **Lenguaje** | Python 3.13, todo tipado (pyright strict), inglés en código, español en mensajes al usuario |
| **Persistencia** | PostgreSQL (principal) + Redis (tokens/cache) + MongoDB (planeado) |
| **Seguridad** | PKCE + Argon2id + RS256 JWT + Fernet + rate limiting + account lockout |
| **Observabilidad** | OpenTelemetry + Logfire + structlog + trace IDs en todas las requests |
| **CI/CD** | GitHub Actions: lint → type check → tests → deploy (Vercel frontend, Render backend) |
