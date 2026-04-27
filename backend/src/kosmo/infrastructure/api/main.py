from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from kosmo.config import settings
from kosmo.infrastructure.api.composition import build_auth_components
from kosmo.infrastructure.api.routers.auth_demo import router as auth_demo_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    components = build_auth_components(settings)
    app.state.issue_token_pair = components.issue_token_pair
    app.state.verify_access_token = components.verify_access_token
    app.state.refresh_token_pair = components.refresh_token_pair
    app.state.revoke_session = components.revoke_session
    app.state.redis = components.redis
    try:
        yield
    finally:
        await components.redis.aclose()


app = FastAPI(
    title="KOSMO",
    version=settings.api_version,
    docs_url="/docs" if settings.env != "production" else None,
    redoc_url="/redoc" if settings.env != "production" else None,
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.include_router(auth_demo_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
