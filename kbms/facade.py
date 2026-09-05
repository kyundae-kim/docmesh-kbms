from __future__ import annotations

from typing import Any

from dms import (
    DocumentContent,
    DocumentManagementSDKFactory,
    DocumentPartition,
    PartitionKind,
    UploadDocumentResult,
)
from sqlalchemy.orm import Session

from .dms import (
    DmsCoreDocumentManager,
    DocumentIngestionService,
    DocumentRepository,
    KnowledgeIndexer,
    KnowledgeSearchService,
    MilvusVectorStore,
    OllamaEmbeddingProvider,
    SearchHit,
    TextChunker,
)


def _build_dms_client(*, engine: Any, minio_client: Any, bucket_name: str) -> Any:
    return DocumentManagementSDKFactory(
        engine=engine,
        minio_client=minio_client,
        bucket_name=bucket_name,
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
        session: Session,
        engine: Any,
        minio_client: Any,
        bucket_name: str,
        ollama_client: Any,
        milvus_client: Any,
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
        )
        embedding_provider = OllamaEmbeddingProvider(ollama_client, embedding_model)
        vector_store = MilvusVectorStore(
            milvus_client,
            collection_name=collection_name,
            dimension=vector_dimension,
        )
        repository = DocumentRepository(session)
        indexer = KnowledgeIndexer(
            TextChunker(chunk_size, overlap), embedding_provider, vector_store
        )
        self._dms = DmsCoreDocumentManager(dms_client)
        self._ingestion = DocumentIngestionService(repository, indexer)
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
            created_by=created_by,
            metadata=metadata,
        )
        try:
            self._ingestion.ingest(
                document_id=result.document_id,
                title=title,
                source_uri=source_uri,
                content_type=content_type,
                owner_id=owner_id,
                content=content,
            )
        except Exception:
            self._dms.delete(result.document_id, partition=partition, hard_delete=True)
            raise
        return result

    def get_document_content(
        self,
        document_id: str,
        *,
        partition_kind: str,
        partition_id: str,
    ) -> DocumentContent:
        partition = _build_partition(
            partition_kind=partition_kind,
            partition_id=partition_id,
        )
        return self._dms.read(document_id, partition=partition)

    def delete_document(
        self,
        document_id: str,
        *,
        partition_kind: str,
        partition_id: str,
        hard_delete: bool = False,
    ) -> object:
        partition = _build_partition(
            partition_kind=partition_kind,
            partition_id=partition_id,
        )
        return self._dms.delete(
            document_id, partition=partition, hard_delete=hard_delete
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        document_id: str | None = None,
    ) -> list[SearchHit]:
        return self._search.search(query, limit=limit, document_id=document_id)
