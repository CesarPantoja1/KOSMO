import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from kosmo.config import settings
from kosmo.contracts.sdd.errors import SpecError
from kosmo.infrastructure.api.composition import (
    build_auth_components,
    build_discovery_components,
    build_features_components,
    build_modelo_components,
    build_pipeline_components,
    build_project_components,
    build_requirements_components,
)
from kosmo.infrastructure.api.middlewares import RequestLoggingMiddleware
from kosmo.infrastructure.api.routers.async_jobs import router as async_jobs_router
from kosmo.infrastructure.api.routers.auth import router as auth_router
from kosmo.infrastructure.api.routers.consistency import router as consistency_router
from kosmo.infrastructure.api.routers.discovery import router as discovery_router
from kosmo.infrastructure.api.routers.feature_chat import router as feature_chat_router
from kosmo.infrastructure.api.routers.features import router as features_router
from kosmo.infrastructure.api.routers.knowledge import router as knowledge_router
from kosmo.infrastructure.api.routers.modelo import router as modelo_router
from kosmo.infrastructure.api.routers.plan import router as plan_router
from kosmo.infrastructure.api.routers.projects import router as projects_router
from kosmo.infrastructure.api.routers.requirement_chat import router as requirement_chat_router
from kosmo.infrastructure.api.routers.requirements import router as requirements_router
from kosmo.infrastructure.api.routers.schemas import router as schemas_router
from kosmo.infrastructure.api.schemas import HttpErrorResponse
from kosmo.infrastructure.telemetry import configure_telemetry, instrument_app, instrument_prometheus

# Metadatos OpenAPI

_OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": (
            "Flujo de autenticación PKCE + OAuth 2.0. "
            "Los endpoints siguen el estándar RFC 6749/7636: el cliente genera un "
            "``code_verifier`` efímero, solicita un ``authorization_code`` en ``/authorize``, "
            "lo intercambia por tokens JWT en ``/token`` y los renueva con ``/refresh``. "
            "Todos los endpoints protegidos requieren ``Authorization: Bearer <access_token>``."
        ),
    },
    {
        "name": "projects",
        "description": (
            "Gestión de proyectos. Permite crear, listar y consultar proyectos "
            "asociados al usuario autenticado. Cada proyecto agrupa el ciclo "
            "completo de especificación, modelado y generación de artefactos."
        ),
    },
    {
        "name": "discovery",
        "description": (
            "Generación de documentos de descubrimiento mediante IA. "
            "Permite generar, consultar y actualizar el documento de visión "
            "de producto de un proyecto. El documento se estructura en 8 "
            "secciones obligatorias que cubren visión, problema, actores, "
            "propuesta de valor, casos de uso, capacidades, reglas de negocio "
            "y atributos de calidad."
        ),
    },
    {
        "name": "features",
        "description": (
            "Generación y gestión de características del producto software mediante IA. "
            "Permite generar características a partir del documento de descubrimiento, "
            "sugerir nuevas características no duplicadas, listar las existentes y "
            "guardar las seleccionadas por el usuario."
        ),
    },
    {
        "name": "requirements",
        "description": (
            "Generación y gestión de requisitos EARS por característica mediante IA. "
            "Permite generar requisitos a partir del documento de descubrimiento y la "
            "característica seleccionada, consultarlos y actualizar su contenido en Markdown."
        ),
    },
    {
        "name": "modelo",
        "description": (
            "Generación y consulta de diagramas de actividad PlantUML por característica mediante IA. "
            "Permite generar diagramas UML a partir de los requisitos EARS y consultar los diagramas generados."
        ),
    },
    {
        "name": "schemas",
        "description": (
            "Introspección de contratos. Permite al Frontend consultar el JSON Schema "
            "de cualquier DTO expuesto por la API para generación dinámica de formularios, "
            "validaciones y tipos TypeScript."
        ),
    },
]

_CONTACT = {
    "name": "Equipo KOSMO",
    "email": "dev@kosmo.app",
    "url": "https://github.com/CesarPantoja1/KOSMO",
}

_LICENSE = {
    "name": "MIT",
    "url": "https://opensource.org/licenses/MIT",
}

