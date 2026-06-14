from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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


def _ttl_for(token_type: TokenType, settings: JwtSettings) -> int:
    if token_type is TokenType.ACCESS:
        return settings.access_ttl_seconds
    return settings.refresh_ttl_seconds


class JoseJwtIssuer:
    def __init__(self, *, private_key_pem: str, settings: JwtSettings) -> None:
        self._private_key = private_key_pem
        self._settings = settings

    def issue(
        self,
        *,
        subject: str,
        scopes: frozenset[str],
        token_type: TokenType,
        family_id: str | None = None,
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
        if family_id is not None:
            claims["fam"] = family_id
        token = jwt.encode(claims, self._private_key, algorithm=self._settings.algorithm)
        return IssuedToken(
            token=token,
            jti=jti,
            expires_at=expires_at,
            token_type=token_type,
            family_id=family_id,
        )


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
            raise TokenExpiredError("Token expirado") from exc
        except JWTClaimsError as exc:
            raise InvalidTokenError(f"Claims invalidos: {exc}") from exc
        except JWTError as exc:
            raise InvalidTokenError(f"Token mal formado: {exc}") from exc

        token_type = payload.get("type")
        if token_type != expected_type.value:
            raise InvalidTokenError(
                f"Tipo de token incorrecto: esperado {expected_type.value}, obtenido {token_type}"
            )

        return TokenClaims(
            subject=payload["sub"],
            scopes=frozenset(payload.get("scopes", [])),
            jti=payload["jti"],
            token_type=TokenType(token_type),
            issued_at=datetime.fromtimestamp(payload["iat"], tz=UTC),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            family_id=payload.get("fam"),
        )
