from __future__ import annotations

import hashlib
from typing import Protocol

from .knowledge import TextChunk
from .models import Document
from .repository import DocumentRepository


class DocumentIndexer(Protocol):
    def index(self, document_id: str, text: str) -> list[TextChunk]: ...


class DocumentIngestionService:
    """Persist an uploaded document and derive searchable text when supported."""

    def __init__(self, repository: DocumentRepository, indexer: DocumentIndexer) -> None:
        self.repository = repository
        self.indexer = indexer

    def ingest(
        self,
        *,
        document_id: str,
        title: str,
        source_uri: str,
        content_type: str,
        owner_id: str,
        content: bytes,
    ) -> Document:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        if not content:
            raise ValueError("content must not be empty")
        if self.repository.get(document_id) is not None:
            raise ValueError("document already exists")

        document = self.repository.create(
            document_id=document_id,
            title=title,
            source_uri=source_uri,
            content_type=content_type,
            content_hash=hashlib.sha256(content).hexdigest(),
            owner_id=owner_id,
        )
        self.repository.save_content(document_id, content)
        text = self._extract_text(content_type, content)
        if text is not None:
            self.repository.update_extracted_text(document_id, text)
            self.indexer.index(document_id, text)
        return document

    @staticmethod
    def _extract_text(content_type: str, content: bytes) -> str | None:
        if not content_type.lower().startswith("text/"):
            return None
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("text content must be valid UTF-8") from error
