from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from kosmo.config import settings
from kosmo.infrastructure.api.composition import (
    build_auth_components,
    build_pipeline_components,
)
from kosmo.infrastructure.api.middlewares import RequestLoggingMiddleware
from kosmo.infrastructure.api.routers.auth import router as auth_router
from kosmo.infrastructure.api.routers.discovery import router as discovery_router
from kosmo.infrastructure.api.routers.features import router as features_router
from kosmo.infrastructure.api.routers.projects import router as projects_router
from kosmo.infrastructure.api.routers.requirements import router as requirements_router
from kosmo.infrastructure.api.routers.schemas import router as schemas_router
from kosmo.infrastructure.api.schemas import HttpErrorResponse
from kosmo.infrastructure.telemetry import configure_telemetry, instrument_app

_OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": (
            "Flujo de autenticacion PKCE + OAuth 2.0. "
            "Los endpoints siguen el estandar RFC 6749/7636: el cliente genera un "
            "``code_verifier`` efimero, solicita un ``authorization_code`` en ``/authorize``, "
            "lo intercambia por tokens JWT en ``/token`` y los renueva con ``/refresh``. "
            "Todos los endpoints protegidos requieren ``Authorization: Bearer <access_token>``."
        ),
    },
    {
        "name": "projects",
        "description": "Gestion de proyectos KOSMO. Crear, listar y consultar proyectos.",
    },
    {
        "name": "discovery",
        "description": "Fase de Descubrimiento: generacion y edicion del documento de discovery.",
    },
    {
        "name": "features",
        "description": "Fase de Caracteristicas: generacion, sugerencia y aprobacion de features.",
    },
    {
        "name": "requirements",
        "description": "Fase de Requisitos EARS: generacion y edicion de requisitos por feature.",
    },
    {
        "name": "schemas",
        "description": (
            "Introspeccion de contratos. Permite al Frontend consultar el JSON Schema "
            "de cualquier DTO expuesto por la API para generacion dinamica de formularios, "
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
Esta API gestiona el ciclo completo de autenticacion de usuarios y la
generacion de especificaciones de diseno tecnico (SDD) asistida por IA.

### Flujo de autenticacion recomendado

```
1. POST /api/v1/auth/register      -> Crear cuenta
2. POST /api/v1/auth/authorize     -> Obtener authorization_code (PKCE)
3. POST /api/v1/auth/token         -> Intercambiar codigo por JWT pair
4. GET  /api/v1/auth/me            -> Verificar identidad (Bearer token)
5. POST /api/v1/auth/refresh       -> Renovar tokens antes de expirar
6. POST /api/v1/auth/logout        -> Revocar sesion activa
```

### Flujo SDD (Spec-Driven Development)

```
1. POST /api/v1/projects                           -> Crear proyecto
2. POST /api/v1/projects/{id}/discovery/generate    -> Generar documento de discovery
3. PUT  /api/v1/projects/{id}/discovery              -> Guardar ediciones de discovery
4. POST /api/v1/projects/{id}/features/generate     -> Generar 5 features (C01-C05)
5. POST /api/v1/projects/{id}/features/suggest      -> Sugerir 3 features adicionales
6. POST /api/v1/projects/{id}/features               -> Guardar features seleccionadas
7. PATCH /api/v1/features/{id}/status                -> Aprobar feature (borrador -> aprobada)
8. POST /api/v1/features/{id}/requirements/generate  -> Generar requisitos EARS por feature
9. PUT  /api/v1/features/{id}/requirements            -> Guardar ediciones de requisitos
```

### Seguridad

- Tokens firmados con **RS256** (par de claves RSA 2048-bit)
- Contrasenias hasheadas con **Argon2id** (OWASP 2025)
- Refresh tokens con **Token Rotation**: cada uso emite un par nuevo
- Rate limiting por IP en todos los endpoints sensibles
- Secrets cifrados con **Fernet** (AES-128-CBC + HMAC-SHA256)

### Respuestas de error

Todos los errores de autenticacion siguen el esquema `OAuthErrorResponse`
(RFC 6749 section 5.2). Los errores de infraestructura usan `HttpErrorResponse`.
"""

_SERVERS = [
    {
        "url": "http://localhost:8000",
        "description": "Local — desarrollo en maquina del programador",
    },
    {
        "url": "https://api-dev.kosmo.app",
        "description": "Desarrollo — entorno de integracion continua",
    },
    {
        "url": "https://api.kosmo.app",
        "description": "Produccion — trafico real de usuarios",
    },
]

_GLOBAL_RESPONSES = {
    403: {
        "description": (
            "Forbidden — El token es valido pero no tiene los scopes necesarios "
            "para acceder al recurso solicitado."
        ),
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/HttpErrorResponse"},
                "example": {"detail": "No tienes permisos suficientes para realizar esta accion."},
            }
        },
    },
    500: {
        "description": (
            "Internal Server Error — Error inesperado en el servidor. "
            "Se registra automaticamente en el sistema de observabilidad (Logfire/OTEL). "
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_telemetry(settings)
    auth_components = build_auth_components(settings)
    pipeline_components = build_pipeline_components(settings, auth_components.db_engine)

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
    app.state.db_engine = auth_components.db_engine

    app.state.pipeline_components = pipeline_components

    instrument_app(settings, app=app, db_engine=auth_components.db_engine)
    try:
        yield
    finally:
        await auth_components.redis.aclose()
        await auth_components.db_engine.dispose()


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth_router)
app.include_router(schemas_router)
app.include_router(projects_router)
app.include_router(discovery_router)
app.include_router(features_router)
app.include_router(requirements_router)


@app.get("/health", tags=["health"], summary="Health check", include_in_schema=True)
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _custom_openapi() -> dict[str, Any]:
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

    http_error_schema = HttpErrorResponse.model_json_schema()

    components: dict[str, Any] = schema.setdefault("components", {})
    schemas_dict: dict[str, Any] = components.setdefault("schemas", {})
    schemas_dict["HttpErrorResponse"] = http_error_schema

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
