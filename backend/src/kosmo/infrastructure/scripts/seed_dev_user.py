"""Seed user de desarrollo para pruebas manuales.

Uso:
    .venv/Scripts/python.exe -m kosmo.infrastructure.scripts.seed_dev_user

Variables de entorno opcionales:
    SEED_EMAIL     (default: dev@kosmo.local)
    SEED_PASSWORD  (default: dev-password-12345)
"""

import asyncio
import os
import sys

from kosmo.config import settings
from kosmo.contracts.auth import UserAlreadyExistsError
from kosmo.infrastructure.api.composition import build_app_components

DEFAULT_EMAIL = "dev@kosmo.dev"
DEFAULT_PASSWORD = "dev-password-12345"


async def _run() -> int:
    email = os.getenv("SEED_EMAIL", DEFAULT_EMAIL).strip().lower()
    password = os.getenv("SEED_PASSWORD", DEFAULT_PASSWORD)

    components = build_app_components(settings)
    try:
        auth = components.auth
        if auth is None:
            print("[seed] error: AUTH_DISABLED=true, no se puede crear el usuario")  # noqa: T201
            return 1

        register = auth.register_user
        repo = auth.user_repository

        try:
            user = await register.execute(name="Usuario Dev", email=email, password=password)
            status = "created"
        except UserAlreadyExistsError:
            existing = await repo.by_email(email)
            assert existing is not None
            user = existing
            status = "already-exists"

        print(f"[seed] status={status}")  # noqa: T201
        print(f"[seed] id={user.id}")  # noqa: T201
        print(f"[seed] email={user.email}")  # noqa: T201
        print(f"[seed] password={password}")  # noqa: T201
        return 0
    finally:
        await components.close()


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
