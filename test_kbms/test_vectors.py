from kbms.dms.vectors import MilvusVectorStore


class FakeMilvusClient:
    def __init__(self) -> None:
        self.collections: set[str] = set()
        self.created = []
        self.inserted = []
        self.searched = []
        self.deleted = []

    def has_collection(self, collection_name: str) -> bool:
        return collection_name in self.collections

    def create_collection(self, **kwargs):
        self.created.append(kwargs)
        self.collections.add(kwargs["collection_name"])

    def insert(self, collection_name, data):
        self.inserted.append((collection_name, data))
        return {"insert_count": len(data)}

    def search(self, collection_name, data, filter, limit, output_fields):
        self.searched.append((collection_name, data, filter, limit, output_fields))
        return [[{"id": "doc:0", "distance": 0.99, "entity": {"text": "hello"}}]]

    def delete(self, collection_name, filter):
        self.deleted.append((collection_name, filter))
        return {"delete_count": 1}


def test_milvus_store_creates_collection_and_upserts_rows() -> None:
    client = FakeMilvusClient()
    store = MilvusVectorStore(client, collection_name="documents", dimension=3)

    result = store.upsert([{"id": "doc:0", "vector": [0.1, 0.2, 0.3], "text": "hello"}])

    assert result == {"insert_count": 1}
    assert client.created == [{
        "collection_name": "documents", "dimension": 3,
        "primary_field_name": "id", "id_type": "str",
        "max_length": 512,
        "vector_field_name": "vector", "metric_type": "COSINE", "auto_id": False,
        "consistency_level": "Strong",
    }]
    assert client.inserted[0][0] == "documents"


def test_milvus_store_reuses_existing_collection_and_searches() -> None:
    client = FakeMilvusClient()
    client.collections.add("documents")
    store = MilvusVectorStore(client, collection_name="documents", dimension=3)

    result = store.search([0.1, 0.2, 0.3], limit=2, document_id="doc-001")

    assert result[0][0]["id"] == "doc:0"
    assert client.created == []
    assert client.searched == [("documents", [[0.1, 0.2, 0.3]], 'document_id == "doc-001"', 2, ["id", "document_id", "chunk_index", "text", "start", "end", "source_uri", "partition_kind", "partition_id"])]


def test_milvus_store_deletes_all_chunks_for_document() -> None:
    client = FakeMilvusClient()
    client.collections.add("documents")
    store = MilvusVectorStore(client, collection_name="documents", dimension=3)

    assert store.delete_document("doc-001") == {"delete_count": 1}
    assert client.deleted == [("documents", 'document_id == "doc-001"')]
