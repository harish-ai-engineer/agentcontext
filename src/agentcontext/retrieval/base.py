"""Retrieval interface + a dependency-free in-memory vector retriever.

Retrieval is the fourth pipeline stage (parse -> chunk -> embed -> **retrieve**
-> context). A retriever indexes :class:`Chunk`s and, given a query, returns the
most relevant ones as :class:`ScoredChunk`s. Because chunks carry provenance,
every retrieved result remains traceable back to its exact source location.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..core.model import Chunk
from ..core.registry import retrievers
from ..embeddings.base import EmbeddingProvider, get_embedder


@dataclass
class ScoredChunk:
    """A retrieved chunk paired with its relevance score (0..1, higher = closer)."""

    chunk: Chunk
    score: float

    def to_dict(self, include_embedding: bool = False) -> dict:
        d = self.chunk.to_dict(include_embedding=include_embedding)
        d["score"] = self.score
        return d


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors. Returns 0 for a zero vector."""
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


class Retriever(ABC):
    name = "base"

    @abstractmethod
    def index(self, chunks: list[Chunk]) -> "Retriever":  # pragma: no cover - interface
        ...

    @abstractmethod
    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:  # pragma: no cover
        ...


class VectorRetriever(Retriever):
    """In-memory cosine-similarity retriever over embedded chunks.

    Uses whatever :class:`EmbeddingProvider` it is given (the offline
    ``HashingEmbedder`` by default), so it runs end-to-end with no API keys and
    no native dependencies. Chunks are embedded once at ``index`` time; embeddings
    already present on a chunk are reused.
    """

    name = "vector"

    def __init__(self, embedder: EmbeddingProvider | str = "hashing") -> None:
        self.embedder = get_embedder(embedder) if isinstance(embedder, str) else embedder
        self._chunks: list[Chunk] = []

    def index(self, chunks: list[Chunk]) -> "VectorRetriever":
        pending = [c for c in chunks if c.embedding is None]
        if pending:
            vectors = self.embedder.embed([c.text for c in pending])
            for c, vec in zip(pending, vectors):
                c.embedding = vec
        self._chunks = list(chunks)
        return self

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        if not self._chunks:
            return []
        qvec = self.embedder.embed_one(query)
        scored = [
            ScoredChunk(chunk=c, score=cosine(qvec, c.embedding))
            for c in self._chunks
            if c.embedding is not None
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored[: max(0, k)]


retrievers.register("vector", VectorRetriever)  # class: constructed on demand


def get_retriever(name: str = "vector", **kwargs) -> Retriever:
    obj = retrievers.get(name)
    return obj(**kwargs) if isinstance(obj, type) else obj


def retrieve(
    chunks: list[Chunk],
    query: str,
    k: int = 5,
    embedder: EmbeddingProvider | str = "hashing",
) -> list[ScoredChunk]:
    """Index ``chunks`` and return the top-``k`` most relevant to ``query``."""
    return VectorRetriever(embedder).index(chunks).search(query, k)
