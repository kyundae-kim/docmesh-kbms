from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class OllamaEmbeddingProvider:
    """Small adapter around Ollama's synchronous ``embed`` API."""

    def __init__(self, client: Any, model: str) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must not be blank")
        self.client = client
        self.model = model

    def embed(self, text: str) -> Sequence[float]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must not be blank")
        response = self.client.embed(model=self.model, input=text)
        embeddings = response.get("embeddings") if isinstance(response, dict) else getattr(response, "embeddings", None)
        if not embeddings or not isinstance(embeddings, (list, tuple)):
            raise ValueError("invalid embedding response")
        vector = embeddings[0] if embeddings and isinstance(embeddings[0], (list, tuple)) else embeddings
        if not vector:
            raise ValueError("invalid embedding response")
        return vector

    async def aembed(self, text: str) -> Sequence[float]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must not be blank")
        response = await self.client.embed(model=self.model, input=text)
        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: Any) -> Sequence[float]:
        embeddings = response.get("embeddings") if isinstance(response, dict) else getattr(response, "embeddings", None)
        if not embeddings or not isinstance(embeddings, (list, tuple)):
            raise ValueError("invalid embedding response")
        vector = embeddings[0] if isinstance(embeddings[0], (list, tuple)) else embeddings
        if not vector:
            raise ValueError("invalid embedding response")
        return vector
