from __future__ import annotations

import os
from uuid import uuid4

import ollama
import pytest
from minio import Minio
from pymilvus import MilvusClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from kbms import KnowledgeManagement


@pytest.mark.integration
@pytest.mark.real_integration
def test_real_facade_upload_index_search_and_delete() -> None:
    """Exercise the facade against DMS, PostgreSQL, MinIO, Ollama, and Milvus."""
    postgres_url = os.getenv(
        "KBMS_POSTGRES_URL",
        "postgresql+psycopg://docmesh:postgres@postgres:5432/kbms",
    )
    milvus_uri = os.getenv("KBMS_MILVUS_URI", "http://milvus:19530")
    ollama_host = os.getenv(
        "KBMS_OLLAMA_HOST", "http://192.168.219.106:11434"
    )

    minio_endpoint = os.getenv("KBMS_MINIO_ENDPOINT", "milvus-minio:9000")
    minio_access_key = os.getenv("KBMS_MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key = os.getenv("KBMS_MINIO_SECRET_KEY", "minioadmin")
    minio_bucket = os.getenv("KBMS_MINIO_BUCKET", "kbms-e2e")
    embedding_model = os.getenv("KBMS_OLLAMA_EMBEDDING_MODEL", "bge-m3")
    engine = create_engine(postgres_url)
    milvus = MilvusClient(uri=milvus_uri)
    collection_name = f"kbms_e2e_{uuid4().hex}"
    document_id = f"kbms-e2e-{uuid4().hex}"
    partition_kind = "personal"
    partition_id = "kbms-e2e"

    try:
        with Session(engine) as session:
            facade = KnowledgeManagement(
                session=session,
                engine=engine,
                minio_client=Minio(
                    minio_endpoint,
                    access_key=minio_access_key,
                    secret_key=minio_secret_key,
                    secure=False,
                ),
                bucket_name=minio_bucket,
                ollama_client=ollama.Client(host=ollama_host),
                milvus_client=milvus,
                embedding_model=embedding_model,
                collection_name=collection_name,
                vector_dimension=1024,
                chunk_size=128,
                overlap=16,
            )
            result = facade.upload_document(
                content=(
                    b"Knowledge management systems organize searchable "
                    b"document knowledge."
                ),
                filename="e2e.txt",
                content_type="text/plain",
                title="Real integration test",
                source_uri="test://real-integration",
                owner_id="kbms-e2e",
                partition_kind=partition_kind,
                partition_id=partition_id,
                document_id=document_id,
                created_by="kbms-e2e",
            )
            session.commit()

            hits = facade.search("searchable document knowledge", limit=1)
            content = facade.get_document_content(
                document_id,
                partition_kind=partition_kind,
                partition_id=partition_id,
            )
            assert result.document_id == document_id
            assert hits and hits[0].document_id == document_id
            assert content.content.startswith(b"Knowledge management")

            facade.delete_document(
                document_id,
                partition_kind=partition_kind,
                partition_id=partition_id,
                hard_delete=True,
            )
            session.commit()
    finally:
        if milvus.has_collection(collection_name):
            milvus.drop_collection(collection_name=collection_name)
        engine.dispose()
