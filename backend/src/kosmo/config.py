from pathlib import Path
from typing import Literal, Self
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
    fernet_master_key: SecretStr | None = None

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
    mongo_url: SecretStr | None = None
    redis_url: SecretStr | None = None

    # LLM BYOK
    llm_provider: Literal["anthropic", "openai", "gemini", "deepseek", "noop"]
    llm_model: str
    llm_api_key: SecretStr | None = None

    # API
    api_version: str = "v1"
    cors_allowed_origins: str = "*"
    auth_disabled: bool = False

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
            raw_value = raw_value.replace("postgresql://", "postgresql+asyncpg://", 1)

        parsed = urlsplit(raw_value)
        if (
            parsed.scheme == "postgresql+asyncpg"
            and (
                (parsed.hostname is not None and (
                    parsed.hostname.endswith(".pooler.supabase.com")
                    or parsed.hostname.endswith(".supabase.co")
                    or "pooler" in parsed.hostname
                ))
                or parsed.port == 6543
            )
        ):
            query = dict(parse_qsl(parsed.query, keep_blank_values=True))
            query.setdefault("prepared_statement_cache_size", "0")
            raw_value = urlunsplit(parsed._replace(query=urlencode(query)))

        return raw_value

    @model_validator(mode="after")
    def _resolve_signing_keys(self) -> Self:
        """Resuelve el contenido PEM: variable de entorno → lectura de archivo."""
        if self.auth_disabled:
            return self

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

        if self.fernet_master_key is None:
            raise ValueError("Debe configurar FERNET_MASTER_KEY cuando AUTH_DISABLED=false")

        if self.redis_url is None:
            raise ValueError("Debe configurar REDIS_URL cuando AUTH_DISABLED=false")

        return self


settings = Settings()  # pyright: ignore[reportCallIssue]
