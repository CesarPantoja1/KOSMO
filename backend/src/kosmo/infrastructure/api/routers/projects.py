from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from kosmo.application.projects.create_project import CreateProjectUseCase
from kosmo.application.projects.get_project import GetProjectUseCase
from kosmo.application.projects.list_projects import ListProjectsUseCase
from kosmo.contracts.auth.principal import Principal
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas_projects import (
    CreateProjectRequest,
    ProjectListItem,
    ProjectResponse,
    ProjectStatusResponse,
)

projects_router = APIRouter(prefix="/api/v1", tags=["projects"])


async def _resolve_project_identifier(
    project_repo: ProjectRepository, identifier: str
) -> ProjectId:
    if identifier.startswith("prj_"):
        return ProjectId(identifier)

    project = await project_repo.get_by_slug(identifier)
    if project is not None:
        return project.id

    return ProjectId(identifier)


@projects_router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    payload: CreateProjectRequest,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> ProjectResponse:
    uc = CreateProjectUseCase(project_repo=request.app.state.project_repo)
    project = await uc.execute(
        name=payload.name, description=payload.description, created_by=principal.subject
    )
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        current_phase=project.current_phase.value,
        status=project.status.value,
        last_activity_at=project.last_activity_at,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@projects_router.get(
    "/projects",
    response_model=list[ProjectListItem],
)
async def list_projects(
    request: Request,
    _principal: Annotated[Principal, Depends(get_principal)],
) -> list[ProjectListItem]:
    uc = ListProjectsUseCase(project_repo=request.app.state.project_repo)
    projects = await uc.execute()
    return [
        ProjectListItem(
            id=p.id,
            name=p.name,
            slug=p.slug,
            description=p.description,
            current_phase=p.current_phase.value,
            status=p.status.value,
            last_activity_at=p.last_activity_at,
        )
        for p in projects
    ]


@projects_router.get(
    "/projects/{identifier}",
    response_model=ProjectResponse,
)
async def get_project(
    identifier: str,
    request: Request,
    _principal: Annotated[Principal, Depends(get_principal)],
) -> ProjectResponse:
    project_repo: ProjectRepository = request.app.state.project_repo
    project_id = await _resolve_project_identifier(project_repo, identifier)

    project = await GetProjectUseCase(project_repo=project_repo).execute(project_id)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        current_phase=project.current_phase.value,
        status=project.status.value,
        last_activity_at=project.last_activity_at,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@projects_router.get(
    "/projects/{identifier}/status",
    response_model=ProjectStatusResponse,
)
async def get_project_status(
    identifier: str,
    request: Request,
    _principal: Annotated[Principal, Depends(get_principal)],
) -> ProjectStatusResponse:
    from datetime import UTC, datetime

    project_repo: ProjectRepository = request.app.state.project_repo
    project_id = await _resolve_project_identifier(project_repo, identifier)

    project = await GetProjectUseCase(project_repo=project_repo).execute(project_id)

    features = await request.app.state.feature_repo.get_by_project(project_id)
    requirements_count = 0
    for f in features:
        if f.requirements:
            requirements_count += f.requirements.total

    now = datetime.now(UTC)
    delta = now - project.last_activity_at
    if delta.total_seconds() < 3600:
        minutes = max(1, int(delta.total_seconds() // 60))
        relative = f"Hace {minutes} minutos"
    elif delta.total_seconds() < 86400:
        hours = int(delta.total_seconds() // 3600)
        relative = f"Hace {hours} horas"
    else:
        days = int(delta.total_seconds() // 86400)
        relative = f"Hace {days} dias"

    return ProjectStatusResponse(
        project_id=str(project_id),
        current_phase=project.current_phase.value,
        status=project.status.value,
        last_activity_at=project.last_activity_at,
        last_activity_relative=relative,
        features_count=len(features),
        requirements_count=requirements_count,
    )
