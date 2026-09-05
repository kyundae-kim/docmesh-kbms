from __future__ import annotations

from datetime import UTC, datetime

from dms import (
    AccessContext,
    DocumentContent,
    DocumentPage,
    DocumentPartition,
    DocumentStatus,
    PartitionKind,
    PublicDocumentMetadata,
    UploadDocumentResult,
)

from kbms.dms.dms_core import DmsCoreDocumentManager


class FakeDmsClient:
    def __init__(self) -> None:
        self.uploads = []
        self.reads = []
        self.deletes = []
        self.list_context = None
        self.metadata_context = None
        self.metadata = PublicDocumentMetadata(
            document_id="doc-1",
            original_filename="hello.txt",
            content_type="text/plain",
            file_size=5,
            status=DocumentStatus.AVAILABLE,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 2, tzinfo=UTC),
            partition=DocumentPartition(kind=PartitionKind.PERSONAL, partition_id="user-1"),
            checksum="abc",
            created_by="user-1",
            extra_metadata={"title": "Hello"},
        )

    def upload_document(self, request, *, partition, access_context=None):
        self.uploads.append((request, partition, access_context))
        return UploadDocumentResult(document_id=request.document_id or "generated", metadata=None)  # type: ignore[arg-type]

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

    def list_documents(self, *, partition, cursor=None, limit=100, status=None, access_context=None):
        self.list_context = access_context
        return DocumentPage(items=[self.metadata], next_cursor="next", has_more=True)

    def get_document_metadata(self, document_id, *, partition, access_context=None):
        self.metadata_context = access_context
        return self.metadata


def test_dms_core_manager_uploads_reads_and_deletes_through_sdk() -> None:
    client = FakeDmsClient()
    manager = DmsCoreDocumentManager(client)
    partition = DocumentPartition(kind=PartitionKind.PERSONAL, partition_id="user-1")

    result = manager.upload(
        content=b"hello",
        filename="hello.txt",
        content_type="text/plain",
        document_id="doc-1",
        created_by="user-1",
        partition=partition,
    )
    content = manager.read("doc-1", partition=partition)
    manager.delete("doc-1", partition=partition, hard_delete=True)

    request, uploaded_partition, _ = client.uploads[0]
    assert result.document_id == "doc-1"
    assert request.checksum is not None
    assert request.content == b"hello"
    assert uploaded_partition == partition
    assert content.content == b"hello"
    assert client.reads[0][:2] == ("doc-1", partition)
    assert client.deletes[0][:3] == ("doc-1", partition, True)


def test_dms_core_manager_rejects_invalid_upload_and_document_id() -> None:
    manager = DmsCoreDocumentManager(FakeDmsClient())
    partition = DocumentPartition(kind=PartitionKind.PERSONAL, partition_id="user-1")

    for kwargs in (
        {"content": b"", "filename": "a.txt", "content_type": "text/plain"},
        {"content": b"a", "filename": " ", "content_type": "text/plain"},
        {"content": b"a", "filename": "a.txt", "content_type": " "},
    ):
        try:
            manager.upload(partition=partition, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid upload was accepted")

    try:
        manager.read(" ", partition=partition)
    except ValueError as error:
        assert str(error) == "document_id must not be blank"
    else:
        raise AssertionError("blank document ID was accepted")


def test_dms_core_manager_lists_and_reads_public_metadata() -> None:
    client = FakeDmsClient()
    manager = DmsCoreDocumentManager(client)
    partition = DocumentPartition(kind=PartitionKind.PERSONAL, partition_id="user-1")

    page = manager.list(partition=partition, cursor="old", limit=10)
    metadata = manager.metadata("doc-1", partition=partition)

    assert page.items[0].document_id == "doc-1"
    assert page.next_cursor == "next"
    assert metadata.original_filename == "hello.txt"


def test_dms_core_manager_forwards_access_context_to_every_operation() -> None:
    client = FakeDmsClient()
    manager = DmsCoreDocumentManager(client)
    partition = DocumentPartition(kind=PartitionKind.GROUP, partition_id="group-1")
    context = AccessContext(user_id="user-1", groups=frozenset({"group-1"}))

    manager.upload(
        content=b"hello", filename="hello.txt", content_type="text/plain",
        partition=partition, access_context=context,
    )
    manager.list(partition=partition, access_context=context)
    manager.metadata("doc-1", partition=partition, access_context=context)
    manager.read("doc-1", partition=partition, access_context=context)
    manager.delete("doc-1", partition=partition, access_context=context)

    assert client.uploads[0][2] is context
    assert client.list_context is context
    assert client.metadata_context is context
    assert client.reads[0][2] is context
    assert client.deletes[0][3] is context
