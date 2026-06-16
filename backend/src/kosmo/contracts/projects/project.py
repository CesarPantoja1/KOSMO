from typing import Protocol

from kosmo.contracts.projects.ids import ProjectId, UserId


class Proyecto(Protocol):
    id: ProjectId
    slug: str
    owner_id: UserId
