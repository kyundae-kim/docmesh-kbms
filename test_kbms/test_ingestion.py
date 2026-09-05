import hashlib

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from kbms.dms.ingestion import DocumentIngestionService
from kbms.dms.knowledge import TextChunk
from kbms.dms.models import Base
from kbms.dms.repository import DocumentRepository


class FakeIndexer:
    def __init__(self) -> None:
        self.calls = []

    def index(self, document_id: str, text: str) -> list[TextChunk]:
        self.calls.append((document_id, text))
        return []


def test_ingestion_persists_content_hash_text_and_indexes_document() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    indexer = FakeIndexer()
    with Session(engine) as session:
        service = DocumentIngestionService(DocumentRepository(session), indexer)
        document = service.ingest(
            document_id="doc-001", title="Notes", source_uri="file:///notes.md",
            content_type="text/markdown", owner_id="user-001", content=b"# Hello",
        )
        session.commit()

        assert document.id == "doc-001"
        assert document.content_hash == hashlib.sha256(b"# Hello").hexdigest()
        assert document.extracted_text == "# Hello"
        assert indexer.calls == [("doc-001", "# Hello")]
        assert service.repository.get_content("doc-001") == b"# Hello"


def test_ingestion_does_not_decode_binary_content_or_index_it() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    indexer = FakeIndexer()
    with Session(engine) as session:
        service = DocumentIngestionService(DocumentRepository(session), indexer)
        document = service.ingest(
            document_id="doc-001", title="Image", source_uri="file:///image.png",
            content_type="image/png", owner_id="user-001", content=b"\x89PNG",
        )

        assert document.extracted_text is None
        assert indexer.calls == []
