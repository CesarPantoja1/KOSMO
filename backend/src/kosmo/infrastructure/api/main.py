from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from kosmo.config import settings
from kosmo.contracts.sdd.errors import SpecError
from kosmo.infrastructure.api.composition import build_auth_components, build_sdd_components
from kosmo.infrastructure.api.errors import generic_http_exception_handler, spec_error_handler
from kosmo.infrastructure.api.middlewares import RequestLoggingMiddleware
from kosmo.infrastructure.api.routers.auth import router as auth_router
from kosmo.infrastructure.api.routers.discovery import discovery_router
from kosmo.infrastructure.api.routers.features import features_router
from kosmo.infrastructure.api.routers.projects import projects_router
from kosmo.infrastructure.api.routers.requirements import requirements_router
from kosmo.infrastructure.api.routers.schemas import router as schemas_router
from kosmo.infrastructure.api.routers.specs import specs_router
from kosmo.infrastructure.api.schemas import HttpErrorResponse
from kosmo.infrastructure.api.websocket.specs import specs_ws_router
from kosmo.infrastructure.telemetry import configure_telemetry, instrument_app

# Metadatos OpenAPI

_OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": (
            "Autenticación PKCE + OAuth 2.0 (RFC 6749/7636). "
            "Registro, autorización con código PKCE S256, intercambio por JWT RS256, "
            "refresh con rotación de tokens y cierre de sesión con revocación de familia."
        ),
    },
    {
        "name": "projects",
        "description": (
            "Gestión de proyectos. Cada proyecto representa un ciclo SDD completo "
            "(Descubrimiento → Características → Requisitos → Modelo → Implementación). "
            "IDs con prefijo `prj_` (ULID). El parámetro `{project_id}` acepta tanto "
            "el ID (`prj_01KT...`) como el slug legible (`mi-proyecto`)."
        ),
    },
    {
        "name": "discovery",
        "description": (
            "Documento de descubrimiento como árbol JSON enriquecido compatible con "
            "editores WYSIWYG (ProseMirror/TipTap). Soporta bold, italic, strike, listas, "
            "citas, bloques de código y reglas horizontales. Incluye índice de navegación "
            "extraído de headings. Endpoints: generar (IA), obtener, guardar (editor), "
            "regenerar (IA reescribe). `{project_id}` acepta ID o slug."
        ),
    },
    {
        "name": "features",
        "description": (
            "Gestión de características del producto. Creación manual o por IA, mejora de "
            "descripciones, sugerencia de alternativas (3, no persiste) y generación automática "
            "(5, persiste). Transición de estados Borrador ↔ Aprobada (vista Kanban). "
            "Rutas scoped (`/projects/{project_id}/features/{feature_identifier}/...`) aceptan "
            "ID o slug. Rutas standalone (`/features/{feature_id}/...`) solo aceptan ID."
        ),
    },
    {
        "name": "requirements",
        "description": (
            "Documento de requisitos EARS como árbol JSON enriquecido, uno por feature "
            "aprobada. Organizado por taxonomía EARS: Ubicuos, Eventos, Estado, Opcionales, "
            "Fallos y Complejos. Endpoints: generar (IA), obtener, guardar (editor), "
            "regenerar (IA). Rutas scoped aceptan ID o slug; standalone solo ID."
        ),
    },
    {
        "name": "specs",
        "description": (
            "Pipeline SDD clásico sobre SpecDocument: creación de especificación, avance por "
            "fases (requirements → design → tasks), consulta de estado y sincronización de "
            "canvas de diseño. `{project_id}` acepta ID o slug; `{spec_id}` solo ID."
        ),
    },
    {
        "name": "schemas",
        "description": (
            "Introspección de contratos: JSON Schema de todos los DTOs expuestos por la API "
            "para generación dinámica de formularios, validaciones y tipos TypeScript."
        ),
    },
    {
        "name": "health",
        "description": "Health check — verificación de disponibilidad del servidor.",
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
KOSMO Backend API — Plataforma de Spec-Driven Development asistido por IA.

## Conceptos clave

### IDs con prefijo tipado (ULID)
Todos los identificadores usan **ULID con prefijo** (26 caracteres Base32 Crockford + prefijo semántico):

| Prefijo | Entidad | Ejemplo |
|---|---|---|
| `prj_` | Proyecto | `prj_01KT07HCKMM...` |
| `feat_` | Feature / Característica | `feat_01KT0CDV84...` |
| `spec_` | Spec / Especificación SDD | `spec_01KT06W284...` |
| `usr_` | Usuario | `usr_01KT05JRA7...` |
| `tsk_` | Tarea | `tsk_01KT08ABC0...` |

### Slugs (URLs amigables)
Proyectos y features también tienen **slugs legibles** generados desde su nombre.
Cualquier ruta que contenga `{project_id}` o `{feature_identifier}` acepta **tanto el ID (prj_...) como el slug**:

```
/api/v1/projects/sistema-gestion-inventario                    ← slug
/api/v1/projects/prj_01KT07HCKMM...                             ← ID
/api/v1/projects/sistema-gestion/features/alertas-stock-bajo     ← ambos slugs
/api/v1/projects/prj_.../features/feat_...                      ← ambos IDs
```

Las rutas standalone (`/features/{id}/status`) solo aceptan ID (no tienen contexto de proyecto para resolver slugs).

### Documentos enriquecidos
Discovery y Requisitos se almacenan como **árboles JSON tipados** compatibles con editores WYSIWYG (ProseMirror/TipTap).
Cada documento incluye un índice de navegación (`sections`) extraído de sus headings.

### Errores — RFC 7807 Problem Detail
Todas las respuestas 4xx/5xx usan `Content-Type: application/problem+json`:

```json
{
  "type": "urn:kosmo:features:not-approved",
  "title": "Feature no aprobada",
  "status": 409,
  "detail": "La característica feat_01KT... debe estar Aprobada",
  "instance": "/api/v1/projects/prj_.../features/feat_.../requirements/generate",
  "trace_id": "01KT05JRA746...",
  "violations": []
}
```

### Convenciones
- **Encoding:** `Content-Type: application/json; charset=utf-8`
- **Llaves:** `snake_case` sin excepciones
- **Fechas:** ISO-8601 UTC con sufijo `Z` (`"2026-06-01T12:00:00Z"`)
- **Booleanos:** `true`/`false`, prefijo `is_`/`has_`
- **Nulables:** `null`, nunca `""` ni `0`

### Flujo SDD completo

```
1. POST /api/v1/projects                              → Crear proyecto (slug auto-generado)
2. POST /api/v1/projects/{id}/discovery/generate      → IA genera documento de descubrimiento
3. POST /api/v1/projects/{id}/features/generate       → IA genera 5 características (persiste)
4. GET  /api/v1/projects/{id}/features                 → Listar features del proyecto
5. PATCH /api/v1/features/{id}/status                  → Aprobar feature (Borrador → Aprobada)
6. POST /api/v1/features/{id}/requirements/generate    → IA genera requisitos EARS
7. PUT  /api/v1/features/{id}/requirements             → Guardar ediciones manuales
```

### Seguridad

- **Auth:** PKCE (RFC 7636) → Authorization Code → RS256 JWT (access + refresh)
- **Hashing:** Argon2id (OWASP 2025)
- **Refresh rotation:** Cada uso emite un par nuevo, el anterior se invalida
- **Rate limiting:** Por IP por endpoint
- **Secrets:** Fernet (AES-128-CBC + HMAC-SHA256)
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
            "Forbidden — El token es válido pero no tiene los scopes necesarios "
            "para acceder al recurso solicitado."
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_telemetry(settings)
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
    app.state.db_engine = auth_components.db_engine

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(auth_components.db_engine, expire_on_commit=False)
    sdd_components = build_sdd_components(settings, session_factory)
    app.state.spec_repo = sdd_components.spec_repo
    app.state.project_repo = sdd_components.project_repo
    app.state.feature_repo = sdd_components.feature_repo
    app.state.llm_client = sdd_components.llm_client
    app.state.blob_storage = sdd_components.blob_storage
    app.state.api_key_vault = sdd_components.api_key_vault

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

app.add_exception_handler(SpecError, spec_error_handler)
app.add_exception_handler(Exception, generic_http_exception_handler)

app.include_router(auth_router)
app.include_router(schemas_router)
app.include_router(specs_router)
app.include_router(specs_ws_router)
app.include_router(projects_router)
app.include_router(discovery_router)
app.include_router(features_router)
app.include_router(requirements_router)


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
