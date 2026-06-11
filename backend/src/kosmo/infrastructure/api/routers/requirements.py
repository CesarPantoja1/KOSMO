from typing import Annotated

from fastapi import APIRouter, Depends, Request

from kosmo.application.features.get_requirements_document import GetRequirementsDocumentUseCase
from kosmo.application.features.save_requirements_document import SaveRequirementsDocumentUseCase
from kosmo.contracts.auth.principal import Principal
from kosmo.contracts.sdd.errors import (
    FeatureNotApprovedError,
    FeatureNotFoundError,
)
from kosmo.contracts.sdd.feature import FeatureStatus
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.project import ProjectPhase
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.contracts.sdd.spec import SpecPhase
from kosmo.contracts.sdd.state import KOSMOState
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas_requirements import (
    RequirementsDocumentRequest,
    RequirementsDocumentResponse,
)

requirements_router = APIRouter(prefix="/api/v1", tags=["requirements"])


async def _resolve_feature_identifier(
    feature_repo: FeatureRepository,
    project_id: str,
    identifier: str,
) -> FeatureId:
    if identifier.startswith("feat_"):
        return FeatureId(identifier)
    feature = await feature_repo.get_by_slug(ProjectId(project_id), identifier)
    if feature is not None:
        return feature.id
    return FeatureId(identifier)


def _to_requirements_response(
    response,
    feature_title: str,
    feature_description: str,
) -> RequirementsDocumentResponse:
    return RequirementsDocumentResponse(
        document=response.document.model_dump(),
        sections=response.sections,
        feature_title=feature_title,
        feature_description=feature_description,
        updated_at=response.updated_at,
    )


async def _fetch_feature(feature_repo: FeatureRepository, fid: FeatureId):
    feature = await feature_repo.get(fid)
    if feature is None:
        raise FeatureNotFoundError(str(fid))
    return feature


@requirements_router.get(
    "/projects/{project_id}/features/{feature_identifier}/requirements",
    response_model=RequirementsDocumentResponse,
)
async def get_requirements(
    project_id: str,
    feature_identifier: str,
    request: Request,
    _principal: Annotated[Principal, Depends(get_principal)],
) -> RequirementsDocumentResponse:
    feature_repo: FeatureRepository = request.app.state.feature_repo
    fid = await _resolve_feature_identifier(feature_repo, project_id, feature_identifier)
    feature = await _fetch_feature(feature_repo, fid)
    uc = GetRequirementsDocumentUseCase(feature_repo=feature_repo)
    result = await uc.execute(fid)
    return _to_requirements_response(result, feature.title, feature.description)


