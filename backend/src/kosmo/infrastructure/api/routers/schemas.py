from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from kosmo.infrastructure.api.schemas import (
    AuthorizationCodeResponse,
    AuthorizeRequest,
    LogoutRequest,
    OAuthErrorResponse,
    PrincipalView,
    RegisterRequest,
    TokenExchangeRequest,
    TokenPairResponse,
    TokenRefreshRequest,
    UserPublic,
)

router = APIRouter(prefix="/api/v1/schemas", tags=["schemas"])


_REGISTRY: dict[str, type[BaseModel]] = {
    "RegisterRequest": RegisterRequest,
    "AuthorizeRequest": AuthorizeRequest,
    "AuthorizationCodeResponse": AuthorizationCodeResponse,
    "TokenExchangeRequest": TokenExchangeRequest,
    "TokenRefreshRequest": TokenRefreshRequest,
    "LogoutRequest": LogoutRequest,
    "TokenPairResponse": TokenPairResponse,
    "PrincipalView": PrincipalView,
    "UserPublic": UserPublic,
    "OAuthErrorResponse": OAuthErrorResponse,
}


@router.get("")
async def list_schemas() -> dict[str, list[str]]:
    return {"schemas": sorted(_REGISTRY.keys())}


@router.get("/{name}")
async def get_schema(name: str) -> dict[str, Any]:
    model = _REGISTRY.get(name)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema '{name}' no encontrado",
        )
    return model.model_json_schema()
