# Exposición DevOps — Estado actual de CI/CD y Docker en KOSMO

## 1. ¿Qué se está explicando aquí?

Este documento resume, de forma **explicativa y orientada a exposición**, qué hace actualmente el componente DevOps del proyecto KOSMO en tres frentes:

1. Pipeline de **CI/CD** (GitHub Actions).
2. Rol de **Docker Desktop** en desarrollo local.
3. Función de los **Dockerfiles** y `docker-compose.yml`.

> Enfoque: “lo que existe y funciona hasta ahora”, no una versión futura ideal.

---

## 2. Pipeline CI/CD: ¿qué hace hoy exactamente?

En el repositorio hay dos workflows:

- `/.github/workflows/ci.yml`
- `/.github/workflows/cd.yml`

### 2.1 CI (`ci.yml`) — Integración continua real

Este pipeline **sí está implementado** y se ejecuta cuando hay:

- `push` a `main` o `develop`
- `pull_request` hacia `main` o `develop`

Tiene dos jobs paralelos:

#### A) Job `backend`

Objetivo: validar calidad y pruebas del backend en Python.

Pasos:

1. `actions/checkout@v4` → descarga el código.
2. `actions/setup-python@v5` con Python `3.13`.
3. `astral-sh/setup-uv@v6` → prepara `uv`.
4. `uv sync --all-groups` → instala dependencias.
5. `uv run ruff check src tests` → linting.
6. `uv run pyright` → tipado estático.
7. `uv run pytest tests/unit --cov=kosmo --cov-fail-under=0` → pruebas unitarias.

Además, inyecta variables de entorno mínimas (modo `development`) para que la app no falle al inicializar `Settings` en CI.

#### B) Job `frontend`

Objetivo: validar frontend con el stack real del proyecto (**Bun**).

Pasos:

1. `actions/checkout@v4`
2. `oven-sh/setup-bun@v2` con Bun `1.2.10`
3. `bun install --frozen-lockfile`
4. `bun run lint`
5. `bun run test -- --run --passWithNoTests`

Resultado esperado de CI: si un lint, type-check o test falla, el pipeline falla y el cambio no queda “verde”.

---

### 2.2 CD (`cd.yml`) — Despliegue continuo aún en fase base

Este pipeline se dispara en `push` a `main`, pero **todavía no despliega**.

Hoy solo hace:

1. Checkout de repositorio.
2. Un paso placeholder:
   - `echo "CD pipeline initialized successfully."`

Conclusión honesta para exposición:

- **CI está operativo y útil**.
- **CD aún es plantilla** y queda como siguiente etapa del componente DevOps.

---

## 3. Docker Desktop: ¿qué papel cumple en este proyecto?

Docker Desktop se usa como la plataforma local para:

1. Construir imágenes (`docker compose build ...`).
2. Levantar contenedores (`docker compose up --build`).
3. Ver logs y estado de servicios.
4. Tener un entorno reproducible entre miembros del equipo.

En la práctica del proyecto, Docker Desktop permitió detectar y resolver problemas típicos de integración:

- rutas de entrypoint incorrectas,
- variables de entorno faltantes,
- diferencias entre `npm` y `bun`,
- dependencias no resueltas por volumen montado.

Es decir, Docker Desktop no solo “ejecuta contenedores”; también funciona como herramienta de verificación de integración local antes de subir cambios.

---

## 4. ¿Qué hace cada Dockerfile?

## 4.1 `backend/Dockerfile`

Propósito: empaquetar la API FastAPI para desarrollo local.

Flujo del archivo:

1. `FROM python:3.13-slim` → imagen base ligera.
2. Variables:
   - `PYTHONDONTWRITEBYTECODE=1`
   - `PYTHONUNBUFFERED=1`
3. `WORKDIR /app`
4. `pip install uv`
5. Copia metadata y código (`pyproject.toml`, `uv.lock`, `src/`).
6. `uv pip install --system -e .` (instalación editable del paquete).
7. Expone puerto `8000`.
8. Arranca con:
   - `python -m uvicorn kosmo.adapters.api.main:app --host 0.0.0.0 --port 8000 --reload`

Interpretación para exposición: este Dockerfile deja al backend listo para desarrollo con recarga y con el módulo correcto de entrada.

---

## 4.2 `frontend/Dockerfile`

Propósito: empaquetar la app Next.js usando Bun.

Flujo del archivo:

1. `FROM oven/bun:1.2.10-alpine`
2. `WORKDIR /app`
3. Copia `package.json` y `bun.lock`
4. `bun install --frozen-lockfile`
5. Copia el resto del proyecto
6. Expone puerto `3000`
7. Ejecuta `bun run dev`

Interpretación para exposición: alinea contenedor con el gestor real del proyecto (`bun`) y evita mezclar toolchains.

---

## 5. ¿Qué hace `docker-compose.yml` en el día a día?

`docker-compose.yml` orquesta ambos servicios:

- `frontend` en puerto `3000`
- `backend` en puerto `8000`

### Aspectos clave configurados

1. **Build por contexto**
   - frontend: `./frontend`
   - backend: `./backend`

2. **Montaje de volúmenes para desarrollo**
   - `./frontend:/app`
   - `./backend:/app`

3. **Comando frontend reforzado**
   - `sh -c "bun install --frozen-lockfile; bun run dev"`
   - Esto asegura dependencias presentes incluso con bind mount.

4. **Variables obligatorias del backend**
   - `ENV`, `DATABASE_URL`, `MONGO_URL`, `REDIS_URL`, etc.
   - Evita el fallo de validación de `pydantic-settings` al iniciar.

5. **Dependencia lógica**
   - `frontend` depende de `backend`.

---

## 6. Flujo completo actual (resumen para defender en clase)

1. El desarrollador ejecuta localmente:
   - `docker compose up --build`
2. Docker Desktop construye imágenes y levanta servicios.
3. Se valida que frontend y backend arranquen en `3000` y `8000`.
4. Al subir cambios, GitHub Actions corre CI:
   - backend: lint + tipado + tests
   - frontend: lint + tests con Bun
5. Si todo pasa, el cambio queda integrado con calidad mínima.
6. CD existe como base, pero aún no despliega a un entorno.

---

## 7. Estado actual del componente DevOps (mensaje final)

- **CI:** implementada y funcional.
- **CD:** declarada, aún en modo placeholder.
- **Docker Desktop:** herramienta principal para integración local reproducible.
- **Dockerfiles:** definidos para backend y frontend, alineados al stack real.
- **Compose:** operativo para levantar ambos servicios con configuración coherente.

En términos de la TIC, el componente ya cubre integración continua y estandarización del entorno; el siguiente salto natural es completar despliegue continuo real en `cd.yml`.
