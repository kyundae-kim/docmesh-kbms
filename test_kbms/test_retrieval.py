from kbms.dms.retrieval import KnowledgeSearchService


class FakeEmbedding:
    def embed(self, text: str) -> list[float]:
        return [float(len(text))]


class FakeVectorStore:
    def __init__(self) -> None:
        self.calls = []

    def search(self, vector, *, limit=5, document_id=None):
        self.calls.append((vector, limit, document_id))
        return [[
            {"id": "doc:0", "distance": 0.91, "entity": {
                "document_id": "doc", "chunk_index": 0, "text": "matching text",
                "start": 0, "end": 13,
            }},
        ]]


def test_search_service_embeds_query_and_returns_ranked_hits() -> None:
    store = FakeVectorStore()
    service = KnowledgeSearchService(FakeEmbedding(), store)

    hits = service.search("architecture", limit=3, document_id="doc")

    assert hits[0].document_id == "doc"
    assert hits[0].text == "matching text"
    assert hits[0].score == 0.91
    assert hits[0].chunk_index == 0
    assert store.calls == [([12.0], 3, "doc")]


def test_search_service_rejects_invalid_query_and_limit() -> None:
    service = KnowledgeSearchService(FakeEmbedding(), FakeVectorStore())

    for query in ("", " \n"):
        try:
            service.search(query)
        except ValueError as error:
            assert str(error) == "query must not be blank"
        else:
            raise AssertionError("blank query was accepted")
    try:
        service.search("query", limit=0)
    except ValueError as error:
        assert str(error) == "limit must be positive"
    else:
        raise AssertionError("invalid limit was accepted")
