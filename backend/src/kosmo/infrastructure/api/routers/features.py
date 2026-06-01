from fastapi import APIRouter, HTTPException, Request

from kosmo.application.features.apply_improvement import ApplyFeatureImprovementUseCase
from kosmo.application.features.create_feature import CreateFeatureUseCase
from kosmo.application.features.delete_feature import DeleteFeatureUseCase
from kosmo.application.features.generate_features import GenerateFeaturesUseCase
from kosmo.application.features.improve_feature import ImproveFeatureSuggestionUseCase
from kosmo.application.features.list_features import ListFeaturesUseCase
from kosmo.application.features.suggest_alternatives import SuggestAlternativeFeaturesUseCase
from kosmo.application.features.suggest_from_idea import SuggestFeatureFromIdeaUseCase
from kosmo.application.features.toggle_feature_status import ToggleFeatureStatusUseCase
from kosmo.contracts.sdd.errors import (
    FeatureNotEditableError,
    FeatureNotFoundError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository, ProjectRepository
from kosmo.infrastructure.api.schemas_features import (
    ApplyImprovementRequest,
    CreateFeatureRequest,
    FeatureAlternativesResponse,
    FeatureResponse,
    FeaturesListResponse,
    ImproveFeatureResponse,
    SuggestFromIdeaRequest,
)

features_router = APIRouter(prefix="/api/v1", tags=["features"])


async def _resolve_project_identifier(
    project_repo: ProjectRepository, identifier: str
) -> ProjectId:
    if identifier.startswith("prj_"):
        return ProjectId(identifier)
    project = await project_repo.get_by_slug(identifier)
    if project is not None:
        return project.id
    return ProjectId(identifier)


async def _resolve_feature_identifier(
    feature_repo: FeatureRepository,
    project_id: ProjectId,
    identifier: str,
) -> FeatureId:
    if identifier.startswith("feat_"):
        return FeatureId(identifier)
    feature = await feature_repo.get_by_slug(project_id, identifier)
    if feature is not None:
        return feature.id
    return FeatureId(identifier)


def _to_feature_response(feature: Feature) -> FeatureResponse:
    return FeatureResponse(
        id=feature.id,
        project_id=feature.project_id,
        title=feature.title,
        slug=feature.slug,
        description=feature.description,
        status=feature.status.value,
        created_at=feature.created_at,
    )


@features_router.get(
    "/projects/{project_id}/features",
    response_model=FeaturesListResponse,
)
async def list_features(
    project_id: str,
    request: Request,
) -> FeaturesListResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = ListFeaturesUseCase(feature_repo=request.app.state.feature_repo)
    features = await uc.execute(pid)
    return FeaturesListResponse(
        features=[_to_feature_response(f) for f in features],
        total=len(features),
    )


@features_router.post(
    "/projects/{project_id}/features",
    response_model=FeatureResponse,
    status_code=201,
)
async def create_feature(
    project_id: str,
    payload: CreateFeatureRequest,
    request: Request,
) -> FeatureResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = CreateFeatureUseCase(
        feature_repo=request.app.state.feature_repo,
        project_repo=request.app.state.project_repo,
    )
    try:
        feature = await uc.execute(pid, title=payload.title, description=payload.description)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_feature_response(feature)


@features_router.post(
    "/projects/{project_id}/features/generate",
    response_model=FeaturesListResponse,
)
async def generate_features(
    project_id: str,
    request: Request,
) -> FeaturesListResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = GenerateFeaturesUseCase(
        feature_repo=request.app.state.feature_repo,
        project_repo=request.app.state.project_repo,
        llm_client=request.app.state.llm_client,
    )
    try:
        features = await uc.execute(pid)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FeaturesListResponse(
        features=[_to_feature_response(f) for f in features],
        total=len(features),
    )


@features_router.post(
    "/projects/{project_id}/features/suggest",
    response_model=FeatureAlternativesResponse,
)
async def suggest_alternative_features(
    project_id: str,
    request: Request,
) -> FeatureAlternativesResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = SuggestAlternativeFeaturesUseCase(
        feature_repo=request.app.state.feature_repo,
        project_repo=request.app.state.project_repo,
        llm_client=request.app.state.llm_client,
    )
    try:
        suggestions = await uc.execute(pid)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FeatureAlternativesResponse(
        suggestions=[_to_feature_response(s) for s in suggestions],
    )


@features_router.post(
    "/projects/{project_id}/features/suggest-from-idea",
    response_model=FeatureResponse,
)
async def suggest_feature_from_user_idea(
    project_id: str,
    payload: SuggestFromIdeaRequest,
    request: Request,
) -> FeatureResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = SuggestFeatureFromIdeaUseCase(
        project_repo=request.app.state.project_repo,
        llm_client=request.app.state.llm_client,
    )
    try:
        suggestion = await uc.execute(pid, payload.idea)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_feature_response(suggestion)


@features_router.delete(
    "/projects/{project_id}/features/{feature_identifier}",
    status_code=204,
)
async def delete_feature(
    project_id: str,
    feature_identifier: str,
    request: Request,
) -> None:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    fid = await _resolve_feature_identifier(request.app.state.feature_repo, pid, feature_identifier)
    uc = DeleteFeatureUseCase(feature_repo=request.app.state.feature_repo)
    try:
        await uc.execute(fid)
    except FeatureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@features_router.patch(
    "/projects/{project_id}/features/{feature_identifier}/status",
    response_model=FeatureResponse,
)
async def toggle_feature_status(
    project_id: str,
    feature_identifier: str,
    request: Request,
) -> FeatureResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    fid = await _resolve_feature_identifier(request.app.state.feature_repo, pid, feature_identifier)
    uc = ToggleFeatureStatusUseCase(feature_repo=request.app.state.feature_repo)
    try:
        feature = await uc.execute(fid)
    except FeatureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_feature_response(feature)


@features_router.post(
    "/projects/{project_id}/features/{feature_identifier}/improve",
    response_model=ImproveFeatureResponse,
)
async def improve_feature(
    project_id: str,
    feature_identifier: str,
    request: Request,
) -> ImproveFeatureResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    fid = await _resolve_feature_identifier(request.app.state.feature_repo, pid, feature_identifier)
    uc = ImproveFeatureSuggestionUseCase(
        feature_repo=request.app.state.feature_repo,
        project_repo=request.app.state.project_repo,
        llm_client=request.app.state.llm_client,
    )
    try:
        suggestion = await uc.execute(fid)
    except FeatureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FeatureNotEditableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ImproveFeatureResponse(
        id=suggestion.id,
        project_id=suggestion.project_id,
        title=suggestion.title,
        slug=suggestion.slug,
        description=suggestion.description,
        status=suggestion.status.value,
        created_at=suggestion.created_at,
    )


@features_router.post(
    "/projects/{project_id}/features/{feature_identifier}/apply-improvement",
    response_model=FeatureResponse,
)
async def apply_feature_improvement(
    project_id: str,
    feature_identifier: str,
    payload: ApplyImprovementRequest,
    request: Request,
) -> FeatureResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    fid = await _resolve_feature_identifier(request.app.state.feature_repo, pid, feature_identifier)
    uc = ApplyFeatureImprovementUseCase(feature_repo=request.app.state.feature_repo)
    try:
        feature = await uc.execute(fid, title=payload.title, description=payload.description)
    except FeatureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FeatureNotEditableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_feature_response(feature)


# ── Rutas standalone con ID directo (compatibilidad) ──


@features_router.delete(
    "/features/{feature_id}",
    status_code=204,
)
async def delete_feature_standalone(
    feature_id: str,
    request: Request,
) -> None:
    uc = DeleteFeatureUseCase(feature_repo=request.app.state.feature_repo)
    try:
        await uc.execute(FeatureId(feature_id))
    except FeatureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@features_router.patch(
    "/features/{feature_id}/status",
    response_model=FeatureResponse,
)
async def toggle_feature_status_standalone(
    feature_id: str,
    request: Request,
) -> FeatureResponse:
    uc = ToggleFeatureStatusUseCase(feature_repo=request.app.state.feature_repo)
    try:
        feature = await uc.execute(FeatureId(feature_id))
    except FeatureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_feature_response(feature)


@features_router.post(
    "/features/{feature_id}/improve",
    response_model=ImproveFeatureResponse,
)
async def improve_feature_standalone(
    feature_id: str,
    request: Request,
) -> ImproveFeatureResponse:
    uc = ImproveFeatureSuggestionUseCase(
        feature_repo=request.app.state.feature_repo,
        project_repo=request.app.state.project_repo,
        llm_client=request.app.state.llm_client,
    )
    try:
        suggestion = await uc.execute(FeatureId(feature_id))
    except FeatureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FeatureNotEditableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ImproveFeatureResponse(
        id=suggestion.id,
        project_id=suggestion.project_id,
        title=suggestion.title,
        slug=suggestion.slug,
        description=suggestion.description,
        status=suggestion.status.value,
        created_at=suggestion.created_at,
    )


@features_router.post(
    "/features/{feature_id}/apply-improvement",
    response_model=FeatureResponse,
)
async def apply_feature_improvement_standalone(
    feature_id: str,
    payload: ApplyImprovementRequest,
    request: Request,
) -> FeatureResponse:
    uc = ApplyFeatureImprovementUseCase(feature_repo=request.app.state.feature_repo)
    try:
        feature = await uc.execute(
            FeatureId(feature_id), title=payload.title, description=payload.description
        )
    except FeatureNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FeatureNotEditableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_feature_response(feature)
