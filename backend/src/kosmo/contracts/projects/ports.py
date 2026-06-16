from typing import Protocol

from kosmo.contracts.projects.ids import ProjectId, UserId
from kosmo.contracts.projects.project import Proyecto


class ProyectoRepository(Protocol):
    async def save(self, project: Proyecto) -> Proyecto: ...

    async def get_by_id(self, project_id: ProjectId) -> Proyecto | None: ...

    async def get_by_slug(self, slug: str) -> Proyecto | None: ...

    async def list_by_owner(self, owner_id: UserId) -> list[Proyecto]: ...
