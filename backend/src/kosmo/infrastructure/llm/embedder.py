from __future__ import annotations

import asyncio
from typing import Any

from openai import AsyncOpenAI


class EmbeddingGenerator:
    _DEFAULT_MODEL = "text-embedding-3-small"
    _DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self._model = model
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url if base_url else "https://api.openai.com/v1",
        )

    async def embed(self, text: str) -> list[float] | None:
        try:
            result = await asyncio.wait_for(
                self._client.embeddings.create(
                    model=self._model,
                    input=text[:8000],
                ),
                timeout=self._DEFAULT_TIMEOUT,
            )
            return list(result.data[0].embedding)
        except Exception:
            return None

    @staticmethod
    def text_for_embedding(output: Any, validation_errors: list[str]) -> str:
        parts = [str(output)[:2000]]
        if validation_errors:
            parts.append("Errores: " + "; ".join(validation_errors[:5]))
        return "\n".join(parts)
