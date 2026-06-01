from dataclasses import dataclass, field

from cryptography.fernet import Fernet
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from kosmo.application.auth import (
    AuthorizeWithPkce,
    ExchangeAuthorizationCode,
    IssueTokenPair,
    RefreshTokenPair,
    RegisterUser,
    RevokeSession,
    VerifyAccessToken,
)
from kosmo.config import Settings
from kosmo.contracts.audit import AuditEventSink
from kosmo.contracts.auth import LoginAttemptStore, PasswordHasher, SecretCipher, UserRepository
from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.repositories import (
    FeatureRepository,
    ProjectRepository,
    SpecRepository,
)
from kosmo.infrastructure.api.websocket.specs import broadcast_event
from kosmo.infrastructure.llm.noop_adapter import NoopLLMClient
from kosmo.infrastructure.persistence.postgres.repositories import (
    SqlAlchemyAuditEventSink,
    SqlAlchemyUserRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.feature_repo import (
    SqlAlchemyFeatureRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.project_repo import (
    SqlAlchemyProjectRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.sdd_repo import SqlAlchemySpecRepository
from kosmo.infrastructure.persistence.redis import (
    RedisAuthorizationCodeStore,
    RedisLoginAttemptStore,
    RedisTokenRevocationStore,
)
from kosmo.infrastructure.security import (
    Argon2idParameters,
    Argon2idPasswordHasher,
    FernetSecretCipher,
    JoseJwtIssuer,
    JoseJwtVerifier,
    JwtSettings,
)
from kosmo.infrastructure.security.key_vault import FernetApiKeyVault
from kosmo.infrastructure.storage.filesystem_blob_storage import FileSystemBlobStorage


@dataclass
class SDDComponents:
    spec_repo: SpecRepository
    project_repo: ProjectRepository
    feature_repo: FeatureRepository
    llm_client: LLMClient
    blob_storage: FileSystemBlobStorage
    api_key_vault: FernetApiKeyVault
    broadcast_event: object = field(default_factory=lambda: broadcast_event)


def build_sdd_components(
    settings: Settings,
    session_factory: callable,  # type: ignore[type-arg]
) -> SDDComponents:
    import structlog

    log = structlog.get_logger()

    spec_repo = SqlAlchemySpecRepository(session_factory)
    project_repo = SqlAlchemyProjectRepository(session_factory)
    feature_repo = SqlAlchemyFeatureRepository(session_factory)

    llm_client: LLMClient
    if settings.llm_provider == "deepseek":
        from kosmo.infrastructure.llm.deepseek_adapter import DeepSeekClient

        api_key = ""
        if settings.llm_api_key:
            api_key = settings.llm_api_key.get_secret_value()
        if not api_key:
            log.error("llm_provider=deepseek pero LLM_API_KEY esta vacia")
            raise ValueError(
                "LLM_PROVIDER=deepseek requiere LLM_API_KEY en .env. "
                "O usa LLM_PROVIDER=noop para pruebas con datos mock."
            )
        log.info("llm.provider_configured", provider="deepseek", model="deepseek-chat")
        llm_client = DeepSeekClient(api_key=api_key)  # type: ignore[assignment]
    elif settings.llm_provider == "noop":
        log.warning(
            "llm.provider_configured",
            provider="noop",
            message="Usando NoopLLMClient — las respuestas seran datos mock, no IA real",
        )
        llm_client = NoopLLMClient()  # type: ignore[assignment]
    else:
        from kosmo.infrastructure.llm.litellm_adapter import (
            LiteLLMClient,  # type: ignore[assignment]
        )

        api_key = ""
        if settings.llm_api_key:
            api_key = settings.llm_api_key.get_secret_value()
        fernet_key = Fernet(settings.fernet_master_key.get_secret_value())
        vault = FernetApiKeyVault(fernet_key)
        llm_client = LiteLLMClient(key_vault=vault)  # type: ignore[assignment]

    blob_storage = FileSystemBlobStorage(base_path="./data/blobs")

    fernet_key = Fernet(settings.fernet_master_key.get_secret_value())
    api_key_vault = FernetApiKeyVault(fernet_key)

    return SDDComponents(
        spec_repo=spec_repo,
        project_repo=project_repo,
        feature_repo=feature_repo,
        llm_client=llm_client,
        blob_storage=blob_storage,
        api_key_vault=api_key_vault,
    )


@dataclass(frozen=True, slots=True)
class AuthComponents:
    redis: Redis
    db_engine: AsyncEngine
    password_hasher: PasswordHasher
    secret_cipher: SecretCipher
    user_repository: UserRepository
    login_attempt_store: LoginAttemptStore
    audit_sink: AuditEventSink
    register_user: RegisterUser
    authorize_with_pkce: AuthorizeWithPkce
    exchange_authorization_code: ExchangeAuthorizationCode
    issue_token_pair: IssueTokenPair
    verify_access_token: VerifyAccessToken
    refresh_token_pair: RefreshTokenPair
    revoke_session: RevokeSession


def build_auth_components(settings: Settings) -> AuthComponents:
    assert settings.jwt_private_key_pem is not None
    assert settings.jwt_public_key_pem is not None

    jwt_settings = JwtSettings(
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        access_ttl_seconds=settings.jwt_access_ttl_seconds,
        refresh_ttl_seconds=settings.jwt_refresh_ttl_seconds,
    )
    issuer = JoseJwtIssuer(
        private_key_pem=settings.jwt_private_key_pem.get_secret_value(),
        settings=jwt_settings,
    )
    verifier = JoseJwtVerifier(
        public_key_pem=settings.jwt_public_key_pem.get_secret_value(),
        settings=jwt_settings,
    )

    redis: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        settings.redis_url.get_secret_value()
    )
    token_store = RedisTokenRevocationStore(redis)
    authorization_code_store = RedisAuthorizationCodeStore(redis)
    login_attempt_store = RedisLoginAttemptStore(redis)

    db_engine = create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    user_repository = SqlAlchemyUserRepository(session_factory)
    audit_sink = SqlAlchemyAuditEventSink(session_factory)

    password_hasher = Argon2idPasswordHasher(
        Argon2idParameters(
            memory_kib=settings.argon2_memory_kib,
            time_cost=settings.argon2_time_cost,
            parallelism=settings.argon2_parallelism,
        )
    )
    secret_cipher = FernetSecretCipher(settings.fernet_master_key.get_secret_value())

    issue_token_pair = IssueTokenPair(issuer=issuer, revocation_store=token_store)

    return AuthComponents(
        redis=redis,
        db_engine=db_engine,
        password_hasher=password_hasher,
        secret_cipher=secret_cipher,
        user_repository=user_repository,
        login_attempt_store=login_attempt_store,
        audit_sink=audit_sink,
        register_user=RegisterUser(
            user_repository=user_repository,
            password_hasher=password_hasher,
            audit_sink=audit_sink,
        ),
        authorize_with_pkce=AuthorizeWithPkce(
            user_repository=user_repository,
            password_hasher=password_hasher,
            authorization_code_store=authorization_code_store,
            login_attempt_store=login_attempt_store,
            audit_sink=audit_sink,
        ),
        exchange_authorization_code=ExchangeAuthorizationCode(
            authorization_code_store=authorization_code_store,
            issue_token_pair=issue_token_pair,
        ),
        issue_token_pair=issue_token_pair,
        verify_access_token=VerifyAccessToken(verifier=verifier, revocation_store=token_store),
        refresh_token_pair=RefreshTokenPair(
            issuer=issuer,
            verifier=verifier,
            revocation_store=token_store,
            audit_sink=audit_sink,
        ),
        revoke_session=RevokeSession(
            verifier=verifier, revocation_store=token_store, audit_sink=audit_sink
        ),
    )
