from __future__ import annotations

import asyncio
from typing import Any


class FastembedEmbedder:
    def __init__(self, model_name: str = "BAAI/all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._embedder: Any = None

    @property
    def model_name(self) -> str:
        return self._model_name

    def _lazy_load(self) -> Any:
        if self._embedder is None:
            from fastembed import TextEmbedding  # pyright: ignore[reportMissingImports, reportUnknownVariableType]

            self._embedder = TextEmbedding(model_name=self._model_name)
        return self._embedder  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    async def embed(self, text: str) -> list[float] | None:
        try:
            embedder = await asyncio.to_thread(self._lazy_load)
            result = await asyncio.to_thread(list, embedder.embed([text[:2000]]))
            if result and len(result) > 0:
                return list(result[0])
            return None
        except Exception:
            return None

    @staticmethod
    def text_for_embedding(output: Any, validation_errors: list[str]) -> str:
        parts = [str(output)[:2000]]
        if validation_errors:
            parts.append("Errores: " + "; ".join(validation_errors[:5]))
        return "\n".join(parts)
