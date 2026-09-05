from kbms.dms.knowledge import KnowledgeIndexer, TextChunker


class FakeEmbedding:
    def embed(self, text: str) -> list[float]:
        return [float(len(text)), 1.0]


class FakeVectorStore:
    def __init__(self) -> None:
        self.rows = []

    def upsert(self, rows):
        self.rows.extend(rows)


def test_knowledge_indexer_chunks_embeds_and_stores_document() -> None:
    store = FakeVectorStore()
    indexer = KnowledgeIndexer(TextChunker(4, overlap=1), FakeEmbedding(), store)

    chunks = indexer.index("doc-001", "abcdefgh")

    assert [chunk.text for chunk in chunks] == ["abcd", "defg", "gh"]
    assert [row["id"] for row in store.rows] == ["doc-001:0", "doc-001:1", "doc-001:2"]
    assert [row["document_id"] for row in store.rows] == ["doc-001"] * 3
    assert [row["vector"] for row in store.rows] == [[4.0, 1.0], [4.0, 1.0], [2.0, 1.0]]


def test_knowledge_indexer_does_not_write_empty_documents() -> None:
    store = FakeVectorStore()
    indexer = KnowledgeIndexer(TextChunker(4), FakeEmbedding(), store)

    assert indexer.index("doc-001", " \n") == []
    assert store.rows == []
