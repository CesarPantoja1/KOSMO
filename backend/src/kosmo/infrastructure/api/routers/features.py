from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from kosmo.application.features.create_feature import CreateFeatureUseCase
from kosmo.application.features.delete_feature import DeleteFeatureUseCase
from kosmo.application.features.list_features import ListFeaturesUseCase
from kosmo.application.features.save_selected_suggestions import (
    SaveSelectedSuggestionsUseCase,
)
from kosmo.application.features.toggle_feature_status import ToggleFeatureStatusUseCase
from kosmo.contracts.auth.principal import Principal
from kosmo.contracts.sdd.errors import (
    FeatureNotEditableError,
    FeatureNotFoundError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.feature import Feature
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository, ProjectRepository
from kosmo.contracts.sdd.spec import SpecPhase
from kosmo.contracts.sdd.state import KOSMOState
from kosmo.domain.sdd.llm_helpers import strip_markdown_formatting
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas_features import (
    CreateFeatureRequest,
    FeatureAlternativesResponse,
    FeatureResponse,
    FeaturesListResponse,
    ImproveFeatureResponse,
    SaveSuggestionsRequest,
    SuggestFromIdeaRequest,
    ToggleStatusRequest,
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
    _principal: Annotated[Principal, Depends(get_principal)],
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
    _principal: Annotated[Principal, Depends(get_principal)],
) -> FeatureResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = CreateFeatureUseCase(
        feature_repo=request.app.state.feature_repo,
        project_repo=request.app.state.project_repo,
    )
    try:
        feature = await uc.execute(pid, title=payload.title, description=payload.description)
    except ProjectNotFoundError:
        raise
    return _to_feature_response(feature)


@features_router.post(
    "/projects/{project_id}/features/generate",
    response_model=FeaturesListResponse,
)
async def generate_features(
    project_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> FeaturesListResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    getattr(request.app.state, "preference_repo", None)
    graph_engine = getattr(request.app.state, "graph_engine", None)

    project = await request.app.state.project_repo.get(pid)

    state = KOSMOState(
        project_id=str(pid),
        user_id=principal.subject,
        phase=SpecPhase.CARACTERISTICAS,
        max_iterations=10,
    )
    state.shared_scratchpad["generation_mode"] = "generate"
    if project and project.discovery_document:
        from kosmo.contracts.sdd.discovery import DiscoveryDocument

        state.discovery = (
            DiscoveryDocument(**project.discovery_document)
            if isinstance(project.discovery_document, dict)
            else None
        )

    existing_features = await request.app.state.feature_repo.get_by_project(pid)
    state.features = existing_features
    state.existing_feature_titles = [f.title for f in existing_features]
    state.existing_feature_ids = [f.id for f in existing_features]

    if graph_engine is not None:
        from ulid import ULID

        thread_id = f"{principal.subject}_{pid}_{ULID().hex}"
        result_state = await graph_engine.invoke(state, {"configurable": {"thread_id": thread_id}})
    else:
        raise HTTPException(status_code=503, detail="Motor de IA no disponible")

    new_features = result_state.features
    features_to_persist = [
        f for f in new_features if f not in await request.app.state.feature_repo.get_by_project(pid)
    ]
    for f in features_to_persist:
        await request.app.state.feature_repo.add(f)

    all_features = await request.app.state.feature_repo.get_by_project(pid)
    return FeaturesListResponse(
        features=[_to_feature_response(f) for f in all_features],
        total=len(all_features),
    )


@features_router.post(
    "/projects/{project_id}/features/suggest",
    response_model=FeatureAlternativesResponse,
)
async def suggest_alternative_features(
    project_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> FeatureAlternativesResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    getattr(request.app.state, "preference_repo", None)
    graph_engine = getattr(request.app.state, "graph_engine", None)

    project = await request.app.state.project_repo.get(pid)

    state = KOSMOState(
        project_id=str(pid),
        user_id=principal.subject,
        phase=SpecPhase.CARACTERISTICAS,
        max_iterations=3,
    )
    if project and project.discovery_document:
        from kosmo.contracts.sdd.discovery import DiscoveryDocument

        state.discovery = (
            DiscoveryDocument(**project.discovery_document)
            if isinstance(project.discovery_document, dict)
            else None
        )

    existing_features = await request.app.state.feature_repo.get_by_project(pid)
    state.existing_feature_titles = [f.title for f in existing_features]
    state.existing_feature_ids = [f.id for f in existing_features]

    if graph_engine is not None:
        from ulid import ULID

        thread_id = f"{principal.subject}_{pid}_suggest_{ULID().hex}"
        result_state = await graph_engine.invoke(state, {"configurable": {"thread_id": thread_id}})
    else:
        raise HTTPException(status_code=503, detail="Motor de IA no disponible")

    suggestions = [
        Feature(**f) for f in result_state.shared_scratchpad.get("generated_features", [])
    ]
    suggestions = await _dedup_features_from_list(suggestions, request.app.state.feature_repo, pid)
    return FeatureAlternativesResponse(
        suggestions=[_to_feature_response(f) for f in suggestions[:3]],
    )


async def _dedup_features_from_list(features: list, feature_repo, pid) -> list:
    existing = await feature_repo.get_by_project(pid)
    existing_titles = {f.title.strip().lower() for f in existing}
    result: list = []
    for f in features:
        if f.title.strip().lower() not in existing_titles:
            result.append(f)
    return result


@features_router.post(
    "/projects/{project_id}/features/suggest-from-idea",
    response_model=FeatureResponse,
)
async def suggest_feature_from_user_idea(
    project_id: str,
    payload: SuggestFromIdeaRequest,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> FeatureResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)

    state = KOSMOState(
        project_id=str(pid),
        user_id=principal.subject,
        phase=SpecPhase.CARACTERISTICAS,
        max_iterations=3,
    )
    state.shared_scratchpad["improve_instruction"] = (
        "Convierte esta idea en bruto en una característica de producto bien "
        "estructurada. Extrae un título conciso (verbo en infinitivo o sustantivo) "
        "y una descripción de 2-4 líneas de valor de negocio. Mejora la claridad "
        "y precisión. Evita tecnología y términos de implementación. "
        "Usa ortografía correcta del español con tildes y eñes."
    )
    state.shared_scratchpad["current_draft"] = payload.idea
    state.shared_scratchpad["generator_action"] = "improve"
    state.shared_scratchpad["phase_context"] = "features"

    graph_engine = getattr(request.app.state, "graph_engine", None)
    if graph_engine is not None:
        from ulid import ULID

        thread_id = f"{principal.subject}_{pid}_idea_{ULID().hex}"
        result_state = await graph_engine.invoke(state, {"configurable": {"thread_id": thread_id}})
    else:
        raise HTTPException(status_code=503, detail="Motor de IA no disponible")

    refined = result_state.shared_scratchpad.get("refined_content", payload.idea)
    title = payload.idea[:80]
    if "\n" in refined:
        raw_title = refined.split("\n")[0].strip().lstrip("# ").strip()
        title = strip_markdown_formatting(raw_title)
        refined = "\n".join(refined.split("\n")[1:]).strip() or refined
    refined = strip_markdown_formatting(refined)
    feature = Feature(
        id=FeatureId("feat_suggested"),
        project_id=pid,
        title=title,
        description=refined,
    )
    return _to_feature_response(feature)


@features_router.post(
    "/projects/{project_id}/features/{feature_identifier}/improve",
    response_model=ImproveFeatureResponse,
)
async def improve_feature(
    project_id: str,
    feature_identifier: str,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> ImproveFeatureResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    feature_repo = request.app.state.feature_repo
    fid = await _resolve_feature_identifier(feature_repo, pid, feature_identifier)
    feature = await feature_repo.get(fid)
    if feature is None:
        raise FeatureNotFoundError(str(fid))
    if feature.status.value != "borrador":
        raise FeatureNotEditableError(str(fid), feature.status.value)

    getattr(request.app.state, "preference_repo", None)

    state = KOSMOState(
        project_id=str(pid),
        user_id=principal.subject,
        phase=SpecPhase.CARACTERISTICAS,
        max_iterations=3,
    )
    state.shared_scratchpad["current_draft"] = f"{feature.title}\n\n{feature.description}"
    state.shared_scratchpad["improve_instruction"] = (
        "Mejora la claridad, estructura y precisión de esta característica. "
        "Refina la descripción para que sea más concreta y aporte más valor de negocio. "
        "Usa ortografía correcta del español con tildes y eñes."
    )
    state.shared_scratchpad["generator_action"] = "improve"
    state.shared_scratchpad["phase_context"] = "features"

    graph_engine = getattr(request.app.state, "graph_engine", None)
    if graph_engine is not None:
        from ulid import ULID

        thread_id = f"{principal.subject}_{fid}_improve_{ULID().hex}"
        result_state = await graph_engine.invoke(state, {"configurable": {"thread_id": thread_id}})
    else:
        raise HTTPException(status_code=503, detail="Motor de IA no disponible")

    refined = (
        result_state.shared_scratchpad.get("refined_content")
        or result_state.shared_scratchpad.get("generated_content_md")
        or result_state.shared_scratchpad.get("current_draft")
        or feature.description
    )
    return ImproveFeatureResponse(
        id=feature.id,
        project_id=feature.project_id,
        title=feature.title,
        slug=feature.slug,
        description=refined.strip(),
        status=feature.status.value,
        created_at=feature.created_at,
    )


@features_router.post(
    "/projects/{project_id}/features/{feature_identifier}/apply-improvement",
    response_model=FeatureResponse,
)
async def apply_feature_improvement(
    project_id: str,
    feature_identifier: str,
    request: Request,
    _principal: Annotated[Principal, Depends(get_principal)],
) -> FeatureResponse:
    from pydantic import BaseModel

    class ApplyReq(BaseModel):
        title: str
        description: str

    body = await request.json()
    payload = ApplyReq(**body) if isinstance(body, dict) else ApplyReq(title="", description="")

    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    feature_repo = request.app.state.feature_repo
    fid = await _resolve_feature_identifier(feature_repo, pid, feature_identifier)
    feature = await feature_repo.get(fid)
    if feature is None:
        raise FeatureNotFoundError(str(fid))
    if feature.status.value != "borrador":
        raise FeatureNotEditableError(str(fid), feature.status.value)

    feature.title = payload.title
    feature.description = payload.description
    await feature_repo.update(feature)
    return _to_feature_response(feature)


@features_router.delete(
    "/projects/{project_id}/features/{feature_identifier}",
    status_code=204,
)
async def delete_feature(
    project_id: str,
    feature_identifier: str,
    request: Request,
    _principal: Annotated[Principal, Depends(get_principal)],
) -> None:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    fid = await _resolve_feature_identifier(request.app.state.feature_repo, pid, feature_identifier)
    uc = DeleteFeatureUseCase(feature_repo=request.app.state.feature_repo)
    try:
        await uc.execute(fid)
    except FeatureNotFoundError:
        raise


@features_router.patch(
    "/projects/{project_id}/features/{feature_identifier}/status",
    response_model=FeatureResponse,
)
async def toggle_feature_status(
    project_id: str,
    feature_identifier: str,
    payload: ToggleStatusRequest,
    request: Request,
    _principal: Annotated[Principal, Depends(get_principal)],
) -> FeatureResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    fid = await _resolve_feature_identifier(request.app.state.feature_repo, pid, feature_identifier)
    uc = ToggleFeatureStatusUseCase(feature_repo=request.app.state.feature_repo)
    feature = await uc.execute(fid, target_status=payload.status)
    return _to_feature_response(feature)


@features_router.post(
    "/projects/{project_id}/features/suggest/save",
    response_model=FeaturesListResponse,
    status_code=201,
)
async def save_selected_suggestions(
    project_id: str,
    payload: SaveSuggestionsRequest,
    request: Request,
    _principal: Annotated[Principal, Depends(get_principal)],
) -> FeaturesListResponse:
    pid = await _resolve_project_identifier(request.app.state.project_repo, project_id)
    uc = SaveSelectedSuggestionsUseCase(
        feature_repo=request.app.state.feature_repo,
    )
    try:
        features = await uc.execute(pid, payload.features)
    except ProjectNotFoundError:
        raise
    return FeaturesListResponse(
        features=[_to_feature_response(f) for f in features],
        total=len(features),
    )
