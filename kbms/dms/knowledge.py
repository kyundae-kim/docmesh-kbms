from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TextChunk:
    document_id: str
    index: int
    text: str
    start: int
    end: int


class TextChunker:
    def __init__(self, chunk_size: int, overlap: int = 0) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be non-negative and smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, *, document_id: str) -> list[TextChunk]:
        if not text or not text.strip():
            return []
        step = self.chunk_size - self.overlap
        chunks: list[TextChunk] = []
        for index, start in enumerate(range(0, len(text), step)):
            end = min(start + self.chunk_size, len(text))
            chunks.append(TextChunk(document_id, index, text[start:end], start, end))
            if end == len(text):
                break
        return chunks


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> Sequence[float]: ...

    async def aembed(self, text: str) -> Sequence[float]: ...


class VectorStore(Protocol):
    def upsert(self, rows: Sequence[dict[str, object]]) -> object: ...

    async def aupsert(self, rows: Sequence[dict[str, object]]) -> object: ...

    def search(
        self,
        vector: Sequence[float],
        *,
        limit: int = 5,
        document_id: str | None = None,
        partition_kind: str | None = None,
        partition_id: str | None = None,
    ) -> list[list[dict[str, object]]]: ...

    async def asearch(
        self,
        vector: Sequence[float],
        *,
        limit: int = 5,
        document_id: str | None = None,
        partition_kind: str | None = None,
        partition_id: str | None = None,
    ) -> list[list[dict[str, object]]]: ...

    def delete_document(self, document_id: str) -> object: ...

    async def adelete_document(self, document_id: str) -> object: ...


class KnowledgeIndexer:
    """Turn extracted document text into vector-store records."""

    def __init__(
        self,
        chunker: TextChunker,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self.chunker = chunker
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    def index(
        self,
        document_id: str,
        text: str,
        *,
        source_uri: str | None = None,
        partition_kind: str | None = None,
        partition_id: str | None = None,
    ) -> list[TextChunk]:
        chunks = self.chunker.chunk(text, document_id=document_id)
        rows = [
            {
                "id": f"{chunk.document_id}:{chunk.index}",
                "document_id": chunk.document_id,
                "chunk_index": chunk.index,
                "text": chunk.text,
                "start": chunk.start,
                "end": chunk.end,
                "vector": list(self.embedding_provider.embed(chunk.text)),
            }
            for chunk in chunks
        ]
        for row in rows:
            if source_uri is not None:
                row["source_uri"] = source_uri
            if partition_kind is not None and partition_id is not None:
                row["partition_kind"] = partition_kind
                row["partition_id"] = partition_id
        if rows:
            self.vector_store.upsert(rows)
        return chunks

    async def aindex(
        self,
        document_id: str,
        text: str,
        *,
        source_uri: str | None = None,
        partition_kind: str | None = None,
        partition_id: str | None = None,
    ) -> list[TextChunk]:
        chunks = self.chunker.chunk(text, document_id=document_id)
        rows = []
        for chunk in chunks:
            rows.append({
                "id": f"{chunk.document_id}:{chunk.index}",
                "document_id": chunk.document_id,
                "chunk_index": chunk.index,
                "text": chunk.text,
                "start": chunk.start,
                "end": chunk.end,
                "vector": list(await self.embedding_provider.aembed(chunk.text)),
            })
        for row in rows:
            if source_uri is not None:
                row["source_uri"] = source_uri
            if partition_kind is not None and partition_id is not None:
                row["partition_kind"] = partition_kind
                row["partition_id"] = partition_id
        if rows:
            await self.vector_store.aupsert(rows)
        return chunks
