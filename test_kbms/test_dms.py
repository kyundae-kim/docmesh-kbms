from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from kbms.dms.embedding import OllamaEmbeddingProvider
from kbms.dms.knowledge import TextChunker
from kbms.dms.models import Base
from kbms.dms.repository import DocumentRepository


def repository() -> tuple[object, Session, DocumentRepository]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    return engine, session, DocumentRepository(session)


def test_document_repository_crud_and_knowledge_text() -> None:
    _, session, repo = repository()
    try:
        created = repo.create(
            document_id="doc-001", title="Architecture notes", source_uri="file:///notes.md",
            content_type="text/markdown", content_hash="hash-001", owner_id="user-001",
        )
        assert repo.save_content("doc-001", b"# Architecture") is not None
        assert repo.update_extracted_text("doc-001", "Architecture uses SQLAlchemy.")
        session.commit()
        loaded = repo.get("doc-001")
        assert loaded is not None
        assert loaded.id == created.id == "doc-001"
        assert loaded.extracted_text == "Architecture uses SQLAlchemy."
        assert repo.get_content("doc-001") == b"# Architecture"
    finally:
        session.close()


def test_repository_lists_owner_newest_first_and_missing_is_safe() -> None:
    _, session, repo = repository()
    try:
        for identifier, day, owner in [("old", 1, "u"), ("new", 2, "u"), ("other", 3, "v")]:
            repo.create(
                document_id=identifier, title=identifier, source_uri="uri", content_type="text/plain",
                content_hash=identifier, owner_id=owner, created_at=datetime(2026, 1, day, tzinfo=UTC),
            )
        session.commit()
        assert [doc.id for doc in repo.list("u")] == ["new", "old"]
        assert repo.get("missing") is None
        assert repo.get_content("missing") is None
        assert repo.update_extracted_text("missing", "text") is False
    finally:
        session.close()


def test_chunker_preserves_identity_and_overlap() -> None:
    chunks = TextChunker(10, overlap=3).chunk("0123456789abcdefghij", document_id="doc-001")
    assert [chunk.index for chunk in chunks] == [0, 1, 2]
    assert [chunk.text for chunk in chunks] == ["0123456789", "789abcdefg", "efghij"]
    assert [(chunk.start, chunk.end) for chunk in chunks] == [(0, 10), (7, 17), (14, 20)]
    assert all(chunk.document_id == "doc-001" for chunk in chunks)
    assert TextChunker(10, 2).chunk("   \n", document_id="doc") == []


@pytest.mark.parametrize("chunk_size, overlap", [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11)])
def test_chunker_rejects_invalid_window(chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        TextChunker(chunk_size, overlap)


class FakeOllamaClient:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[dict[str, str]] = []

    def embed(self, *, model: str, input: str) -> object:
        self.calls.append({"model": model, "input": input})
        return self.response


def test_ollama_embedding_provider_uses_configured_model() -> None:
    client = FakeOllamaClient({"embeddings": [[0.1, 0.2, 0.3]]})
    provider = OllamaEmbeddingProvider(client, "nomic-embed-text")
    assert provider.embed("SQLAlchemy document") == [0.1, 0.2, 0.3]
    assert client.calls == [{"model": "nomic-embed-text", "input": "SQLAlchemy document"}]


def test_ollama_embedding_provider_validates_input_and_response() -> None:
    with pytest.raises(ValueError, match="model must not be blank"):
        OllamaEmbeddingProvider(FakeOllamaClient({"embeddings": [[0.1]]}), " ")
    client = FakeOllamaClient({"embeddings": [[0.1]]})
    provider = OllamaEmbeddingProvider(client, "model")
    with pytest.raises(ValueError, match="text must not be blank"):
        provider.embed(" \n")
    for response in ({}, {"embeddings": []}, {"embeddings": [[]]}):
        with pytest.raises(ValueError, match="invalid embedding response"):
            OllamaEmbeddingProvider(FakeOllamaClient(response), "model").embed("content")
