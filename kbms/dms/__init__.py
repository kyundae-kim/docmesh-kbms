"""Document management and knowledgeization primitives."""

from .dms_core import DmsCoreClient, DmsCoreDocumentManager
from .dto import KnowledgeDocument, KnowledgeDocumentPage
from .embedding import OllamaEmbeddingProvider
from .ingestion import DocumentIndexer, DocumentIngestionService
from .knowledge import (
    EmbeddingProvider,
    KnowledgeIndexer,
    TextChunk,
    TextChunker,
    VectorStore,
)
from .models import Base, Document, DocumentContent
from .repository import DocumentRepository
from .retrieval import KnowledgeSearchService, SearchHit
from .vectors import MilvusVectorStore

__all__ = [
    "Base",
    "DmsCoreClient",
    "DmsCoreDocumentManager",
    "Document",
    "DocumentContent",
    "DocumentIndexer",
    "DocumentIngestionService",
    "DocumentRepository",
    "EmbeddingProvider",
    "KnowledgeDocument",
    "KnowledgeDocumentPage",
    "KnowledgeIndexer",
    "KnowledgeSearchService",
    "MilvusVectorStore",
    "OllamaEmbeddingProvider",
    "SearchHit",
    "TextChunk",
    "TextChunker",
    "VectorStore",
]
