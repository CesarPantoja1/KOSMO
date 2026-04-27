from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # ¡Cambio clave: ahora acepta mayúsculas del .env!
        extra="forbid",
    )

    # Runtime
    env: Literal["development", "staging", "production"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Secretos criptográficos
    jwt_private_key_path: str  # ¡Corregido para coincidir con el .env!
    jwt_public_key_path: str  # ¡Corregido para coincidir con el .env!
    fernet_master_key: SecretStr

    # JWT
    jwt_algorithm: Literal["RS256"] = "RS256"
    jwt_issuer: str = "kosmo"
    jwt_audience: str = "kosmo-api"
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_seconds: int = 604800

    # Argon2id (OWASP 2025)
    argon2_memory_kib: int = 65536
    argon2_time_cost: int = 3
    argon2_parallelism: int = 4

    # DSN de persistencia
    database_url: SecretStr
    mongo_url: SecretStr
    redis_url: SecretStr

    # LLM BYOK
    llm_provider: Literal["anthropic", "openai", "gemini", "noop"]
    llm_model: str
    llm_api_key: SecretStr | None = None

    # API
    api_version: str = "v1"
    cors_allowed_origins: str = "http://localhost:3000"

    # Observabilidad
    logfire_token: SecretStr | None = None


settings = Settings()  # pyright: ignore[reportCallIssue]