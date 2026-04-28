# syntax=docker/dockerfile:1.7
# ============================================================================
# KOSMO backend — Dockerfile multi-stage con uv
# ----------------------------------------------------------------------------
# - builder : resuelve y compila dependencias en /opt/venv 
# - runtime : python:3.13-slim minimalista, usuario non-root, libs solo runtime
# ============================================================================

ARG PYTHON_VERSION=3.13

# ---------------------------------------------------------------------------
# Stage 1: builder
# ---------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Toolchain de compilación + headers de libpq para wheels que falten en manylinux
# (asyncpg, hiredis, argon2-cffi, cryptography traen wheels)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
        libffi-dev \
        curl \
 && rm -rf /var/lib/apt/lists/*

# 1) Instalar SOLO dependencias (sin proyecto) para maximizar cache hits
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# 2) Copiar el código y construir el proyecto (uv_build backend)
COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Limpieza extra: borrar pyc duplicados en .pyc.opt y bytecode tests
RUN find /opt/venv -depth -type d -name '__pycache__' -prune -exec rm -rf {} + \
 && find /opt/venv -depth -type d -name 'tests' -prune -exec rm -rf {} +


# ---------------------------------------------------------------------------
# Stage 2: runtime
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Solo libs de RUNTIME
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libpq5 \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1000 kosmo \
 && useradd --system --uid 1000 --gid kosmo --home /app --shell /usr/sbin/nologin kosmo

WORKDIR /app

# Copiar venv ya construido
COPY --from=builder --chown=kosmo:kosmo /opt/venv /opt/venv

# Copiar artefactos mínimos del proyecto necesarios en runtime
COPY --chown=kosmo:kosmo alembic.ini ./alembic.ini
COPY --chown=kosmo:kosmo alembic ./alembic
COPY --chown=kosmo:kosmo src ./src
COPY --chown=kosmo:kosmo entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

USER kosmo:kosmo

EXPOSE 8000

# Healthcheck usando stdlib contra /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; r=urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3); sys.exit(0 if r.status==200 else 1)" || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "kosmo.infrastructure.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