_DESCRIPTION = """
KOSMO Backend API

KOSMO es una plataforma de agentes de IA con identidad centralizada.
Esta API gestiona el ciclo completo de autenticación de usuarios y la
introspección de contratos de datos para el Frontend.

### Flujo de autenticación recomendado

```
1. POST /api/v1/auth/register      → Crear cuenta
2. POST /api/v1/auth/authorize     → Obtener authorization_code (PKCE)
3. POST /api/v1/auth/token         → Intercambiar código por JWT pair
4. GET  /api/v1/auth/me            → Verificar identidad (Bearer token)
5. POST /api/v1/auth/refresh       → Renovar tokens antes de expirar
6. POST /api/v1/auth/logout        → Revocar sesión activa
```

### Seguridad

- Tokens firmados con **RS256** (par de claves RSA 2048-bit)
- Contraseñas hasheadas con **Argon2id** (OWASP 2025)
- Refresh tokens con **Token Rotation**: cada uso emite un par nuevo
- Rate limiting por IP en todos los endpoints sensibles
- Secrets cifrados con **Fernet** (AES-128-CBC + HMAC-SHA256)

### Respuestas de error

Todos los errores de autenticación siguen el esquema `OAuthErrorResponse`
(RFC 6749 §5.2). Los errores de infraestructura usan `HttpErrorResponse`.
"""

_SERVERS = [
    {
        "url": "http://localhost:8000",
        "description": "Local — desarrollo en máquina del programador",
    },
    {
        "url": "https://api-dev.kosmo.app",
        "description": "Desarrollo — entorno de integración continua",
    },
    {
        "url": "https://api.kosmo.app",
        "description": "Producción — tráfico real de usuarios",
    },
]

# Respuestas globales reutilizables

_GLOBAL_RESPONSES = {
    403: {
        "description": (
            "Forbidden — El token es válido pero no tiene los scopes necesarios para acceder al recurso solicitado."
        ),
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/HttpErrorResponse"},
                "example": {"detail": "No tienes permisos suficientes para realizar esta acción."},
            }
        },
    },
    500: {
        "description": (
            "Internal Server Error — Error inesperado en el servidor. "
            "Se registra automáticamente en el sistema de observabilidad (Logfire/OTEL). "
            "El cliente debe implementar retry con back-off exponencial."
        ),
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/HttpErrorResponse"},
                "example": {"detail": "Error interno del servidor. Por favor contacte al soporte."},
            }
        },
    },
}

# Ciclo de vida y aplicación


