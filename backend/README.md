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

## 10. Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `pydantic_core._pydantic_core.ValidationError` al arrancar | Falta una variable obligatoria en `.env` | Revisa `.env` contra `kosmo/config.py` |
| `connection refused` a Postgres/Mongo/Redis | Contenedores no levantados | `docker ps` y vuelve al paso 4 |
| `ModuleNotFoundError: kosmo` | Ejecutaste fuera del venv | Usa `uv run <comando>` o activa `.venv` |
| `alembic: command not found` | Dependencias dev no instaladas | `uv sync --all-groups` |
