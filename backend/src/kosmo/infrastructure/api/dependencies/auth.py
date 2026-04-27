from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from kosmo.application.auth import VerifyAccessToken
from kosmo.contracts.auth import (
    AuthError,
    MissingTokenError,
    Principal,
    TokenExpiredError,
    TokenRevokedError,
)

_bearer_scheme = HTTPBearer(auto_error=False, description="JWT de acceso (RS256)")


def _verify_use_case(request: Request) -> VerifyAccessToken:
    return request.app.state.verify_access_token


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    verify: Annotated[VerifyAccessToken, Depends(_verify_use_case)],
) -> Principal:
    if credentials is None:
        raise _to_http(MissingTokenError("Missing bearer token"))
    try:
        return await verify.execute(credentials.credentials)
    except AuthError as exc:
        raise _to_http(exc) from exc


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
