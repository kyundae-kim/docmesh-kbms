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
    result = service.ingest(document_id="doc-001", content_type="text/markdown", content=b"# Hello")
    assert result.text == "# Hello"
    assert result.chunks == []
    assert indexer.calls == [("doc-001", "# Hello")]


def test_ingestion_does_not_decode_binary_content_or_index_it() -> None:
    indexer = FakeIndexer()
    service = DocumentIngestionService(indexer)
    assert service.ingest(document_id="doc-001", content_type="image/png", content=b"\x89PNG").text is None
    assert indexer.calls == []


def test_ingestion_extracts_json_content() -> None:
    indexer = FakeIndexer()
    service = DocumentIngestionService(indexer)

    result = service.ingest(
        document_id="doc-001",
        content_type="application/json",
        content=b'{"name":"Ada","active":true}',
    )

    assert result.text == '{\n  "active": true,\n  "name": "Ada"\n}'
    assert indexer.calls == [("doc-001", result.text)]


def test_ingestion_rejects_invalid_json_content() -> None:
    service = DocumentIngestionService(FakeIndexer())

    try:
        service.ingest(
            document_id="doc-001",
            content_type="application/json",
            content=b"not-json",
        )
    except ValueError as error:
        assert str(error) == "JSON content must be valid UTF-8 JSON"
    else:
        raise AssertionError("invalid JSON was accepted")