def _make_outbox_handler(pipeline: Any) -> Any:
    async def handler(job_type: str, payload: dict[str, Any]) -> None:
        import structlog

        _log = structlog.get_logger("kosmo.outbox")
        agent = pipeline.agent
        if job_type == "reflect_and_consolidate":
            from kosmo.contracts.agent_memory import AgentMemoryId
            from kosmo.contracts.pipeline.phase_outputs import ValidationResult
            from kosmo.contracts.sdd.document import SpecPhase

            try:
                await agent._reflect_and_consolidate(  # type: ignore[reportPrivateUsage]
                    session_id=AgentMemoryId(payload["session_id"]),
                    phase=SpecPhase(payload["phase"]),
                    session_type=payload["session_type"],
                    is_completed=payload.get("is_completed", True),
                    current_iteration=payload.get("current_iteration", 1),
                    validation=ValidationResult(
                        is_valid=payload.get("validation_is_valid", True),
                        errors=payload.get("validation_errors", "").split("; "),
                    ),
                )
            except Exception:
                _log.warning("outbox.handler_failed", job_type=job_type, exc_info=True)
                raise
        else:
            _log.warning("outbox.unknown_job_type", job_type=job_type)

    return handler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_telemetry(settings)
    auth_components = None
    if settings.auth_disabled:
        db_engine = create_async_engine(
            settings.database_url.get_secret_value(),
            pool_pre_ping=True,
            connect_args={"statement_cache_size": 0},
        )
        app.state.redis = None
    else:
        auth_components = build_auth_components(settings)
        app.state.register_user = auth_components.register_user
        app.state.login_attempt_store = auth_components.login_attempt_store
        app.state.authorize_with_pkce = auth_components.authorize_with_pkce
        app.state.exchange_authorization_code = auth_components.exchange_authorization_code
        app.state.issue_token_pair = auth_components.issue_token_pair
        app.state.verify_access_token = auth_components.verify_access_token
        app.state.refresh_token_pair = auth_components.refresh_token_pair
        app.state.revoke_session = auth_components.revoke_session
        app.state.password_hasher = auth_components.password_hasher
        app.state.secret_cipher = auth_components.secret_cipher
        app.state.user_repository = auth_components.user_repository
        app.state.redis = auth_components.redis
        db_engine = auth_components.db_engine

    app.state.db_engine = db_engine
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    project_components = build_project_components(session_factory)
    app.state.create_project = project_components.create_project
    app.state.get_project = project_components.get_project
    app.state.list_projects = project_components.list_projects

    pipeline_components = build_pipeline_components(settings, session_factory)
    app.state.validate_phase_context = pipeline_components.validate_phase_context
    app.state.process_chat_message = pipeline_components.process_chat_message
    app.state.context_builder = pipeline_components.context_builder
    app.state.agent = pipeline_components.agent
    app.state.chat_repo = pipeline_components.chat_repo
    app.state.traceability_repo = pipeline_components.traceability_repo
    app.state.async_job_store = pipeline_components.async_job_store
    discovery_components = build_discovery_components(session_factory, pipeline_components)
    features_components = build_features_components(session_factory, pipeline_components)
    app.state.generate_discovery = discovery_components.generate_discovery
    app.state.get_discovery = discovery_components.get_discovery
    app.state.save_discovery = discovery_components.save_discovery
    app.state.refine_discovery = discovery_components.refine_discovery
    app.state.get_discovery_chat_history = discovery_components.get_discovery_chat_history
    app.state.manage_plan_changes = discovery_components.manage_plan_changes
    app.state.apply_plan_changes = discovery_components.apply_plan_changes
    app.state.document_repo = discovery_components.document_repo
    app.state.propagate_discovery_changes = discovery_components.propagate_discovery_changes
    app.state.consistency_evaluator = discovery_components.consistency_evaluator

    from kosmo.application.consistency.evaluate_project_consistency import EvaluateProjectConsistencyUseCase
    from kosmo.infrastructure.persistence.postgres.repositories import SqlAlchemyProjectRepository
    from kosmo.infrastructure.persistence.postgres.repositories.activity_diagram_repo import (
        SqlAlchemyActivityDiagramRepository,
    )
    from kosmo.infrastructure.persistence.postgres.repositories.feature_repo import SqlAlchemyFeatureRepository
    from kosmo.infrastructure.persistence.postgres.repositories.requirement_repo import SqlAlchemyRequirementRepository

    app.state.evaluate_project_consistency = EvaluateProjectConsistencyUseCase(
        project_repo=SqlAlchemyProjectRepository(session_factory),
        evaluator=discovery_components.consistency_evaluator,
        feature_repo=SqlAlchemyFeatureRepository(session_factory),
        requirement_repo=SqlAlchemyRequirementRepository(session_factory),
        diagram_repo=SqlAlchemyActivityDiagramRepository(session_factory),
    )

    app.state.generate_features = features_components.generate_features
    app.state.suggest_features = features_components.suggest_features
    app.state.save_selected_features = features_components.save_selected_features
    app.state.create_characteristic = features_components.create_characteristic
    app.state.feature_repo = features_components.feature_repo
    app.state.get_feature_chat_history = features_components.get_feature_chat_history
    app.state.list_features = features_components.list_features

    requirements_components = build_requirements_components(session_factory, pipeline_components)
    app.state.generate_ears = requirements_components.generate_ears
    app.state.get_requirements = requirements_components.get_requirements
    app.state.save_requirements = requirements_components.save_requirements
    app.state.refine_requirements = requirements_components.refine_requirements
    app.state.get_requirement_chat_history = requirements_components.get_requirement_chat_history
    app.state.requirement_repo = requirements_components.requirement_repo

    modelo_components = build_modelo_components(session_factory, pipeline_components)
    app.state.generate_diagram = modelo_components.generate_diagram
    app.state.get_diagram = modelo_components.get_diagram
    app.state.diagram_repo = modelo_components.diagram_repo

    from kosmo.application.knowledge import ConsolidateKnowledgePatterns

    consolidate_uc = ConsolidateKnowledgePatterns(
        memory=pipeline_components.agent_memory,
        pattern_store=pipeline_components.pattern_store,
        llm_client=pipeline_components.llm_client,
    )
    app.state.consolidate_patterns = consolidate_uc

    from kosmo.infrastructure.persistence.postgres.outbox import run_outbox_worker

    outbox_store = pipeline_components.outbox
    app.state.outbox = outbox_store

    outbox_task = asyncio.create_task(
        run_outbox_worker(outbox_store, _make_outbox_handler(pipeline_components))
    )

    instrument_app(settings, app=app, db_engine=db_engine)
    try:
        yield
    finally:
        outbox_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await outbox_task
        if auth_components is not None:
            await auth_components.redis.aclose()
        await db_engine.dispose()


