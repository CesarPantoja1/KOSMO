from dataclasses import dataclass

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
from kosmo.application.discovery import (
    GenerateDiscoveryUseCase,
    GetDiscoveryUseCase,
    SaveDiscoveryUseCase,
)
from kosmo.application.features import (
    GenerateFeaturesUseCase,
    SaveSelectedFeaturesUseCase,
    SuggestFeaturesUseCase,
)
from kosmo.application.projects import CreateProjectUseCase, GetProjectUseCase, ListProjectsUseCase
from kosmo.application.requirements import GenerateEARSUseCase, SaveRequirementsUseCase
from kosmo.config import Settings
from kosmo.contracts.audit import AuditEventSink
from kosmo.contracts.auth import LoginAttemptStore, PasswordHasher, SecretCipher, UserRepository
from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.contracts.sdd.repositories import FeatureRepository, ProjectRepository
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.pipeline.kosmo_agent import KOSMOAgent
from kosmo.domain.pipeline.phase_modes import DiscoveryMode, EARSMode, FeaturesMode
from kosmo.domain.pipeline.sequential_orchestrator import SequentialOrchestrator
from kosmo.infrastructure.llm import NoopLLMClient, PydanticAILLMClient
from kosmo.infrastructure.persistence.postgres.repositories import (
    SqlAlchemyAuditEventSink,
    SqlAlchemyDocumentRepository,
    SqlAlchemyFeatureRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyUserRepository,
)
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


@dataclass(frozen=True, slots=True)
class PipelineComponents:
    project_repo: ProjectRepository
    feature_repo: FeatureRepository
    generate_discovery_uc: GenerateDiscoveryUseCase
    get_discovery_uc: GetDiscoveryUseCase
    save_discovery_uc: SaveDiscoveryUseCase
    generate_features_uc: GenerateFeaturesUseCase
    suggest_features_uc: SuggestFeaturesUseCase
    save_features_uc: SaveSelectedFeaturesUseCase
    generate_ears_uc: GenerateEARSUseCase
    save_requirements_uc: SaveRequirementsUseCase
    create_project_uc: CreateProjectUseCase
    get_project_uc: GetProjectUseCase
    list_projects_uc: ListProjectsUseCase


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

    redis: Redis = Redis.from_url(settings.redis_url.get_secret_value())
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


def _build_pydantic_ai_model(provider: str, model: str, api_key: str | None) -> object:
    if provider == "deepseek":
        from pydantic_ai.models.openai import OpenAIModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIModel(
            model,
            provider=OpenAIProvider(base_url="https://api.deepseek.com", api_key=api_key),
        )

    return f"{provider}:{model}"


def build_pipeline_components(
    settings: Settings,
    db_engine: AsyncEngine,
) -> PipelineComponents:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    project_repo = SqlAlchemyProjectRepository(session_factory)
    document_repo = SqlAlchemyDocumentRepository(session_factory)
    feature_repo = SqlAlchemyFeatureRepository(session_factory)

    if settings.llm_provider == "noop":
        llm_client: LLMClient = NoopLLMClient()
    else:
        api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
        model = _build_pydantic_ai_model(settings.llm_provider, settings.llm_model, api_key)
        llm_client = PydanticAILLMClient(model=model)

    context_builder = ContextBuilder(
        document_repo=document_repo,
        project_repo=project_repo,
        feature_repo=feature_repo,
    )

    modes = {
        SpecPhase.DESCUBRIMIENTO: DiscoveryMode(),
        SpecPhase.CARACTERISTICAS: FeaturesMode(),
        SpecPhase.REQUISITOS: EARSMode(),
    }

    agent = KOSMOAgent(
        llm_client=llm_client,
        context_builder=context_builder,
        modes=modes,
    )

    orchestrator = SequentialOrchestrator(
        document_repo=document_repo,
        feature_repo=feature_repo,
        project_repo=project_repo,
    )

    generate_discovery_uc = GenerateDiscoveryUseCase(
        agent=agent,
        context_builder=context_builder,
        project_repo=project_repo,
        document_repo=document_repo,
    )
    get_discovery_uc = GetDiscoveryUseCase(document_repo=document_repo)
    save_discovery_uc = SaveDiscoveryUseCase(document_repo=document_repo)
    generate_features_uc = GenerateFeaturesUseCase(
        agent=agent,
        context_builder=context_builder,
        orchestrator=orchestrator,
        feature_repo=feature_repo,
    )
    suggest_features_uc = SuggestFeaturesUseCase(
        agent=agent,
        context_builder=context_builder,
        feature_repo=feature_repo,
    )
    save_features_uc = SaveSelectedFeaturesUseCase(feature_repo=feature_repo)
    generate_ears_uc = GenerateEARSUseCase(
        agent=agent,
        context_builder=context_builder,
        orchestrator=orchestrator,
        feature_repo=feature_repo,
    )
    save_requirements_uc = SaveRequirementsUseCase(feature_repo=feature_repo)
    create_project_uc = CreateProjectUseCase(project_repo=project_repo)
    get_project_uc = GetProjectUseCase(project_repo=project_repo)
    list_projects_uc = ListProjectsUseCase(project_repo=project_repo)

    return PipelineComponents(
        project_repo=project_repo,
        feature_repo=feature_repo,
        generate_discovery_uc=generate_discovery_uc,
        get_discovery_uc=get_discovery_uc,
        save_discovery_uc=save_discovery_uc,
        generate_features_uc=generate_features_uc,
        suggest_features_uc=suggest_features_uc,
        save_features_uc=save_features_uc,
        generate_ears_uc=generate_ears_uc,
        save_requirements_uc=save_requirements_uc,
        create_project_uc=create_project_uc,
        get_project_uc=get_project_uc,
        list_projects_uc=list_projects_uc,
    )
