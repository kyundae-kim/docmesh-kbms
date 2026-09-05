from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    """KMS document projection that hides dms-core-specific types."""

    document_id: str
    filename: str
    content_type: str
    file_size: int
    status: str
    created_at: datetime
    updated_at: datetime
    partition_kind: str
    partition_id: str
    checksum: str | None
    created_by: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class KnowledgeDocumentPage:
    items: list[KnowledgeDocument]
    next_cursor: str | None
    has_more: bool