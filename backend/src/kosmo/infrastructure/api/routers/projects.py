from fastapi import APIRouter, HTTPException, Request, status

from kosmo.application.projects.create_project import CreateProjectUseCase
from kosmo.application.projects.get_project import GetProjectUseCase
from kosmo.application.projects.list_projects import ListProjectsUseCase
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.infrastructure.api.schemas_projects import (
    CreateProjectRequest,
    ProjectListItem,
    ProjectResponse,
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
) -> ProjectResponse:
    uc = CreateProjectUseCase(project_repo=request.app.state.project_repo)
    project = await uc.execute(name=payload.name, description=payload.description)
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
) -> ProjectResponse:
    project_repo: ProjectRepository = request.app.state.project_repo
    project_id = await _resolve_project_identifier(project_repo, identifier)

    try:
        project = await GetProjectUseCase(project_repo=project_repo).execute(project_id)
    except ProjectNotFoundError as exc:
        if not identifier.startswith("prj_"):
            msg = f"Proyecto '{identifier}' no encontrado"
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=404, detail=str(exc)) from exc

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
