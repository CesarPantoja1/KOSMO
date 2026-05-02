"""DTOs Pydantic expuestos por la API HTTP.

Pertenecen al adaptador de entrada (FastAPI), por lo que viven en infraestructura
y pueden referenciar entidades de dominio para conversión I/O sin invertir capas.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from kosmo.contracts.auth import TokenPair


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class AuthorizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    code_challenge: str = Field(min_length=43, max_length=128)
    code_challenge_method: Literal["S256"] = "S256"
    scopes: list[str] = Field(default_factory=list)


class AuthorizationCodeResponse(BaseModel):
    authorization_code: str
    expires_in: int = Field(ge=1, le=600)


class TokenExchangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grant_type: Literal["authorization_code"]
    code: str = Field(min_length=1, max_length=256)
    code_verifier: str = Field(min_length=43, max_length=128)


class TokenRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grant_type: Literal["refresh_token"]
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str | None = None


class TokenView(BaseModel):
    token: str
    jti: str
    expires_at: datetime


class TokenPairResponse(BaseModel):
    access: TokenView
    refresh: TokenView
    token_type: Literal["Bearer"] = "Bearer"

    @classmethod
    def from_pair(cls, pair: TokenPair) -> "TokenPairResponse":
        return cls(
            access=TokenView(
                token=pair.access.token,
                jti=pair.access.jti,
                expires_at=pair.access.expires_at,
            ),
            refresh=TokenView(
                token=pair.refresh.token,
                jti=pair.refresh.jti,
                expires_at=pair.refresh.expires_at,
            ),
        )


class PrincipalView(BaseModel):
    subject: str
    scopes: list[str]


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime


class OAuthErrorResponse(BaseModel):
    error: str
    error_description: str
