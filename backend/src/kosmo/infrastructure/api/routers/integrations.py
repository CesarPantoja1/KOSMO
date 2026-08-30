from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from kosmo.application.integrations.link_github_account import (
    LinkGitHubAccountCommand,
    LinkGitHubAccountUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.integrations.github import (
    GitHubApiError,
    GitHubAuthenticationError,
    GitHubPermissionError,
)
from kosmo.contracts.sdd.ids import UserId
from kosmo.infrastructure.api.dependencies import (
    get_container,
    get_link_github_account_use_case,
    get_principal,
)
from kosmo.infrastructure.api.schemas import (
    ConnectOAuthRequest,
    IntegrationStatusResponse,
)

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


@router.post(
    "/{provider}/connect",
    response_model=IntegrationStatusResponse,
    summary="Vincular cuenta de plataforma externa mediante OAuth",
    description="Procesa el código de autorización temporal e intercambia credenciales.",
)
async def connect_oauth(
    provider: str,
    body: ConnectOAuthRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[LinkGitHubAccountUseCase, Depends(get_link_github_account_use_case)],
) -> IntegrationStatusResponse:
    if provider.lower() != "github":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proveedor de integración '{provider}' no soportado.",
        )

    try:
        cmd = LinkGitHubAccountCommand(
            code=body.code,
        )
        integration = await use_case.execute(principal, cmd)
    except GitHubAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except GitHubPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except GitHubApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return IntegrationStatusResponse(
        provider=provider.lower(),
        is_connected=True,
        username=integration.github_username,
        connected_at=integration.updated_at,
    )


@router.get(
    "/{provider}/status",
    response_model=IntegrationStatusResponse,
    summary="Consultar estado de vinculación de plataforma externa",
    description="Verifica si el usuario tiene una cuenta vinculada activa para la plataforma.",
)
async def get_integration_status(
    provider: str,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> IntegrationStatusResponse:
    if provider.lower() != "github":
        return IntegrationStatusResponse(
            provider=provider.lower(),
            is_connected=False,
            username=None,
            connected_at=None,
        )

    container = get_container(request)
    integration = await container.repos.user_github_integrations.get_by_user_id(UserId(principal.subject))
    if integration is None:
        return IntegrationStatusResponse(
            provider=provider.lower(),
            is_connected=False,
            username=None,
            connected_at=None,
        )

    return IntegrationStatusResponse(
        provider=provider.lower(),
        is_connected=True,
        username=integration.github_username,
        connected_at=integration.updated_at,
    )


@router.delete(
    "/{provider}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desvincular plataforma externa",
    description="Revoca y elimina las credenciales OAuth almacenadas de la plataforma.",
)
async def disconnect_integration(
    provider: str,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
) -> Response:
    if provider.lower() != "github":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La integración '{provider}' no se encuentra vinculada",
        )

    container = get_container(request)
    user_id = UserId(principal.subject)
    existing = await container.repos.user_github_integrations.get_by_user_id(user_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La integración no se encuentra vinculada",
        )

    await container.repos.user_github_integrations.delete_by_user_id(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
