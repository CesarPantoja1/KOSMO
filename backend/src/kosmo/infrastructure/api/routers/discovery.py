from fastapi import APIRouter, HTTPException, Request

from kosmo.application.sdd.capture import CaptureDiscoveryUseCase
from kosmo.application.sdd.get_discovery_document import GetDiscoveryDocumentUseCase
from kosmo.application.sdd.regenerate_discovery import RegenerateDiscoveryUseCase
from kosmo.application.sdd.save_discovery_document import SaveDiscoveryDocumentUseCase
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    DocumentValidationError,
    MarkdownParseError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.infrastructure.api.schemas_discovery import (
    DiscoveryDocumentRequest,
    DiscoveryDocumentResponse,
)

discovery_router = APIRouter(prefix="/api/v1", tags=["discovery"])


async def _resolve_project_identifier(
    project_repo: ProjectRepository, identifier: str
) -> ProjectId:
    if identifier.startswith("prj_"):
        return ProjectId(identifier)
    project = await project_repo.get_by_slug(identifier)
    if project is not None:
        return project.id
    return ProjectId(identifier)


def _to_discovery_response(response) -> DiscoveryDocumentResponse:
    return DiscoveryDocumentResponse(
        document=response.document.model_dump(),
        sections=response.sections,
        updated_at=response.updated_at,
    )


@discovery_router.get(
    "/projects/{project_id}/discovery",
    response_model=DiscoveryDocumentResponse,
)
async def get_discovery(
    project_id: str,
    request: Request,
) -> DiscoveryDocumentResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = GetDiscoveryDocumentUseCase(project_repo=request.app.state.project_repo)
    try:
        result = await uc.execute(pid)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_discovery_response(result)


@discovery_router.put(
    "/projects/{project_id}/discovery",
    response_model=DiscoveryDocumentResponse,
)
async def save_discovery(
    project_id: str,
    payload: DiscoveryDocumentRequest,
    request: Request,
) -> DiscoveryDocumentResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = SaveDiscoveryDocumentUseCase(
        project_repo=request.app.state.project_repo,
        spec_repo=request.app.state.spec_repo,
    )
    try:
        result = await uc.execute(pid, payload.document)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MarkdownParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_discovery_response(result)


@discovery_router.post(
    "/projects/{project_id}/discovery/generate",
    response_model=DiscoveryDocumentResponse,
)
async def generate_discovery(
    project_id: str,
    request: Request,
) -> DiscoveryDocumentResponse:
    from kosmo.application.projects.get_project import GetProjectUseCase

    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    project_uc = GetProjectUseCase(project_repo=request.app.state.project_repo)
    try:
        project = await project_uc.execute(pid)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    capture_uc = CaptureDiscoveryUseCase(
        spec_repo=request.app.state.spec_repo,
        project_repo=request.app.state.project_repo,
        llm_client=request.app.state.llm_client,
    )
    await capture_uc.execute(project_id=pid, description=project.description)

    get_uc = GetDiscoveryDocumentUseCase(project_repo=request.app.state.project_repo)
    try:
        result = await get_uc.execute(pid)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _to_discovery_response(result)


@discovery_router.post(
    "/projects/{project_id}/discovery/regenerate",
    response_model=DiscoveryDocumentResponse,
)
async def regenerate_discovery(
    project_id: str,
    request: Request,
) -> DiscoveryDocumentResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = RegenerateDiscoveryUseCase(
        project_repo=request.app.state.project_repo,
        spec_repo=request.app.state.spec_repo,
        llm_client=request.app.state.llm_client,
    )
    try:
        result = await uc.execute(pid)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_discovery_response(result)
