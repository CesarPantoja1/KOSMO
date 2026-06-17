from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from kosmo.contracts.sdd.ids import ProjectId
    from kosmo.contracts.sdd.project import Project


class ProjectRepository(Protocol):
    async def by_id(self, project_id: ProjectId) -> Project | None: ...

    async def by_slug(self, owner_id: str, slug: str) -> Project | None: ...

    async def find_by_slug(self, slug: str) -> Project | None: ...

    async def list_by_owner(self, owner_id: str) -> list[Project]: ...

    async def save(self, project: Project) -> Project: ...
