"""Context assembly — the final pipeline stage and AgentContext's differentiator.

Instead of handing an agent a bag of raw chunks, :func:`build_context` assembles
retrieved results into a :class:`ContextPackage`: the relevant chunks, a
deduplicated set of citations, any tables/images those chunks were built from,
and an overall confidence. The result is ready to hand to an LLM via
``package.to_prompt()`` and to attribute via ``package.citations``.
"""

from __future__ import annotations

from typing import Iterable, Optional

from ..core.model import (
    Block,
    BlockType,
    Citation,
    ContextPackage,
    Document,
    Provenance,
)
from ..retrieval.base import ScoredChunk


def _citation_key(c: Citation) -> tuple:
    return (c.source, c.page, c.section, c.bbox)


def _collect_citations(results: Iterable[ScoredChunk]) -> list[Citation]:
    seen: set[tuple] = set()
    citations: list[Citation] = []
    for r in results:
        for prov in r.chunk.provenance:
            cite = Citation.from_provenance(prov)
            key = _citation_key(cite)
            if key not in seen:
                seen.add(key)
                citations.append(cite)
    return citations


def _index_blocks(documents: Iterable[Document]) -> dict[str, Block]:
    index: dict[str, Block] = {}
    for doc in documents:
        for block in doc.blocks:
            index[block.id] = block
    return index


def _prov_dict(prov: Optional[Provenance]) -> dict:
    return prov.to_dict() if prov else {}


def build_context(
    query: str,
    results: list[ScoredChunk],
    *,
    documents: Optional[Iterable[Document]] = None,
    summary: str = "",
    metadata: Optional[dict] = None,
) -> ContextPackage:
    """Assemble retrieved results into a cited :class:`ContextPackage`.

    ``documents`` (optional) lets the builder surface the tables and images that
    the retrieved chunks were built from, traced by block id.
    """
    chunks = [r.chunk for r in results]
    citations = _collect_citations(results)

    tables: list[dict] = []
    images: list[dict] = []
    if documents is not None:
        block_index = _index_blocks(documents)
        seen_blocks: set[str] = set()
        for r in results:
            for bid in r.chunk.block_ids:
                if bid in seen_blocks:
                    continue
                block = block_index.get(bid)
                if block is None:
                    continue
                if block.type == BlockType.TABLE:
                    seen_blocks.add(bid)
                    tables.append(
                        {
                            "text": block.text,
                            "markdown": block.meta.get("markdown"),
                            "provenance": _prov_dict(block.provenance),
                        }
                    )
                elif block.type == BlockType.IMAGE:
                    seen_blocks.add(bid)
                    images.append(
                        {
                            "caption": block.text,
                            "src": block.meta.get("src"),
                            "provenance": _prov_dict(block.provenance),
                        }
                    )

    # Confidence: the strongest match anchors how much to trust this context.
    confidence = max((r.score for r in results), default=0.0)
    confidence = min(1.0, max(0.0, confidence))

    meta = {"retrieved": len(results)}
    if metadata:
        meta.update(metadata)

    return ContextPackage(
        query=query,
        summary=summary,
        chunks=chunks,
        tables=tables,
        images=images,
        citations=citations,
        metadata=meta,
        confidence=confidence,
    )
