from __future__ import annotations

import re
import unicodedata
from uuid import uuid4

from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import ProjectRepository

_SLUG_DISALLOWED_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_SLUG_SEPARATOR_RE = re.compile(r"[-\s]+")


def slugify_spanish(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower().strip())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = _SLUG_DISALLOWED_RE.sub("", normalized)
    return _SLUG_SEPARATOR_RE.sub("-", normalized).strip("-")


class CreateProjectUseCase:
    def __init__(self, project_repository: ProjectRepository) -> None:
        self._project_repository = project_repository

    async def execute(self, *, name: str, description: str, owner_id: UserId) -> Project:
        slug = await self._build_unique_slug(name=name, owner_id=owner_id)
        project = Project(
            id=ProjectId(f"prj_{uuid4().hex}"),
            name=name,
            slug=slug,
            description=description,
            owner_id=owner_id,
        )
        return await self._project_repository.save(project)

    async def _build_unique_slug(self, *, name: str, owner_id: UserId) -> str:
        base_slug = slugify_spanish(name) or "proyecto"
        slug = base_slug
        suffix = 2

        while await self._project_repository.by_slug(str(owner_id), slug) is not None:
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        return slug
