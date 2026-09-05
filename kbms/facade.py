from __future__ import annotations

import asyncio
from typing import Any

from dms import (
    AccessContext,
    AccessPolicy,
    AsyncDocumentManagementSDK,
    AsyncDocumentManagementSDKFactory,
    DocumentContent,
    DocumentManagementSDKFactory,
    DocumentPartition,
    PartitionKind,
    UploadDocumentResult,
)
from minio import Minio
from ollama import AsyncClient, Client
from pymilvus import AsyncMilvusClient, MilvusClient
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from .dms import (
    DmsCoreDocumentManager,
    DocumentIngestionService,
    KnowledgeDocument,
    KnowledgeDocumentPage,
    KnowledgeIndexer,
    KnowledgeSearchService,
    MilvusVectorStore,
    OllamaEmbeddingProvider,
    PipelineBase,
    PipelineState,
    PipelineStateRepository,
    SearchHit,
    TextChunker,
)


def _build_dms_client(
    *,
    engine: Engine,
    minio_client: Minio,
    bucket_name: str,
    access_policy: Any = None,
) -> Any:
    return DocumentManagementSDKFactory(
        engine=engine,
        minio_client=minio_client,
        bucket_name=bucket_name,
        access_policy=access_policy,
    ).create()


def _build_async_dms_client(
    *,
    engine: AsyncEngine,
    minio_client: Minio,
    bucket_name: str,
    access_policy: Any = None,
) -> AsyncDocumentManagementSDK:
    return AsyncDocumentManagementSDKFactory(
        engine=engine,
        minio_client=minio_client,
        bucket_name=bucket_name,
        access_policy=access_policy,
    ).create()


def _build_partition(*, partition_kind: str, partition_id: str) -> DocumentPartition:
    if not partition_kind.strip():
        raise ValueError("partition_kind must not be blank")
    if not partition_id.strip():
        raise ValueError("partition_id must not be blank")
    try:
        kind = PartitionKind(partition_kind)
    except ValueError as error:
        raise ValueError("partition_kind must be 'personal' or 'group'") from error
    return DocumentPartition(kind=kind, partition_id=partition_id)