@requirements_router.put(
    "/projects/{project_id}/features/{feature_identifier}/requirements",
    response_model=RequirementsDocumentResponse,
)
async def save_requirements(
    project_id: str,
    feature_identifier: str,
    payload: RequirementsDocumentRequest,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> RequirementsDocumentResponse:
    feature_repo: FeatureRepository = request.app.state.feature_repo
    fid = await _resolve_feature_identifier(feature_repo, project_id, feature_identifier)
    feature = await _fetch_feature(feature_repo, fid)
    uc = SaveRequirementsDocumentUseCase(
        feature_repo=feature_repo,
        preference_repo=getattr(request.app.state, "preference_repo", None),
        llm_client=getattr(request.app.state, "llm_client", None),
    )
    result = await uc.execute(
        fid,
        payload.document,
        user_id=principal.subject,
        project_id=feature.project_id,
    )
    return _to_requirements_response(result, feature.title, feature.description)


@requirements_router.post(
    "/projects/{project_id}/features/{feature_identifier}/requirements/generate",
    response_model=RequirementsDocumentResponse,
)
async def generate_requirements(
    project_id: str,
    feature_identifier: str,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> RequirementsDocumentResponse:
    feature_repo: FeatureRepository = request.app.state.feature_repo
    fid = await _resolve_feature_identifier(feature_repo, project_id, feature_identifier)
    feature = await _fetch_feature(feature_repo, fid)

    if feature.status != FeatureStatus.APROBADA:
        raise FeatureNotApprovedError(str(fid))

    getattr(request.app.state, "preference_repo", None)
    graph_engine = getattr(request.app.state, "graph_engine", None)

    state = KOSMOState(
        project_id=str(feature.project_id),
        user_id=principal.subject,
        phase=SpecPhase.REQUISITOS,
        max_iterations=10,
    )
    state.shared_scratchpad["current_feature_title"] = feature.title
    state.shared_scratchpad["current_feature_description"] = feature.description
    state.shared_scratchpad["current_feature_status"] = feature.status.value

    project = await request.app.state.project_repo.get(feature.project_id)
    if project:
        specs = await request.app.state.spec_repo.list_by_project(feature.project_id)
        if specs and specs[0].discovery:
            state.discovery = specs[0].discovery

    if graph_engine is not None:
        from ulid import ULID

        thread_id = f"{principal.subject}_{fid}_{ULID().hex}"
        result_state = await graph_engine.invoke(state, {"configurable": {"thread_id": thread_id}})
    else:
        result_state = state

    if result_state.requirements:
        from kosmo.contracts.sdd.requirements_document import RequirementsDocument

        ears = RequirementsDocument()
        for r in result_state.requirements:
            if r.pattern.value == "ubiquitous":
                ears.ubiquitous.append(r)
            elif r.pattern.value == "event":
                ears.event.append(r)
            elif r.pattern.value == "state":
                ears.state.append(r)
            elif r.pattern.value == "optional":
                ears.optional.append(r)
            elif r.pattern.value == "unwanted":
                ears.unwanted.append(r)
            elif r.pattern.value == "complex":
                ears.complex.append(r)

        await feature_repo.update_requirements(fid, ears)

        from kosmo.domain.sdd.document_converters import (
            markdown_to_document,
            requirements_document_to_markdown,
        )

        md = requirements_document_to_markdown(ears, feature.title)
        doc_tree = result_state.shared_scratchpad.get(
            "generated_document_tree", markdown_to_document(md)
        )
        await feature_repo.update_requirements_document(fid, doc_tree)
    else:
        from kosmo.domain.sdd.document_converters import markdown_to_document

        empty_md = f"# Requisitos: {feature.title}\n\nSin requisitos generados."
        empty_tree = markdown_to_document(empty_md)
        await feature_repo.update_requirements_document(fid, empty_tree)

        if project and project.current_phase != ProjectPhase.REQUISITOS:
            project.current_phase = ProjectPhase.REQUISITOS
            await request.app.state.project_repo.update(project)

    doc_uc = GetRequirementsDocumentUseCase(feature_repo=feature_repo)
    result = await doc_uc.execute(fid)
    return _to_requirements_response(result, feature.title, feature.description)


@requirements_router.post(
    "/projects/{project_id}/features/{feature_identifier}/requirements/regenerate",
    response_model=RequirementsDocumentResponse,
)
async def regenerate_requirements(
    project_id: str,
    feature_identifier: str,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> RequirementsDocumentResponse:
    feature_repo: FeatureRepository = request.app.state.feature_repo
    fid = await _resolve_feature_identifier(feature_repo, project_id, feature_identifier)
    feature = await _fetch_feature(feature_repo, fid)

    if feature.status != FeatureStatus.APROBADA:
        raise FeatureNotApprovedError(str(fid))

    graph_engine = getattr(request.app.state, "graph_engine", None)

    state = KOSMOState(
        project_id=str(feature.project_id),
        user_id=principal.subject,
        phase=SpecPhase.REQUISITOS,
        max_iterations=10,
    )
    state.shared_scratchpad["current_feature_title"] = feature.title
    state.shared_scratchpad["current_feature_description"] = feature.description

    existing_doc = await feature_repo.get_requirements_document(fid)
    if existing_doc:
        from kosmo.domain.sdd.document_converters import document_to_markdown

        current_md = document_to_markdown(existing_doc)
        state.shared_scratchpad["current_draft"] = current_md
        state.shared_scratchpad["improve_instruction"] = (
            "Mejora este documento de requisitos manteniendo las ideas "
            "y modificaciones del usuario. Refina la estructura EARS, "
            "completa requisitos incompletos y corrige errores de formato. "
            "NO elimines requisitos que el usuario anadio ni cambies su intencion."
        )
        state.shared_scratchpad["generator_action"] = "improve"

    if graph_engine is not None:
        from ulid import ULID

        thread_id = f"{principal.subject}_{fid}_regen_{ULID().hex}"
        result_state = await graph_engine.invoke(state, {"configurable": {"thread_id": thread_id}})
    else:
        result_state = state

    if result_state.requirements:
        from kosmo.contracts.sdd.requirements_document import RequirementsDocument

        ears = RequirementsDocument()
        for r in result_state.requirements:
            if r.pattern.value == "ubiquitous":
                ears.ubiquitous.append(r)
            elif r.pattern.value == "event":
                ears.event.append(r)
            elif r.pattern.value == "state":
                ears.state.append(r)
            elif r.pattern.value == "optional":
                ears.optional.append(r)
            elif r.pattern.value == "unwanted":
                ears.unwanted.append(r)
            elif r.pattern.value == "complex":
                ears.complex.append(r)
        await feature_repo.update_requirements(fid, ears)

        from kosmo.domain.sdd.document_converters import (
            clean_document_tree,
            markdown_to_document,
            requirements_document_to_markdown,
        )

        md = requirements_document_to_markdown(ears, feature.title)
        doc_tree = result_state.shared_scratchpad.get(
            "generated_document_tree", markdown_to_document(md)
        )
        doc_tree = clean_document_tree(doc_tree)
        await feature_repo.update_requirements_document(fid, doc_tree)
    else:
        from kosmo.domain.sdd.document_converters import markdown_to_document

        empty_md = f"# Requisitos: {feature.title}\n\nSin requisitos generados."
        empty_tree = markdown_to_document(empty_md)
        await feature_repo.update_requirements_document(fid, empty_tree)

    doc_uc = GetRequirementsDocumentUseCase(feature_repo=feature_repo)
    result = await doc_uc.execute(fid)
    return _to_requirements_response(result, feature.title, feature.description)
