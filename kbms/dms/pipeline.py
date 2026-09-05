from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class PipelineBase(DeclarativeBase):
    pass


class PipelineStateRecord(PipelineBase):
    __tablename__ = "knowledge_pipeline_states"

    document_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    chunks_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


@dataclass(frozen=True, slots=True)
class PipelineState:
    document_id: str
    status: str
    chunks_count: int
    error: str | None
    updated_at: datetime


class PipelineStateRepository:
    """Engine-backed projection for knowledgeization progress."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def set(
        self,
        document_id: str,
        *,
        status: str,
        chunks_count: int = 0,
        error: str | None = None,
    ) -> PipelineState:
        with Session(self.engine) as session:
            record = session.get(PipelineStateRecord, document_id)
            if record is None:
                record = PipelineStateRecord(document_id=document_id, status=status)
                session.add(record)
            record.status = status
            record.chunks_count = chunks_count
            record.error = error
            record.updated_at = datetime.now(UTC)
            session.commit()
            session.refresh(record)
            return self._to_state(record)

    def get(self, document_id: str) -> PipelineState | None:
        with Session(self.engine) as session:
            record = session.get(PipelineStateRecord, document_id)
            return None if record is None else self._to_state(record)

    @staticmethod
    def _to_state(record: PipelineStateRecord) -> PipelineState:
        return PipelineState(
            document_id=record.document_id,
            status=record.status,
            chunks_count=record.chunks_count,
            error=record.error,
            updated_at=record.updated_at,
        )
