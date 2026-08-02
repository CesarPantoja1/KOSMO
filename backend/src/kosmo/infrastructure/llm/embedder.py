from __future__ import annotations

import asyncio
from typing import Any

import structlog
from openai import AsyncOpenAI

_log = structlog.get_logger(__name__)


class OpenAIEmbedder:
    _DEFAULT_MODEL = "text-embedding-3-small"
    _DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self._model_name = model
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url if base_url else "https://api.openai.com/v1",
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    async def embed(self, text: str) -> list[float] | None:
        try:
            result = await asyncio.wait_for(
                self._client.embeddings.create(
                    model=self._model_name,
                    input=text[:8000],
                ),
                timeout=self._DEFAULT_TIMEOUT,
            )
            return list(result.data[0].embedding)
        except Exception:
            _log.warning("embedder.failed", model=self._model_name, exc_info=True)
            return None

    @staticmethod
    def text_for_embedding(output: Any, validation_errors: list[str]) -> str:
        parts = [str(output)[:2000]]
        if validation_errors:
            parts.append("Errores: " + "; ".join(validation_errors[:5]))
        return "\n".join(parts)


EmbeddingGenerator = OpenAIEmbedder  # ponytail: alias de retrocompatibilidad, eliminar cuando no se referencie
