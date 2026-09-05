from __future__ import annotations

from typing import Any

from dms import (
    AccessContext,
    DocumentContent,
    DocumentManagementSDKFactory,
    DocumentPartition,
    PartitionKind,
    UploadDocumentResult,
)

from .dms import (
    DmsCoreDocumentManager,
    DocumentIngestionService,
    KnowledgeDocument,
    KnowledgeDocumentPage,
    KnowledgeIndexer,
    KnowledgeSearchService,
    MilvusVectorStore,
    OllamaEmbeddingProvider,
    SearchHit,
    TextChunker,
)


def _build_dms_client(
    *,
    engine: Any,
    minio_client: Any,
    bucket_name: str,
    access_policy: Any = None,
) -> Any:
    return DocumentManagementSDKFactory(
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
        engine: Any,
        minio_client: Any,
        bucket_name: str,
        ollama_client: Any,
        milvus_client: Any,
        access_policy: Any = None,
        embedding_model: str = "bge-m3",
        collection_name: str = "kbms_documents",
        vector_dimension: int = 1024,
        chunk_size: int = 1000,
        overlap: int = 100,
    ) -> None:
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
        self._search = KnowledgeSearchService(embedding_provider, vector_store)

    def upload_document(
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
        result = self._dms.upload(
            content=content,
            filename=filename,
            content_type=content_type,
            partition=partition,
            document_id=document_id,
            created_by=created_by or owner_id,
            metadata=metadata,
            access_context=access_context,
        )
        try:
            self._ingestion.ingest(
                document_id=result.document_id,
                content_type=content_type,
                content=content,
            )
        except Exception:
            self._dms.delete(
                result.document_id,
                partition=partition,
                hard_delete=True,
                access_context=access_context,
            )
            raise
        return result

    def list_documents(
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

    def get_document_metadata(
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

    def get_document_content(
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

    def delete_document(
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
        return self._dms.delete(
            document_id,
            partition=partition,
            hard_delete=hard_delete,
            access_context=access_context,
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        document_id: str | None = None,
    ) -> list[SearchHit]:
        return self._search.search(query, limit=limit, document_id=document_id)

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
