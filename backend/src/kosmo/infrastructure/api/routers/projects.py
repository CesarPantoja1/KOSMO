from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from kosmo.application.projects import (
    CreateProjectUseCase,
    GetProjectUseCase,
    ListProjectsUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.errors import ProjectNotFoundError
from kosmo.contracts.sdd.ids import ProjectId, UserId
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas import (
    CreateProjectRequest,
    ProjectResponse,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def _create_project(request: Request) -> CreateProjectUseCase:
    return request.app.state.create_project


def _get_project(request: Request) -> GetProjectUseCase:
    return request.app.state.get_project


def _list_projects(request: Request) -> ListProjectsUseCase:
    return request.app.state.list_projects


@router.post(
    "",
    summary="Crear nuevo proyecto",
    description=(
        "Crea un nuevo proyecto en KOSMO. "
        "El nombre se transforma automáticamente en un slug único para el usuario. "
        "Requiere autenticación mediante Bearer token."
    ),
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "description": "Proyecto creado exitosamente.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token de acceso inválido o ausente.",
        },
    },
)
async def create_project(
    payload: Annotated[CreateProjectRequest, Body(...)],
    principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[CreateProjectUseCase, Depends(_create_project)],
) -> ProjectResponse:
    project = await use_case.execute(
        name=payload.name,
        description=payload.description,
        owner_id=UserId(principal.subject),
    )
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        owner_id=project.owner_id,
        current_phase=project.current_phase.value,
        status=project.status.value,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get(
    "",
    summary="Listar proyectos del usuario",
    description=(
        "Devuelve todos los proyectos del usuario autenticado. "
        "Requiere autenticación mediante Bearer token."
    ),
    response_model=list[ProjectResponse],
    responses={
        status.HTTP_200_OK: {
            "description": "Lista de proyectos del usuario.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token de acceso inválido o ausente.",
        },
    },
)
async def list_projects(
    principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[ListProjectsUseCase, Depends(_list_projects)],
) -> list[ProjectResponse]:
    projects = await use_case.execute(owner_id=UserId(principal.subject))
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            slug=p.slug,
            description=p.description,
            owner_id=p.owner_id,
            current_phase=p.current_phase.value,
            status=p.status.value,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in projects
    ]


@router.get(
    "/{project_id}",
    summary="Obtener proyecto por ID",
    description=(
        "Devuelve los detalles de un proyecto específico por su identificador. "
        "Requiere autenticación mediante Bearer token."
    ),
    response_model=ProjectResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "Detalles del proyecto.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token de acceso inválido o ausente.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Proyecto no encontrado.",
        },
    },
)
async def get_project(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[GetProjectUseCase, Depends(_get_project)],
) -> ProjectResponse:
    try:
        project = await use_case.execute(project_id=ProjectId(project_id))
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        owner_id=project.owner_id,
        current_phase=project.current_phase.value,
        status=project.status.value,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
