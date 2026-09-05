from datetime import UTC, datetime

from dms import (
    AccessContext,
    DocumentContent,
    DocumentPage,
    DocumentStatus,
    PublicDocumentMetadata,
    UploadDocumentResult,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import kbms
from kbms import KnowledgeManagement


class FakeDms:
    def __init__(self) -> None:
        self.uploads = []
        self.deletes = []
        self.reads = []

    def upload_document(self, request, *, partition, access_context=None):
        self.uploads.append((request, partition, access_context))
        return UploadDocumentResult(document_id=request.document_id or "generated", metadata=None)

    def get_document_content(self, document_id, *, partition, access_context=None):
        self.reads.append((document_id, partition, access_context))
        return DocumentContent(
            document_id=document_id,
            content=b"hello",
            content_type="text/plain",
            filename="hello.txt",
            size=5,
        )

    def delete_document(self, document_id, *, partition, hard_delete=False, access_context=None):
        self.deletes.append((document_id, partition, hard_delete, access_context))
        return {"document_id": document_id}

    def _metadata(self, partition):
        return PublicDocumentMetadata(
            document_id="doc-1",
            original_filename="hello.txt",
            content_type="text/plain",
            file_size=5,
            status=DocumentStatus.AVAILABLE,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 2, tzinfo=UTC),
            partition=partition,
            checksum="abc",
            created_by="user-1",
            extra_metadata={"title": "Hello"},
        )

    def list_documents(self, *, partition, cursor=None, limit=100, status=None, access_context=None):
        return DocumentPage(items=[self._metadata(partition)], next_cursor="next", has_more=True)

    def get_document_metadata(self, document_id, *, partition, access_context=None):
        return self._metadata(partition)


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
    dms = FakeDms()
    vectors = FakeMilvus()
    monkeypatch.setattr("kbms.facade._build_dms_client", lambda **kwargs: dms)
    partition_kind = "personal"
    partition_id = "user-1"

    with Session(engine):
        facade = KnowledgeManagement(
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

        assert result.document_id == "doc-1"
        assert dms.uploads[0][0].created_by == "user-1"
        assert len(vectors.rows) == 2
        assert facade.get_document_content(
            "doc-1",
            partition_kind=partition_kind,
            partition_id=partition_id,
        ).content == b"hello"


def test_facade_deletes_via_dms_core(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    dms = FakeDms()
    monkeypatch.setattr("kbms.facade._build_dms_client", lambda **kwargs: dms)
    partition_kind = "personal"
    partition_id = "user-1"

    with Session(engine):
        facade = KnowledgeManagement(
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


def test_facade_exposes_kms_document_metadata_and_cursor_page(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    dms = FakeDms()
    monkeypatch.setattr("kbms.facade._build_dms_client", lambda **kwargs: dms)

    with Session(engine):
        facade = KnowledgeManagement(
            engine=engine,
            minio_client=object(),
            bucket_name="test-bucket",
            ollama_client=FakeOllama(),
            milvus_client=FakeMilvus(),
            vector_dimension=1,
        )
        page = facade.list_documents(
            partition_kind="personal",
            partition_id="user-1",
            cursor="old",
            limit=10,
        )
        document = facade.get_document_metadata(
            "doc-1",
            partition_kind="personal",
            partition_id="user-1",
        )

    assert page.items[0].filename == "hello.txt"
    assert page.items[0].metadata == {"title": "Hello"}
    assert page.next_cursor == "next"
    assert page.has_more is True
    assert document.status == "available"
    assert document.partition_id == "user-1"


def test_facade_accepts_user_and_group_access_context(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    dms = FakeDms()
    monkeypatch.setattr("kbms.facade._build_dms_client", lambda **kwargs: dms)
    context = AccessContext(user_id="user-1", groups=frozenset({"group-1"}))

    with Session(engine):
        facade = KnowledgeManagement(
            engine=engine, minio_client=object(),
            bucket_name="test-bucket", ollama_client=FakeOllama(),
            milvus_client=FakeMilvus(), vector_dimension=1,
        )
        facade.get_document_content(
            "doc-1", partition_kind="group", partition_id="group-1",
            access_context=context,
        )

    assert dms.reads[-1][2] is context


def test_facade_installs_host_access_policy_in_dms_client(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    captured = {}
    dms = FakeDms()
    monkeypatch.setattr(
        "kbms.facade._build_dms_client",
        lambda **kwargs: captured.update(kwargs) or dms,
    )
    policy = object()

    with Session(engine):
        KnowledgeManagement(
            engine=engine, minio_client=object(),
            bucket_name="test-bucket", ollama_client=FakeOllama(),
            milvus_client=FakeMilvus(), access_policy=policy,
        )

    assert captured["access_policy"] is policy