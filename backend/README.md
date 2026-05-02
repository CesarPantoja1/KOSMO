# KOSMO — Backend

API del proyecto KOSMO construida con **FastAPI** sobre Python 3.13, arquitectura hexagonal por capas (`infrastructure → application → domain → contracts`) y `uv` como gestor de dependencias.

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
├── src/kosmo/
│   ├── infrastructure/               # Adaptadores: FastAPI, persistencia, LLM, seguridad, telemetría
│   │   ├── api/
│   │   │   ├── main.py               # Punto de entrada de la app
│   │   │   ├── schemas.py            # DTOs Pydantic expuestos por la API HTTP
│   │   │   ├── composition.py        # Composition root (wiring de puertos y adaptadores)
│   │   │   ├── dependencies/         # FastAPI Depends (auth, scopes)
│   │   │   ├── middlewares/          # Middlewares HTTP (request logging, trace context)
│   │   │   └── routers/              # Endpoints REST
│   │   ├── persistence/              # Postgres (SQLAlchemy), Redis (token store, authcode store)
│   │   ├── security/                 # Argon2id, JOSE/JWT, Fernet
│   │   └── telemetry/                # Bootstrap de structlog + Logfire/OpenTelemetry
│   ├── application/                  # Casos de uso (orquestación) — depende de contracts y domain
│   │   └── auth/                     # Register, Authorize, Exchange, Issue/Verify/Refresh/Revoke
│   ├── domain/                       # Algoritmos de dominio puro
│   │   └── auth/pkce.py              # s256_challenge, verify_s256 (RFC 7636)
│   ├── contracts/                    # Kernel: entidades, errores, puertos, telemetría
│   │   ├── auth/                     # User, Principal, Token*, AuthorizationCode, errors, ports
│   │   └── telemetry.py              # Decorador @traced y record_auth_event (no-op si no hay infra)
│   └── config.py                     # Carga de Settings desde .env
├── tests/
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
| `AuthorizeWithPkce` | `application/auth/authorize.py` | Valida credenciales y emite un código de autorización ligado al `code_challenge`. |
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

| Clave | Significado |
|---|---|
| `auth:refresh:{jti}` | Refresh token vigente. Se borra al usarse o al hacer logout. Si no existe, el refresh es rechazado (defensa contra replay). |
| `auth:revoked:{jti}` | Access token revocado antes de su `exp`. `get_principal` lo consulta en cada request. |
| `auth:family:{family_id}` | Familia de sesión activa. Al detectar reuso de refresh, se revoca la familia completa. |

La rotación de refresh (lectura + borrado del JTI viejo) se ejecuta en una transacción Redis (`MULTI/EXEC`) para evitar carreras entre clientes concurrentes.

### 10.5. Endpoints

| Método | Ruta | Auth requerida | Descripción |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | — | Registra un usuario nuevo. Devuelve `UserPublic`. |
| `POST` | `/api/v1/auth/authorize` | — | Valida credenciales + `code_challenge`. Devuelve `authorization_code`. |
| `POST` | `/api/v1/auth/token` | — | Intercambia `code` + `code_verifier` por un par de tokens. |
| `POST` | `/api/v1/auth/refresh` | Refresh token en el body | Rota el par. El refresh anterior queda invalidado. |
| `GET`  | `/api/v1/auth/me` | Bearer access | Devuelve el `Principal` autenticado (`subject`, `scopes`). |
| `POST` | `/api/v1/auth/logout` | Bearer access | Revoca el access y, si se envía, también el refresh. |

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

### 10.9. Pruebas

```bash
uv run pytest tests/unit/test_auth_use_cases.py tests/integration/test_auth_router.py
```

Los tests usan un store en memoria que implementa el mismo puerto que el adaptador de Redis, así que no requieren contenedores levantados.

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

## 12. Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `pydantic_core._pydantic_core.ValidationError` al arrancar | Falta una variable obligatoria en `.env` | Revisa `.env` contra `kosmo/config.py` |
| `connection refused` a Postgres/Mongo/Redis | Contenedores no levantados | `docker ps` y vuelve al paso 4 |
| `ModuleNotFoundError: kosmo` | Ejecutaste fuera del venv | Usa `uv run <comando>` o activa `.venv` |
| `alembic: command not found` | Dependencias dev no instaladas | `uv sync --all-groups` |
| `FileNotFoundError: .secrets/jwt_*.pem` al arrancar | Claves JWT no generadas | Ejecuta el paso 5.1 |
| `401 Token revoked` tras reiniciar Redis | Allowlist y denylist son volátiles; tokens emitidos antes ya no se reconocen | Repite el flujo desde `/api/v1/auth/authorize` |
