"""AgentContext — turn any document into AI-ready, cited context for LLMs.

The full pipeline runs offline with zero hard dependencies:

    parse -> chunk -> embed -> retrieve -> context

Quick start::

    import agentcontext as ac

    pkg = ac.build_context_from_files(
        "What is the refund policy?",
        ["policy.pdf", "faq.md"],
        k=5,
    )
    print(pkg.to_prompt())   # citation-annotated context for an LLM
    print(pkg.citations)     # traceable source pointers
"""

from __future__ import annotations

from .chunking import chunk
from .context import build_context
from .core.model import (
    Block,
    BlockType,
    Chunk,
    Citation,
    ContextPackage,
    Document,
    Provenance,
)
from .embeddings import get_embedder
from .parsers import parse
from .retrieval import ScoredChunk, VectorRetriever, retrieve

__version__ = "0.1.0"

__all__ = [
    # data model
    "Block",
    "BlockType",
    "Chunk",
    "Citation",
    "ContextPackage",
    "Document",
    "Provenance",
    "ScoredChunk",
    # pipeline stages
    "parse",
    "chunk",
    "get_embedder",
    "retrieve",
    "VectorRetriever",
    "build_context",
    # high-level helpers
    "ingest",
    "build_context_from_files",
]


def ingest(
    paths: list[str],
    *,
    chunker: str = "token",
    **chunk_kwargs,
) -> tuple[list[Document], list[Chunk]]:
    """Parse and chunk every path. Returns ``(documents, chunks)``."""
    documents: list[Document] = []
    chunks: list[Chunk] = []
    for path in paths:
        doc = parse(path)
        documents.append(doc)
        chunks.extend(chunk(doc, strategy=chunker, **chunk_kwargs))
    return documents, chunks


def build_context_from_files(
    query: str,
    paths: list[str],
    *,
    k: int = 5,
    embedder: str = "hashing",
    chunker: str = "token",
    summary: str = "",
    **chunk_kwargs,
) -> ContextPackage:
    """One-shot: parse -> chunk -> embed -> retrieve -> context over ``paths``."""
    documents, chunks = ingest(paths, chunker=chunker, **chunk_kwargs)
    results = retrieve(chunks, query, k=k, embedder=embedder)
    return build_context(
        query,
        results,
        documents=documents,
        summary=summary,
        metadata={"embedder": embedder, "chunker": chunker, "k": k},
    )
