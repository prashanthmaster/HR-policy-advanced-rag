"""Version-aware hybrid retrieval adapters."""

from hr_policy_rag.retrieval.embeddings import (
    DenseEncoder,
    FastEmbedBm25Encoder,
    OpenAIDenseEncoder,
    SparseEmbedding,
    SparseEncoder,
)
from hr_policy_rag.retrieval.qdrant_store import (
    IndexAlreadyExistsError,
    QdrantHybridRetriever,
    RetrievalContextError,
    RetrievalIntegrityError,
    RetrievalUnavailableError,
    build_candidate_index,
)

__all__ = [
    "DenseEncoder",
    "FastEmbedBm25Encoder",
    "IndexAlreadyExistsError",
    "OpenAIDenseEncoder",
    "QdrantHybridRetriever",
    "RetrievalContextError",
    "RetrievalIntegrityError",
    "RetrievalUnavailableError",
    "SparseEmbedding",
    "SparseEncoder",
    "build_candidate_index",
]
