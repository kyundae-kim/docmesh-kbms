from __future__ import annotations

from dms import DocumentContent, DocumentPartition, PartitionKind, UploadDocumentResult

from kbms.dms.dms_core import DmsCoreDocumentManager


class FakeDmsClient:
    def __init__(self) -> None:
        self.uploads = []
        self.reads = []
        self.deletes = []

    def upload_document(self, request, *, partition):
        self.uploads.append((request, partition))
        return UploadDocumentResult(document_id=request.document_id or "generated", metadata=None)  # type: ignore[arg-type]

    def get_document_content(self, document_id, *, partition):
        self.reads.append((document_id, partition))
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

    request, uploaded_partition = client.uploads[0]
    assert result.document_id == "doc-1"
    assert request.checksum is not None
    assert request.content == b"hello"
    assert uploaded_partition == partition
    assert content.content == b"hello"
    assert client.reads == [("doc-1", partition)]
    assert client.deletes == [("doc-1", partition, True)]


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
