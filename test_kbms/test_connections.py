from __future__ import annotations

import os

import ollama
import pytest
from pymilvus import MilvusClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


def _round_trip(url: str) -> None:
    engine = create_engine(url)
    with Session(engine) as session:
        assert session.scalar(text("SELECT 1")) == 1
    engine.dispose()


def test_sqlite_memory_connection() -> None:
    _round_trip("sqlite:///:memory:")


def test_sqlite_disk_connection(tmp_path) -> None:
    _round_trip(f"sqlite:///{tmp_path / 'kbms.db'}")


@pytest.mark.integration
def test_milvus_local_connection(tmp_path) -> None:
    client = MilvusClient(uri=str(tmp_path / "milvus.db"))
    assert isinstance(client.list_collections(), list)


@pytest.mark.integration
def test_postgres_connection() -> None:
    url = os.getenv(
        "KBMS_POSTGRES_URL",
        "postgresql+psycopg://docmesh:postgres@postgres:5432/kbms",
    )
    _round_trip(url)


@pytest.mark.integration
def test_milvus_connection() -> None:
    uri = os.getenv("KBMS_MILVUS_URI", "http://milvus:19530")
    client = MilvusClient(uri=uri)
    assert isinstance(client.list_collections(), list)


@pytest.mark.integration
def test_ollama_connection() -> None:
    host = os.getenv("KBMS_OLLAMA_HOST", "http://192.168.219.106:11434")
    response = ollama.Client(host=host).list()
    assert response is not None
