#!/bin/sh
# =============================================================================
# entrypoint.sh — KOSMO backend
# -----------------------------------------------------------------------------
# 1) (Opcional) Ejecuta alembic upgrade head si RUN_MIGRATIONS=1 (default)
# 2) Hace exec del CMD recibido (uvicorn por defecto)
#
# Uso:
#   RUN_MIGRATIONS=0  -> salta migraciones (útil para workers / tests)
# =============================================================================
set -eu

log() { printf '[entrypoint] %s\n' "$*"; }

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    log "Aplicando migraciones Alembic (alembic upgrade head)..."
    if ! alembic upgrade head; then
        log "ERROR: alembic upgrade head falló."
        exit 1
    fi
    log "Migraciones aplicadas correctamente."
else
    log "RUN_MIGRATIONS=0 — saltando migraciones."
fi

log "Iniciando proceso principal: $*"
exec "$@"
