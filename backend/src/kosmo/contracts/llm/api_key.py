from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from kosmo.contracts.sdd.ids import UserId


class LLMProvider(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    NOOP = "noop"


class EncryptedApiKey(BaseModel):
    key_id: str
    user_id: UserId
    provider: LLMProvider
    cipher_text: str = Field(exclude=True)
    model_default: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class ApiKeyVault(Protocol):
    async def encrypt(self, plaintext: str, key_id: str, user_id: UserId) -> str: ...
    async def decrypt(self, key_id: str) -> str: ...
    async def delete(self, key_id: str) -> None: ...
