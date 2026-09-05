from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .knowledge import EmbeddingProvider, VectorStore


@dataclass(frozen=True, slots=True)
class SearchHit:
    document_id: str
    chunk_index: int
    text: str
    score: float
    start: int | None = None
    end: int | None = None


class KnowledgeSearchService:
    """Application service for semantic search over indexed document chunks."""

    def __init__(self, embedding_provider: EmbeddingProvider, vector_store: VectorStore) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        document_id: str | None = None,
    ) -> list[SearchHit]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must not be blank")
        if limit <= 0:
            raise ValueError("limit must be positive")
        vector = self.embedding_provider.embed(query)
        batches = self.vector_store.search(vector, limit=limit, document_id=document_id)
        if not batches:
            return []
        return [self._to_hit(item) for item in batches[0]]

    @staticmethod
    def _to_hit(item: Any) -> SearchHit:
        entity = item.get("entity", {}) if isinstance(item, dict) else getattr(item, "entity", {})
        if not isinstance(entity, dict):
            entity = {field: getattr(entity, field, None) for field in (
                "document_id", "chunk_index", "text", "start", "end"
            )}
        identifier = item.get("id") if isinstance(item, dict) else getattr(item, "id", "")
        document_id = entity.get("document_id") or str(identifier).rsplit(":", 1)[0]
        return SearchHit(
            document_id=str(document_id),
            chunk_index=int(entity.get("chunk_index") or 0),
            text=str(entity.get("text", "")),
            score=float(item.get("distance", 0.0) if isinstance(item, dict) else getattr(item, "distance", 0.0)),
            start=entity.get("start"),
            end=entity.get("end"),
        )
