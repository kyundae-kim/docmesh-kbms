import pytest

from kbms.dms.embedding import OllamaEmbeddingProvider
from kbms.dms.knowledge import TextChunker


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
