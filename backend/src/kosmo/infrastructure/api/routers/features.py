from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from kosmo.application.features import (
    GenerateFeaturesInput,
    GenerateFeaturesUseCase,
    SaveSelectedFeaturesInput,
    SaveSelectedFeaturesUseCase,
    SuggestFeaturesInput,
    SuggestFeaturesUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    LLMInvocationError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.repositories import FeatureRepository
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas import (
    FeatureResponse,
    FeatureSuggestionResponse,
    SaveSelectedFeaturesRequest,
)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/features",
    tags=["features"],
)


def _generate_features(request: Request) -> GenerateFeaturesUseCase:
    return request.app.state.generate_features


def _suggest_features(request: Request) -> SuggestFeaturesUseCase:
    return request.app.state.suggest_features


def _save_selected_features(request: Request) -> SaveSelectedFeaturesUseCase:
    return request.app.state.save_selected_features


def _feature_repo(request: Request) -> FeatureRepository:
    return request.app.state.feature_repo


@router.post(
    "",
    summary="Generar características con IA",
    description=(
        "Genera las características del producto software a partir del "
        "documento de descubrimiento utilizando inteligencia artificial. "
        "Requiere autenticación mediante Bearer token."
    ),
    response_model=list[FeatureResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "description": "Características generadas exitosamente.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token de acceso inválido o ausente.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Proyecto o documento de descubrimiento no encontrado.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "description": "Error al invocar el servicio de IA.",
        },
    },
)
async def generate_features(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[GenerateFeaturesUseCase, Depends(_generate_features)],
) -> list[FeatureResponse]:
    try:
        output = await use_case.execute(
            GenerateFeaturesInput(project_id=ProjectId(project_id))
        )
    except (ProjectNotFoundError, DocumentNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc
    except LLMInvocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.problem.detail,
        ) from exc
    return [_feature_to_response(f) for f in output.features]


@router.get(
    "",
    summary="Listar características del proyecto",
    description=(
        "Devuelve todas las características asociadas a un proyecto. "
        "Requiere autenticación mediante Bearer token."
    ),
    response_model=list[FeatureResponse],
    responses={
        status.HTTP_200_OK: {
            "description": "Lista de características del proyecto.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token de acceso inválido o ausente.",
        },
    },
)
async def list_features(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    repo: Annotated[FeatureRepository, Depends(_feature_repo)],
) -> list[FeatureResponse]:
    features = await repo.list_by_project(ProjectId(project_id))
    return [_feature_to_response(f) for f in features]


@router.post(
    "/suggest",
    summary="Sugerir nuevas características",
    description=(
        "Sugiere 3 características adicionales basadas en el documento "
        "de descubrimiento, evitando duplicar las existentes. "
        "Requiere autenticación mediante Bearer token."
    ),
    response_model=list[FeatureSuggestionResponse],
    responses={
        status.HTTP_200_OK: {
            "description": "Sugerencias de características generadas.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token de acceso inválido o ausente.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Documento de descubrimiento no encontrado.",
        },
    },
)
async def suggest_features(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[SuggestFeaturesUseCase, Depends(_suggest_features)],
) -> list[FeatureSuggestionResponse]:
    try:
        output = await use_case.execute(
            SuggestFeaturesInput(project_id=ProjectId(project_id))
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc
    return [
        FeatureSuggestionResponse(
            number=s.number,
            title=s.title,
            description=s.description,
            rationale=s.rationale,
            inferred_from=s.inferred_from,
        )
        for s in output.suggestions
    ]


@router.post(
    "/save",
    summary="Guardar características seleccionadas",
    description=(
        "Guarda las características que el usuario seleccionó desde las "
        "sugerencias de la IA. Requiere autenticación mediante Bearer token."
    ),
    response_model=list[FeatureResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "description": "Características guardadas exitosamente.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token de acceso inválido o ausente.",
        },
    },
)
async def save_selected_features(
    project_id: str,
    payload: Annotated[SaveSelectedFeaturesRequest, Body(...)],
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[SaveSelectedFeaturesUseCase, Depends(_save_selected_features)],
) -> list[FeatureResponse]:
    items: list[dict[str, str]] = [
        {
            "title": f.title,
            "description": f.description,
            "rationale": f.rationale,
        }
        for f in payload.features
    ]
    output = await use_case.execute(
        SaveSelectedFeaturesInput(
            project_id=ProjectId(project_id),
            features=items,
        )
    )
    return [_feature_to_response(f) for f in output.features]


def _feature_to_response(f: Any) -> FeatureResponse:
    inferred: list[str] = (
        [str(x) for x in f.inferred_from]  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportUnknownArgumentType]
        if isinstance(f.inferred_from, list)
        else []
    )
    return FeatureResponse(
        id=str(f.id),
        project_id=str(f.project_id),
        number=f.number,
        title=f.title,
        slug=f.slug,
        description=f.description,
        rationale=f.rationale,
        inferred_from=inferred,
        display_id=f.display_id,
    )
