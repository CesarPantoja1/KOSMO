from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from kosmo.contracts.sdd.ids import UserId


class IntegrationProvider(StrEnum):
    """Proveedores de servicios externos soportados por KOSMO."""

    GITHUB = "github"
    RAILWAY = "railway"


@dataclass(frozen=True, slots=True)
class UserIntegration:
    """Credenciales cifradas y metadatos de integración de un usuario con una plataforma externa."""

    user_id: UserId
    provider: IntegrationProvider
    encrypted_access_token: str
    account_name: str | None = None
    encrypted_refresh_token: str | None = None
    scopes: list[str] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class UserIntegrationRepository(Protocol):
    """Puerto de persistencia para credenciales de integración de usuario."""

    async def get_by_user_and_provider(self, user_id: UserId, provider: IntegrationProvider) -> UserIntegration | None:
        """Obtiene la integración de un usuario con un proveedor específico."""
        ...

    async def save(self, integration: UserIntegration) -> UserIntegration:
        """Almacena o actualiza la integración del usuario."""
        ...

    async def delete(self, user_id: UserId, provider: IntegrationProvider) -> bool:
        """Elimina las credenciales de integración del usuario para el proveedor indicado."""
        ...

    async def list_by_user(self, user_id: UserId) -> list[UserIntegration]:
        """Lista todas las integraciones registradas para el usuario."""
        ...
