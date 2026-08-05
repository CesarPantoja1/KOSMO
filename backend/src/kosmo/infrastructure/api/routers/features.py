from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from kosmo.application.features import (
    CreateCharacteristicInput,
    CreateCharacteristicUseCase,
    EditFeatureInput,
    EditFeatureUseCase,
    GenerateFeaturesInput,
    GenerateFeaturesUseCase,
    SaveSelectedFeaturesInput,
    SaveSelectedFeaturesUseCase,
    SuggestFeaturesInput,
    SuggestFeaturesUseCase,
)
from kosmo.application.features.delete_feature import DeleteFeatureUseCase
from kosmo.application.features.list_features import (
    ListFeaturesInput,
    ListFeaturesUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.sdd.errors import (
    DocumentNotFoundError,
    FeatureNotFoundError,
    ProjectNotFoundError,
)
from kosmo.contracts.sdd.ids import FeatureId, ProjectId
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.dependencies.rate_limit import ProjectGenerationRateLimiter
from kosmo.infrastructure.api.schemas import (
    CreateCharacteristicRequest,
    EditFeatureManualRequest,
    FeatureResponse,
    FeatureSuggestionResponse,
    PhaseNotificationList,
    PhaseNotificationView,
    PropagateFeatureChangesRequest,
    SaveSelectedFeaturesRequest,
)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/features",
    tags=["features"],
)

_generation_rate_limiter = ProjectGenerationRateLimiter(requests_per_hour=20)


def _generate_features(request: Request) -> GenerateFeaturesUseCase:
    return request.app.state.generate_features


def _suggest_features(request: Request) -> SuggestFeaturesUseCase:
    return request.app.state.suggest_features


def _save_selected_features(request: Request) -> SaveSelectedFeaturesUseCase:
    return request.app.state.save_selected_features


def _create_characteristic(request: Request) -> CreateCharacteristicUseCase:
    return request.app.state.create_characteristic


def _edit_feature(request: Request) -> EditFeatureUseCase:
    return request.app.state.edit_feature


def _list_features(request: Request) -> ListFeaturesUseCase:
    return request.app.state.list_features


@router.post(
    "",
    summary="Generar características del producto con IA",
    description=(
        "Genera características de alto nivel evaluando el documento de "
        "descubrimiento del proyecto. Las características representan capacidades "
        "funcionales del producto software a construir."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Características generadas exitosamente."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Token de acceso inválido o ausente."},
    },
)
async def generate_features(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    _rate: Annotated[None, Depends(_generation_rate_limiter)],
    use_case: Annotated[GenerateFeaturesUseCase, Depends(_generate_features)],
) -> dict[str, Any]:
    output = await use_case.execute(GenerateFeaturesInput(project_id=ProjectId(project_id)))
    return {
        "project_id": str(output.project_id),
        "features": [
            {
                "id": str(f.id),
                "title": f.title,
                "description": f.description,
                "origin": f.origin,
                "created_at": f.created_at.isoformat().replace("+00:00", "Z"),
                "updated_at": f.updated_at.isoformat().replace("+00:00", "Z"),
            }
            for f in output.features
        ],
    }


@router.get(
    "",
    summary="Listar características del proyecto",
    description=(
        "Devuelve todas las características asociadas a un proyecto. Requiere autenticación mediante Bearer token."
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
    uc: Annotated[ListFeaturesUseCase, Depends(_list_features)],
) -> list[FeatureResponse]:
    output = await uc.execute(ListFeaturesInput(project_id=ProjectId(project_id)))
    return [_feature_to_response(f) for f in output.features]


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
        status.HTTP_502_BAD_GATEWAY: {
            "description": "Error al invocar el servicio de IA.",
        },
    },
)
async def suggest_features(
    project_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[SuggestFeaturesUseCase, Depends(_suggest_features)],
) -> list[FeatureSuggestionResponse]:
    try:
        output = await use_case.execute(SuggestFeaturesInput(project_id=ProjectId(project_id)))
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al generar sugerencias: {exc}",
        ) from exc
    return [
        FeatureSuggestionResponse(
            number=s.number,
            title=s.title,
            description=s.description,
            origin=s.origin,
        )
        for s in output.suggestions
    ]


