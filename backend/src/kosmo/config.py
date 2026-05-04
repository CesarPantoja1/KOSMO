from pathlib import Path
from typing import Literal, Self

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
    )

    # Runtime
    env: Literal["development", "staging", "production"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Secretos criptográficos — contenido PEM (prioridad) o rutas como fallback
    jwt_private_key_pem: SecretStr | None = None
    jwt_public_key_pem: SecretStr | None = None
    jwt_private_key_path: str | None = None
    jwt_public_key_path: str | None = None
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
    otel_service_name: str = "kosmo-backend"
    otel_environment: str = "development"

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_async_postgres_url(cls, value: object) -> object:
        if isinstance(value, SecretStr):
            raw_value = value.get_secret_value()
        elif isinstance(value, str):
            raw_value = value
        else:
            return value

        if raw_value.startswith("postgresql://"):
            return raw_value.replace("postgresql://", "postgresql+asyncpg://", 1)

        return value

    @model_validator(mode="after")
    def _resolve_signing_keys(self) -> Self:
        """Resuelve el contenido PEM: variable de entorno → lectura de archivo."""
        if self.jwt_private_key_pem is None:
            if self.jwt_private_key_path is None:
                raise ValueError("Debe configurar JWT_PRIVATE_KEY_PEM o JWT_PRIVATE_KEY_PATH")
            pem = Path(self.jwt_private_key_path).read_text(encoding="utf-8")
            self.jwt_private_key_pem = SecretStr(pem)

        if self.jwt_public_key_pem is None:
            if self.jwt_public_key_path is None:
                raise ValueError("Debe configurar JWT_PUBLIC_KEY_PEM o JWT_PUBLIC_KEY_PATH")
            pem = Path(self.jwt_public_key_path).read_text(encoding="utf-8")
            self.jwt_public_key_pem = SecretStr(pem)

        return self


settings = Settings()  # pyright: ignore[reportCallIssue]
