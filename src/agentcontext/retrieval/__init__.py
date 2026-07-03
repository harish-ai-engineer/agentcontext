"""Retrieval plugins. Importing this package registers built-in retrievers."""

from .base import (
    Retriever,
    ScoredChunk,
    VectorRetriever,
    cosine,
    get_retriever,
    retrieve,
)

__all__ = [
    "Retriever",
    "ScoredChunk",
    "VectorRetriever",
    "cosine",
    "get_retriever",
    "retrieve",
]
