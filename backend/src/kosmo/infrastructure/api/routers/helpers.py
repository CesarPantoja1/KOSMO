from __future__ import annotations

from fastapi import Request

from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.project import Project
from kosmo.contracts.sdd.repositories import ProjectRepository


async def resolve_project(
    request: Request,
    id_or_slug: str,
) -> Project:
    repo: ProjectRepository = request.app.state.pipeline_components.project_repo

    if id_or_slug.startswith("prj_"):
        project = await repo.by_id(ProjectId(id_or_slug))
    else:
        project = await repo.find_by_slug(id_or_slug)

    if project is None:
        raise ProjectNotFoundError(
            project_id=id_or_slug,
            instance=f"/api/v1/projects/{id_or_slug}",
        )

    return project
