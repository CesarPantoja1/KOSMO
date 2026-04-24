from fastapi import FastAPI

from kosmo.config import settings  # fuerza fail-fast al importar

app = FastAPI(
    title="KOSMO",
    version=settings.api_version,
    docs_url="/docs" if settings.env != "production" else None,
    redoc_url="/redoc" if settings.env != "production" else None,
    openapi_url="/api/v1/openapi.json",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
