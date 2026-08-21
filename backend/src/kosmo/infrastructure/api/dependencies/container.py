from __future__ import annotations

from typing import cast

from fastapi import Request

from kosmo.infrastructure.api.composition import AppContainer


def get_container(request: Request) -> AppContainer:
    """Recupera el contenedor tipado de dependencias del estado de la app."""
    return cast(AppContainer, request.app.state.container)
