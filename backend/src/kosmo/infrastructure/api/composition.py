from dataclasses import dataclass
from typing import Any, cast

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
    GetDiscoveryChatHistoryUseCase,
    GetDiscoveryUseCase,
    ProcessDiscoveryChatMessageUseCase,
    RefineDiscoveryUseCase,
    SaveDiscoveryUseCase,
)
from kosmo.application.features import (
    CreateCharacteristicUseCase,
    GenerateFeaturesUseCase,
    SaveSelectedFeaturesUseCase,
    SuggestFeaturesUseCase,
)
from kosmo.application.modelo import (
    GenerateActivityDiagramUseCase,
    GetActivityDiagramUseCase,
)
from kosmo.application.pipeline.kosmo_agent import KOSMOAgent
from kosmo.application.projects import (
    CreateProjectUseCase,
    GetProjectUseCase,
    ListProjectsUseCase,
)
from kosmo.application.requirements import (
    GenerateEARSUseCase,
    GetRequirementsUseCase,
    RefineRequirementsUseCase,
    SaveRequirementsUseCase,
)
from kosmo.config import Settings
from kosmo.contracts.agent_memory import AgentMemoryPort, KnowledgePatternStore
from kosmo.contracts.audit import AuditEventSink
from kosmo.contracts.auth import LoginAttemptStore, PasswordHasher, SecretCipher, UserRepository
from kosmo.contracts.llm.ports import Embedder, LLMClient
from kosmo.contracts.pipeline.orchestrator_ports import AgentPort, Skill
from kosmo.contracts.pipeline.phase_outputs import (
    ValidationResult,
)
from kosmo.contracts.sdd.document import RichTextDocument, SpecPhase
from kosmo.domain.pipeline.context_builder import ContextBuilder
from kosmo.domain.pipeline.guard_registry import GuardRegistry
from kosmo.domain.pipeline.knowledge_tool_registry import KnowledgeToolRegistry
from kosmo.domain.pipeline.phase_modes.discovery_chat_mode import DiscoveryChatMode
from kosmo.domain.pipeline.phase_modes.discovery_mode import DiscoveryMode
from kosmo.domain.pipeline.phase_modes.discovery_refine_mode import (
    DiscoveryRefineMode,
)
from kosmo.domain.pipeline.phase_modes.ears_mode import EARSMode
from kosmo.domain.pipeline.phase_modes.features_chat_mode import FeaturesChatMode
from kosmo.domain.pipeline.phase_modes.features_mode import FeaturesMode
from kosmo.domain.pipeline.phase_modes.modelo_mode import ModeloMode
from kosmo.domain.pipeline.phase_modes.requirements_refine_mode import (
    RequirementsRefineMode,
)
from kosmo.domain.pipeline.phase_validators.discovery_refine_validator import (
    validate_business_level,
)
from kosmo.domain.pipeline.phase_validators.discovery_validator import (
    validate_discovery_quality,
    validate_discovery_structure,
)
from kosmo.domain.pipeline.phase_validators.features_validator import (
    validate_feature_structure,
    validate_feature_uniqueness,
)
from kosmo.domain.pipeline.skill_registry import SkillRegistry
from kosmo.domain.sdd.validators.activity_diagram_validator import (
    validate_activity_diagram_syntax,
)
from kosmo.domain.sdd.validators.ears_validator import (
    validate_ears_quality,
    validate_ears_software_level,
    validate_ears_syntax,
)
from kosmo.infrastructure.llm.embedder import OpenAIEmbedder
from kosmo.infrastructure.llm.knowledge_tools import (
    build_find_similar_sessions,
    build_get_diagram_for_feature,
    build_get_downstream_artifacts,
    build_get_phase_document,
    build_get_requirements_for_feature,
)
from kosmo.infrastructure.llm.noop_adapter import NoopLLMClient
from kosmo.infrastructure.llm.pydantic_ai_adapter import PydanticAILLMClient
from kosmo.infrastructure.persistence.memory.sqlalchemy_store import (
    SqlAlchemyAgentSessionStore,
    SqlAlchemyKnowledgePatternStore,
)
from kosmo.infrastructure.persistence.postgres.repositories import (
    SqlAlchemyAuditEventSink,
    SqlAlchemyProjectRepository,
    SqlAlchemyUserRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.activity_diagram_repo import (
    SqlAlchemyActivityDiagramRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.document_repo import (
    SqlAlchemyDocumentRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.feature_repo import (
    SqlAlchemyFeatureRepository,
)
from kosmo.infrastructure.persistence.postgres.repositories.requirement_repo import (
    SqlAlchemyRequirementRepository,
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
        connect_args={"statement_cache_size": 0},
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
        revoke_session=RevokeSession(verifier=verifier, revocation_store=token_store, audit_sink=audit_sink),
    )


@dataclass(frozen=True, slots=True)
class PipelineComponents:
    llm_client: LLMClient
    context_builder: ContextBuilder
    agent: AgentPort
    guard_registry: GuardRegistry
    skill_registry: SkillRegistry
    agent_memory: AgentMemoryPort
    pattern_store: KnowledgePatternStore


def _build_pydantic_ai_model(provider: str, model: str, api_key: str | None) -> object:
    if provider == "deepseek":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIChatModel(
            model,
            provider=OpenAIProvider(base_url="https://api.deepseek.com", api_key=api_key),
        )
    elif provider == "openai":
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        return OpenAIChatModel(
            model,
            provider=OpenAIProvider(api_key=api_key),
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
    feature_repo = SqlAlchemyFeatureRepository(session_factory)
    requirement_repo = SqlAlchemyRequirementRepository(session_factory)
    diagram_repo = SqlAlchemyActivityDiagramRepository(session_factory)

    context_builder = ContextBuilder(
        document_repo=document_repo,
        project_repo=project_repo,
    )

    # 4. Configurar el registro de guardrails con los validadores existentes
    guard_registry = GuardRegistry()
    guard_registry.register(
        "validate_discovery_structure",
        lambda inp: _adapt_validation_result(validate_discovery_structure(_markdown_input(inp))),
    )
    guard_registry.register(
        "validate_discovery_quality",
        lambda inp: _adapt_validation_result(validate_discovery_quality(_markdown_input(inp))),
    )
    guard_registry.register(
        "validate_business_level",
        lambda inp: _adapt_validation_result(validate_business_level(_markdown_input(inp))),
    )
    guard_registry.register(
        "validate_feature_structure",
        lambda inp: _adapt_validation_result(_validate_features_input(inp)),
    )
    guard_registry.register(
        "validate_feature_uniqueness",
        lambda inp: _adapt_validation_result(validate_feature_uniqueness(_extract_array(inp, "features"))),
    )
    guard_registry.register(
        "validate_ears_syntax",
        lambda inp: _adapt_validation_result(_validate_ears_syntax_raw(inp)),
    )
    guard_registry.register(
        "validate_ears_quality",
        lambda inp: _adapt_validation_result(_validate_ears_quality_raw(inp)),
    )
    guard_registry.register(
        "validate_ears_software_level",
        lambda inp: _adapt_validation_result(_validate_ears_software_level_raw(inp)),
    )
    guard_registry.register(
        "validate_activity_diagram_syntax",
        lambda inp: _adapt_validation_result(validate_activity_diagram_syntax(str(inp.get("diagram", "")))),
    )

    # 6. Instanciar el repositorio de memoria del agente
    agent_memory = SqlAlchemyAgentSessionStore(session_factory)

    # 7. Instanciar el SkillRegistry y registrar todos los skills
    skill_registry = SkillRegistry()
    skill_registry.register(
        Skill(
            name="discovery_generate",
            description="Genera el documento de descubrimiento desde cero",
            phase=SpecPhase.DESCUBRIMIENTO,
            mode=DiscoveryMode(),  # type: ignore[reportArgumentType]
        )
    )
    skill_registry.register(
        Skill(
            name="discovery_refine",
            description="Refina el documento de descubrimiento existente",
            phase=SpecPhase.DESCUBRIMIENTO,
            mode=DiscoveryRefineMode(),  # type: ignore[reportArgumentType]
        )
    )
    skill_registry.register(
        Skill(
            name="features_generate",
            description="Genera caracteristicas a partir del descubrimiento",
            phase=SpecPhase.CARACTERISTICAS,
            mode=FeaturesMode(),  # type: ignore[reportArgumentType]
        )
    )
    skill_registry.register(
        Skill(
            name="ears_generate",
            description="Genera requisitos EARS para una caracteristica",
            phase=SpecPhase.REQUISITOS,
            mode=EARSMode(),  # type: ignore[reportArgumentType]
        )
    )
    skill_registry.register(
        Skill(
            name="requirements_refine",
            description="Refina requisitos EARS existentes",
            phase=SpecPhase.REQUISITOS,
            mode=RequirementsRefineMode(),  # type: ignore[reportArgumentType]
        )
    )
    skill_registry.register(
        Skill(
            name="modelo_generate",
            description="Genera diagrama de actividad UML desde requisitos EARS",
            phase=SpecPhase.MODELO,
            mode=ModeloMode(),  # type: ignore[reportArgumentType]
        )
    )
    skill_registry.register(
        Skill(
            name="discovery_chat",
            description="Chat conversacional de descubrimiento a nivel de negocio",
            phase=SpecPhase.DESCUBRIMIENTO,
            mode=DiscoveryChatMode(),  # type: ignore[reportArgumentType]
        )
    )
    skill_registry.register(
        Skill(
            name="features_chat",
            description="Chat conversacional de característica a nivel de usuario",
            phase=SpecPhase.CARACTERISTICAS,
            mode=FeaturesChatMode(),  # type: ignore[reportArgumentType]
        )
    )

    # 8. Instanciar el agente unico con el SkillRegistry y memoria

    def _build_embedder() -> Embedder | None:
        if settings.embedding_provider == "none":
            return None
        if settings.embedding_provider == "openai" and settings.llm_api_key:
            return OpenAIEmbedder(api_key=settings.llm_api_key.get_secret_value())
        if settings.embedding_provider == "fastembed":
            from kosmo.infrastructure.llm.local_embedder import FastembedEmbedder

            return FastembedEmbedder()
        if settings.embedding_provider == "auto":
            if settings.llm_provider.lower() == "openai" and settings.llm_api_key:
                return OpenAIEmbedder(api_key=settings.llm_api_key.get_secret_value())
            try:
                from kosmo.infrastructure.llm.local_embedder import FastembedEmbedder

                return FastembedEmbedder()
            except ImportError:
                return None
        return None

    embedding_generator = _build_embedder()

    pattern_store = SqlAlchemyKnowledgePatternStore(session_factory)

    knowledge_tools = KnowledgeToolRegistry()
    knowledge_tools.register(*build_get_phase_document(document_repo))
    knowledge_tools.register(*build_get_downstream_artifacts(feature_repo))
    knowledge_tools.register(*build_get_requirements_for_feature(requirement_repo))
    knowledge_tools.register(*build_get_diagram_for_feature(diagram_repo))
    if embedding_generator is not None:
        knowledge_tools.register(*build_find_similar_sessions(agent_memory, embedding_generator))

    agent = KOSMOAgent(
        llm_client=llm_client,
        guard_registry=guard_registry,
        skill_registry=skill_registry,
        memory=agent_memory,  # type: ignore[reportArgumentType]
        embedding_generator=embedding_generator,
        knowledge_tools=knowledge_tools,
        pattern_store=pattern_store,  # type: ignore[reportArgumentType]
    )

    return PipelineComponents(
        llm_client=llm_client,
        context_builder=context_builder,
        agent=agent,
        guard_registry=guard_registry,
        skill_registry=skill_registry,
        agent_memory=agent_memory,
        pattern_store=pattern_store,
    )


@dataclass(frozen=True, slots=True)
class DiscoveryComponents:
    generate_discovery: GenerateDiscoveryUseCase
    get_discovery: GetDiscoveryUseCase
    save_discovery: SaveDiscoveryUseCase
    refine_discovery: RefineDiscoveryUseCase
    process_discovery_chat_message: ProcessDiscoveryChatMessageUseCase
    get_discovery_chat_history: GetDiscoveryChatHistoryUseCase
    manage_plan_changes: Any


def build_discovery_components(
    session_factory: async_sessionmaker[AsyncSession],
    pipeline: PipelineComponents,
) -> DiscoveryComponents:
    project_repo = SqlAlchemyProjectRepository(session_factory)
    document_repo = SqlAlchemyDocumentRepository(session_factory)
    from kosmo.application.chat.manage_plan_changes import ManagePlanChangesUseCase
    from kosmo.application.discovery.get_discovery_chat_history import GetDiscoveryChatHistoryUseCase
    from kosmo.application.discovery.process_discovery_chat_message import ProcessDiscoveryChatMessageUseCase
    from kosmo.infrastructure.persistence.postgres.repositories.chat_repo import SqlAlchemyChatRepository

    chat_repo = SqlAlchemyChatRepository(session_factory)

    return DiscoveryComponents(
        generate_discovery=GenerateDiscoveryUseCase(
            project_repo=project_repo,
            document_repo=document_repo,
            agent=pipeline.agent,
        ),
        get_discovery=GetDiscoveryUseCase(document_repo=document_repo),
        save_discovery=SaveDiscoveryUseCase(document_repo=document_repo),
        refine_discovery=RefineDiscoveryUseCase(
            project_repo=project_repo,
            document_repo=document_repo,
            context_builder=pipeline.context_builder,
            agent=pipeline.agent,
        ),
        process_discovery_chat_message=ProcessDiscoveryChatMessageUseCase(
            project_repo=project_repo,
            document_repo=document_repo,
            chat_repo=chat_repo,
            context_builder=pipeline.context_builder,
            agent=pipeline.agent,
        ),
        get_discovery_chat_history=GetDiscoveryChatHistoryUseCase(
            project_repo=project_repo,
            chat_repo=chat_repo,
        ),
        manage_plan_changes=ManagePlanChangesUseCase(
            project_repo=project_repo,
            chat_repo=chat_repo,
        ),
    )


@dataclass(frozen=True, slots=True)
class FeaturesComponents:
    generate_features: GenerateFeaturesUseCase
    suggest_features: SuggestFeaturesUseCase
    save_selected_features: SaveSelectedFeaturesUseCase
    create_characteristic: CreateCharacteristicUseCase
    feature_repo: SqlAlchemyFeatureRepository


def build_features_components(
    session_factory: async_sessionmaker[AsyncSession],
    pipeline: PipelineComponents,
) -> FeaturesComponents:
    document_repo = SqlAlchemyDocumentRepository(session_factory)
    feature_repo = SqlAlchemyFeatureRepository(session_factory)
    project_repo = SqlAlchemyProjectRepository(session_factory)
    suggest_features = SuggestFeaturesUseCase(
        document_repo=document_repo,
        feature_repo=feature_repo,
        llm_client=pipeline.llm_client,
    )
    return FeaturesComponents(
        generate_features=GenerateFeaturesUseCase(
            project_repo=project_repo,
            document_repo=document_repo,
            feature_repo=feature_repo,
            agent=pipeline.agent,
        ),
        suggest_features=suggest_features,
        save_selected_features=SaveSelectedFeaturesUseCase(
            feature_repo=feature_repo,
        ),
        create_characteristic=CreateCharacteristicUseCase(
            feature_repo=feature_repo,
            suggest_use_case=suggest_features,
        ),
        feature_repo=feature_repo,
    )


@dataclass(frozen=True, slots=True)
class RequirementsComponents:
    generate_ears: GenerateEARSUseCase
    get_requirements: GetRequirementsUseCase
    save_requirements: SaveRequirementsUseCase
    refine_requirements: RefineRequirementsUseCase


def build_requirements_components(
    session_factory: async_sessionmaker[AsyncSession],
    pipeline: PipelineComponents,
) -> RequirementsComponents:
    project_repo = SqlAlchemyProjectRepository(session_factory)
    document_repo = SqlAlchemyDocumentRepository(session_factory)
    feature_repo = SqlAlchemyFeatureRepository(session_factory)
    requirement_repo = SqlAlchemyRequirementRepository(session_factory)
    return RequirementsComponents(
        generate_ears=GenerateEARSUseCase(
            project_repo=project_repo,
            document_repo=document_repo,
            feature_repo=feature_repo,
            requirement_repo=requirement_repo,
            agent=pipeline.agent,
        ),
        get_requirements=GetRequirementsUseCase(
            project_repo=project_repo,
            feature_repo=feature_repo,
            requirement_repo=requirement_repo,
        ),
        save_requirements=SaveRequirementsUseCase(
            project_repo=project_repo,
            feature_repo=feature_repo,
            requirement_repo=requirement_repo,
        ),
        refine_requirements=RefineRequirementsUseCase(
            project_repo=project_repo,
            feature_repo=feature_repo,
            requirement_repo=requirement_repo,
            agent=pipeline.agent,
        ),
    )


@dataclass(frozen=True, slots=True)
class ModeloComponents:
    generate_diagram: GenerateActivityDiagramUseCase
    get_diagram: GetActivityDiagramUseCase


def build_modelo_components(
    session_factory: async_sessionmaker[AsyncSession],
    pipeline: PipelineComponents,
) -> ModeloComponents:
    feature_repo = SqlAlchemyFeatureRepository(session_factory)
    requirement_repo = SqlAlchemyRequirementRepository(session_factory)
    diagram_repo = SqlAlchemyActivityDiagramRepository(session_factory)
    return ModeloComponents(
        generate_diagram=GenerateActivityDiagramUseCase(
            feature_repo=feature_repo,
            requirement_repo=requirement_repo,
            diagram_repo=diagram_repo,
            agent=pipeline.agent,
        ),
        get_diagram=GetActivityDiagramUseCase(
            feature_repo=feature_repo,
            diagram_repo=diagram_repo,
        ),
    )


def _markdown_input(inp: dict[str, object]) -> RichTextDocument:
    from kosmo.domain.sdd.document_converters import markdown_to_document

    raw = inp.get("document", inp.get("text", ""))
    return markdown_to_document(str(raw))


def _adapt_validation_result(vr: ValidationResult) -> dict[str, object]:
    return {"is_valid": vr.is_valid, "errors": vr.errors, "warnings": vr.warnings}


def _extract_array(inp: dict[str, object], key: str) -> list[Any]:
    import json

    raw = inp.get(key, [])
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(raw, list):
        return []

    result: list[Any] = []
    for item in cast(list[object], raw):
        if isinstance(item, dict):
            cleaned: dict[str, Any] = {}
            for k, v in cast(dict[object, object], item).items():
                if isinstance(k, str):
                    cleaned[k] = v
            result.append(cleaned)
        else:
            result.append(item)
    return result


def _validate_features_input(inp: dict[str, object]) -> ValidationResult:
    features = _extract_array(inp, "features")
    return validate_feature_structure(features)


def _validate_ears_syntax_raw(inp: dict[str, object]) -> ValidationResult:
    requirements = _extract_array(inp, "requirements")
    return validate_ears_syntax(requirements)


def _validate_ears_quality_raw(inp: dict[str, object]) -> ValidationResult:
    requirements = _extract_array(inp, "requirements")
    return validate_ears_quality(requirements)


def _validate_ears_software_level_raw(inp: dict[str, object]) -> ValidationResult:
    requirements = _extract_array(inp, "requirements")
    return validate_ears_software_level(requirements)
