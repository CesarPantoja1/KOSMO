from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from kosmo.application.auth import (
    AuthorizeWithPkce,
    ExchangeAuthorizationCode,
    RefreshTokenPair,
    RegisterUser,
    RevokeSession,
)
from kosmo.contracts.auth import (
    AuthorizationCodeError,
    InvalidCredentialsError,
    InvalidTokenError,
    PkceMismatchError,
    Principal,
    TokenExpiredError,
    TokenReusedError,
    TokenRevokedError,
    UserAlreadyExistsError,
)
from kosmo.infrastructure.api.dependencies.auth import get_principal
from kosmo.infrastructure.api.schemas import (
    AuthorizationCodeResponse,
    AuthorizeRequest,
    LogoutRequest,
    OAuthErrorResponse,
    PrincipalView,
    RegisterRequest,
    TokenExchangeRequest,
    TokenPairResponse,
    TokenRefreshRequest,
    UserPublic,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _register(request: Request) -> RegisterUser:
    return request.app.state.register_user


def _authorize(request: Request) -> AuthorizeWithPkce:
    return request.app.state.authorize_with_pkce


def _exchange(request: Request) -> ExchangeAuthorizationCode:
    return request.app.state.exchange_authorization_code


def _refresh(request: Request) -> RefreshTokenPair:
    return request.app.state.refresh_token_pair


def _revoke(request: Request) -> RevokeSession:
    return request.app.state.revoke_session


def _oauth_error(*, status_code: int, error: str, description: str) -> JSONResponse:
    body = OAuthErrorResponse(error=error, error_description=description)
    return JSONResponse(status_code=status_code, content=body.model_dump())


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_409_CONFLICT: {"model": OAuthErrorResponse}},
)
async def register(
    payload: Annotated[RegisterRequest, Body(...)],
    use_case: Annotated[RegisterUser, Depends(_register)],
) -> UserPublic:
    try:
        user = await use_case.execute(email=str(payload.email), password=payload.password)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email ya registrado",
        ) from exc
    return UserPublic(id=user.id, email=user.email, created_at=user.created_at)


@router.post(
    "/authorize",
    response_model=AuthorizationCodeResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": OAuthErrorResponse}},
)
async def authorize(
    payload: Annotated[AuthorizeRequest, Body(...)],
    use_case: Annotated[AuthorizeWithPkce, Depends(_authorize)],
) -> AuthorizationCodeResponse | JSONResponse:
    try:
        entry = await use_case.execute(
            email=str(payload.email),
            password=payload.password,
            code_challenge=payload.code_challenge,
            scopes=frozenset(payload.scopes),
        )
    except InvalidCredentialsError:
        return _oauth_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="invalid_grant",
            description="Credenciales inválidas",
        )
    expires_in = max(
        int((entry.expires_at - datetime.now(UTC)).total_seconds()),
        1,
    )
    return AuthorizationCodeResponse(authorization_code=entry.code, expires_in=expires_in)


@router.post(
    "/token",
    response_model=TokenPairResponse,
    responses={status.HTTP_400_BAD_REQUEST: {"model": OAuthErrorResponse}},
)
async def token(
    payload: Annotated[TokenExchangeRequest, Body(...)],
    use_case: Annotated[ExchangeAuthorizationCode, Depends(_exchange)],
) -> TokenPairResponse | JSONResponse:
    try:
        pair = await use_case.execute(code=payload.code, code_verifier=payload.code_verifier)
    except AuthorizationCodeError as exc:
        return _oauth_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="invalid_grant",
            description=str(exc) or "Código de autorización inválido",
        )
    except PkceMismatchError as exc:
        return _oauth_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="invalid_grant",
            description=str(exc) or "code_verifier no coincide",
        )
    return TokenPairResponse.from_pair(pair)


@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": OAuthErrorResponse}},
)
async def refresh(
    payload: Annotated[TokenRefreshRequest, Body(...)],
    use_case: Annotated[RefreshTokenPair, Depends(_refresh)],
) -> TokenPairResponse | JSONResponse:
    try:
        pair = await use_case.execute(payload.refresh_token, scopes=frozenset())
    except TokenReusedError as exc:
        return _oauth_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="invalid_grant",
            description=str(exc) or "Refresh token reusado, sesión revocada",
        )
    except TokenExpiredError:
        return _oauth_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="invalid_grant",
            description="Refresh token expirado",
        )
    except (InvalidTokenError, TokenRevokedError) as exc:
        return _oauth_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="invalid_grant",
            description=str(exc) or "Refresh token inválido",
        )
    return TokenPairResponse.from_pair(pair)


@router.get("/me", response_model=PrincipalView)
async def me(principal: Annotated[Principal, Depends(get_principal)]) -> PrincipalView:
    return PrincipalView(subject=principal.subject, scopes=sorted(principal.scopes))


@router.post("/logout")
async def logout(
    payload: Annotated[LogoutRequest, Body(...)],
    principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[RevokeSession, Depends(_revoke)],
    request: Request,
) -> Response:
    _ = principal
    bearer = request.headers.get("authorization", "")
    access_token = bearer.removeprefix("Bearer ").strip()
    try:
        await use_case.execute(access_token=access_token, refresh_token=payload.refresh_token)
    except (InvalidTokenError, TokenExpiredError, TokenRevokedError) as exc:
        return _oauth_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="invalid_token",
            description=str(exc) or "Token inválido",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
