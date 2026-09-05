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
from .pipeline import PipelineBase, PipelineState, PipelineStateRepository
from .retrieval import KnowledgeSearchService, SearchHit
from .vectors import MilvusVectorStore

__all__ = [

    "DmsCoreClient",
    "DmsCoreDocumentManager",

    "DocumentIndexer",
    "DocumentIngestionService",

    "EmbeddingProvider",
    "KnowledgeDocument",
    "KnowledgeDocumentPage",
    "KnowledgeIndexer",
    "KnowledgeSearchService",
    "MilvusVectorStore",
    "OllamaEmbeddingProvider",
    "PipelineBase",
    "PipelineState",
    "PipelineStateRepository",
    "SearchHit",
    "TextChunk",
    "TextChunker",
    "VectorStore",
]
