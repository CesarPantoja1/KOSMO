from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class PkceMethod(StrEnum):
    S256 = "S256"


@dataclass(frozen=True, slots=True)
class AuthorizationCode:
    code: str
    subject: str
    code_challenge: str
    code_challenge_method: PkceMethod
    expires_at: datetime
    scopes: frozenset[str] = field(default_factory=lambda: frozenset[str]())
