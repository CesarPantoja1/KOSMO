from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from kosmo.application.auth import IssueTokenPair, RefreshTokenPair, RevokeSession
from kosmo.contracts.auth import AuthError, Principal, TokenPair
from kosmo.infrastructure.api.dependencies.auth import get_principal, require_scopes

router = APIRouter(prefix="/api/v1/auth/demo", tags=["auth-demo"])


class IssueRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=128)
    scopes: list[str] = Field(default_factory=list)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)
    scopes: list[str] = Field(default_factory=list)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenView(BaseModel):
    token: str
    jti: str
    expires_at: str


class TokenPairView(BaseModel):
    access: TokenView
    refresh: TokenView

    @classmethod
    def from_pair(cls, pair: TokenPair) -> "TokenPairView":
        return cls(
            access=TokenView(
                token=pair.access.token,
                jti=pair.access.jti,
                expires_at=pair.access.expires_at.isoformat(),
            ),
            refresh=TokenView(
                token=pair.refresh.token,
                jti=pair.refresh.jti,
                expires_at=pair.refresh.expires_at.isoformat(),
            ),
        )


class PrincipalView(BaseModel):
    subject: str
    scopes: list[str]


def _issue(request: Request) -> IssueTokenPair:
    return request.app.state.issue_token_pair


def _refresh(request: Request) -> RefreshTokenPair:
    return request.app.state.refresh_token_pair


def _revoke(request: Request) -> RevokeSession:
    return request.app.state.revoke_session


@router.post("/token", response_model=TokenPairView, status_code=status.HTTP_201_CREATED)
async def issue_token(
    payload: Annotated[IssueRequest, Body(...)],
    use_case: Annotated[IssueTokenPair, Depends(_issue)],
) -> TokenPairView:
    pair = await use_case.execute(subject=payload.subject, scopes=frozenset(payload.scopes))
    return TokenPairView.from_pair(pair)


@router.post("/refresh", response_model=TokenPairView)
async def refresh_token(
    payload: Annotated[RefreshRequest, Body(...)],
    use_case: Annotated[RefreshTokenPair, Depends(_refresh)],
) -> TokenPairView:
    try:
        pair = await use_case.execute(
            payload.refresh_token, scopes=frozenset(payload.scopes)
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc) or "Invalid refresh token"
        ) from exc
    return TokenPairView.from_pair(pair)


@router.get("/me", response_model=PrincipalView)
async def whoami(principal: Annotated[Principal, Depends(get_principal)]) -> PrincipalView:
    return PrincipalView(subject=principal.subject, scopes=sorted(principal.scopes))


@router.get("/admin", response_model=PrincipalView)
async def admin_only(
    principal: Annotated[Principal, Depends(require_scopes("admin"))],
) -> PrincipalView:
    return PrincipalView(subject=principal.subject, scopes=sorted(principal.scopes))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: Annotated[LogoutRequest, Body(...)],
    principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[RevokeSession, Depends(_revoke)],
    request: Request,
) -> None:
    _ = principal
    bearer = request.headers.get("authorization", "")
    access_token = bearer.removeprefix("Bearer ").strip()
    try:
        await use_case.execute(access_token=access_token, refresh_token=payload.refresh_token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc) or "Invalid token"
        ) from exc
