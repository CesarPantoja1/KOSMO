#!/bin/sh
# KOSMO backend entrypoint.
#
# Local development can set DEV_GENERATE_SECRETS=1 to create an ephemeral
# RS256 key pair inside the container. Production should provide real keys.

set -eu

log() {
    printf '[entrypoint] %s\n' "$*"
}

generate_dev_keys() {
    private_key_path="${JWT_PRIVATE_KEY_PATH:-/tmp/kosmo-secrets/jwt_private.pem}"
    public_key_path="${JWT_PUBLIC_KEY_PATH:-/tmp/kosmo-secrets/jwt_public.pem}"

    if [ -s "$private_key_path" ] && [ -s "$public_key_path" ]; then
        log "JWT development keys already exist."
        return
    fi

    if [ "${DEV_GENERATE_SECRETS:-0}" != "1" ]; then
        log "DEV_GENERATE_SECRETS is disabled; expecting JWT keys to exist."
        return
    fi

    log "Generating local development JWT key pair..."
    mkdir -p "$(dirname "$private_key_path")" "$(dirname "$public_key_path")"

    python - <<'PY'
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

private_key_path = Path(os.environ.get("JWT_PRIVATE_KEY_PATH", "/tmp/kosmo-secrets/jwt_private.pem"))
public_key_path = Path(os.environ.get("JWT_PUBLIC_KEY_PATH", "/tmp/kosmo-secrets/jwt_public.pem"))

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
private_key_path.write_bytes(
    key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
)
public_key_path.write_bytes(
    key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
)
PY

    chmod 600 "$private_key_path"
    chmod 644 "$public_key_path"
    log "JWT development keys generated."
}

generate_dev_keys

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    log "Applying Alembic migrations..."
    alembic upgrade head
    log "Migrations applied."
else
    log "RUN_MIGRATIONS=0; skipping migrations."
fi

log "Starting process: $*"
exec "$@"
