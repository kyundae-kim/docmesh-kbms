from __future__ import annotations

import hashlib
from typing import Protocol

from dms import (
    DocumentContent,
    DocumentManagementClient,
    DocumentPartition,
    UploadDocumentRequest,
    UploadDocumentResult,
)


class DmsCoreClient(Protocol):
    def upload_document(
        self,
        request: UploadDocumentRequest,
        *,
        partition: DocumentPartition,
    ) -> UploadDocumentResult: ...

    def get_document_content(
        self,
        document_id: str,
        *,
        partition: DocumentPartition,
    ) -> DocumentContent: ...

    def delete_document(
        self,
        document_id: str,
        *,
        partition: DocumentPartition,
        hard_delete: bool = False,
    ) -> object: ...


class DmsCoreDocumentManager:
    """Document-management boundary backed by the dms-core SDK."""

    def __init__(self, client: DmsCoreClient | DocumentManagementClient) -> None:
        self.client = client

    def upload(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
        partition: DocumentPartition,
        document_id: str | None = None,
        created_by: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> UploadDocumentResult:
        if not content:
            raise ValueError("content must not be empty")
        if not filename.strip():
            raise ValueError("filename must not be blank")
        if not content_type.strip():
            raise ValueError("content_type must not be blank")

        request = UploadDocumentRequest(
            content=content,
            filename=filename,
            content_type=content_type,
            document_id=document_id,
            created_by=created_by,
            metadata=metadata,
            checksum=hashlib.sha256(content).hexdigest(),
        )
        return self.client.upload_document(request, partition=partition)

    def read(
        self,
        document_id: str,
        *,
        partition: DocumentPartition,
    ) -> DocumentContent:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        return self.client.get_document_content(document_id, partition=partition)

    def delete(
        self,
        document_id: str,
        *,
        partition: DocumentPartition,
        hard_delete: bool = False,
    ) -> object:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        return self.client.delete_document(
            document_id,
            partition=partition,
            hard_delete=hard_delete,
        )
