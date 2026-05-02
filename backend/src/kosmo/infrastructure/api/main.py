from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kosmo.config import settings
from kosmo.infrastructure.api.composition import build_auth_components
from kosmo.infrastructure.api.middlewares import RequestLoggingMiddleware
from kosmo.infrastructure.api.routers.auth import router as auth_router
from kosmo.infrastructure.api.routers.schemas import router as schemas_router
from kosmo.infrastructure.telemetry import configure_telemetry, instrument_app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_telemetry(settings)
    components = build_auth_components(settings)
    app.state.register_user = components.register_user
    app.state.login_attempt_store = components.login_attempt_store
    app.state.authorize_with_pkce = components.authorize_with_pkce
    app.state.exchange_authorization_code = components.exchange_authorization_code
    app.state.issue_token_pair = components.issue_token_pair
    app.state.verify_access_token = components.verify_access_token
    app.state.refresh_token_pair = components.refresh_token_pair
    app.state.revoke_session = components.revoke_session
    app.state.password_hasher = components.password_hasher
    app.state.secret_cipher = components.secret_cipher
    app.state.user_repository = components.user_repository
    app.state.redis = components.redis
    app.state.db_engine = components.db_engine
    instrument_app(settings, app=app, db_engine=components.db_engine)
    try:
        yield
    finally:
        await components.redis.aclose()
        await components.db_engine.dispose()


app = FastAPI(
    title="KOSMO",
    version=settings.api_version,
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
