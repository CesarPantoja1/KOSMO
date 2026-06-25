from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

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
from kosmo.application.projects import (
    CreateProjectUseCase,
    GetProjectUseCase,
    ListProjectsUseCase,
)
from kosmo.config import Settings
from kosmo.contracts.audit import AuditEventSink
from kosmo.contracts.auth import LoginAttemptStore, PasswordHasher, SecretCipher, UserRepository
from kosmo.contracts.llm.ports import LLMClient
from kosmo.contracts.sdd.document import SpecPhase
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.pipeline.kosmo_agent import KOSMOAgent
from kosmo.domain.pipeline.phase_modes.discovery_mode import DiscoveryMode
from kosmo.domain.pipeline.sequential_orchestrator import SequentialOrchestrator
from kosmo.infrastructure.llm.noop_adapter import NoopLLMClient
from kosmo.infrastructure.llm.pydantic_ai_adapter import PydanticAILLMClient
from kosmo.infrastructure.persistence.postgres.repositories import (
    SqlAlchemyAuditEventSink,
    SqlAlchemyProjectRepository,
    SqlAlchemyUserRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.document_repo import (
    SqlAlchemyDocumentRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.feature_repo import (
    SqlAlchemyFeatureRepository,
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
class ProjectComponents:
    create_project: CreateProjectUseCase
    get_project: GetProjectUseCase
    list_projects: ListProjectsUseCase


def build_project_components(
    session_factory: async_sessionmaker[AsyncSession],
) -> ProjectComponents:
    project_repository = SqlAlchemyProjectRepository(session_factory)
    return ProjectComponents(
        create_project=CreateProjectUseCase(project_repository=project_repository),
        get_project=GetProjectUseCase(project_repository=project_repository),
        list_projects=ListProjectsUseCase(project_repository=project_repository),
    )


def build_auth_components(settings: Settings) -> AuthComponents:
    assert settings.jwt_private_key_pem is not None
    assert settings.jwt_public_key_pem is not None
    assert settings.redis_url is not None
    assert settings.fernet_master_key is not None

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


@dataclass(frozen=True, slots=True)
class PipelineComponents:
    llm_client: LLMClient
    context_builder: ContextBuilder
    agent: KOSMOAgent
    orchestrator: SequentialOrchestrator


def _build_pydantic_ai_model(provider: str, model: str, api_key: str | None) -> object:
    if provider == "deepseek":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIChatModel(
            model,
            provider=OpenAIProvider(base_url="https://api.deepseek.com", api_key=api_key),
        )

    return f"{provider}:{model}"


def build_pipeline_components(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> PipelineComponents:
    # 1. Seleccionar el adaptador LLM según la configuración
    if settings.llm_provider.lower() == "noop":
        llm_client: LLMClient = NoopLLMClient()
    else:
        api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
        model = _build_pydantic_ai_model(settings.llm_provider, settings.llm_model, api_key)
        llm_client = PydanticAILLMClient(model=model)

    # 2. Instanciar los repositorios disponibles
    project_repo = SqlAlchemyProjectRepository(session_factory)
    document_repo = SqlAlchemyDocumentRepository(session_factory)

    context_builder = ContextBuilder(
        document_repo=document_repo,
        project_repo=project_repo,
    )

    # 4. Configurar modos de fase
    modes = {
        SpecPhase.DESCUBRIMIENTO: DiscoveryMode(),
    }

    # 5. Instanciar el agente KOSMO
    agent = KOSMOAgent(
        llm_client=llm_client,
        context_builder=context_builder,
        modes=modes,  # type: ignore[reportArgumentType]
    )

    # 6. Instanciar el orquestador secuencial
    orchestrator = SequentialOrchestrator()

    # (Aquí se instanciarán y retornarán los casos de uso a medida que se implementen)

    return PipelineComponents(
        llm_client=llm_client,
        context_builder=context_builder,
        agent=agent,
        orchestrator=orchestrator,
    )


@dataclass(frozen=True, slots=True)
class DiscoveryComponents:
    generate_discovery: GenerateDiscoveryUseCase
    get_discovery: GetDiscoveryUseCase
    save_discovery: SaveDiscoveryUseCase


def build_discovery_components(
    session_factory: async_sessionmaker[AsyncSession],
    pipeline: PipelineComponents,
) -> DiscoveryComponents:
    project_repo = SqlAlchemyProjectRepository(session_factory)
    document_repo = SqlAlchemyDocumentRepository(session_factory)
    return DiscoveryComponents(
        generate_discovery=GenerateDiscoveryUseCase(
            project_repo=project_repo,
            document_repo=document_repo,
            context_builder=pipeline.context_builder,
            agent=pipeline.agent,
        ),
        get_discovery=GetDiscoveryUseCase(document_repo=document_repo),
        save_discovery=SaveDiscoveryUseCase(document_repo=document_repo),
    )


@dataclass(frozen=True, slots=True)
class FeaturesComponents:
    generate_features: GenerateFeaturesUseCase
    suggest_features: SuggestFeaturesUseCase
    save_selected_features: SaveSelectedFeaturesUseCase
    feature_repo: SqlAlchemyFeatureRepository


def build_features_components(
    session_factory: async_sessionmaker[AsyncSession],
    pipeline: PipelineComponents,
) -> FeaturesComponents:
    document_repo = SqlAlchemyDocumentRepository(session_factory)
    feature_repo = SqlAlchemyFeatureRepository(session_factory)
    project_repo = SqlAlchemyProjectRepository(session_factory)
    return FeaturesComponents(
        generate_features=GenerateFeaturesUseCase(
            project_repo=project_repo,
            document_repo=document_repo,
            feature_repo=feature_repo,
            llm_client=pipeline.llm_client,
        ),
        suggest_features=SuggestFeaturesUseCase(
            document_repo=document_repo,
            feature_repo=feature_repo,
            llm_client=pipeline.llm_client,
        ),
        save_selected_features=SaveSelectedFeaturesUseCase(
            feature_repo=feature_repo,
        ),
        feature_repo=feature_repo,
    )
