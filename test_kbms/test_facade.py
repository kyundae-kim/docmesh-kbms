from dms import DocumentContent, UploadDocumentResult
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import kbms
from kbms import KnowledgeManagement
from kbms.dms.models import Base
from kbms.dms.repository import DocumentRepository


class FakeDms:
    def __init__(self) -> None:
        self.uploads = []
        self.deletes = []

    def upload_document(self, request, *, partition):
        self.uploads.append((request, partition))
        return UploadDocumentResult(document_id=request.document_id or "generated", metadata=None)

    def get_document_content(self, document_id, *, partition):
        return DocumentContent(
            document_id=document_id,
            content=b"hello",
            content_type="text/plain",
            filename="hello.txt",
            size=5,
        )

    def delete_document(self, document_id, *, partition, hard_delete=False):
        self.deletes.append((document_id, partition, hard_delete))
        return {"document_id": document_id}


class FakeOllama:
    def embed(self, *, model, input):
        return {"embeddings": [[float(len(input))]]}


class FakeMilvus:
    def __init__(self) -> None:
        self.rows = []

    def has_collection(self, *, collection_name):
        return True

    def insert(self, *, collection_name, data):
        self.rows.extend(data)

    def search(self, *, collection_name, data, filter, limit, output_fields):
        return []


def test_package_exposes_one_public_facade() -> None:
    assert kbms.__all__ == ["KnowledgeManagement"]
    assert KnowledgeManagement.__name__ == "KnowledgeManagement"


def test_facade_composes_dms_persistence_indexing_and_search(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    dms = FakeDms()
    vectors = FakeMilvus()
    monkeypatch.setattr("kbms.facade._build_dms_client", lambda **kwargs: dms)
    partition_kind = "personal"
    partition_id = "user-1"

    with Session(engine) as session:
        facade = KnowledgeManagement(
            session=session,
            engine=engine,
            minio_client=object(),
            bucket_name="test-bucket",
            ollama_client=FakeOllama(),
            milvus_client=vectors,
            vector_dimension=1,
            chunk_size=4,
            overlap=1,
        )
        result = facade.upload_document(
            content=b"hello",
            filename="hello.txt",
            content_type="text/plain",
            title="Hello",
            source_uri="test://hello",
            owner_id="user-1",
            document_id="doc-1",
            partition_kind=partition_kind,
            partition_id=partition_id,
        )
        session.commit()

        assert result.document_id == "doc-1"
        assert len(vectors.rows) == 2
        assert DocumentRepository(session).get("doc-1") is not None
        assert facade.get_document_content(
            "doc-1",
            partition_kind=partition_kind,
            partition_id=partition_id,
        ).content == b"hello"


def test_facade_deletes_via_dms_core(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    dms = FakeDms()
    monkeypatch.setattr("kbms.facade._build_dms_client", lambda **kwargs: dms)
    partition_kind = "personal"
    partition_id = "user-1"

    with Session(engine) as session:
        facade = KnowledgeManagement(
            session=session,
            engine=engine,
            minio_client=object(),
            bucket_name="test-bucket",
            ollama_client=FakeOllama(),
            milvus_client=FakeMilvus(),
            vector_dimension=1,
        )
        facade.delete_document(
            "doc-1",
            partition_kind=partition_kind,
            partition_id=partition_id,
            hard_delete=True,
        )

    assert len(dms.deletes) == 1
    assert dms.deletes[0][0] == "doc-1"
    assert dms.deletes[0][1].kind.value == "personal"
    assert dms.deletes[0][1].partition_id == "user-1"
    assert dms.deletes[0][2] is True