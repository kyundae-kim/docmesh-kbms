from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from .knowledge import TextChunk


class DocumentIndexer(Protocol):
    def index(self, document_id: str, text: str, **kwargs: object) -> list[TextChunk]: ...

    async def aindex(self, document_id: str, text: str, **kwargs: object) -> list[TextChunk]: ...


@dataclass(frozen=True, slots=True)
class IngestionResult:
    text: str | None
    chunks: list[TextChunk]


class DocumentIngestionService:
    """Extract text from dms-core content and derive searchable knowledge."""

    def __init__(self, indexer: DocumentIndexer) -> None:
        self.indexer = indexer

    def ingest(
        self,
        *,
        document_id: str,
        content_type: str,
        content: bytes,
        source_uri: str | None = None,
        partition_kind: str | None = None,
        partition_id: str | None = None,
    ) -> IngestionResult:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        if not content:
            raise ValueError("content must not be empty")
        text = self._extract_text(content_type, content)
        if text is None:
            chunks = []
        elif any(value is not None for value in (source_uri, partition_kind, partition_id)):
            chunks = self.indexer.index(
                document_id,
                text,
                source_uri=source_uri,
                partition_kind=partition_kind,
                partition_id=partition_id,
            )
        else:
            chunks = self.indexer.index(document_id, text)
        return IngestionResult(text=text, chunks=chunks)

    async def aingest(
        self,
        *,
        document_id: str,
        content_type: str,
        content: bytes,
        source_uri: str | None = None,
        partition_kind: str | None = None,
        partition_id: str | None = None,
    ) -> IngestionResult:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        if not content:
            raise ValueError("content must not be empty")
        text = self._extract_text(content_type, content)
        if text is None:
            chunks = []
        elif any(value is not None for value in (source_uri, partition_kind, partition_id)):
            chunks = await self.indexer.aindex(
                document_id,
                text,
                source_uri=source_uri,
                partition_kind=partition_kind,
                partition_id=partition_id,
            )
        else:
            chunks = await self.indexer.aindex(document_id, text)
        return IngestionResult(text=text, chunks=chunks)

    @staticmethod
    def _extract_text(content_type: str, content: bytes) -> str | None:
        media_type = content_type.lower().split(";", 1)[0].strip()
        if media_type == "application/json":
            try:
                value = json.loads(content.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError("JSON content must be valid UTF-8 JSON") from error
            return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
        if not media_type.startswith("text/"):
            return None
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("text content must be valid UTF-8") from error