app = FastAPI(
    title="KOSMO API",
    version=settings.api_version,
    description=_DESCRIPTION,
    contact=_CONTACT,
    license_info=_LICENSE,
    openapi_tags=_OPENAPI_TAGS,
    servers=_SERVERS,
    docs_url="/docs" if settings.env != "production" else None,
    redoc_url="/redoc" if settings.env != "production" else None,
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

instrument_prometheus(app)


@app.exception_handler(SpecError)
async def spec_error_handler(_request: Request, exc: SpecError) -> JSONResponse:
    problem = exc.problem
    return JSONResponse(
        status_code=problem.status,
        content={
            "type": problem.type,
            "title": problem.title,
            "status": problem.status,
            "detail": problem.detail,
            "instance": problem.instance,
            "trace_id": problem.trace_id,
            "violations": [
                {"loc": v.loc, "msg": v.msg, "input": v.input} for v in problem.violations
            ],
        },
        media_type="application/problem+json",
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

if not settings.auth_disabled:
    app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(plan_router)
app.include_router(discovery_router)
app.include_router(features_router)
app.include_router(feature_chat_router)
app.include_router(requirements_router)
app.include_router(requirement_chat_router)
app.include_router(modelo_router)
app.include_router(consistency_router)
app.include_router(schemas_router)
app.include_router(knowledge_router)
app.include_router(async_jobs_router)


@app.get("/health", tags=["health"], summary="Health check", include_in_schema=True)
async def health() -> dict[str, str]:
    """Verificación de disponibilidad del servidor.

    Devuelve ``{"status": "ok"}`` si el proceso está activo.
    No verifica conectividad con base de datos ni Redis.
    """
    return {"status": "ok"}


# Especificación OpenAPI customizada


def _custom_openapi() -> dict[str, Any]:
    """Genera la especificación OpenAPI enriquecida con respuestas globales.

    Se inyectan las respuestas 403 y 500 en cada operación para que el
    Frontend pueda manejar todos los errores de forma consistente.
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema: dict[str, Any] = get_openapi(
        title=app.title,
        version=app.version,
        description=_DESCRIPTION,
        contact=_CONTACT,
        license_info=_LICENSE,
        tags=_OPENAPI_TAGS,
        servers=_SERVERS,
        routes=app.routes,
    )

    # Registrar HttpErrorResponse en components/schemas
    http_error_schema = HttpErrorResponse.model_json_schema()

    components: dict[str, Any] = schema.setdefault("components", {})
    schemas: dict[str, Any] = components.setdefault("schemas", {})
    schemas["HttpErrorResponse"] = http_error_schema

    # Inyectar respuestas globales (403, 500) en todos los paths
    paths = cast(dict[str, Any], schema.get("paths", {}))
    for path_item in paths.values():
        if isinstance(path_item, dict):
            path_item_dict = cast(dict[str, Any], path_item)
            for operation in path_item_dict.values():
                if isinstance(operation, dict):
                    operation_dict = cast(dict[str, Any], operation)
                    responses = operation_dict.get("responses")
                    if isinstance(responses, dict):
                        responses_dict = cast(dict[str, Any], responses)
                        for status_code, response_def in _GLOBAL_RESPONSES.items():
                            responses_dict.setdefault(str(status_code), response_def)

    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi  # type: ignore[method-assign]
