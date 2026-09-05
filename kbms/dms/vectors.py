from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from pymilvus import MilvusClient


class MilvusVectorStore:
    """Milvus adapter for chunk vectors and their searchable metadata."""

    _OUTPUT_FIELDS: ClassVar[tuple[str, ...]] = (
        "id", "document_id", "chunk_index", "text", "start", "end", "source_uri",
        "partition_kind", "partition_id",
    )

    def __init__(self, client: MilvusClient, *, collection_name: str, dimension: int) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be blank")
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self.client = client
        self.collection_name = collection_name
        self.dimension = dimension

    def ensure_collection(self) -> None:
        if self.client.has_collection(collection_name=self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            dimension=self.dimension,
            primary_field_name="id",
            id_type="str",
            max_length=512,
            vector_field_name="vector",
            metric_type="COSINE",
            auto_id=False,
            consistency_level="Strong",
        )

    def upsert(self, rows: Sequence[dict[str, object]]) -> object:
        if not rows:
            return {"insert_count": 0}
        self.ensure_collection()
        return self.client.insert(collection_name=self.collection_name, data=list(rows))

    def search(
        self,
        vector: Sequence[float],
        *,
        limit: int = 5,
        document_id: str | None = None,
        partition_kind: str | None = None,
        partition_id: str | None = None,
    ) -> list[list[dict[str, object]]]:
        if not vector:
            raise ValueError("vector must not be empty")
        if limit <= 0:
            raise ValueError("limit must be positive")
        self.ensure_collection()
        filter_expression = ""
        filters = []
        for field, value in (("document_id", document_id), ("partition_kind", partition_kind), ("partition_id", partition_id)):
            if value is not None:
                escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
                filters.append(f'{field} == "{escaped_value}"')
        filter_expression = " and ".join(filters)
        return self.client.search(
            collection_name=self.collection_name,
            data=[list(vector)],
            filter=filter_expression,
            limit=limit,
            output_fields=list(self._OUTPUT_FIELDS),
        )

    def delete_document(self, document_id: str) -> object:
        if not document_id.strip():
            raise ValueError("document_id must not be blank")
        if not self.client.has_collection(collection_name=self.collection_name):
            return {"delete_count": 0}
        escaped_id = document_id.replace("\\", "\\\\").replace('"', '\\"')
        return self.client.delete(
            collection_name=self.collection_name,
            filter=f'document_id == "{escaped_id}"',
        )
