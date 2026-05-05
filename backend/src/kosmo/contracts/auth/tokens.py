from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token: str
    jti: str
    expires_at: datetime
    token_type: TokenType
    family_id: str | None = None


@dataclass(frozen=True, slots=True)
class TokenPair:
    access: IssuedToken
    refresh: IssuedToken


@dataclass(frozen=True, slots=True)
class TokenClaims:
    subject: str
    jti: str
    issued_at: datetime
    expires_at: datetime
    token_type: TokenType
    scopes: frozenset[str] = field(default_factory=lambda: frozenset[str]())
    family_id: str | None = None


@dataclass(frozen=True, slots=True)
class RefreshConsumeResult:
    subject: str
    family_id: str | None = None
