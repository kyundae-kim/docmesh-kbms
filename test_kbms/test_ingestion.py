from kbms.dms.ingestion import DocumentIngestionService
from kbms.dms.knowledge import TextChunk


class FakeIndexer:
    def __init__(self) -> None:
        self.calls = []

    def index(self, document_id: str, text: str) -> list[TextChunk]:
        self.calls.append((document_id, text))
        return []


def test_ingestion_extracts_text_and_indexes_document() -> None:
    indexer = FakeIndexer()
    service = DocumentIngestionService(indexer)
    assert service.ingest(document_id="doc-001", content_type="text/markdown", content=b"# Hello") == "# Hello"
    assert indexer.calls == [("doc-001", "# Hello")]


def test_ingestion_does_not_decode_binary_content_or_index_it() -> None:
    indexer = FakeIndexer()
    service = DocumentIngestionService(indexer)
    assert service.ingest(document_id="doc-001", content_type="image/png", content=b"\x89PNG") is None
    assert indexer.calls == []
