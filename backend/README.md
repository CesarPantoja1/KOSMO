# KOSMO — Backend

API del proyecto KOSMO construida con **FastAPI** sobre Python 3.13, arquitectura hexagonal (Ports & Adapters) y `uv` como gestor de dependencias.

---

## 1. Requisitos previos

| Herramienta | Versión | Uso |
|---|---|---|
| [Python](https://www.python.org/downloads/) | **3.13** | Runtime |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | >= 0.11 | Gestor de dependencias y entorno virtual |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | última | Levantar PostgreSQL y Redis |
| [Git](https://git-scm.com/downloads) | cualquiera | Clonar el repositorio |
| OpenSSL | incluido en Git Bash / macOS / Linux | Generar claves JWT RS256 |

> **Windows:** se recomienda usar **Git Bash** o **WSL** para los comandos `openssl`.

---

## 2. Instalación y configuración

```bash
git clone https://github.com/CesarPantoja1/KOSMO.git
cd KOSMO/backend
uv sync --all-groups
```

Esto instala dependencias de producción y desarrollo (`pytest`, `ruff`, `pyright`, etc.).

### 2.1. Levantar servicios de infraestructura

```bash
docker run -d --name kosmo-postgres \
  -e POSTGRES_USER=kosmo -e POSTGRES_PASSWORD=kosmo -e POSTGRES_DB=kosmo_dev \
  -p 5432:5432 postgres:16

docker run -d --name kosmo-redis -p 6379:6379 redis:7
```

### 2.2. Variables de entorno

```bash
cp .env.example .env
```

#### Generar claves JWT (RS256)

```bash
mkdir -p .secrets
openssl genrsa -out .secrets/jwt_private.pem 2048
openssl rsa -in .secrets/jwt_private.pem -pubout -out .secrets/jwt_public.pem
```

#### Generar FERNET_MASTER_KEY

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copia el valor en `.env` como `FERNET_MASTER_KEY=<valor>`.

Los valores por defecto de `.env.example` funcionan para desarrollo local con los comandos Docker anteriores. Si cambiaste puertos o credenciales, ajusta `DATABASE_URL` y `REDIS_URL`.

### 2.3. Migraciones

```bash
uv run alembic upgrade head
```

Para crear una nueva migración:

```bash
uv run alembic revision -m "descripcion_del_cambio"
```

---

## 3. Ejecutar el servidor

```bash
uv run uvicorn kosmo.infrastructure.api.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints disponibles:

- Health check: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json

> En `ENV=production` las rutas `/docs` y `/redoc` se deshabilitan.

---

## 4. Pruebas y calidad de código

```bash
uv run pytest                                           # Todos los tests
uv run pytest tests/unit/                               # Unitarios
uv run pytest tests/integration/                        # Integración (requiere Docker)
uv run pytest --cov=kosmo --cov-report=html             # Cobertura (min 60%)

uv run ruff check .       # Lint
uv run ruff format .      # Formato
uv run pyright            # Type check (strict)
uv run lint-imports       # Validar arquitectura por capas
```

Los tests usan stores en memoria que implementan los mismos puertos que los adaptadores reales, por lo que `tests/unit/` no requiere contenedores.

---

## 5. Arquitectura

### 5.1. Capas

Arquitectura hexagonal con cuatro capas. La dependencia fluye de izquierda a derecha:

```
infrastructure  →  application  →  domain  →  contracts
(adaptadores)      (casos de uso)  (algoritmos) (kernel)
```

| Capa | Responsabilidad | Depende de |
|---|---|---|
| **contracts** | Entidades, tipos de error e interfaces de puerto | — (kernel sin dependencias externas) |
| **domain** | Algoritmos puros. Sin I/O, sin clocks, sin randomness | contracts |
| **application** | Casos de uso que orquestan lógica de dominio vía puertos | domain, contracts |
| **infrastructure** | Adaptadores: FastAPI, SQLAlchemy, Redis, seguridad, LLM, telemetría | application |

La composition root está en `infrastructure/api/composition.py`: todo el wiring ocurre durante el lifespan de FastAPI.

### 5.2. Estructura del proyecto

```
backend/
├── alembic/                                    # Migraciones de PostgreSQL
├── src/kosmo/
│   ├── contracts/                              # KERNEL: entidades, errores, puertos
│   │   ├── sdd/                                #   Entidades SDD y repositorios (Protocol)
│   │   │   ├── document.py                     #     RichTextDocument, DocumentNode, SpecPhase
│   │   │   ├── feature.py                      #     Feature (id, number, title, slug, origin, display_id)
│   │   │   ├── project.py                      #     Project
│   │   │   ├── ears.py                         #     EARSRequirement (patrones EARS)
│   │   │   ├── ids.py                          #     NewTypes: ProjectId, FeatureId, RequirementId, UserId...
│   │   │   ├── errors.py                       #     SpecError, ProblemDetail, RFC 7807
│   │   │   ├── guardrails.py                   #     Términos prohibidos, secciones del discovery
│   │   │   └── repositories.py                 #     ProjectRepository, FeatureRepository, DocumentRepository
│   │   ├── auth/                               #   Entidades y puertos de autenticación
│   │   ├── llm/ports.py                        #   LLMClient Protocol (complete, complete_json)
│   │   ├── pipeline/                           #   Puertos del pipeline de agentes
│   │   │   ├── orchestrator_ports.py           #     PhaseMode Protocol, AgentPort Protocol, Skill, Tool
│   │   │   ├── phase_contexts.py               #     Contextos por fase (Discovery, Features, EARS)
│   │   │   ├── phase_outputs.py                #     Outputs estructurados por fase
│   │   │   └── phase_errors.py                 #     PhaseTransitionError, PhaseNotSupportedError
│   │   ├── audit/                              #   AuditEvent, AuditEventSink
│   │   ├── memory/                             #   UserPreference
│   │   └── telemetry.py                        #   Decorador @traced, record_auth_event
│   ├── domain/                                 # Algoritmos puros (sin I/O)
│   │   ├── sdd/                                #   Lógica de dominio SDD
│   │   │   ├── id_generator.py                 #     IdGenerator.generate("entity") → ULID con prefijo tipado
│   │   │   ├── document_converters.py          #     Markdown ↔ RichTextDocument, slugify
│   │   │   ├── output_guardrails.py            #     Detección de términos técnicos en outputs de IA
│   │   │   └── validators/                     #     Validación EARS (sintaxis, calidad)
│   │   ├── pipeline/                           #   Orquestación pura de fases
│   │   │   ├── sequential_orchestrator.py      #     Orden estricto: DESCUBRIMIENTO → CARACTERISTICAS → REQUISITOS
│   │   │   ├── context_builder.py              #     Construye PhaseContext desde repositorios
│   │   │   ├── skill_registry.py               #     Registro dinámico de skills por fase
│   │   │   ├── tool_registry.py                #     Registro y ejecución de herramientas del agente
│   │   │   ├── phase_modes/                    #     Modos concretos de cada fase
│   │   │   │   ├── discovery_mode.py           #       Generación de documento de descubrimiento
│   │   │   │   ├── discovery_refine_mode.py    #       Refinamiento de descubrimiento existente
│   │   │   │   ├── features_mode.py            #       Generación de características (4 campos, nivel usuario)
│   │   │   │   └── ears_mode.py                #       Generación de requisitos EARS
│   │   │   └── phase_validators/               #   Validadores de calidad por fase
│   │   └── auth/pkce.py                        #   s256_challenge, verify_s256 (RFC 7636)
│   ├── application/                            # Casos de uso (orquestación)
│   │   ├── auth/                               #   Register, Authorize, Exchange, IssueToken, Refresh, Revoke
│   │   ├── projects/                           #   CreateProject, GetProject, ListProjects
│   │   ├── discovery/                          #   GenerateDiscovery, GetDiscovery, SaveDiscovery, RefineDiscovery
│   │   ├── features/                           #   GenerateFeatures, SuggestFeatures, CreateCharacteristic, SaveSelected
│   │   ├── requirements/                       #   GenerateEARS, GetRequirements, SaveRequirements
│   │   └── pipeline/kosmo_agent.py             #   KOSMOAgent: bucle ReAct con herramientas y validación
│   ├── infrastructure/                         # Adaptadores concretos
│   │   ├── api/                                #   Capa HTTP (FastAPI)
│   │   │   ├── main.py                         #     FastAPI app factory, lifespan, CORS, middlewares
│   │   │   ├── composition.py                  #     Composition root: wiring de todos los componentes
│   │   │   ├── schemas.py                      #     DTOs Pydantic de request/response
│   │   │   ├── dependencies/                   #     FastAPI Depends (auth, rate limiting)
│   │   │   ├── middlewares/                    #     Request logging, trace context
│   │   │   └── routers/                        #     Endpoints REST por dominio
│   │   │       ├── auth.py                     #       /api/v1/auth/*
│   │   │       ├── projects.py                 #       /api/v1/projects/*
│   │   │       ├── discovery.py                #       /api/v1/projects/{id}/discovery/*
│   │   │       ├── features.py                 #       /api/v1/projects/{id}/features/*
│   │   │       └── requirements.py             #       /api/v1/features/{id}/requirements/*
│   │   ├── persistence/                        #   Adaptadores de persistencia
│   │   │   ├── postgres/                       #     SQLAlchemy async (models + repositories)
│   │   │   └── redis/                          #     Token store, auth code store, login attempts
│   │   ├── llm/                                #   Adaptadores de LLM
│   │   │   ├── pydantic_ai_adapter.py          #     Cliente real vía pydantic-ai (DeepSeek)
│   │   │   └── noop_adapter.py                 #     Mock de desarrollo (respuestas predefinidas)
│   │   ├── security/                           #   Argon2id (passwords), RS256 JWT, Fernet (secrets)
│   │   └── telemetry/                          #   Bootstrap structlog + Logfire/OpenTelemetry
│   └── config.py                               # Pydantic Settings desde .env
├── tests/
│   ├── unit/                                   # Tests unitarios con fakes en memoria
│   ├── integration/                            # Tests con contenedores reales
│   ├── contract/                               # Validación de contrato OpenAPI
│   └── properties/                             # Tests de invariantes con hypothesis
├── .env.example
├── .importlinter                               # Reglas de arquitectura por capas
├── alembic.ini
├── pyproject.toml
└── uv.lock
```

### 5.3. Convenciones obligatorias

#### Naming

- **snake_case** sin excepciones en llaves JSON, atributos y nombres de archivo
- Booleanos con prefijo `is_` / `has_` (`is_active`, `has_access`)
- Enums como strings en `snake_case` declarados como `enum` en JSON Schema
- Código en **inglés**, mensajes al usuario en **español neutro**

#### IDs

- **ULID con prefijo tipado** vía `IdGenerator.generate("entity")`
- Prefijos: `prj_` (project), `feat_` (feature), `spec_` (spec), `tsk_` (task), `usr_` (user), `apk_` (apikey), `aud_` (audit)
- **Paquete ULID: únicamente `python-ulid`** con `from ulid import ULID` y `ULID()`
- **Prohibido `ulid-py`**: ambos paquetes ocupan el módulo `ulid` y entran en conflicto. `ulid-py` no tiene type stubs y rompe `pyright` y el runtime
- **Prohibido UUID**: nunca `uuid.uuid4()` ni `uuid.UUID(...)`
- Request ID usa `ULID().hex` (sin prefijo)

#### Fechas

- **ISO-8601 UTC con sufijo `Z`**: `"2026-04-20T18:30:00Z"`
- Usar `datetime.now(UTC)` (de `datetime import UTC`)

#### Nulables

- Se serializan como `null`, nunca como `""` ni `0`
- Campos opcionales siempre presentes en el schema

#### Valores compuestos: siempre objeto, nunca string

| MAL (string ambiguo) | BIEN (objeto estructurado) |
|---|---|
| `"price": "29.90 EUR"` | `"price": { "amount": 29.90, "currency": "EUR" }` |
| `"distance": "5 km"` | `"distance": { "value": 5, "unit": "km" }` |
| `"location": "40.41,-3.70"` | `"location": { "lat": 40.41, "lng": -3.70 }` |

---

## 6. API Reference

### 6.1. Endpoints

| Método | Ruta | Auth | Tag | Descripción |
|---|---|---|---|---|
| `POST` | `/api/v1/auth/register` | — | auth | Registra un nuevo usuario |
| `POST` | `/api/v1/auth/authorize` | — | auth | Valida credenciales + PKCE, emite authorization_code |
| `POST` | `/api/v1/auth/token` | — | auth | Intercambia code + verifier por JWT pair |
| `POST` | `/api/v1/auth/refresh` | Refresh token | auth | Rota el par de tokens |
| `GET` | `/api/v1/auth/me` | Bearer | auth | Devuelve Principal autenticado |
| `POST` | `/api/v1/auth/logout` | Bearer | auth | Revoca access y refresh |
| `POST` | `/api/v1/projects` | Bearer | projects | Crea un nuevo proyecto |
| `GET` | `/api/v1/projects` | Bearer | projects | Lista proyectos del usuario |
| `GET` | `/api/v1/projects/{id}` | Bearer | projects | Obtiene un proyecto por ID |
| `POST` | `/api/v1/projects/{id}/discovery` | Bearer | discovery | Genera documento de descubrimiento con IA |
| `GET` | `/api/v1/projects/{id}/discovery` | Bearer | discovery | Obtiene el documento de descubrimiento |
| `PUT` | `/api/v1/projects/{id}/discovery` | Bearer | discovery | Guarda manualmente el documento de descubrimiento |
| `POST` | `/api/v1/projects/{id}/discovery/refine` | Bearer | discovery | Refina el descubrimiento con IA |
| `POST` | `/api/v1/projects/{id}/features` | Bearer | features | Genera características con IA |
| `GET` | `/api/v1/projects/{id}/features` | Bearer | features | Lista características del proyecto |
| `POST` | `/api/v1/projects/{id}/features/suggest` | Bearer | features | Sugiere 3 características con IA |
| `POST` | `/api/v1/projects/{id}/features/manual` | Bearer | features | Crea una característica manualmente |
| `POST` | `/api/v1/projects/{id}/features/save` | Bearer | features | Guarda características seleccionadas |
| `POST` | `/api/v1/features/{id}/requirements/generate` | Bearer | requirements | Genera requisitos EARS con IA |
| `GET` | `/api/v1/features/{id}/requirements` | Bearer | requirements | Obtiene requisitos de la característica |
| `PUT` | `/api/v1/features/{id}/requirements` | Bearer | requirements | Guarda manualmente requisitos |

### 6.2. Autenticación

Flujo **Authorization Code + PKCE** (RFC 7636) sobre JWT firmados con **RS256**.

```
1. POST /api/v1/auth/register          → crea cuenta
2. POST /api/v1/auth/authorize         → valida credenciales + PKCE → authorization_code
3. POST /api/v1/auth/token             → code + code_verifier → { access_token, refresh_token }
4. GET  /api/v1/auth/me                → Bearer access → Principal { subject, scopes }
5. POST /api/v1/auth/refresh           → refresh_token → nuevo par (rotación)
6. POST /api/v1/auth/logout            → revoca access y refresh
```

| Token | TTL por defecto | Uso |
|---|---|---|
| **Access** | 15 minutos | `Authorization: Bearer <token>` en cada request |
| **Refresh** | 7 días | Solo en `POST /refresh`. Se rota en cada uso |

**Protección contra abuso:**

- **Rate limiting por IP**: ventana fija de 60s por IP y ruta
- **Bloqueo de cuenta**: 10 fallos en 15 minutos bloquean el acceso
- **Token Rotation**: el refresh anterior queda invalidado al usarse. Si se detecta reúso, se revoca la familia completa

### 6.3. Pipeline SDD

KOSMO implementa un pipeline de especificación dirigida (Spec-Driven Development) que guía al usuario desde la visión del producto hasta los requisitos formales EARS.

#### Flujo de fases

```
DESCUBRIMIENTO  →  CARACTERISTICAS  →  REQUISITOS  →  MODELO  →  IMPLEMENTACION
   (7 secciones)     (4 campos)         (EARS)         (futuro)     (futuro)
```

| Fase | Output | Formato |
|---|---|---|
| **Descubrimiento** | Documento de visión del producto | 7 secciones: Visión, Problema, Actores, Propuesta de valor, Metas, Reglas de negocio, Alcance |
| **Características** | Funcionalidades del producto | 4 campos: código (C01..), título (máx 6 palabras), descripción (perspectiva usuario), origen (trazabilidad al descubrimiento) |
| **Requisitos** | Especificación formal EARS | 5 campos: código (REQ-n.m), patrón EARS, enunciado, origen, criterios de aceptación (Given/When/Then) |

#### Agente KOSMO

El agente central (`application/pipeline/kosmo_agent.py`) implementa un bucle **ReAct** (Reasoning + Acting):

1. Combina el `PhaseMode.system_prompt` + descripción de herramientas + formato ReAct
2. Envía el prompt al LLM (`LLMClient.complete()`)
3. Parsea la respuesta JSON: llamada a herramienta (`action` + `input`) o output final
4. Si es herramienta: ejecuta vía `ToolRegistry`, devuelve observación al LLM
5. Si es output final: valida con `mode.validate_output()`. Si es inválido, reinyecta errores
6. Repite hasta máximo 8 iteraciones o output válido

**Herramientas del agente** registradas en `composition.py`:

| Herramienta | Fase | Función |
|---|---|---|
| `validate_discovery_structure` | Descubrimiento | Verifica 7 secciones, mínimo de metas/reglas/exclusiones |
| `validate_discovery_quality` | Descubrimiento | Detecta formato user story, términos técnicos |
| `validate_business_level` | Refinamiento | Verifica que el texto refinado no contenga términos técnicos |
| `validate_feature_structure` | Características | Valida formato de 4 campos, prohíbe términos técnicos |
| `validate_feature_uniqueness` | Características | Detecta títulos duplicados |
| `validate_ears_syntax` | Requisitos | Valida sintaxis EARS |
| `validate_ears_quality` | Requisitos | Evalúa calidad de requisitos EARS |
| `detect_implementation_leaks` | Requisitos | Detecta fugas de implementación en requisitos |

#### Proveedor LLM

El adaptador `PydanticAILLMClient` usa el modelo **DeepSeek** (compatible con API OpenAI) vía `pydantic-ai`. En desarrollo se puede usar `NoopLLMClient` que devuelve respuestas predefinidas sin coste de API. La selección se configura en `.env`:

```env
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_API_KEY=<tu_api_key>
```

### 6.4. Formato de errores

Toda respuesta 4xx/5xx usa **RFC 7807 Problem Detail** con `Content-Type: application/problem+json`:

```json
{
  "type": "urn:kosmo:features:not-found",
  "title": "Feature no encontrada",
  "status": 404,
  "detail": "La feature feat_01KT... no existe en este proyecto",
  "instance": "/api/v1/projects/prj_01KT/features",
  "trace_id": "01KT05JRA7466PPYQXYTX",
  "violations": []
}
```

| Error | HTTP | URN |
|---|---|---|
| `ProjectNotFoundError` | 404 | `urn:kosmo:projects:not-found` |
| `FeatureNotFoundError` | 404 | `urn:kosmo:features:not-found` |
| `DocumentNotFoundError` | 404 | `urn:kosmo:document:not-found` |
| `DocumentValidationError` | 422 | `urn:kosmo:document:invalid-structure` |
| `MarkdownParseError` | 422 | `urn:kosmo:document:parse-error` |
| `LLMInvocationError` | 502 | `urn:kosmo:llm:invocation-error` |
| `PhaseTransitionError` | 409 | `urn:kosmo:pipeline:phase-transition-error` |

---

## 7. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Runtime | Python 3.13, FastAPI 0.136, Uvicorn |
| Base de datos | PostgreSQL 16 (SQLAlchemy 2.0 asyncio + asyncpg, pgvector) |
| Cache / Sesiones | Redis 7 (token store, rate limiting, login attempts) |
| Autenticación | Argon2id (OWASP 2025), RS256 JWT, Fernet (AES-128-CBC) |
| IA / Agentes | pydantic-ai 1.86, LangGraph 1.1, DeepSeek (compatible OpenAI) |
| Observabilidad | structlog, OpenTelemetry, Logfire |
| Validación | Pydantic 2.7 |
| IDs | ULID vía `python-ulid` (prohibido `ulid-py`) |
| Testing | pytest 9, hypothesis 6, schemathesis 4 |
| Calidad de código | ruff, pyright (strict), import-linter |
| Dependencias | uv |

---

## 8. Observabilidad

El backend implementa los tres pilares de observabilidad sobre **structlog** y **OpenTelemetry**. En desarrollo no se necesita ningún servicio externo: todo sale por consola. En producción, con `LOGFIRE_TOKEN` configurado, los datos se envían a **Logfire**.

### 8.1. Logging (structlog)

Cada request HTTP genera un log estructurado emitido por `RequestLoggingMiddleware`:

```
http.request.completed  method=GET  path=/health  status_code=200  duration_ms=1.234  request_id=a3f...
```

| Campo | Descripción |
|---|---|
| `request_id` | ULID hex único por request, propagado vía `structlog.contextvars` |
| `duration_ms` | Tiempo total de procesamiento en milisegundos |
| `trace_id` / `span_id` | Presentes cuando el request corre dentro de un span OTel |

### 8.2. Trazas (OpenTelemetry)

**Auto-instrumentación** de FastAPI, SQLAlchemy y HTTPX al arrancar.

**Decorador `@traced`** disponible en `kosmo.contracts.telemetry`:

```python
from kosmo.contracts.telemetry import traced

class MiCasoDeUso:
    @traced("mi_dominio.accion")
    async def execute(self, cmd: MiComando) -> Resultado: ...
```

### 8.3. Métricas

El contador `kosmo.auth.events` registra eventos de autenticación (`register_success`, `login_success`, `login_failure`, `token_refresh`, `logout`).

### 8.4. Variables de entorno

| Variable | Defecto | Descripción |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Nivel mínimo de logging. `DEBUG` activa renderer con colores |
| `LOGFIRE_TOKEN` | _(vacío)_ | Token Logfire. Vacío → exportadores de consola |
| `OTEL_SERVICE_NAME` | `kosmo-backend` | `service.name` en recursos OTel |
| `OTEL_ENVIRONMENT` | `development` | `deployment.environment` en recursos OTel |

---

## 9. Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `pydantic_core._pydantic_core.ValidationError` al arrancar | Falta una variable obligatoria en `.env` | Revisa `.env` contra `config.py` |
| `connection refused` a Postgres/Redis | Contenedores no levantados | `docker ps` y vuelve al paso 2.1 |
| `ModuleNotFoundError: kosmo` | Ejecutaste fuera del venv | Usa `uv run <comando>` o activa `.venv` |
| `alembic: command not found` | Dependencias dev no instaladas | `uv sync --all-groups` |
| `FileNotFoundError: .secrets/jwt_*.pem` | Claves JWT no generadas | Ejecuta generación de claves en 2.2 |
| `401 Token revoked` tras reiniciar Redis | Tokens emitidos antes ya no se reconocen | Repite el flujo desde `/authorize` |
| `ImportError: cannot import name 'ULID'` | `ulid-py` instalado en conflicto con `python-ulid` | `uv pip uninstall ulid-py && uv sync` |
