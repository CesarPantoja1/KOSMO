from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from kosmo.contracts.auth import (
    InvalidTokenError,
    IssuedToken,
    TokenClaims,
    TokenExpiredError,
    TokenType,
)


@dataclass(frozen=True, slots=True)
class JwtSettings:
    algorithm: str
    issuer: str
    audience: str
    access_ttl_seconds: int
    refresh_ttl_seconds: int


@dataclass(frozen=True, slots=True)
class _SigningKeys:
    private_pem: str
    public_pem: str


def load_signing_keys(*, private_key_path: str, public_key_path: str) -> _SigningKeys:
    private_pem = Path(private_key_path).read_text(encoding="utf-8")
    public_pem = Path(public_key_path).read_text(encoding="utf-8")
    return _SigningKeys(private_pem=private_pem, public_pem=public_pem)


def _ttl_for(token_type: TokenType, settings: JwtSettings) -> int:
    if token_type is TokenType.ACCESS:
        return settings.access_ttl_seconds
    return settings.refresh_ttl_seconds


class JoseJwtIssuer:
    def __init__(self, *, private_key_pem: str, settings: JwtSettings) -> None:
        self._private_key = private_key_pem
        self._settings = settings

    def issue(
        self, *, subject: str, scopes: frozenset[str], token_type: TokenType
    ) -> IssuedToken:
        now = datetime.now(UTC)
        ttl = _ttl_for(token_type, self._settings)
        expires_at = now + timedelta(seconds=ttl)
        jti = uuid4().hex
        claims: dict[str, Any] = {
            "sub": subject,
            "iss": self._settings.issuer,
            "aud": self._settings.audience,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": jti,
            "type": token_type.value,
            "scopes": sorted(scopes),
        }
        token = jwt.encode(claims, self._private_key, algorithm=self._settings.algorithm)
        return IssuedToken(token=token, jti=jti, expires_at=expires_at, token_type=token_type)


class JoseJwtVerifier:
    def __init__(self, *, public_key_pem: str, settings: JwtSettings) -> None:
        self._public_key = public_key_pem
        self._settings = settings

    def verify(self, token: str, *, expected_type: TokenType) -> TokenClaims:
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._public_key,
                algorithms=[self._settings.algorithm],
                audience=self._settings.audience,
                issuer=self._settings.issuer,
            )
        except ExpiredSignatureError as exc:
            raise TokenExpiredError("Token expired") from exc
        except (JWTClaimsError, JWTError) as exc:
            raise InvalidTokenError(str(exc)) from exc

        token_type_raw = payload.get("type")
        if token_type_raw != expected_type.value:
            raise InvalidTokenError(
                f"Unexpected token type: got {token_type_raw!r}, expected {expected_type.value!r}"
            )

        try:
            return TokenClaims(
                subject=str(payload["sub"]),
                jti=str(payload["jti"]),
                issued_at=datetime.fromtimestamp(int(payload["iat"]), tz=UTC),
                expires_at=datetime.fromtimestamp(int(payload["exp"]), tz=UTC),
                token_type=TokenType(token_type_raw),
                scopes=frozenset(payload.get("scopes") or []),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidTokenError(f"Malformed claims: {exc}") from exc
