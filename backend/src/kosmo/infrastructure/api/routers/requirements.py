from fastapi import APIRouter, HTTPException, Request

from kosmo.application.features.generate_requirements import GenerateFeatureRequirementsUseCase
from kosmo.application.features.get_requirements_document import GetRequirementsDocumentUseCase
from kosmo.application.features.regenerate_requirements import RegenerateRequirementsUseCase
from kosmo.application.features.save_requirements_document import SaveRequirementsDocumentUseCase
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    DocumentValidationError,
    FeatureNotApprovedError,
    FeatureNotFoundError,
)
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository
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
        raise HTTPException(status_code=404, detail="Caracteristica no encontrada")
    return feature


# ── Rutas scoped (aceptan id o slug) ──


@requirements_router.get(
    "/projects/{project_id}/features/{feature_identifier}/requirements",
    response_model=RequirementsDocumentResponse,
)
async def get_requirements(
    project_id: str,
    feature_identifier: str,
    request: Request,
) -> RequirementsDocumentResponse:
    feature_repo: FeatureRepository = request.app.state.feature_repo
    fid = await _resolve_feature_identifier(feature_repo, project_id, feature_identifier)
    feature = await _fetch_feature(feature_repo, fid)

    uc = GetRequirementsDocumentUseCase(feature_repo=feature_repo)
    try:
        result = await uc.execute(fid)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

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
) -> RequirementsDocumentResponse:
    feature_repo: FeatureRepository = request.app.state.feature_repo
    fid = await _resolve_feature_identifier(feature_repo, project_id, feature_identifier)
    feature = await _fetch_feature(feature_repo, fid)

    uc = SaveRequirementsDocumentUseCase(feature_repo=feature_repo)
    try:
        result = await uc.execute(fid, payload.document)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _to_requirements_response(result, feature.title, feature.description)


@requirements_router.post(
    "/projects/{project_id}/features/{feature_identifier}/requirements/generate",
    response_model=RequirementsDocumentResponse,
)
async def generate_requirements(
    project_id: str,
    feature_identifier: str,
    request: Request,
) -> RequirementsDocumentResponse:
    feature_repo: FeatureRepository = request.app.state.feature_repo
    fid = await _resolve_feature_identifier(feature_repo, project_id, feature_identifier)
    feature = await _fetch_feature(feature_repo, fid)

    uc = GenerateFeatureRequirementsUseCase(
        feature_repo=request.app.state.feature_repo,
        spec_repo=request.app.state.spec_repo,
        llm_client=request.app.state.llm_client,
    )
    try:
        await uc.execute(fid)
    except FeatureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FeatureNotApprovedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    doc_uc = GetRequirementsDocumentUseCase(feature_repo=feature_repo)
    try:
        result = await doc_uc.execute(fid)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _to_requirements_response(result, feature.title, feature.description)


@requirements_router.post(
    "/projects/{project_id}/features/{feature_identifier}/requirements/regenerate",
    response_model=RequirementsDocumentResponse,
)
async def regenerate_requirements(
    project_id: str,
    feature_identifier: str,
    request: Request,
) -> RequirementsDocumentResponse:
    feature_repo: FeatureRepository = request.app.state.feature_repo
    fid = await _resolve_feature_identifier(feature_repo, project_id, feature_identifier)
    feature = await _fetch_feature(feature_repo, fid)

    uc = RegenerateRequirementsUseCase(
        feature_repo=request.app.state.feature_repo,
        spec_repo=request.app.state.spec_repo,
        llm_client=request.app.state.llm_client,
    )
    try:
        result = await uc.execute(fid)
    except FeatureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FeatureNotApprovedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _to_requirements_response(result, feature.title, feature.description)


# ── Rutas standalone con ID directo ──


@requirements_router.get(
    "/features/{feature_id}/requirements",
    response_model=RequirementsDocumentResponse,
)
async def get_requirements_standalone(
    feature_id: str,
    request: Request,
) -> RequirementsDocumentResponse:
    feature_repo = request.app.state.feature_repo
    feature = await _fetch_feature(feature_repo, FeatureId(feature_id))
    uc = GetRequirementsDocumentUseCase(feature_repo=feature_repo)
    try:
        result = await uc.execute(FeatureId(feature_id))
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_requirements_response(result, feature.title, feature.description)


@requirements_router.put(
    "/features/{feature_id}/requirements",
    response_model=RequirementsDocumentResponse,
)
async def save_requirements_standalone(
    feature_id: str,
    payload: RequirementsDocumentRequest,
    request: Request,
) -> RequirementsDocumentResponse:
    feature_repo = request.app.state.feature_repo
    feature = await _fetch_feature(feature_repo, FeatureId(feature_id))
    uc = SaveRequirementsDocumentUseCase(feature_repo=feature_repo)
    try:
        result = await uc.execute(FeatureId(feature_id), payload.document)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_requirements_response(result, feature.title, feature.description)


@requirements_router.post(
    "/features/{feature_id}/requirements/generate",
    response_model=RequirementsDocumentResponse,
)
async def generate_requirements_standalone(
    feature_id: str,
    request: Request,
) -> RequirementsDocumentResponse:
    feature_repo = request.app.state.feature_repo
    feature = await _fetch_feature(feature_repo, FeatureId(feature_id))
    uc = GenerateFeatureRequirementsUseCase(
        feature_repo=feature_repo,
        spec_repo=request.app.state.spec_repo,
        llm_client=request.app.state.llm_client,
    )
    try:
        await uc.execute(FeatureId(feature_id))
    except FeatureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FeatureNotApprovedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    doc_uc = GetRequirementsDocumentUseCase(feature_repo=feature_repo)
    try:
        result = await doc_uc.execute(FeatureId(feature_id))
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _to_requirements_response(result, feature.title, feature.description)


@requirements_router.post(
    "/features/{feature_id}/requirements/regenerate",
    response_model=RequirementsDocumentResponse,
)
async def regenerate_requirements_standalone(
    feature_id: str,
    request: Request,
) -> RequirementsDocumentResponse:
    feature_repo = request.app.state.feature_repo
    feature = await _fetch_feature(feature_repo, FeatureId(feature_id))
    uc = RegenerateRequirementsUseCase(
        feature_repo=feature_repo,
        spec_repo=request.app.state.spec_repo,
        llm_client=request.app.state.llm_client,
    )
    try:
        result = await uc.execute(FeatureId(feature_id))
    except FeatureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FeatureNotApprovedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_requirements_response(result, feature.title, feature.description)
