from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from kosmo.application.auth import VerifyAccessToken
from kosmo.config import settings
from kosmo.contracts.auth import (
    AuthError,
    MissingTokenError,
    Principal,
    TokenExpiredError,
    TokenRevokedError,
)
from kosmo.contracts.auth.context import current_user_id
from kosmo.contracts.sdd.ids import ProjectId
from kosmo.contracts.sdd.project import Project
from kosmo.infrastructure.api.dependencies.container import get_container

_bearer_scheme = HTTPBearer(auto_error=False, description="JWT de acceso (RS256)")


async def get_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> Principal:
    if settings.auth_disabled:
        mock_user = request.headers.get("x-mock-user", "dev_user")
        principal = Principal(subject=mock_user, scopes=frozenset({"*"}))
        current_user_id.set(principal.subject)
        return principal
    if credentials is None:
        raise _to_http(MissingTokenError("Missing bearer token"))
    container = get_container(request)
    assert container.auth is not None
    verify: VerifyAccessToken = container.auth.verify_access_token
    try:
        principal = await verify.execute(credentials.credentials)
        current_user_id.set(principal.subject)
        return principal
    except AuthError as exc:
        raise _to_http(exc) from exc


async def require_project_owner(
    container: Any,
    project_id: ProjectId | str,
    principal: Principal,
) -> Project | None:
    """Verifica que el proyecto exista y pertenezca al usuario autenticado (IDOR / BOLA guard).

    Si no existe o pertenece a otro usuario, responde 404 para ocultar su existencia.
    """
    if not hasattr(container, "repos") or not hasattr(container.repos, "projects"):
        return None
    pid = ProjectId(str(project_id))
    project = await container.repos.projects.by_id(pid)
    if project is None or str(getattr(project, "owner_id", "")) != principal.subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proyecto '{project_id}' no encontrado.",
        )
    return project


async def verify_project_owner(
    project_id: str,
    principal: Annotated[Principal, Depends(get_principal)],
    request: Request,
) -> None:
    """Dependencia FastAPI para routers con {project_id} en el path."""
    container = get_container(request)
    await require_project_owner(container, project_id, principal)


def require_scopes(
    *required: str,
) -> Callable[[Principal], Coroutine[Any, Any, Principal]]:
    needed = frozenset(required)

    async def _dependency(
        principal: Annotated[Principal, Depends(get_principal)],
    ) -> Principal:
        if not principal.has_scopes(needed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient scope",
            )
        return principal

    return _dependency


def _to_http(error: AuthError) -> HTTPException:
    if isinstance(error, MissingTokenError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error) or "Missing credentials",
            headers={"WWW-Authenticate": 'Bearer realm="kosmo"'},
        )
    if isinstance(error, TokenExpiredError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    if isinstance(error, TokenRevokedError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
    )
