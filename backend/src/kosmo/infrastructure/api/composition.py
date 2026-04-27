from dataclasses import dataclass

from redis.asyncio import Redis

from kosmo.application.auth import (
    IssueTokenPair,
    RefreshTokenPair,
    RevokeSession,
    VerifyAccessToken,
)
from kosmo.config import Settings
from kosmo.infrastructure.persistence.redis import RedisTokenRevocationStore
from kosmo.infrastructure.security import (
    JoseJwtIssuer,
    JoseJwtVerifier,
    JwtSettings,
    load_signing_keys,
)


@dataclass(frozen=True, slots=True)
class AuthComponents:
    redis: Redis
    issue_token_pair: IssueTokenPair
    verify_access_token: VerifyAccessToken
    refresh_token_pair: RefreshTokenPair
    revoke_session: RevokeSession


def build_auth_components(settings: Settings) -> AuthComponents:
    keys = load_signing_keys(
        private_key_path=settings.jwt_private_key_path,
        public_key_path=settings.jwt_public_key_path,
    )
    jwt_settings = JwtSettings(
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        access_ttl_seconds=settings.jwt_access_ttl_seconds,
        refresh_ttl_seconds=settings.jwt_refresh_ttl_seconds,
    )
    issuer = JoseJwtIssuer(private_key_pem=keys.private_pem, settings=jwt_settings)
    verifier = JoseJwtVerifier(public_key_pem=keys.public_pem, settings=jwt_settings)
    redis: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        settings.redis_url.get_secret_value()
    )
    store = RedisTokenRevocationStore(redis)

    return AuthComponents(
        redis=redis,
        issue_token_pair=IssueTokenPair(issuer=issuer, revocation_store=store),
        verify_access_token=VerifyAccessToken(verifier=verifier, revocation_store=store),
        refresh_token_pair=RefreshTokenPair(
            issuer=issuer, verifier=verifier, revocation_store=store
        ),
        revoke_session=RevokeSession(verifier=verifier, revocation_store=store),
    )
