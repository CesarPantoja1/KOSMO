from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from ulid import ULID

from kosmo.contracts.sdd.ids import ProjectId, UserId


class CodeSyncStatus(enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class UserGitHubIntegration:
    """Configuración de integración con GitHub a nivel de usuario."""

    user_id: UserId
    github_username: str
    encrypted_token: str
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ProjectGitHubIntegration:
    """Vínculo de un proyecto de KOSMO con un repositorio remoto en GitHub."""

    project_id: ProjectId
    repo_url: str
    default_branch: str = "main"
    last_synced_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CodeSyncLog:
    """Registro de auditoría de cada intento de subida de código."""

    id: ULID = field(default_factory=ULID)
    project_id: ProjectId = field(default_factory=lambda: ProjectId(""))
    commit_sha: str | None = None
    status: CodeSyncStatus = CodeSyncStatus.FAILED
    message: str | None = None
    synced_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class UserGitHubIntegrationRepository(Protocol):
    async def get_by_user_id(self, user_id: UserId) -> UserGitHubIntegration | None: ...

    async def save(self, integration: UserGitHubIntegration) -> None: ...


class ProjectGitHubIntegrationRepository(Protocol):
    async def get_by_project_id(self, project_id: ProjectId) -> ProjectGitHubIntegration | None: ...

    async def save(self, integration: ProjectGitHubIntegration) -> None: ...


class CodeSyncLogRepository(Protocol):
    async def add_log(self, log: CodeSyncLog) -> None: ...

    async def get_logs_by_project(self, project_id: ProjectId) -> list[CodeSyncLog]: ...
