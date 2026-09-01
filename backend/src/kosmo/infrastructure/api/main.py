import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy import text

from kosmo.application.codegen.recover_zombie_implementations import recover_zombie_implementations
from kosmo.config import settings
from kosmo.contracts.sdd.errors import SpecError
from kosmo.infrastructure.api.composition import AppContainer, build_app_components
from kosmo.infrastructure.api.middlewares import RequestLoggingMiddleware
from kosmo.infrastructure.api.routers.ai_config import router as ai_config_router
from kosmo.infrastructure.api.routers.auth import router as auth_router
from kosmo.infrastructure.api.routers.chat_sessions import router as chat_sessions_router
from kosmo.infrastructure.api.routers.consistency import router as consistency_router
from kosmo.infrastructure.api.routers.deployment import router as deployment_router
from kosmo.infrastructure.api.routers.discovery import router as discovery_router
from kosmo.infrastructure.api.routers.documents import router as documents_router
from kosmo.infrastructure.api.routers.feature_chat import router as feature_chat_router
from kosmo.infrastructure.api.routers.features import router as features_router
from kosmo.infrastructure.api.routers.github import router as github_router
from kosmo.infrastructure.api.routers.implementations import router as implementations_router
from kosmo.infrastructure.api.routers.integrations import router as integrations_router
from kosmo.infrastructure.api.routers.knowledge import router as knowledge_router
from kosmo.infrastructure.api.routers.mcp import router as mcp_router
from kosmo.infrastructure.api.routers.modelo import router as modelo_router
from kosmo.infrastructure.api.routers.projects import router as projects_router
from kosmo.infrastructure.api.routers.requirement_chat import router as requirement_chat_router
from kosmo.infrastructure.api.routers.requirements import router as requirements_router
from kosmo.infrastructure.api.routers.schemas import router as schemas_router
from kosmo.infrastructure.api.routers.traceability import router as traceability_router
from kosmo.infrastructure.api.schemas import HttpErrorResponse
from kosmo.infrastructure.persistence.postgres.outbox import OutboxHandler, run_outbox_worker
from kosmo.infrastructure.telemetry import configure_telemetry, instrument_app, instrument_prometheus

# Metadatos OpenAPI

_OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": (
            "Flujo de autenticaciÃ³n PKCE + OAuth 2.0. "
            "Los endpoints siguen el estÃ¡ndar RFC 6749/7636: el cliente genera un "
            "``code_verifier`` efÃ­mero, solicita un ``authorization_code`` en ``/authorize``, "
            "lo intercambia por tokens JWT en ``/token`` y los renueva con ``/refresh``. "
            "Todos los endpoints protegidos requieren ``Authorization: Bearer <access_token>``."
        ),
    },
    {
        "name": "projects",
        "description": (
            "GestiÃ³n de proyectos. Permite crear, listar y consultar proyectos "
            "asociados al usuario autenticado. Cada proyecto agrupa el ciclo "
            "completo de especificaciÃ³n, modelado y generaciÃ³n de artefactos."
        ),
    },
    {
        "name": "discovery",
        "description": (
            "GeneraciÃ³n de documentos de descubrimiento mediante IA. "
            "Permite generar, consultar y actualizar el documento de visiÃ³n "
            "de producto de un proyecto. El documento se estructura en 8 "
            "secciones obligatorias que cubren visiÃ³n, problema, actores, "
            "propuesta de valor, casos de uso, capacidades, reglas de negocio "
            "y atributos de calidad."
        ),
    },
    {
        "name": "features",
        "description": (
            "GeneraciÃ³n y gestiÃ³n de caracterÃ­sticas del producto software mediante IA. "
            "Permite generar caracterÃ­sticas a partir del documento de descubrimiento, "
            "sugerir nuevas caracterÃ­sticas no duplicadas, listar las existentes y "
            "guardar las seleccionadas por el usuario."
        ),
    },
    {
        "name": "requirements",
        "description": (
            "GeneraciÃ³n y gestiÃ³n de requisitos EARS por caracterÃ­stica mediante IA. "
            "Permite generar requisitos a partir del documento de descubrimiento y la "
            "caracterÃ­stica seleccionada, consultarlos y actualizar su contenido en Markdown."
        ),
    },
    {
        "name": "modelo",
        "description": (
            "GeneraciÃ³n y consulta de diagramas de actividad PlantUML por caracterÃ­stica mediante IA. "
            "Permite generar diagramas UML a partir de los requisitos EARS y consultar los diagramas generados."
        ),
    },
    {
        "name": "schemas",
        "description": (
            "IntrospecciÃ³n de contratos. Permite al Frontend consultar el JSON Schema "
            "de cualquier DTO expuesto por la API para generaciÃ³n dinÃ¡mica de formularios, "
            "validaciones y tipos TypeScript."
        ),
    },
    {
        "name": "documents",
        "description": "ModificaciÃ³n directa de documentos sin fase de plan intermedio.",
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
Esta API gestiona el ciclo completo de autenticaciÃ³n de usuarios y la
introspecciÃ³n de contratos de datos para el Frontend.

### Flujo de autenticaciÃ³n recomendado

```
1. POST /api/v1/auth/register      â†’ Crear cuenta
2. POST /api/v1/auth/authorize     â†’ Obtener authorization_code (PKCE)
3. POST /api/v1/auth/token         â†’ Intercambiar cÃ³digo por JWT pair
4. GET  /api/v1/auth/me            â†’ Verificar identidad (Bearer token)
5. POST /api/v1/auth/refresh       â†’ Renovar tokens antes de expirar
6. POST /api/v1/auth/logout        â†’ Revocar sesiÃ³n activa
```

### Seguridad

- Tokens firmados con **RS256** (par de claves RSA 2048-bit)
- ContraseÃ±as hasheadas con **Argon2id** (OWASP 2025)
- Refresh tokens con **Token Rotation**: cada uso emite un par nuevo
- Rate limiting por IP en todos los endpoints sensibles
- Secrets cifrados con **Fernet** (AES-128-CBC + HMAC-SHA256)

### Respuestas de error

Todos los errores de autenticaciÃ³n siguen el esquema `OAuthErrorResponse`
(RFC 6749 Â§5.2). Los errores de infraestructura usan `HttpErrorResponse`.
"""

_SERVERS = [
    {
        "url": "http://localhost:8000",
        "description": "Local â€” desarrollo en mÃ¡quina del programador",
    },
    {
        "url": "https://api-dev.kosmo.app",
        "description": "Desarrollo â€” entorno de integraciÃ³n continua",
    },
    {
        "url": "https://api.kosmo.app",
        "description": "ProducciÃ³n â€” trÃ¡fico real de usuarios",
    },
]

# Respuestas globales reutilizables

_GLOBAL_RESPONSES = {
    403: {
        "description": (
            "Forbidden â€” El token es vÃ¡lido pero no tiene los scopes necesarios para acceder al recurso solicitado."
        ),
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/HttpErrorResponse"},
                "example": {"detail": "No tienes permisos suficientes para realizar esta acciÃ³n."},
            }
        },
    },
    500: {
        "description": (
            "Internal Server Error â€” Error inesperado en el servidor. "
            "Se registra automÃ¡ticamente en el sistema de observabilidad (Logfire/OTEL). "
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

# Ciclo de vida y aplicaciÃ³n


def _make_outbox_handler(container: AppContainer) -> OutboxHandler:
    async def handler(job_type: str, payload: dict[str, Any]) -> None:
        import structlog

        _log = structlog.get_logger("kosmo.outbox")
        agent = container.pipeline.agent
        if job_type == "reflect_and_consolidate":
            from kosmo.contracts.memory.agent_memory import AgentMemoryId
            from kosmo.contracts.pipeline.phase_outputs import ValidationResult
            from kosmo.contracts.sdd.document import SpecPhase

            try:
                await agent.reflect_and_consolidate(
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
        elif job_type == "consistency_evaluate":
            from kosmo.application.consistency.run_consistency_evaluation import run_consistency_evaluation

            await run_consistency_evaluation(
                payload,
                project_repo=container.repos.projects,
                feature_repo=container.repos.features,
                requirement_repo=container.repos.requirements,
                diagram_repo=container.repos.diagrams,
                document_repo=container.repos.documents,
                evaluator=container.pipeline.consistency_evaluator,
                evaluation_repo=container.repos.consistency_evaluations,
            )
        else:
            _log.warning("outbox.unknown_job_type", job_type=job_type)

    return handler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_telemetry(settings)
    components = build_app_components(settings)
    app.state.container = components
    app.state.requirement_repo = components.repos.requirements
    app.state.diagram_repo = components.repos.diagrams

    outbox_task = asyncio.create_task(run_outbox_worker(components.pipeline.outbox, _make_outbox_handler(components)))

    # RecuperaciÃ³n best-effort de generaciones huÃ©rfanas tras un reinicio del backend:
    # marcar IN_PROGRESS como FAILED, cerrar sesiones OpenCode y liberar locks de workspace.
    with contextlib.suppress(Exception):
        await recover_zombie_implementations(
            implementation_repo=components.repos.implementations,
            opencode_client=components.codegen.opencode_client,
            workspace_manager=components.codegen.workspace_manager,
        )

    instrument_app(settings, app=app, db_engine=components.db_engine)
    try:
        yield
    finally:
        outbox_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await outbox_task
        await components.close()


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
            "violations": [{"loc": v.loc, "msg": v.msg, "input": v.input} for v in problem.violations],
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
app.include_router(ai_config_router)
app.include_router(projects_router)
app.include_router(discovery_router)
app.include_router(features_router)
app.include_router(feature_chat_router)
app.include_router(requirements_router)
app.include_router(requirement_chat_router)
app.include_router(chat_sessions_router)
app.include_router(modelo_router)
app.include_router(consistency_router)
app.include_router(schemas_router)
app.include_router(knowledge_router)
app.include_router(documents_router)
app.include_router(traceability_router)
app.include_router(mcp_router)
app.include_router(implementations_router)
app.include_router(integrations_router)
app.include_router(github_router)
app.include_router(deployment_router)


@app.get("/health", tags=["health"], summary="Health check", include_in_schema=True)
async def health() -> dict[str, str]:
    """VerificaciÃ³n de disponibilidad del servidor.

    Devuelve ``{"status": "ok"}`` si el proceso estÃ¡ activo.
    No verifica conectividad con base de datos ni Redis.
    """
    return {"status": "ok"}


@app.get("/ready", tags=["health"], summary="Readiness check", include_in_schema=False)
async def readiness(request: Request) -> dict[str, str]:
    """Verifica las dependencias requeridas antes de aceptar tráfico público."""
    try:
        container = cast(AppContainer, request.app.state.container)
        async with container.db_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        if container.redis is not None:
            await cast(Any, container.redis).ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dependencias no disponibles",
        ) from exc

    return {"status": "ready"}


# EspecificaciÃ³n OpenAPI customizada


def _custom_openapi() -> dict[str, Any]:
    """Genera la especificaciÃ³n OpenAPI enriquecida con respuestas globales.

    Se inyectan las respuestas 403 y 500 en cada operaciÃ³n para que el
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