class KnowledgeManagement:
    """Single application boundary for DMS-backed knowledge management."""

    def __init__(
        self,
        *,
        engine: Engine | AsyncEngine,
        minio_client: Minio,
        bucket_name: str,
        ollama_client: Client | AsyncClient,
        milvus_client: MilvusClient | AsyncMilvusClient,
        access_policy: AccessPolicy | None = None,
        embedding_model: str = "bge-m3",
        collection_name: str = "kbms_documents",
        vector_dimension: int = 1024,
        chunk_size: int = 1000,
        overlap: int = 100,
    ) -> None:
        self._async_mode = isinstance(engine, AsyncEngine)
        if self._async_mode:
            dms_client = _build_async_dms_client(
                engine=engine,
                minio_client=minio_client,
                bucket_name=bucket_name,
                access_policy=access_policy,
            )
        else:
            PipelineBase.metadata.create_all(engine)
            dms_client = _build_dms_client(
                engine=engine,
                minio_client=minio_client,
                bucket_name=bucket_name,
                access_policy=access_policy,
            )
        embedding_provider = OllamaEmbeddingProvider(ollama_client, embedding_model)
        vector_store = MilvusVectorStore(
            milvus_client,
            collection_name=collection_name,
            dimension=vector_dimension,
        )
        indexer = KnowledgeIndexer(
            TextChunker(chunk_size, overlap), embedding_provider, vector_store
        )
        self._dms = DmsCoreDocumentManager(dms_client)
        self._ingestion = DocumentIngestionService(indexer)
        self._pipeline = PipelineStateRepository(engine)
        self._search = KnowledgeSearchService(embedding_provider, vector_store)
        self._vectors = vector_store
        self._ready = False
        self._ready_lock = asyncio.Lock()

    async def _run_sync(self, method: Any, /, *args: Any, **kwargs: Any) -> Any:
        """Run blocking adapters without breaking SQLite memory databases."""
        if self._pipeline.engine.url.database == ":memory:":
            return method(*args, **kwargs)
        return await asyncio.to_thread(method, *args, **kwargs)

    async def _ensure_async_ready(self) -> None:
        if not self._async_mode or self._ready:
            return
        async with self._ready_lock:
            if self._ready:
                return
            await self._dms.client.ready()
            await self._pipeline.initialize()
            self._ready = True

    async def upload_document(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
        title: str,
        source_uri: str,
        owner_id: str,
        partition_kind: str,
        partition_id: str,
        document_id: str | None = None,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
        access_context: AccessContext | None = None,
    ) -> UploadDocumentResult:
        if self._async_mode:
            await self._ensure_async_ready()
            return await self._aupload_document(
                content=content, filename=filename, content_type=content_type,
                title=title, source_uri=source_uri, owner_id=owner_id,
                partition_kind=partition_kind, partition_id=partition_id,
                document_id=document_id, created_by=created_by, metadata=metadata,
                access_context=access_context,
            )
        return await self._run_sync(
            self._upload_document,
            content=content,
            filename=filename,
            content_type=content_type,
            title=title,
            source_uri=source_uri,
            owner_id=owner_id,
            partition_kind=partition_kind,
            partition_id=partition_id,
            document_id=document_id,
            created_by=created_by,
            metadata=metadata,
            access_context=access_context,
        )

    async def _aupload_document(self, **kwargs: Any) -> UploadDocumentResult:
        partition = _build_partition(
            partition_kind=kwargs["partition_kind"], partition_id=kwargs["partition_id"]
        )
        if not kwargs["title"].strip():
            raise ValueError("title must not be blank")
        if not kwargs["source_uri"].strip():
            raise ValueError("source_uri must not be blank")
        document_metadata = dict(kwargs.get("metadata") or {})
        document_metadata.update({"title": kwargs["title"], "source_uri": kwargs["source_uri"]})
        result = await self._dms.aupload(
            content=kwargs["content"], filename=kwargs["filename"],
            content_type=kwargs["content_type"], partition=partition,
            document_id=kwargs.get("document_id"),
            created_by=kwargs.get("created_by") or kwargs["owner_id"],
            metadata=document_metadata, access_context=kwargs.get("access_context"),
        )
        await self._pipeline.aset(result.document_id, status="uploaded")
        try:
            await self._pipeline.aset(result.document_id, status="indexing")
            ingestion = await self._ingestion.aingest(
                document_id=result.document_id, content_type=kwargs["content_type"],
                content=kwargs["content"], source_uri=kwargs["source_uri"],
                partition_kind=partition.kind.value, partition_id=partition.partition_id,
            )
            await self._pipeline.aset(
                result.document_id, status="indexed", chunks_count=len(ingestion.chunks)
            )
        except Exception:
            await self._pipeline.aset(
                result.document_id, status="failed", error="knowledgeization failed"
            )
            await self._dms.adelete(
                result.document_id, partition=partition, hard_delete=True,
                access_context=kwargs.get("access_context"),
            )
            raise
        return result

    def _upload_document(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
        title: str,
        source_uri: str,
        owner_id: str,
        partition_kind: str,
        partition_id: str,
        document_id: str | None = None,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
        access_context: AccessContext | None = None,
    ) -> UploadDocumentResult:
        """Upload through dms-core, then persist and index its projection."""
        partition = _build_partition(
            partition_kind=partition_kind,
            partition_id=partition_id,
        )
        if not title.strip():
            raise ValueError("title must not be blank")
        if not source_uri.strip():
            raise ValueError("source_uri must not be blank")
        document_metadata = dict(metadata or {})
        document_metadata.update({"title": title, "source_uri": source_uri})
        result = self._dms.upload(
            content=content,
            filename=filename,
            content_type=content_type,
            partition=partition,
            document_id=document_id,
            created_by=created_by or owner_id,
            metadata=document_metadata,
            access_context=access_context,
        )
        self._pipeline.set(result.document_id, status="uploaded")
        try:
            self._pipeline.set(result.document_id, status="indexing")
            ingestion = self._ingestion.ingest(
                document_id=result.document_id,
                content_type=content_type,
                content=content,
                source_uri=source_uri,
                partition_kind=partition.kind.value,
                partition_id=partition.partition_id,
            )
            self._pipeline.set(
                result.document_id,
                status="indexed",
                chunks_count=len(ingestion.chunks),
            )
        except Exception:
            self._pipeline.set(
                result.document_id,
                status="failed",
                error="knowledgeization failed",
            )
            self._dms.delete(
                result.document_id,
                partition=partition,
                hard_delete=True,
                access_context=access_context,
            )
            raise
        return result

    async def get_pipeline_status(self, document_id: str) -> PipelineState | None:
        if self._async_mode:
            await self._ensure_async_ready()
            if not document_id.strip():
                raise ValueError("document_id must not be blank")
            return await self._pipeline.aget(document_id)
        return await self._run_sync(self._get_pipeline_status, document_id)

    def _get_pipeline_status(self, document_id: str) -> PipelineState | None:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        return self._pipeline.get(document_id)

    async def list_documents(
        self,
        *,
        partition_kind: str,
        partition_id: str,
        cursor: str | None = None,
        limit: int = 100,
        access_context: AccessContext | None = None,
    ) -> KnowledgeDocumentPage:
        if self._async_mode:
            await self._ensure_async_ready()
            partition = _build_partition(partition_kind=partition_kind, partition_id=partition_id)
            page = await self._dms.alist(
                partition=partition, cursor=cursor, limit=limit, access_context=access_context
            )
            return KnowledgeDocumentPage(
                items=[self._to_knowledge_document(item) for item in page.items],
                next_cursor=page.next_cursor, has_more=page.has_more,
            )
        return await self._run_sync(
            self._list_documents,
            partition_kind=partition_kind,
            partition_id=partition_id,
            cursor=cursor,
            limit=limit,
            access_context=access_context,
        )

    def _list_documents(
        self,
        *,
        partition_kind: str,
        partition_id: str,
        cursor: str | None = None,
        limit: int = 100,
        access_context: AccessContext | None = None,
    ) -> KnowledgeDocumentPage:
        """List documents using a KMS DTO rather than exposing dms-core types."""
        partition = _build_partition(
            partition_kind=partition_kind,
            partition_id=partition_id,
        )
        page = self._dms.list(
            partition=partition,
            cursor=cursor,
            limit=limit,
            access_context=access_context,
        )
        return KnowledgeDocumentPage(
            items=[self._to_knowledge_document(item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )

    async def get_document_metadata(
        self,
        document_id: str,
        *,
        partition_kind: str,
        partition_id: str,
        access_context: AccessContext | None = None,
    ) -> KnowledgeDocument:
        if self._async_mode:
            await self._ensure_async_ready()
            partition = _build_partition(partition_kind=partition_kind, partition_id=partition_id)
            return self._to_knowledge_document(
                await self._dms.ametadata(
                    document_id, partition=partition, access_context=access_context
                )
            )
        return await self._run_sync(
            self._get_document_metadata,
            document_id,
            partition_kind=partition_kind,
            partition_id=partition_id,
            access_context=access_context,
        )

    def _get_document_metadata(
        self,
        document_id: str,
        *,
        partition_kind: str,
        partition_id: str,
        access_context: AccessContext | None = None,
    ) -> KnowledgeDocument:
        """Return public document metadata in the KMS vocabulary."""
        partition = _build_partition(
            partition_kind=partition_kind,
            partition_id=partition_id,
        )
        return self._to_knowledge_document(
            self._dms.metadata(
                document_id, partition=partition, access_context=access_context
            )
        )

    async def get_document_content(
        self,
        document_id: str,
        *,
        partition_kind: str,
        partition_id: str,
        access_context: AccessContext | None = None,
    ) -> DocumentContent:
        if self._async_mode:
            await self._ensure_async_ready()
            partition = _build_partition(partition_kind=partition_kind, partition_id=partition_id)
            return await self._dms.aread(
                document_id, partition=partition, access_context=access_context
            )
        return await self._run_sync(
            self._get_document_content,
            document_id,
            partition_kind=partition_kind,
            partition_id=partition_id,
            access_context=access_context,
        )

    def _get_document_content(
        self,
        document_id: str,
        *,
        partition_kind: str,
        partition_id: str,
        access_context: AccessContext | None = None,
    ) -> DocumentContent:
        partition = _build_partition(
            partition_kind=partition_kind,
            partition_id=partition_id,
        )
        return self._dms.read(
            document_id, partition=partition, access_context=access_context
        )

    async def delete_document(
        self,
        document_id: str,
        *,
        partition_kind: str,
        partition_id: str,
        hard_delete: bool = False,
        access_context: AccessContext | None = None,
    ) -> object:
        if self._async_mode:
            await self._ensure_async_ready()
            partition = _build_partition(partition_kind=partition_kind, partition_id=partition_id)
            result = await self._dms.adelete(
                document_id, partition=partition, hard_delete=hard_delete,
                access_context=access_context,
            )
            await self._vectors.adelete_document(document_id)
            await self._pipeline.aset(document_id, status="deleted")
            return result
        return await self._run_sync(
            self._delete_document,
            document_id,
            partition_kind=partition_kind,
            partition_id=partition_id,
            hard_delete=hard_delete,
            access_context=access_context,
        )

    def _delete_document(
        self,
        document_id: str,
        *,
        partition_kind: str,
        partition_id: str,
        hard_delete: bool = False,
        access_context: AccessContext | None = None,
    ) -> object:
        partition = _build_partition(
            partition_kind=partition_kind,
            partition_id=partition_id,
        )
        result = self._dms.delete(
            document_id,
            partition=partition,
            hard_delete=hard_delete,
            access_context=access_context,
        )
        self._vectors.delete_document(document_id)
        self._pipeline.set(document_id, status="deleted")
        return result

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        document_id: str | None = None,
        partition_kind: str | None = None,
        partition_id: str | None = None,
        access_context: AccessContext | None = None,
    ) -> list[SearchHit]:
        if self._async_mode:
            await self._ensure_async_ready()
            if access_context is not None:
                if partition_kind is None or partition_id is None:
                    raise ValueError(
                        "partition_kind and partition_id are required for authorized search"
                    )
                if partition_kind == "personal" and access_context.user_id != partition_id:
                    raise PermissionError("search access denied")
                if partition_kind == "group" and partition_id not in access_context.groups:
                    raise PermissionError("search access denied")
            return await self._search.asearch(
                query, limit=limit, document_id=document_id,
                partition_kind=partition_kind, partition_id=partition_id,
            )
        return await self._run_sync(
            self._search_documents,
            query,
            limit=limit,
            document_id=document_id,
            partition_kind=partition_kind,
            partition_id=partition_id,
            access_context=access_context,
        )

    def _search_documents(
        self,
        query: str,
        *,
        limit: int = 5,
        document_id: str | None = None,
        partition_kind: str | None = None,
        partition_id: str | None = None,
        access_context: AccessContext | None = None,
    ) -> list[SearchHit]:
        if access_context is not None:
            if partition_kind is None or partition_id is None:
                raise ValueError(
                    "partition_kind and partition_id are required for authorized search"
                )
            if partition_kind == "personal" and access_context.user_id != partition_id:
                raise PermissionError("search access denied")
            if partition_kind == "group" and partition_id not in access_context.groups:
                raise PermissionError("search access denied")
        return self._search.search(
            query,
            limit=limit,
            document_id=document_id,
            partition_kind=partition_kind,
            partition_id=partition_id,
        )

    @staticmethod
    def _to_knowledge_document(metadata: Any) -> KnowledgeDocument:
        partition = metadata.partition
        status = metadata.status.value if hasattr(metadata.status, "value") else str(metadata.status)
        return KnowledgeDocument(
            document_id=metadata.document_id,
            filename=metadata.original_filename,
            content_type=metadata.content_type,
            file_size=metadata.file_size,
            status=status,
            created_at=metadata.created_at,
            updated_at=metadata.updated_at,
            partition_kind=partition.kind.value,
            partition_id=partition.partition_id,
            checksum=metadata.checksum,
            created_by=metadata.created_by,
            metadata=dict(metadata.extra_metadata),
        )
