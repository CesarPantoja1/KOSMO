from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from kosmo.application.integrations.link_deployment_provider import (
    LinkDeploymentPlatformCommand,
    LinkDeploymentPlatformUseCase,
)
from kosmo.application.integrations.link_github_account import (
    LinkGitHubAccountCommand,
    LinkGitHubAccountUseCase,
)
from kosmo.contracts.auth import Principal
from kosmo.contracts.integrations.deployment import (
    DeploymentApiError,
    DeploymentAuthenticationError,
    DeploymentPermissionError,
    DeploymentProvider,
)
from kosmo.contracts.integrations.github import (
    GitHubApiError,
    GitHubAuthenticationError,
    GitHubPermissionError,
)
from kosmo.contracts.sdd.ids import UserId
from kosmo.infrastructure.api.dependencies import (
    get_container,
    get_link_deployment_platform_use_case,
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
    github_use_case: Annotated[LinkGitHubAccountUseCase, Depends(get_link_github_account_use_case)],
    railway_use_case: Annotated[LinkDeploymentPlatformUseCase, Depends(get_link_deployment_platform_use_case)],
) -> IntegrationStatusResponse:
    provider_clean = provider.lower().strip()

    if provider_clean == "github":
        try:
            cmd = LinkGitHubAccountCommand(code=body.code)
            github_integration = await github_use_case.execute(principal, cmd)
            return IntegrationStatusResponse(
                provider="github",
                is_connected=True,
                username=github_integration.github_username,
                connected_at=github_integration.updated_at,
            )
        except GitHubAuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except GitHubPermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except GitHubApiError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    elif provider_clean == "railway":
        try:
            cmd_railway = LinkDeploymentPlatformCommand(
                code=body.code,
                provider=DeploymentProvider.RAILWAY,
                redirect_uri=body.redirect_uri,
            )
            railway_integration = await railway_use_case.execute(principal, cmd_railway)
            return IntegrationStatusResponse(
                provider="railway",
                is_connected=True,
                username=railway_integration.provider_username,
                connected_at=railway_integration.updated_at,
            )
        except DeploymentAuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except DeploymentPermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except DeploymentApiError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Proveedor de integración '{provider}' no soportado.",
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
    provider_clean = provider.lower().strip()
    container = get_container(request)
    user_id = UserId(principal.subject)

    if provider_clean == "github":
        integration = await container.repos.user_github_integrations.get_by_user_id(user_id)
        if integration is None:
            return IntegrationStatusResponse(
                provider="github",
                is_connected=False,
                username=None,
                connected_at=None,
            )
        return IntegrationStatusResponse(
            provider="github",
            is_connected=True,
            username=integration.github_username,
            connected_at=integration.updated_at,
        )

    elif provider_clean == "railway":
        deployment_integration = await container.repos.user_deployment_integrations.get_by_user_id(
            user_id, DeploymentProvider.RAILWAY
        )
        if deployment_integration is None:
            return IntegrationStatusResponse(
                provider="railway",
                is_connected=False,
                username=None,
                connected_at=None,
            )
        return IntegrationStatusResponse(
            provider="railway",
            is_connected=True,
            username=deployment_integration.provider_username,
            connected_at=deployment_integration.updated_at,
        )

    return IntegrationStatusResponse(
        provider=provider_clean,
        is_connected=False,
        username=None,
        connected_at=None,
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
    provider_clean = provider.lower().strip()
    container = get_container(request)
    user_id = UserId(principal.subject)

    if provider_clean == "github":
        existing_github = await container.repos.user_github_integrations.get_by_user_id(user_id)
        if existing_github is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La integración no se encuentra vinculada",
            )
        await container.repos.user_github_integrations.delete_by_user_id(user_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    elif provider_clean == "railway":
        existing_railway = await container.repos.user_deployment_integrations.get_by_user_id(
            user_id, DeploymentProvider.RAILWAY
        )
        if existing_railway is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La integración no se encuentra vinculada",
            )
        await container.repos.user_deployment_integrations.delete_by_user_id(user_id, DeploymentProvider.RAILWAY)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"La integración '{provider}' no se encuentra vinculada",
    )
