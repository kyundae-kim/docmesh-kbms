from __future__ import annotations

import hashlib
from typing import Protocol

from dms import (
    AccessContext,
    DocumentContent,
    DocumentManagementClient,
    DocumentPage,
    DocumentPartition,
    PublicDocumentMetadata,
    UploadDocumentRequest,
    UploadDocumentResult,
)


class DmsCoreClient(Protocol):
    def list_documents(
        self,
        *,
        partition: DocumentPartition,
        cursor: str | None = None,
        limit: int = 100,
        status: object | None = None,
        access_context: AccessContext | None = None,
    ) -> DocumentPage: ...

    def get_document_metadata(
        self,
        document_id: str,
        *,
        partition: DocumentPartition,
        access_context: AccessContext | None = None,
    ) -> PublicDocumentMetadata: ...

    def upload_document(
        self,
        request: UploadDocumentRequest,
        *,
        partition: DocumentPartition,
        access_context: AccessContext | None = None,
    ) -> UploadDocumentResult: ...

    def get_document_content(
        self,
        document_id: str,
        *,
        partition: DocumentPartition,
        access_context: AccessContext | None = None,
    ) -> DocumentContent: ...

    def delete_document(
        self,
        document_id: str,
        *,
        partition: DocumentPartition,
        hard_delete: bool = False,
        access_context: AccessContext | None = None,
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
        access_context: AccessContext | None = None,
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
        return self.client.upload_document(
            request, partition=partition, access_context=access_context
        )

    def list(
        self,
        *,
        partition: DocumentPartition,
        cursor: str | None = None,
        limit: int = 100,
        access_context: AccessContext | None = None,
    ) -> DocumentPage:
        if limit <= 0:
            raise ValueError("limit must be positive")
        return self.client.list_documents(
            partition=partition,
            cursor=cursor,
            limit=limit,
            access_context=access_context,
        )

    def metadata(
        self,
        document_id: str,
        *,
        partition: DocumentPartition,
        access_context: AccessContext | None = None,
    ) -> PublicDocumentMetadata:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        return self.client.get_document_metadata(
            document_id, partition=partition, access_context=access_context
        )

    def read(
        self,
        document_id: str,
        *,
        partition: DocumentPartition,
        access_context: AccessContext | None = None,
    ) -> DocumentContent:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        return self.client.get_document_content(
            document_id, partition=partition, access_context=access_context
        )

    def delete(
        self,
        document_id: str,
        *,
        partition: DocumentPartition,
        hard_delete: bool = False,
        access_context: AccessContext | None = None,
    ) -> object:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        return self.client.delete_document(
            document_id,
            partition=partition,
            hard_delete=hard_delete,
            access_context=access_context,
        )

    async def aupload(self, **kwargs: object) -> UploadDocumentResult:
        self._validate_upload_kwargs(kwargs)
        request = UploadDocumentRequest(
            content=kwargs["content"],
            filename=kwargs["filename"],
            content_type=kwargs["content_type"],
            document_id=kwargs.get("document_id"),
            created_by=kwargs.get("created_by"),
            metadata=kwargs.get("metadata"),
            checksum=hashlib.sha256(kwargs["content"]).hexdigest(),
        )
        return await self.client.upload_document(
            request,
            partition=kwargs["partition"],
            access_context=kwargs.get("access_context"),
        )

    async def alist(self, **kwargs: object) -> DocumentPage:
        limit = kwargs.get("limit", 100)
        if limit <= 0:
            raise ValueError("limit must be positive")
        return await self.client.list_documents(
            partition=kwargs["partition"],
            cursor=kwargs.get("cursor"),
            limit=limit,
            access_context=kwargs.get("access_context"),
        )

    async def ametadata(self, document_id: str, **kwargs: object) -> PublicDocumentMetadata:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        return await self.client.get_document_metadata(
            document_id,
            partition=kwargs["partition"],
            access_context=kwargs.get("access_context"),
        )

    async def aread(self, document_id: str, **kwargs: object) -> DocumentContent:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        return await self.client.get_document_content(
            document_id,
            partition=kwargs["partition"],
            access_context=kwargs.get("access_context"),
        )

    async def adelete(self, document_id: str, **kwargs: object) -> object:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        return await self.client.delete_document(
            document_id,
            partition=kwargs["partition"],
            hard_delete=kwargs.get("hard_delete", False),
            access_context=kwargs.get("access_context"),
        )

    @staticmethod
    def _validate_upload_kwargs(kwargs: dict[str, object]) -> None:
        content = kwargs["content"]
        if not content:
            raise ValueError("content must not be empty")
        if not kwargs["filename"].strip():
            raise ValueError("filename must not be blank")
        if not kwargs["content_type"].strip():
            raise ValueError("content_type must not be blank")
