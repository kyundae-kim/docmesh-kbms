from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import ollama
import pytest
from minio import Minio
from pymilvus import MilvusClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from kbms import KnowledgeManagement
from kbms.dms.models import Base


@pytest.fixture
def real_service_config() -> dict[str, str]:
    return {
        "ollama_host": os.getenv(
            "KBMS_OLLAMA_HOST", "http://192.168.219.106:11434"
        ),
        "minio_endpoint": os.getenv("KBMS_MINIO_ENDPOINT", "milvus-minio:9000"),
        "minio_access_key": os.getenv("KBMS_MINIO_ACCESS_KEY", "minioadmin"),
        "minio_secret_key": os.getenv("KBMS_MINIO_SECRET_KEY", "minioadmin"),
        "minio_bucket": os.getenv("KBMS_MINIO_BUCKET", "kbms-e2e"),
        "embedding_model": os.getenv("KBMS_OLLAMA_EMBEDDING_MODEL", "bge-m3"),
    }


def _exercise_facade(
    *,
    engine: Engine,
    milvus: MilvusClient,
    config: dict[str, str],
) -> None:
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
                    config["minio_endpoint"],
                    access_key=config["minio_access_key"],
                    secret_key=config["minio_secret_key"],
                    secure=False,
                ),
                bucket_name=config["minio_bucket"],
                ollama_client=ollama.Client(host=config["ollama_host"]),
                milvus_client=milvus,
                embedding_model=config["embedding_model"],
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


@pytest.mark.integration
@pytest.mark.real_integration
@pytest.mark.parametrize("database_kind", ["memory", "disk", "postgres"])
@pytest.mark.parametrize("milvus_kind", ["local", "server"])
def test_real_facade_supports_database_and_milvus_access_modes(
    database_kind: str,
    milvus_kind: str,
    tmp_path: Path,
    real_service_config: dict[str, str],
) -> None:
    if database_kind == "memory":
        database_uri = "sqlite:///:memory:"
    elif database_kind == "disk":
        database_uri = f"sqlite:///{tmp_path / 'kbms-e2e.db'}"
    else:
        database_uri = os.getenv(
            "KBMS_POSTGRES_URL",
            "postgresql+psycopg://docmesh:postgres@postgres:5432/kbms",
        )

    if milvus_kind == "local":
        milvus_uri = str(tmp_path / f"milvus-{database_kind}.db")
    else:
        milvus_uri = os.getenv("KBMS_MILVUS_URI", "http://milvus:19530")

    engine = create_engine(database_uri)
    milvus = MilvusClient(uri=milvus_uri)
    try:
        Base.metadata.create_all(engine)
        _exercise_facade(
            engine=engine,
            milvus=milvus,
            config=real_service_config,
        )
    finally:
        engine.dispose()
