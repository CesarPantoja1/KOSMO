from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from kosmo.contracts.sdd.project import Project

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    description: str
    owner_id: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    owner_id: str
    current_phase: str
    status: str
    created_at: str
    updated_at: str


def _project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        slug=project.slug,
        description=project.description,
        owner_id=str(project.owner_id),
        current_phase=project.current_phase.value,
        status=project.status.value,
        created_at=project.created_at.isoformat().replace("+00:00", "Z"),
        updated_at=project.updated_at.isoformat().replace("+00:00", "Z"),
    )


@router.post("", status_code=201)
async def create_project(body: CreateProjectRequest, request: Request) -> ProjectResponse:
    uc = request.app.state.pipeline_components.create_project_uc
    project = await uc.execute(
        name=body.name,
        description=body.description,
        owner_id=body.owner_id,
    )
    return _project_to_response(project)


@router.get("")
async def list_projects(owner_id: str, request: Request) -> list[ProjectResponse]:
    uc = request.app.state.pipeline_components.list_projects_uc
    projects = await uc.execute(owner_id=owner_id)
    return [_project_to_response(p) for p in projects]


@router.get("/{project_id}")
async def get_project(project_id: str, request: Request) -> ProjectResponse:
    from kosmo.infrastructure.api.routers.helpers import resolve_project

    project = await resolve_project(request, project_id)
    return _project_to_response(project)
