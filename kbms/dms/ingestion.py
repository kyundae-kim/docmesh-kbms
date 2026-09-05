from __future__ import annotations

from typing import Protocol

from .knowledge import TextChunk


class DocumentIndexer(Protocol):
    def index(self, document_id: str, text: str) -> list[TextChunk]: ...


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
    ) -> str | None:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        if not content:
            raise ValueError("content must not be empty")
        text = self._extract_text(content_type, content)
        if text is not None:
            self.indexer.index(document_id, text)
        return text

    @staticmethod
    def _extract_text(content_type: str, content: bytes) -> str | None:
        if not content_type.lower().startswith("text/"):
            return None
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("text content must be valid UTF-8") from error
