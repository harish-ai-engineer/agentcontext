"""Chunking interface + built-in strategies.

Chunks always carry the provenance of the blocks they were built from, so a
retrieved chunk can be cited back to its exact source location.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.model import Block, Chunk, Document, Provenance
from ..core.registry import chunkers


class Chunker(ABC):
    name = "base"

    @abstractmethod
    def chunk(self, doc: Document) -> list[Chunk]:  # pragma: no cover - interface
        ...


def _mk_chunk(blocks: list[Block], meta: dict | None = None) -> Chunk:
    text = "\n\n".join(b.text for b in blocks if b.text).strip()
    prov: list[Provenance] = [b.provenance for b in blocks if b.provenance]
    return Chunk(
        text=text,
        block_ids=[b.id for b in blocks],
        provenance=prov,
        meta=meta or {},
    )


class SectionChunker(Chunker):
    """One chunk per top-level section. Preserves document structure."""

    name = "section"

    def chunk(self, doc: Document) -> list[Chunk]:
        out: list[Chunk] = []
        for title, blocks in doc.iter_sections():
            c = _mk_chunk(blocks, {"strategy": self.name, "section": title})
            if c.text:
                out.append(c)
        return out


class TokenChunker(Chunker):
    """Word-approximate fixed-size chunks with overlap. Provider-agnostic.

    ``max_tokens`` is measured in whitespace words (a portable proxy for tokens);
    swap in a real tokenizer via a plugin when exactness matters.
    """

    name = "token"

    def __init__(self, max_tokens: int = 350, overlap: int = 50) -> None:
        self.max_tokens = max_tokens
        self.overlap = overlap

    def chunk(self, doc: Document) -> list[Chunk]:
        out: list[Chunk] = []
        window: list[Block] = []
        count = 0
        for b in doc.blocks:
            if not b.text:
                continue
            n = len(b.text.split())
            if count + n > self.max_tokens and window:
                out.append(_mk_chunk(window, {"strategy": self.name}))
                # carry overlap by keeping trailing blocks
                kept: list[Block] = []
                kc = 0
                for wb in reversed(window):
                    kept.insert(0, wb)
                    kc += len(wb.text.split())
                    if kc >= self.overlap:
                        break
                window = kept
                count = kc
            window.append(b)
            count += n
        if window:
            out.append(_mk_chunk(window, {"strategy": self.name}))
        return out


# Register built-ins.
chunkers.register("section", SectionChunker())
chunkers.register("token", TokenChunker())


def chunk(doc: Document, strategy: str = "token", **kwargs) -> list[Chunk]:
    if kwargs and strategy == "token":
        return TokenChunker(**kwargs).chunk(doc)
    return chunkers.get(strategy).chunk(doc)
