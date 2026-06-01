# KOSMO — Backend

API del proyecto KOSMO construida con **FastAPI** sobre Python 3.13, arquitectura hexagonal por capas (`contracts → domain → application → infrastructure`) y `uv` como gestor de dependencias.

## OpenAPI / Swagger

- **Puerto:** `8000`
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json

---

## 1. Requisitos previos

Instala lo siguiente antes de empezar:

| Herramienta | Versión | Uso |
|---|---|---|
| [Python](https://www.python.org/downloads/) | **3.13** | Runtime |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | ≥ 0.11 | Gestor de dependencias y entorno virtual |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | última | Levantar PostgreSQL, MongoDB y Redis |
| [Git](https://git-scm.com/downloads) | cualquiera | Clonar el repositorio |
| OpenSSL | incluido en Git Bash / macOS / Linux | Generar claves JWT |

> **Windows:** se recomienda usar **Git Bash** o **WSL** para los comandos `openssl` y los scripts de ejemplo.

---

## 2. Clonar el repositorio

```bash
git clone https://github.com/CesarPantoja1/KOSMO.git
cd KOSMO/backend
```

---

## 3. Instalar dependencias

`uv` crea el entorno virtual (`.venv`) y sincroniza dependencias a partir de `uv.lock`:

```bash
uv sync --all-groups
```

Esto instala tanto las dependencias de producción como las de desarrollo (`pytest`, `ruff`, `pyright`, etc.).

---

## 4. Levantar servicios de infraestructura

El backend depende de **PostgreSQL**, **MongoDB** y **Redis**. La forma más simple es con Docker:

```bash
docker run -d --name kosmo-postgres \
  -e POSTGRES_USER=kosmo -e POSTGRES_PASSWORD=kosmo -e POSTGRES_DB=kosmo_dev \
  -p 5432:5432 postgres:16

docker run -d --name kosmo-mongo -p 27017:27017 mongo:7

docker run -d --name kosmo-redis -p 6379:6379 redis:7
```

Verifica que los tres contenedores estén corriendo:

```bash
docker ps
```

---

## 5. Configurar variables de entorno

Copia la plantilla:

```bash
cp .env.example .env
```

Edita `.env` y rellena los valores vacíos. A continuación se explica cómo generar los secretos obligatorios.

### 5.1. Generar claves JWT (RS256)

Crea el directorio `.secrets/` y genera un par de claves:

```bash
mkdir -p .secrets
openssl genrsa -out .secrets/jwt_private.pem 2048
openssl rsa -in .secrets/jwt_private.pem -pubout -out .secrets/jwt_public.pem
```

Las rutas ya coinciden con las de `.env.example`:

```
JWT_PRIVATE_KEY_PATH=./.secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=./.secrets/jwt_public.pem
```

### 5.2. Generar `FERNET_MASTER_KEY`

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copia el valor resultante en `.env`:

```
FERNET_MASTER_KEY=<valor_generado>
```

### 5.3. Resto de variables

Los valores por defecto en `.env.example` funcionan para desarrollo local si usaste los comandos de Docker del paso 4. Si cambiaste usuarios, puertos o nombres, ajusta `DATABASE_URL`, `MONGO_URL` y `REDIS_URL` en consecuencia.

---

## 6. Aplicar migraciones

Las migraciones viven en `alembic/versions/`. Para aplicarlas:

```bash
uv run alembic upgrade head
```

Para crear una nueva migración:

```bash
uv run alembic revision -m "descripcion_del_cambio"
```

---

## 7. Ejecutar el servidor

```bash
uv run uvicorn kosmo.infrastructure.api.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints disponibles una vez arriba:

- Health check: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json

> En `ENV=production` las rutas `/docs` y `/redoc` se deshabilitan automáticamente.

---

## 8. Pruebas y calidad de código

```bash
# Tests (cobertura mínima 60%)
uv run pytest

# Linter
uv run ruff check .

# Formateo
uv run ruff format .

# Type checking
uv run pyright

# Validar arquitectura por capas
uv run lint-imports
```

Los tests están organizados en `tests/unit`, `tests/integration`, `tests/contract` y `tests/properties`.

---

## 9. Estructura del proyecto

```
backend/
├── alembic/                          # Migraciones de PostgreSQL
├── postman/                          # Colecciones Postman (Auth + SDD Pipeline)
├── src/kosmo/
│   ├── contracts/                    # Kernel: entidades, errores, puertos, telemetría
│   │   ├── auth/                     # User, Principal, Token*, AuthorizationCode, errors, ports
│   │   ├── sdd/                      # SpecDocument, Feature, Project, DocumentNode, EARS, repos
│   │   │   ├── document.py           # Árbol de documento enriquecido (ProseMirror/TipTap)
│   │   │   └── ...
│   │   ├── llm/                      # LLMClient, PromptTemplate, ApiKeyVault
│   │   ├── storage/                  # BlobStorage port
│   │   └── telemetry.py              # Decorador @traced y record_auth_event
│   ├── domain/                       # Algoritmos de dominio puro (sin I/O)
│   │   ├── agents/                   # Agentes de IA (spec_capture, discovery_writer, 
│   │   │                              #   requirements_generator, feature_generator, analyzer, ...)
│   │   ├── sdd/                      # Lógica SDD pura
│   │   │   ├── document_converters.py # Markdown ↔ Document tree, slugify_spanish, validación
│   │   │   ├── validators/           # EARS, DomainModel, TaskDAG, XMI
│   │   │   └── serializers/          # PlantUML, XMI
│   │   ├── auth/pkce.py              # s256_challenge, verify_s256 (RFC 7636)
│   │   └── features/                 # Lógica de transiciones de estado
│   ├── application/                  # Casos de uso (orquestación)
│   │   ├── auth/                     # Register, Authorize, Exchange, Issue/Verify/Refresh/Revoke
│   │   ├── sdd/                      # Capture, Regenerate, Save/Get Discovery, Design, Tasks
│   │   │   ├── save_discovery_document.py   # Guarda edición manual del documento
│   │   │   ├── get_discovery_document.py    # Retorna documento + índice
│   │   │   ├── regenerate_discovery.py      # IA reescribe el discovery
│   │   │   └── ...
│   │   ├── features/                 # CRUD, Generate, Improve, Suggest, Requirements
│   │   │   ├── save_requirements_document.py  # Guarda edición manual de requisitos
│   │   │   ├── get_requirements_document.py   # Retorna documento + índice + header
│   │   │   ├── regenerate_requirements.py     # IA reescribe requisitos
│   │   │   └── ...
│   │   ├── projects/                 # Create, List, Get Project
│   │   └── orchestration/            # LangGraph SDD pipeline
│   ├── infrastructure/               # Adaptadores concretos
│   │   ├── api/
│   │   │   ├── main.py               # FastAPI app, lifespan, CORS, OpenAPI tags
│   │   │   ├── composition.py        # Composition root (wiring de puertos y adaptadores)
│   │   │   ├── schemas*.py           # DTOs Pydantic (discovery doc, requirements doc, features, ...)
│   │   │   ├── dependencies/         # FastAPI Depends (auth, scopes, rate limiting)
│   │   │   ├── middlewares/          # RequestLoggingMiddleware
│   │   │   └── routers/              # auth, projects, discovery, features, requirements, specs, schemas
│   │   ├── persistence/              # PostgreSQL (SQLAlchemy async), Redis (token store, rate limit)
│   │   ├── llm/                      # DeepSeek, LiteLLM, Noop adapters (LLMClient)
│   │   ├── security/                 # Argon2id, JOSE/JWT, Fernet
│   │   └── telemetry/                # Bootstrap de structlog + Logfire/OpenTelemetry
│   └── config.py                     # Carga de Settings desde .env
├── tests/
│   ├── unit/
│   │   ├── test_document_converters.py  # 34 tests: slugify español, conversión doc↔md, validación
│   │   ├── test_feature_use_cases.py
│   │   ├── test_auth_use_cases.py
│   │   └── ...
│   ├── integration/
│   ├── contract/
│   └── properties/
├── .env.example
├── .importlinter                     # Reglas de arquitectura por capas
├── alembic.ini
├── pyproject.toml
└── uv.lock
```

---

## 10. Autenticación

El sistema de autenticación implementa el flujo **Authorization Code + PKCE** sobre JWT firmados con **RS256**. La arquitectura es hexagonal: los puertos y entidades del kernel viven en `contracts/auth`, los algoritmos de dominio puro en `domain/auth`, los casos de uso en `application/auth`, los adaptadores (Argon2, RS256, Postgres, Redis, Fernet) en `infrastructure/`, y los DTOs HTTP de la API en `infrastructure/api/schemas.py`.

### 10.1. Casos de uso

| Caso de uso | Archivo | Descripción |
|---|---|---|
| `RegisterUser` | `application/auth/register.py` | Crea un usuario con contraseña hasheada en Argon2. |
| `AuthorizeWithPkce` | `application/auth/authorize.py` | Verifica bloqueo de cuenta, valida credenciales, registra intentos fallidos, emite código de autorización. |
| `ExchangeAuthorizationCode` | `application/auth/exchange.py` | Intercambia el código + `code_verifier` por un par de tokens. Verifica PKCE. |
| `IssueTokenPair` | `application/auth/use_cases.py` | Emite un access + refresh token y registra el refresh en Redis. |
| `VerifyAccessToken` | `application/auth/use_cases.py` | Valida firma, tipo y estado de revocación del access token. |
| `RefreshTokenPair` | `application/auth/use_cases.py` | Rota el par. Detecta reuso y revoca la familia completa si ocurre. |
| `RevokeSession` | `application/auth/use_cases.py` | Revoca el access actual y, opcionalmente, el refresh y toda la familia. |

### 10.2. Flujo completo

```
1. POST /api/v1/auth/register          → crea cuenta
2. POST /api/v1/auth/authorize         → valida credenciales + PKCE → authorization_code
3. POST /api/v1/auth/token             → code + code_verifier → { access_token, refresh_token }
4. GET  /api/v1/auth/me                → Bearer access → Principal { subject, scopes }
5. POST /api/v1/auth/refresh           → refresh_token → nuevo par (rotación)
6. POST /api/v1/auth/logout            → revoca access y refresh
```

### 10.3. Modelo de tokens

| Token | Vida útil por defecto | Uso |
|---|---|---|
| **Access** | 15 minutos | Se envía en `Authorization: Bearer <token>` en cada request protegido. |
| **Refresh** | 7 días | Solo se envía a `POST /api/v1/auth/refresh` para obtener un nuevo par. Se rota en cada uso. |

Ambos llevan los claims estándar (`sub`, `iss`, `aud`, `iat`, `exp`, `jti`) más `type` (access/refresh), `scopes[]` y `family_id` (agrupa tokens de una misma sesión).

### 10.4. Estado en Redis

| Clave | TTL | Significado |
|---|---|---|
| `auth:refresh:{jti}` | TTL del refresh token | Refresh token vigente. Se borra al usarse o al hacer logout. Si no existe, el refresh es rechazado (defensa contra replay). |
| `auth:revoked:{jti}` | TTL residual del access | Access token revocado antes de su `exp`. `get_principal` lo consulta en cada request. |
| `auth:family:{family_id}` | TTL del refresh token | Familia de sesión activa. Al detectar reuso de refresh, se revoca la familia completa. |
| `auth:login_attempts:{email}` | 15 minutos desde el primer fallo | Contador de intentos fallidos por cuenta. Al llegar a 10, los siguientes intentos reciben 429 hasta que expira la clave. Se borra en un login exitoso. |
| `auth:ip_rate:{ruta}:{ip}` | 60 segundos | Contador de requests por IP y endpoint. Se resetea cada minuto. |

La rotación de refresh (lectura + borrado del JTI viejo) se ejecuta en una transacción Redis (`MULTI/EXEC`) para evitar carreras entre clientes concurrentes.

### 10.5. Endpoints

| Método | Ruta | Auth requerida | Límite IP | Descripción |
|---|---|---|---|---|
| `POST` | `/api/v1/auth/register` | — | 3/min | Registra un usuario nuevo. Devuelve `UserPublic`. |
| `POST` | `/api/v1/auth/authorize` | — | 10/min | Valida credenciales + `code_challenge`. Devuelve `authorization_code`. |
| `POST` | `/api/v1/auth/token` | — | 5/min | Intercambia `code` + `code_verifier` por un par de tokens. |
| `POST` | `/api/v1/auth/refresh` | Refresh token en el body | 30/min | Rota el par. El refresh anterior queda invalidado. |
| `GET`  | `/api/v1/auth/me` | Bearer access | — | Devuelve el `Principal` autenticado (`subject`, `scopes`). |
| `POST` | `/api/v1/auth/logout` | Bearer access | 20/min | Revoca el access y, si se envía, también el refresh. |

### 10.6. Variables de entorno

Las claves PEM se generan en el paso 5.1. El resto tiene valores por defecto y son opcionales en `.env`:

```env
JWT_PRIVATE_KEY_PATH=./.secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=./.secrets/jwt_public.pem
JWT_ALGORITHM=RS256
JWT_ISSUER=kosmo
JWT_AUDIENCE=kosmo-api
JWT_ACCESS_TTL_SECONDS=900
JWT_REFRESH_TTL_SECONDS=604800
```

### 10.7. Proteger una ruta

```python
from typing import Annotated

from fastapi import APIRouter, Depends

from kosmo.contracts.auth import Principal
from kosmo.infrastructure.api.dependencies.auth import get_principal, require_scopes

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("/me")
async def me(principal: Annotated[Principal, Depends(get_principal)]) -> dict[str, str]:
    return {"subject": principal.subject}


@router.post("", dependencies=[Depends(require_scopes("projects:write"))])
async def create_project() -> dict[str, str]:
    return {"status": "created"}
```

`get_principal` valida la firma, `iss`, `aud`, `exp`, el tipo de token y la lista de revocación. `require_scopes(*scopes)` añade comprobación de permisos sobre lo que ya hizo `get_principal`.

### 10.8. Códigos de respuesta

| Caso | Status | Detalle |
|---|---|---|
| Falta cabecera `Authorization` | `401` | `Bearer realm="kosmo"` |
| Firma inválida o token mal formado | `401` | `Bearer error="invalid_token"` |
| Token expirado | `401` | `detail: Token expired` |
| Token revocado | `401` | `detail: Token revoked` |
| Credenciales inválidas | `401` | `error: invalid_grant` |
| Código de autorización inválido o PKCE fallido | `400` | `error: invalid_grant` |
| Email ya registrado | `409` | — |
| Scope insuficiente | `403` | — |
| Rate limit por IP excedido | `429` | `detail: Demasiadas solicitudes...` + header `Retry-After` |
| Cuenta bloqueada por intentos fallidos | `429` | `error: account_locked` + header `Retry-After` |

### 10.9. Pruebas

```bash
uv run pytest tests/unit/test_auth_use_cases.py \
              tests/unit/test_identity_use_cases.py \
              tests/unit/test_rate_limiter.py \
              tests/integration/test_auth_router.py
```

Los tests usan stores en memoria que implementan los mismos puertos que los adaptadores de Redis, así que no requieren contenedores levantados.

---

### 10.10. Protección contra abuso

El sistema implementa dos mecanismos de protección independientes que se complementan.

#### Rate limiting por IP

`IpRateLimiter` (en `infrastructure/api/dependencies/rate_limit.py`) es una dependencia FastAPI que aplica una ventana fija de 60 segundos por IP y por ruta. Se inyecta con `dependencies=[Depends(...)]` en el decorador del endpoint sin contaminar la lógica de negocio.

Cuando la IP supera el límite, la respuesta incluye el header `Retry-After` con los segundos restantes de la ventana. Si Redis no está disponible (por ejemplo, en tests unitarios), el limiter se omite sin error.

#### Bloqueo de cuenta

`LoginAttemptStore` es un puerto definido en `contracts/auth/ports.py` e implementado por `RedisLoginAttemptStore` en `infrastructure/persistence/redis/`. El caso de uso `AuthorizeWithPkce` lo consume de la siguiente manera:

1. Al inicio de cada intento de login consulta `lockout_seconds(email)`. Si la cuenta está bloqueada lanza `AccountLockedError` con el tiempo restante.
2. Ante credenciales inválidas llama a `record_failure(email)`.
3. Ante un login exitoso llama a `clear(email)` para reiniciar el contador.

| Parámetro | Valor |
|---|---|
| Máximo de intentos fallidos | 10 |
| Duración del bloqueo | 15 minutos |
| Ventana de conteo | 15 minutos desde el primer fallo |
| Reseteo | Automático en login exitoso o al expirar la clave Redis |

El error `AccountLockedError` se mapea a HTTP 429 en el router con el header `Retry-After` y un mensaje descriptivo en español.

---

## 11. Observabilidad

El backend implementa los tres pilares de observabilidad sobre **structlog** y **OpenTelemetry**. En desarrollo no se necesita ningún servicio externo: todo sale por consola. En producción, con `LOGFIRE_TOKEN` configurado, los datos se envían a **Logfire**.

### 11.1. Logging (structlog)

Cada request HTTP genera un log estructurado emitido por `RequestLoggingMiddleware`:

```
http.request.completed  method=GET  path=/health  status_code=200  duration_ms=1.234  request_id=a3f…
```

| Campo | Descripción |
|---|---|
| `request_id` | UUID hex único por request, propagado a todos los logs del mismo contexto via `structlog.contextvars`. |
| `duration_ms` | Tiempo total de procesamiento en milisegundos. |
| `trace_id` / `span_id` | Presentes en todos los logs cuando el request corre dentro de un span OTel. Permiten correlacionar logs con trazas. |

El renderer cambia según el entorno:

| `ENV` / `LOG_LEVEL` | Renderer | Uso |
|---|---|---|
| `development` o `LOG_LEVEL=DEBUG` | `ConsoleRenderer` con colores | Lectura humana en terminal |
| `production` o `LOG_LEVEL` ≠ `DEBUG` | `JSONRenderer` | Ingestión en colectores de logs |

Los loggers ruidosos (`uvicorn.access`, `httpx`, `httpcore`, `asyncio`) se silencian a nivel `WARNING` para reducir el ruido.

### 11.2. Trazas (OpenTelemetry)

**Auto-instrumentación** — al arrancar, el stack instrumenta automáticamente:

| Librería | Qué registra |
|---|---|
| FastAPI | Spans por endpoint con método, ruta y status code. |
| SQLAlchemy | Spans por query SQL. |
| HTTPX | Spans por llamada HTTP saliente. |

**Decorador `@traced`** — disponible en `kosmo.contracts.telemetry` para instrumentar casos de uso de negocio:

```python
from kosmo.contracts.telemetry import traced

class MiCasoDeUso:
    @traced("mi_dominio.accion")
    async def execute(self, cmd: MiComando) -> Resultado: ...
```

El decorador funciona con funciones `async` y síncronas, registra la excepción en el span y propaga el error sin alterarlo.

Los spans de auth ya instrumentados:

| Span | Caso de uso |
|---|---|
| `auth.register` | `RegisterUser` |
| `auth.login` | `AuthorizeWithPkce` |
| `auth.token_refresh` | `RefreshTokenPair` |
| `auth.logout` | `RevokeSession` |

### 11.3. Métricas (OpenTelemetry)

El módulo `kosmo.contracts.telemetry` expone el contador `kosmo.auth.events`:

```python
from kosmo.contracts.telemetry import record_auth_event

record_auth_event("login_success", user_id=user.id)
record_auth_event("login_failure")
```

Atributos registrados en el contador:

| `event_type` | Cuándo se emite |
|---|---|
| `register_success` | Usuario creado correctamente. |
| `login_success` | Credenciales válidas en `/authorize`. |
| `login_failure` | Credenciales inválidas en `/authorize`. |
| `token_refresh` | Par de tokens rotado correctamente. |
| `logout` | Sesión revocada. |

### 11.4. Backend en producción: Logfire

Si `LOGFIRE_TOKEN` tiene valor, el stack llama a `logfire.configure(...)` en lugar de los exportadores de consola. Las trazas y métricas se envían a Logfire; los logs de structlog se siguen escribiendo por stdout (Logfire los recoge si el colector está configurado).

Si `LOGFIRE_TOKEN` está vacío (valor por defecto en `.env.example`), las trazas se imprimen por stdout con `ConsoleSpanExporter` y las métricas se exportan cada 60 segundos con `ConsoleMetricExporter`. No hay dependencia de ningún servicio externo para desarrollo local.

### 11.5. Variables de entorno

| Variable | Defecto | Descripción |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Nivel mínimo de logging. `DEBUG` activa el renderer con colores. |
| `LOGFIRE_TOKEN` | _(vacío)_ | Token del proyecto Logfire. Vacío → exportadores de consola. |
| `OTEL_SERVICE_NAME` | `kosmo-backend` | Valor de `service.name` en los recursos OTel. |
| `OTEL_ENVIRONMENT` | `development` | Valor de `deployment.environment` en los recursos OTel. |

---

## 12. Sistema de IDs y Slugs

### 12.1. IDs con prefijo tipado (ULID)

Todos los identificadores usan **ULID** (26 caracteres Base32 Crockford, ordenables por timestamp) con prefijo semántico:

| Prefijo | Entidad | Ejemplo |
|---|---|---|
| `prj_` | Proyecto | `prj_01KT07HCKMM07BD30NP1PQBERD` |
| `feat_` | Feature / Característica | `feat_01KT0CDV846118TW28496YAX0K` |
| `spec_` | Spec / Especificación | `spec_01KT06W284WGSG7HBDBFW39K3W` |
| `usr_` | Usuario | `usr_01KT05JRA7466PPYQXYTXXBMN4` |
| `tsk_` | Tarea | `tsk_01KT08ABC0...` |
| `apk_` | API Key | `apk_01KT05JRA7...` |
| `aud_` | Auditoría | `aud_01KT05JRA7...` |

Propiedades del ULID:
- **Ordenable** por timestamp (milisegundos desde epoch)
- **26 caracteres** sin guiones ni caracteres ambiguos (I, L, O, U excluidos)
- **Timestamp extraíble** → `IdGenerator.extract_timestamp(id)` devuelve la fecha de creación
- Generado por `IdGenerator.generate("entity")` desde `kosmo.domain.sdd.id_generator`

### 12.2. Slugs (URLs amigables)

Proyectos y features generan automáticamente un **slug legible** desde su nombre. El slug usa `slugify_spanish()` que:

1. Normaliza tildes y diéresis (NFKD) → `gestión` → `gestion`
2. Preserva la ñ → `diseño` → `diseno`
3. Reemplaza espacios y puntuación por guiones
4. **Nunca corta palabras** → truncado en el último guion antes del límite
5. Límite: **80 chars** para proyectos, **60 chars** para features

| Entidad | Slug | Ejemplo de URL |
|---|---|---|
| Proyecto | `sistema-gestion-inventario` | `/api/v1/projects/sistema-gestion-inventario` |
| Feature | `alertas-stock-bajo` | `/api/v1/projects/sistema-gestion/features/alertas-stock-bajo` |

### 12.3. Resolución dual (ID o slug)

**Toda ruta** que contenga `{project_id}` o `{feature_identifier}` acepta **ambos formatos**:

```
/api/v1/projects/sistema-gestion-inventario                  ← slug
/api/v1/projects/prj_01KT07HCKMM...                           ← ID (prefijo prj_)

/api/v1/projects/mi-proyecto/features/alertas-stock           ← ambos slugs
/api/v1/projects/prj_.../features/feat_...                    ← ambos IDs
/api/v1/projects/prj_.../features/alertas-stock               ← mixto: ID + slug
```

**Excepción:** Las rutas standalone (`/features/{feature_id}/...`) solo aceptan ID porque no tienen contexto de proyecto para resolver slugs. Son llamadas internas de API — el usuario final nunca las ve en la URL del navegador.

### 12.4. Colisiones de slug

Si dos entidades generan el mismo slug, se agrega sufijo numérico:

```
"Gestión de inventario" → gestion-de-inventario
"Gestión de inventario" (segunda) → gestion-de-inventario-2
"Gestión de inventario" (tercera) → gestion-de-inventario-3
```

En features, la unicidad del slug es **dentro del mismo proyecto** (`get_by_slug(project_id, slug)`). Dos proyectos distintos pueden tener features con el mismo slug sin conflicto.

---

## 13. Referencia Completa de Endpoints

> **Notación:** `{project_id}` acepta ID (`prj_...`) o slug. `{feature_identifier}` acepta ID (`feat_...`) o slug. `{id}` solo acepta ID.

### 13.1. Auth

| Método | Ruta | Auth | Rate Limit | Descripción |
|---|---|---|---|---|
| `POST` | `/api/v1/auth/register` | — | 3/min | Registra usuario. Retorna `{ id, email, created_at }`. |
| `POST` | `/api/v1/auth/authorize` | — | 10/min | Valida credenciales + PKCE S256. Retorna `authorization_code`. |
| `POST` | `/api/v1/auth/token` | — | 5/min | Intercambia `code` + `code_verifier` por JWT pair. |
| `POST` | `/api/v1/auth/refresh` | Refresh token | 30/min | Rota el par. Refresh anterior invalidado. |
| `GET` | `/api/v1/auth/me` | Bearer | — | Retorna `Principal { subject, scopes }`. |
| `POST` | `/api/v1/auth/logout` | Bearer | 20/min | Revoca access + refresh. |

### 13.2. Proyectos

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v1/projects` | Crea proyecto. Genera slug desde `name`. Fase inicial: `descubrimiento`. |
| `GET` | `/api/v1/projects` | Lista todos los proyectos con `id`, `name`, `slug`, `phase`, `status`. |
| `GET` | `/api/v1/projects/{project_id}` | Obtiene proyecto por ID o slug. |

### 13.3. Discovery

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v1/projects/{project_id}/discovery/generate` | IA genera documento de discovery (9 secciones). Retorna `{ document, sections, updated_at }`. |
| `GET` | `/api/v1/projects/{project_id}/discovery` | Obtiene documento actual + índice de navegación. |
| `PUT` | `/api/v1/projects/{project_id}/discovery` | Guarda edición manual. Body: `{ document: { type: "doc", content: [...] } }`. 422 si estructura inválida. |
| `POST` | `/api/v1/projects/{project_id}/discovery/regenerate` | IA reescribe el documento desde el contenido actual + contexto del proyecto. |

### 13.4. Features

| Método | Ruta | Slug? | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/projects/{project_id}/features` | ✅ | Lista features del proyecto. |
| `POST` | `/api/v1/projects/{project_id}/features` | ✅ | Crea feature manual (slug desde título). Estado: `borrador`. |
| `POST` | `/api/v1/projects/{project_id}/features/generate` | ✅ | **IA genera y persiste 5 features.** |
| `POST` | `/api/v1/projects/{project_id}/features/suggest` | ✅ | IA sugiere 3 alternativas. **No persiste.** |
| `POST` | `/api/v1/projects/{project_id}/features/suggest-from-idea` | ✅ | IA formaliza una idea en feature. **No persiste.** |
| `DELETE` | `/api/v1/projects/{project_id}/features/{feature_identifier}` | ✅ | Elimina feature (ID o slug). |
| `DELETE` | `/api/v1/features/{id}` | ❌ | Elimina feature (solo ID). |
| `PATCH` | `/api/v1/projects/{project_id}/features/{feature_identifier}/status` | ✅ | Alterna Borrador ↔ Aprobada. |
| `PATCH` | `/api/v1/features/{id}/status` | ❌ | Alterna Borrador ↔ Aprobada (solo ID). |
| `POST` | `/api/v1/projects/{project_id}/features/{feature_identifier}/improve` | ✅ | IA mejora descripción. Solo Borrador (409 si Aprobada). |
| `POST` | `/api/v1/features/{id}/improve` | ❌ | IA mejora descripción (solo ID). |
| `POST` | `/api/v1/projects/{project_id}/features/{feature_identifier}/apply-improvement` | ✅ | Aplica mejora sugerida. Solo Borrador. |
| `POST` | `/api/v1/features/{id}/apply-improvement` | ❌ | Aplica mejora sugerida (solo ID). |

### 13.5. Requisitos

| Método | Ruta | Slug? | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/projects/{project_id}/features/{feature_identifier}/requirements` | ✅ | Obtiene documento de requisitos + índice + header. |
| `GET` | `/api/v1/features/{id}/requirements` | ❌ | Obtiene documento (solo ID). |
| `PUT` | `/api/v1/projects/{project_id}/features/{feature_identifier}/requirements` | ✅ | Guarda edición manual de requisitos. |
| `PUT` | `/api/v1/features/{id}/requirements` | ❌ | Guarda edición manual (solo ID). |
| `POST` | `/api/v1/projects/{project_id}/features/{feature_identifier}/requirements/generate` | ✅ | IA genera requisitos EARS. Feature debe estar Aprobada (409 si Borrador). |
| `POST` | `/api/v1/features/{id}/requirements/generate` | ❌ | IA genera requisitos (solo ID). |
| `POST` | `/api/v1/projects/{project_id}/features/{feature_identifier}/requirements/regenerate` | ✅ | IA reescribe todos los requisitos. |
| `POST` | `/api/v1/features/{id}/requirements/regenerate` | ❌ | IA reescribe requisitos (solo ID). |

### 13.6. SDD Pipeline (Specs)

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v1/projects/{project_id}/specs` | Crea spec desde RawIdea. `{project_id}` acepta slug. |
| `POST` | `/api/v1/specs/{spec_id}/advance/requirements` | Avanza a fase Requirements (EARS). |
| `POST` | `/api/v1/specs/{spec_id}/advance/design` | Avanza a fase Design (UML). |
| `POST` | `/api/v1/specs/{spec_id}/advance/tasks` | Avanza a fase Tasks. |
| `GET` | `/api/v1/specs/{spec_id}` | Obtiene spec completo. |
| `POST` | `/api/v1/specs/{spec_id}/canvas` | Sincroniza canvas de diseño. |

### 13.7. Utilidades

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Health check. |
| `GET` | `/api/v1/schemas` | Lista DTOs disponibles. |
| `GET` | `/api/v1/schemas/{name}` | JSON Schema del DTO. |
| `GET` | `/api/v1/openapi.json` | Especificación OpenAPI completa. |

---

## 14. SDD — Documentos Enriquecidos

### 14.1. Formato del documento

El backend persiste documentos como **árbol JSON tipado** compatible con editores WYSIWYG (ProseMirror, TipTap, Milkdown). Cada nodo tiene `type`, `attrs`, `content`, `marks` y `text`.

```json
{
  "type": "doc",
  "content": [
    {
      "type": "heading",
      "attrs": { "level": 2, "id": "vision-del-producto" },
      "content": [{ "type": "text", "text": "Visión del producto" }]
    },
    {
      "type": "paragraph",
      "content": [
        { "type": "text", "text": "Una plataforma " },
        { "type": "text", "marks": [{ "type": "bold" }], "text": "web" },
        { "type": "text", "text": " de gestión." }
      ]
    }
  ]
}
```

**Tipos de nodo:** `heading`, `paragraph`, `bulletList`, `orderedList`, `listItem`, `blockquote`, `codeBlock`, `horizontalRule`, `hardBreak`, `text`.

**Marcas inline:** `bold`, `italic`, `strike`, `code`, `link`.

### 14.2. Índice de navegación

```json
{
  "sections": [
    {
      "title": "Visión del producto",
      "anchor": "vision-del-producto",
      "level": 2,
      "children": [
        { "title": "Detalle", "anchor": "detalle", "level": 3, "children": [] }
      ]
    }
  ]
}
```

Anclas generadas con `slugify_spanish()` (NFKD, sin diacríticos, preserva ñ).

### 14.3. Undo/Redo

El editor maneja deshacer/rehacer **localmente en memoria** (stack de steps de ProseMirror). El backend recibe snapshots completos en `[Guardar]`.

---

## 15. Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `pydantic_core._pydantic_core.ValidationError` al arrancar | Falta una variable obligatoria en `.env` | Revisa `.env` contra `kosmo/config.py` |
| `connection refused` a Postgres/Mongo/Redis | Contenedores no levantados | `docker ps` y vuelve al paso 4 |
| `ModuleNotFoundError: kosmo` | Ejecutaste fuera del venv | Usa `uv run <comando>` o activa `.venv` |
| `alembic: command not found` | Dependencias dev no instaladas | `uv sync --all-groups` |
| `FileNotFoundError: .secrets/jwt_*.pem` al arrancar | Claves JWT no generadas | Ejecuta el paso 5.1 |
| `401 Token revoked` tras reiniciar Redis | Allowlist y denylist son volátiles; tokens emitidos antes ya no se reconocen | Repite el flujo desde `/api/v1/auth/authorize` |
