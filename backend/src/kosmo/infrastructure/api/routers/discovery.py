from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from kosmo.contracts.auth.principal import Principal
from kosmo.contracts.sdd.discovery import RawIdea
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.spec import SpecPhase
from kosmo.contracts.sdd.state import KOSMOState
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas_discovery import (
    DiscoveryDocumentRequest,
    DiscoveryDocumentResponse,
)

discovery_router = APIRouter(prefix="/api/v1", tags=["discovery"])


async def _resolve_project_identifier(
    project_repo, identifier: str
) -> ProjectId:
    if identifier.startswith("prj_"):
        return ProjectId(identifier)
    project = await project_repo.get_by_slug(identifier)
    if project is not None:
        return project.id
    return ProjectId(identifier)


@discovery_router.get(
    "/projects/{project_id}/discovery",
    response_model=DiscoveryDocumentResponse,
)
async def get_discovery(
    project_id: str,
    request: Request,
    _principal: Annotated[Principal, Depends(get_principal)],
) -> DiscoveryDocumentResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    document_repo = getattr(request.app.state, "document_repo", None)
    markdown = ""
    if document_repo:
        result = await document_repo.get_discovery_md(pid)
        if result:
            markdown = result
    return DiscoveryDocumentResponse(document=markdown)


@discovery_router.put(
    "/projects/{project_id}/discovery",
    response_model=DiscoveryDocumentResponse,
)
async def save_discovery(
    project_id: str,
    payload: DiscoveryDocumentRequest,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> DiscoveryDocumentResponse:
    from kosmo.application.sdd.save_discovery_document import SaveDiscoveryDocumentUseCase

    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)

    uc = SaveDiscoveryDocumentUseCase(
        project_repo=request.app.state.project_repo,
        spec_repo=request.app.state.spec_repo,
        document_repo=getattr(request.app.state, "document_repo", None),
        preference_repo=getattr(request.app.state, "preference_repo", None),
        llm_client=getattr(request.app.state, "llm_client", None),
    )
    await uc.execute(pid, payload.document, user_id=principal.subject)
    return DiscoveryDocumentResponse(document=payload.document)


@discovery_router.post(
    "/projects/{project_id}/discovery/generate",
    response_model=DiscoveryDocumentResponse,
)
async def generate_discovery(
    project_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> DiscoveryDocumentResponse:
    from kosmo.application.projects.get_project import GetProjectUseCase

    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    project_uc = GetProjectUseCase(project_repo=request.app.state.project_repo)
    project = await project_uc.execute(pid)

    graph_engine = getattr(request.app.state, "graph_engine", None)

    state = KOSMOState(
        project_id=str(pid),
        user_id=principal.subject,
        phase=SpecPhase.DESCUBRIMIENTO,
        raw_idea=RawIdea(text=project.description),
        max_iterations=10,
    )

    if graph_engine is not None:
        import structlog
        from ulid import ULID

        logger = structlog.get_logger()
        try:
            thread_id = f"{principal.subject}_{pid}_{ULID().hex}"
            result_state = await graph_engine.invoke(
                state, {"configurable": {"thread_id": thread_id}}
            )
        except Exception as exc:
            logger.error("graph_engine.invoke failed", error=str(exc), project_id=str(pid))
            raise HTTPException(status_code=500, detail=f"Graph engine error: {exc}")
    else:
        result_state = state
        result_state.discovery = f"# Descubrimiento de Producto\n\n## Visión del producto\n\n{project.description}"

    markdown = result_state.discovery or ""
    if markdown.strip():
        document_repo = getattr(request.app.state, "document_repo", None)
        if document_repo:
            await document_repo.save_discovery_md(pid, markdown)

    return DiscoveryDocumentResponse(document=markdown)


@discovery_router.post(
    "/projects/{project_id}/discovery/regenerate",
    response_model=DiscoveryDocumentResponse,
)
async def regenerate_discovery(
    project_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> DiscoveryDocumentResponse:
    from kosmo.application.projects.get_project import GetProjectUseCase

    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    project_uc = GetProjectUseCase(project_repo=request.app.state.project_repo)
    project = await project_uc.execute(pid)

    graph_engine = getattr(request.app.state, "graph_engine", None)

    state = KOSMOState(
        project_id=str(pid),
        user_id=principal.subject,
        phase=SpecPhase.DESCUBRIMIENTO,
        raw_idea=RawIdea(text=project.description),
        max_iterations=10,
    )

    document_repo = getattr(request.app.state, "document_repo", None)
    if document_repo:
        existing_md = await document_repo.get_discovery_md(pid)
        if existing_md:
            state.shared_scratchpad["current_draft"] = existing_md
            state.shared_scratchpad["improve_instruction"] = (
                "Mejora este documento de descubrimiento manteniendo las ideas "
                "y modificaciones del usuario. Enriquece el analisis de negocio, "
                "completa secciones vacias y refina la redaccion. "
                "NO elimines contenido que el usuario anadio."
            )
            state.shared_scratchpad["generator_action"] = "improve"

    if graph_engine is not None:
        from ulid import ULID

        thread_id = f"{principal.subject}_{pid}_regen_{ULID().hex}"
        result_state = await graph_engine.invoke(state, {"configurable": {"thread_id": thread_id}})
    else:
        result_state = state
        result_state.discovery = ""

    markdown = result_state.discovery or ""
    if markdown.strip() and document_repo:
        await document_repo.save_discovery_md(pid, markdown)

    return DiscoveryDocumentResponse(document=markdown)
