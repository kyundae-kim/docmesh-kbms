from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Document, DocumentContent


class DocumentRepository:
    """Persistence operations for documents and their derived text."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        document_id: str,
        title: str,
        source_uri: str,
        content_type: str,
        content_hash: str,
        owner_id: str,
        created_at: datetime | None = None,
    ) -> Document:
        document = Document(
            id=document_id,
            title=title,
            source_uri=source_uri,
            content_type=content_type,
            content_hash=content_hash,
            owner_id=owner_id,
            created_at=created_at or datetime.now(UTC),
        )
        self.session.add(document)
        return document

    def get(self, document_id: str) -> Document | None:
        return self.session.get(Document, document_id)

    def list(self, owner_id: str) -> list[Document]:
        statement = (
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def save_content(self, document_id: str, content: bytes) -> DocumentContent | None:
        document = self.get(document_id)
        if document is None:
            return None
        stored = self.session.get(DocumentContent, document_id)
        if stored is None:
            stored = DocumentContent(document_id=document_id, content=content)
            self.session.add(stored)
        else:
            stored.content = content
        return stored

    def get_content(self, document_id: str) -> bytes | None:
        stored = self.session.get(DocumentContent, document_id)
        return None if stored is None else stored.content

    def update_extracted_text(self, document_id: str, text: str) -> bool:
        document = self.get(document_id)
        if document is None:
            return False
        document.extracted_text = text
        return True
