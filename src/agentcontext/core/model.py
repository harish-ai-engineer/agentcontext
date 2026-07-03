"""Unified Document Model — the keystone data model of AgentContext.

Every parser produces a :class:`Document` (an ordered list of :class:`Block`s
carrying provenance). Every downstream stage — chunking, embedding, retrieval,
context building — reads and writes these same types. Get this right and the
rest of the platform composes cleanly; get it wrong and every module inherits
the mistake.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Iterable, Optional


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class BlockType(str, Enum):
    """The kind of content a block holds. Extend via plugins as needed."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"
    FORMULA = "formula"
    CAPTION = "caption"
    QUOTE = "quote"
    PAGE_BREAK = "page_break"
    OTHER = "other"


@dataclass
class Provenance:
    """Where a piece of content came from — the basis for citations.

    Provenance travels with content through every stage so that a chunk
    returned to an agent can always be traced back to an exact location.
    """

    source: str  # path or URI of the origin document
    page: Optional[int] = None  # 1-indexed page, when applicable
    section: Optional[str] = None  # section path, e.g. "1.2 Methods"
    bbox: Optional[tuple[float, float, float, float]] = None  # (x0, y0, x1, y1)
    char_span: Optional[tuple[int, int]] = None  # char offsets in source text
    confidence: float = 1.0  # 0..1, parser/OCR confidence
    parser: Optional[str] = None  # which parser produced it
    version: Optional[str] = None  # processing version, for reproducibility

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Block:
    """One atomic unit of a document, in reading order."""

    type: BlockType
    text: str = ""
    id: str = field(default_factory=lambda: _new_id("blk"))
    level: Optional[int] = None  # heading depth / list nesting
    provenance: Optional[Provenance] = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "type": self.type.value, "text": self.text}
        if self.level is not None:
            d["level"] = self.level
        if self.provenance is not None:
            d["provenance"] = self.provenance.to_dict()
        if self.meta:
            d["meta"] = self.meta
        return d


@dataclass
class Document:
    """A parsed document: ordered blocks plus document-level metadata."""

    source: str
    blocks: list[Block] = field(default_factory=list)
    id: str = field(default_factory=lambda: _new_id("doc"))
    meta: dict[str, Any] = field(default_factory=dict)

    # -- construction helpers -------------------------------------------------
    def add(self, block: Block) -> Block:
        self.blocks.append(block)
        return block

    def blocks_of(self, *types: BlockType) -> list[Block]:
        wanted = set(types)
        return [b for b in self.blocks if b.type in wanted]

    def iter_sections(self) -> Iterable[tuple[str, list[Block]]]:
        """Yield ``(section_title, blocks)`` grouped by top-level headings."""
        current_title = ""
        bucket: list[Block] = []
        for b in self.blocks:
            if b.type == BlockType.HEADING and (b.level or 1) <= 1:
                if bucket:
                    yield current_title, bucket
                current_title = b.text
                bucket = [b]
            else:
                bucket.append(b)
        if bucket:
            yield current_title, bucket

    # -- exporters ------------------------------------------------------------
    def to_text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks if b.text).strip() + "\n"

    def to_markdown(self) -> str:
        out: list[str] = []
        for b in self.blocks:
            if b.type == BlockType.HEADING:
                out.append(f"{'#' * max(1, b.level or 1)} {b.text}")
            elif b.type == BlockType.LIST_ITEM:
                out.append(f"{'  ' * ((b.level or 1) - 1)}- {b.text}")
            elif b.type == BlockType.CODE:
                lang = b.meta.get("language", "")
                out.append(f"```{lang}\n{b.text}\n```")
            elif b.type == BlockType.QUOTE:
                out.append("\n".join(f"> {line}" for line in b.text.splitlines()))
            elif b.type == BlockType.TABLE:
                out.append(b.meta.get("markdown") or b.text)
            elif b.type == BlockType.IMAGE:
                out.append(f"![{b.text or 'image'}]({b.meta.get('src', '')})")
            elif b.type == BlockType.PAGE_BREAK:
                out.append("\n---\n")
            elif b.text:
                out.append(b.text)
        return "\n\n".join(out).strip() + "\n"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "meta": self.meta,
            "blocks": [b.to_dict() for b in self.blocks],
        }


@dataclass
class Chunk:
    """A retrieval unit assembled from one or more blocks."""

    text: str
    id: str = field(default_factory=lambda: _new_id("chk"))
    block_ids: list[str] = field(default_factory=list)
    provenance: list[Provenance] = field(default_factory=list)
    embedding: Optional[list[float]] = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_embedding: bool = False) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "text": self.text,
            "block_ids": self.block_ids,
            "provenance": [p.to_dict() for p in self.provenance],
            "meta": self.meta,
        }
        if include_embedding and self.embedding is not None:
            d["embedding"] = self.embedding
        return d


@dataclass
class Citation:
    """A traceable pointer to source content, attached to retrieved results."""

    source: str
    page: Optional[int] = None
    section: Optional[str] = None
    bbox: Optional[tuple[float, float, float, float]] = None
    confidence: float = 1.0
    version: Optional[str] = None

    @classmethod
    def from_provenance(cls, p: Provenance) -> "Citation":
        return cls(
            source=p.source,
            page=p.page,
            section=p.section,
            bbox=p.bbox,
            confidence=p.confidence,
            version=p.version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ContextPackage:
    """The differentiator: a structured, cited bundle ready to hand to an LLM.

    Rather than returning raw chunks, AgentContext returns everything an agent
    needs to answer *and* to attribute its answer.
    """

    query: str
    summary: str = ""
    chunks: list[Chunk] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "summary": self.summary,
            "chunks": [c.to_dict() for c in self.chunks],
            "tables": self.tables,
            "images": self.images,
            "entities": self.entities,
            "relationships": self.relationships,
            "citations": [c.to_dict() for c in self.citations],
            "metadata": self.metadata,
            "confidence": self.confidence,
        }

    def to_prompt(self) -> str:
        """Render the package as a citation-annotated prompt block for an LLM."""
        lines: list[str] = []
        if self.summary:
            lines.append(f"Summary: {self.summary}\n")
        lines.append("Context:")
        for i, chunk in enumerate(self.chunks, 1):
            cite = ""
            if chunk.provenance:
                p = chunk.provenance[0]
                loc = p.section or (f"p.{p.page}" if p.page else "")
                cite = f" [source: {p.source}{(' ' + loc) if loc else ''}]"
            lines.append(f"[{i}]{cite}\n{chunk.text}\n")
        return "\n".join(lines).strip()