@router.post(
    "/manual",
    summary="Crear característica manualmente",
    description=(
        "Crea una nueva característica con los datos proporcionados por el usuario. "
        "El título no puede exceder 50 caracteres y la descripción no puede exceder 500 caracteres. "
        "Requiere autenticación mediante Bearer token."
    ),
    response_model=FeatureResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "description": "Característica creada exitosamente.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Datos de entrada inválidos (título vacío, título muy largo, descripción muy larga).",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token de acceso inválido o ausente.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Error inesperado del servidor.",
        },
    },
)
async def create_characteristic_manual(
    project_id: str,
    payload: Annotated[CreateCharacteristicRequest, Body(...)],
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[CreateCharacteristicUseCase, Depends(_create_characteristic)],
) -> FeatureResponse:
    try:
        output = await use_case.execute(
            CreateCharacteristicInput(
                project_id=ProjectId(project_id),
                title=payload.title,
                description=payload.description,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return _feature_to_response(output.characteristic)


@router.put(
    "/{feature_id}/manual",
    summary="Editar característica manualmente",
    description=(
        "Edita una característica de forma manual. "
        "Si los cambios contradicen flagrantemente el documento de Descubrimiento, "
        "el guardado es rechazado por consistencia."
    ),
    response_model=FeatureResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Característica editada exitosamente.",
        },
        status.HTTP_409_CONFLICT: {
            "description": "Contradicción detectada. No se guardaron los cambios.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Característica no encontrada.",
        },
    },
)
async def edit_characteristic_manual(
    project_id: str,
    feature_id: str,
    payload: Annotated[EditFeatureManualRequest, Body(...)],
    _principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[EditFeatureUseCase, Depends(_edit_feature)],
) -> FeatureResponse:
    try:
        output = await use_case.execute(
            EditFeatureInput(
                project_id=ProjectId(project_id),
                feature_id=FeatureId(feature_id),
                title=payload.title,
                description=payload.description,
            )
        )
    except FeatureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.problem.detail,
        ) from exc

    if not output.is_saved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=output.inconsistency_reason or "Inconsistencia detectada en el documento.",
        )

    assert output.feature is not None
    return _feature_to_response(output.feature)


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
    items: list[dict[str, object]] = [
        {
            "title": f.title,
            "description": f.description,
            "origin": f.origin,
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
    return FeatureResponse(
        id=str(f.id),
        project_id=str(f.project_id),
        number=f.number,
        title=f.title,
        slug=f.slug,
        description=f.description,
        origin=f.origin,
        display_id=f.display_id,
    )


def _propagate_feature_changes(request: Request):
    return request.app.state.propagate_feature_changes


@router.post(
    "/{feature_id}/propagate",
    summary="Propagar cambios desde característica",
    description=(
        "Evalúa el impacto bidireccional de los cambios aplicados en una característica. "
        "Notifica fases afectadas upstream (Descubrimiento) y downstream (Requisitos, Modelo) "
        "para la actualización de insignias en el wizard."
    ),
    response_model=PhaseNotificationList,
    status_code=status.HTTP_200_OK,
)
async def propagate_feature_changes(
    project_id: str,
    feature_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    request: Annotated[PropagateFeatureChangesRequest, Body(...)],
    uc: Annotated[Any, Depends(_propagate_feature_changes)],
) -> PhaseNotificationList:
    from kosmo.application.consistency.propagate_feature_changes import (
        PropagateFeatureChangesInput,
    )
    from kosmo.contracts.sdd.ids import PlanChangeId

    try:
        output = await uc.execute(
            PropagateFeatureChangesInput(
                project_id=ProjectId(project_id),
                feature_id=FeatureId(feature_id),
                applied_change_ids=[PlanChangeId(cid) for cid in request.applied_change_ids],
            )
        )
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e

    return PhaseNotificationList(
        affected_phases=[
            PhaseNotificationView(
                phase=p.phase,
                affected_count=p.affected_count,
                affected_ids=p.affected_ids,
            )
            for p in output.affected_phases
        ]
    )


def _delete_feature_uc(request: Request) -> DeleteFeatureUseCase:
    return request.app.state.delete_feature


@router.delete(
    "/{feature_id}",
    summary="Eliminar característica",
    description="Elimina una característica y todos sus artefactos asociados (requisitos, diagrama).",
    status_code=status.HTTP_200_OK,
)
async def delete_feature(
    project_id: str,
    feature_id: str,
    _principal: Annotated[Principal, Depends(get_principal)],
    uc: Annotated[DeleteFeatureUseCase, Depends(_delete_feature_uc)],
) -> dict[str, str]:
    try:
        await uc.execute(
            project_id=ProjectId(project_id),
            feature_id=FeatureId(feature_id),
        )
    except FeatureNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.problem.detail) from e
    return {"status": "deleted", "feature_id": feature_id}
