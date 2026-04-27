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
# Tests (cobertura mínima 80%)
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
├── alembic/                  # Migraciones de PostgreSQL
├── src/kosmo/
│   ├── infrastructure/       # FastAPI, persistencia, LLM, seguridad, etc.
│   │   └── api/main.py       # Punto de entrada de la app
│   ├── application/          # Casos de uso
│   ├── domain/               # Modelo de dominio puro
│   ├── contracts/            # Contratos compartidos
│   └── config.py             # Carga de Settings desde .env
├── tests/
├── .env.example
├── .importlinter             # Reglas de arquitectura por capas
├── alembic.ini
├── pyproject.toml
└── uv.lock
```

---

## 10. Autenticación JWT

El backend protege rutas mediante JSON Web Tokens firmados con **RS256** (clave asimétrica). El estado de sesión vive en **Redis**: una *allowlist* de refresh tokens y una *denylist* de access tokens revocados. Toda la lógica respeta la arquitectura hexagonal: los puertos viven en `contracts/auth`, los casos de uso en `application/auth`, y los adaptadores de jose y Redis en `infrastructure/`.

### 10.1. Modelo de tokens

| Token | Vida útil por defecto | Uso |
|---|---|---|
| **Access** | 15 minutos | Se envía en `Authorization: Bearer <token>` en cada request a una ruta protegida. |
| **Refresh** | 7 días | Solo se envía a `POST /api/v1/auth/demo/refresh` para obtener un nuevo par. Se rota en cada uso. |

Ambos llevan los claims estándar (`sub`, `iss`, `aud`, `iat`, `exp`, `jti`) más `type` (access/refresh) y `scopes[]`.

### 10.2. Estado en Redis

| Clave | Significado |
|---|---|
| `auth:refresh:{jti}` | Refresh token vigente. Se borra al usarse o al hacer logout. Si no existe, el refresh es rechazado (defensa contra replay). |
| `auth:revoked:{jti}` | Access token revocado antes de su `exp`. `get_principal` lo consulta en cada request. |

La rotación de refresh (lectura + borrado del JTI viejo) se ejecuta en una transacción Redis (`MULTI/EXEC`) para evitar carreras entre clientes concurrentes.

### 10.3. Variables de entorno

Las claves PEM ya se generan en el paso 5.1. El resto tiene valores por defecto y son opcionales en `.env`:

```env
JWT_PRIVATE_KEY_PATH=./.secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=./.secrets/jwt_public.pem
JWT_ALGORITHM=RS256
JWT_ISSUER=kosmo
JWT_AUDIENCE=kosmo-api
JWT_ACCESS_TTL_SECONDS=900
JWT_REFRESH_TTL_SECONDS=604800
```

### 10.4. Proteger una ruta

Importa las dependencias y aplícalas con `Depends`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends

from kosmo.contracts.auth import Principal
from kosmo.infrastructure.api.dependencies.auth import get_principal, require_scopes

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


# Requiere token válido. Inyecta el Principal autenticado.
@router.get("/me")
async def me(principal: Annotated[Principal, Depends(get_principal)]) -> dict[str, str]:
    return {"subject": principal.subject}


# Requiere token válido + scope "projects:write".
@router.post("", dependencies=[Depends(require_scopes("projects:write"))])
async def create_project() -> dict[str, str]:
    return {"status": "created"}
```

Para proteger un router completo de una sola vez:

```python
admin_router = APIRouter(
    prefix="/api/v1/admin",
    dependencies=[Depends(require_scopes("admin"))],
)
```

`get_principal` valida la firma, `iss`, `aud`, `exp`, el tipo de token y la lista de revocación. `require_scopes(*scopes)` añade comprobación de permisos sobre lo que ya hizo `get_principal`.

### 10.5. Endpoints de prueba

Pensados para verificar el flujo de extremo a extremo. **No son el login real**: el endpoint de emisión es público y se reemplazará por un caso de uso que valide credenciales con Argon2.

| Método | Ruta | Auth requerida | Descripción |
|---|---|---|---|
| `POST` | `/api/v1/auth/demo/token` | — | Emite un par para un `subject` y `scopes` arbitrarios. |
| `POST` | `/api/v1/auth/demo/refresh` | Refresh token en el body | Rota el par. El refresh anterior queda invalidado. |
| `GET`  | `/api/v1/auth/demo/me` | Bearer access | Devuelve el `Principal` decodificado. |
| `GET`  | `/api/v1/auth/demo/admin` | Bearer access + scope `admin` | Devuelve 403 si falta el scope. |
| `POST` | `/api/v1/auth/demo/logout` | Bearer access | Revoca el access actual y, si se envía, también el refresh. |

Smoke manual con `curl` (servidor en `:8000`):

```bash
PAIR=$(curl -sX POST http://localhost:8000/api/v1/auth/demo/token \
  -H "Content-Type: application/json" \
  -d '{"subject":"alice","scopes":["read","admin"]}')

ACCESS=$(echo "$PAIR" | python -c "import json,sys;print(json.load(sys.stdin)['access']['token'])")

curl -H "Authorization: Bearer $ACCESS" http://localhost:8000/api/v1/auth/demo/me
```

### 10.6. Códigos de respuesta

| Caso | Status | Cabecera `WWW-Authenticate` |
|---|---|---|
| Falta cabecera `Authorization` | `401` | `Bearer realm="kosmo"` |
| Firma inválida o token mal formado | `401` | `Bearer error="invalid_token"` |
| Token expirado | `401` | `Bearer error="invalid_token"` (`detail: Token expired`) |
| Token revocado | `401` | `Bearer error="invalid_token"` (`detail: Token revoked`) |
| Scope insuficiente | `403` | — |

### 10.7. Pruebas

```bash
uv run pytest tests/unit/test_auth_use_cases.py tests/integration/test_auth_demo_router.py
```

Los tests usan un store en memoria que implementa el mismo puerto que el adaptador de Redis, así que no requieren contenedores levantados.

---

## 11. Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `pydantic_core._pydantic_core.ValidationError` al arrancar | Falta una variable obligatoria en `.env` | Revisa `.env` contra `kosmo/config.py` |
| `connection refused` a Postgres/Mongo/Redis | Contenedores no levantados | `docker ps` y vuelve al paso 4 |
| `ModuleNotFoundError: kosmo` | Ejecutaste fuera del venv | Usa `uv run <comando>` o activa `.venv` |
| `alembic: command not found` | Dependencias dev no instaladas | `uv sync --all-groups` |
| `FileNotFoundError: .secrets/jwt_*.pem` al arrancar | Claves JWT no generadas | Ejecuta el paso 5.1 |
| `401 Token revoked` tras reiniciar Redis | Allowlist y denylist son volátiles; tokens emitidos antes ya no se reconocen | Pide un par nuevo en `/api/v1/auth/demo/token` |
