from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from kosmo.application.sdd.get_discovery_document import GetDiscoveryDocumentUseCase
from kosmo.application.sdd.save_discovery_document import SaveDiscoveryDocumentUseCase
from kosmo.contracts.auth.principal import Principal
from kosmo.contracts.sdd.discovery import RawIdea
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
)
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import ProjectRepository
from kosmo.contracts.sdd.spec import SpecPhase
from kosmo.contracts.sdd.state import KOSMOState
from kosmo.infrastructure.api.dependencies.auth import get_principal
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
    _principal: Annotated[Principal, Depends(get_principal)],
) -> DiscoveryDocumentResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = GetDiscoveryDocumentUseCase(project_repo=request.app.state.project_repo)
    result = await uc.execute(pid)
    return _to_discovery_response(result)


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
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = SaveDiscoveryDocumentUseCase(
        project_repo=request.app.state.project_repo,
        spec_repo=request.app.state.spec_repo,
        preference_repo=getattr(request.app.state, "preference_repo", None),
        llm_client=getattr(request.app.state, "llm_client", None),
    )
    result = await uc.execute(pid, payload.document, user_id=principal.subject)
    return _to_discovery_response(result)


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
    getattr(request.app.state, "preference_repo", None)

    state = KOSMOState(
        project_id=str(pid),
        user_id=principal.subject,
        phase=SpecPhase.DESCUBRIMIENTO,
        raw_idea=RawIdea(text=project.description),
        max_iterations=10,
    )

    if graph_engine is not None:
        import structlog

        logger = structlog.get_logger()
        try:
            result_state = await graph_engine.invoke(
                state, {"configurable": {"thread_id": f"{principal.subject}_{pid}"}}
            )
        except Exception as exc:
            logger.error("graph_engine.invoke failed", error=str(exc), project_id=str(pid))
            raise HTTPException(status_code=500, detail=f"Graph engine error: {exc}")

        has_discovery = result_state.discovery is not None
        has_errors = bool(result_state.errors)
        has_shared = bool(result_state.shared_scratchpad)
        logger.info(
            "graph_result",
            has_discovery=has_discovery,
            has_errors=has_errors,
            validation_status=result_state.validation_status,
            attempts=result_state.generation_attempts,
            scratchpad_keys=list(result_state.shared_scratchpad.keys()) if has_shared else [],
        )
    else:
        from kosmo.domain.sdd.document_converters import markdown_to_document

        discovery_dict = {
            "vision": project.description,
            "problem_space": "",
            "actors": "",
            "value_proposition": "",
            "use_cases": "",
            "core_capabilities": "",
            "business_rules": "",
            "quality_attributes": "",
            "scope": "",
        }
        from kosmo.contracts.sdd.discovery import DiscoveryDocument

        result_state = state
        result_state.discovery = DiscoveryDocument(**discovery_dict)
        result_state.shared_scratchpad["generated_document_tree"] = markdown_to_document(
            project.description
        )

    if result_state.discovery:
        from kosmo.domain.sdd.document_converters import (
            clean_document_tree,
            discovery_to_markdown,
            markdown_to_document,
        )

        markdown = discovery_to_markdown(result_state.discovery)
        document_tree = result_state.shared_scratchpad.get(
            "generated_document_tree", markdown_to_document(markdown)
        )
        document_tree = clean_document_tree(document_tree)
        await request.app.state.project_repo.update_discovery_document(pid, document_tree)
        spec_repo = request.app.state.spec_repo
        specs = await spec_repo.list_by_project(pid)
        if specs:
            spec = specs[0]
            spec.discovery = result_state.discovery
            await spec_repo.update(spec)

        from kosmo.application.sdd.get_discovery_document import GetDiscoveryDocumentUseCase

        get_uc = GetDiscoveryDocumentUseCase(project_repo=request.app.state.project_repo)
        try:
            result = await get_uc.execute(pid)
        except DocumentNotFoundError:
            from datetime import UTC, datetime

            from kosmo.contracts.sdd.document import (
                DocumentResponse,
                RichTextDocument,
                SectionHeading,
            )
            from kosmo.domain.sdd.document_converters import extract_sections

            sections_raw = extract_sections(document_tree)
            result = DocumentResponse(
                document=RichTextDocument(**document_tree),
                sections=[SectionHeading(**s) for s in sections_raw],
                updated_at=datetime.now(UTC).isoformat(),
            )
        return _to_discovery_response(result)

    raise HTTPException(status_code=500, detail="Discovery generation produced no output")


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
    getattr(request.app.state, "preference_repo", None)

    state = KOSMOState(
        project_id=str(pid),
        user_id=principal.subject,
        phase=SpecPhase.DESCUBRIMIENTO,
        raw_idea=RawIdea(text=project.description),
        max_iterations=10,
    )

    existing_doc = await request.app.state.project_repo.get_discovery_document(pid)
    if existing_doc:
        from kosmo.domain.sdd.document_converters import document_to_markdown

        current_md = document_to_markdown(existing_doc)
        state.shared_scratchpad["current_draft"] = current_md
        state.shared_scratchpad["improve_instruction"] = (
            "Mejora este documento de descubrimiento manteniendo las ideas "
            "y modificaciones del usuario. Enriquece el analisis de negocio, "
            "completa secciones vacias y refina la redaccion. "
            "NO elimines contenido que el usuario anadio."
        )
        state.shared_scratchpad["generator_action"] = "improve"

    if graph_engine is not None:
        result_state = await graph_engine.invoke(
            state, {"configurable": {"thread_id": f"{principal.subject}_{pid}_regen"}}
        )
    else:
        from kosmo.contracts.sdd.discovery import DiscoveryDocument

        result_state = state
        result_state.discovery = DiscoveryDocument()

    if result_state.discovery:
        from kosmo.domain.sdd.document_converters import (
            clean_document_tree,
            discovery_to_markdown,
            markdown_to_document,
        )

        markdown = discovery_to_markdown(result_state.discovery)
        document_tree = result_state.shared_scratchpad.get(
            "generated_document_tree", markdown_to_document(markdown)
        )
        document_tree = clean_document_tree(document_tree)
        await request.app.state.project_repo.update_discovery_document(pid, document_tree)
        spec_repo = request.app.state.spec_repo
        specs = await spec_repo.list_by_project(pid)
        if specs:
            spec = specs[0]
            spec.discovery = result_state.discovery
            await spec_repo.update(spec)

        from kosmo.application.sdd.get_discovery_document import GetDiscoveryDocumentUseCase

        get_uc = GetDiscoveryDocumentUseCase(project_repo=request.app.state.project_repo)
        try:
            result = await get_uc.execute(pid)
        except DocumentNotFoundError:
            from datetime import UTC, datetime

            from kosmo.contracts.sdd.document import (
                DocumentResponse,
                RichTextDocument,
                SectionHeading,
            )
            from kosmo.domain.sdd.document_converters import extract_sections

            sections_raw = extract_sections(document_tree)
            result = DocumentResponse(
                document=RichTextDocument(**document_tree),
                sections=[SectionHeading(**s) for s in sections_raw],
                updated_at=datetime.now(UTC).isoformat(),
            )
        return _to_discovery_response(result)

    raise HTTPException(status_code=500, detail="Regeneration produced no output")
