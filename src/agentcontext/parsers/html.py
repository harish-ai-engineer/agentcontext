"""HTML parser built on the standard-library html.parser (no dependencies)."""

from __future__ import annotations

from html.parser import HTMLParser as _StdHTMLParser

from ..core.model import Block, BlockType, Document, Provenance
from .base import Parser, register_parser

_SKIP = {"script", "style", "head", "meta", "link", "noscript"}
_HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
_BLOCK_TAGS = {"p", "li", "blockquote", "pre", "td", "th"} | set(_HEADINGS)


class _Collector(_StdHTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, int, str]] = []  # (kind, level, text)
        self._stack: list[str] = []
        self._buf: list[str] = []
        self._title: str = ""

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _BLOCK_TAGS or tag == "title":
            self._flush()
        self._stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_TAGS or tag == "title":
            self._flush(tag)
        if tag in self._stack:
            # pop back to the matching tag
            while self._stack and self._stack.pop() != tag:
                pass

    def handle_data(self, data: str) -> None:
        if any(t in _SKIP for t in self._stack):
            return
        if data.strip():
            self._buf.append(data)

    def _flush(self, tag: str | None = None) -> None:
        text = " ".join(" ".join(self._buf).split())
        self._buf.clear()
        if not text:
            return
        ctx = tag or (self._stack[-1] if self._stack else "")
        if ctx == "title":
            self._title = text
        elif ctx in _HEADINGS:
            self.blocks.append(("heading", _HEADINGS[ctx], text))
        elif ctx == "li":
            self.blocks.append(("list_item", 1, text))
        elif ctx in ("pre",):
            self.blocks.append(("code", 0, text))
        elif ctx == "blockquote":
            self.blocks.append(("quote", 0, text))
        else:
            self.blocks.append(("paragraph", 0, text))


class HTMLParser(Parser):
    name = "html"
    extensions = ("html", "htm")

    def parse(self, path: str) -> Document:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        return self.parse_string(raw, source=path)

    def parse_string(self, raw: str, source: str = "<string>") -> Document:
        c = _Collector()
        c.feed(raw)
        c._flush()
        doc = Document(source=source, meta={"parser": self.name})
        if c._title:
            doc.meta["title"] = c._title
        section = c._title
        for kind, level, text in c.blocks:
            btype = BlockType(kind)
            if btype == BlockType.HEADING and level <= 1:
                section = text
            doc.add(
                Block(
                    type=btype,
                    text=text,
                    level=level or None,
                    provenance=Provenance(source=source, section=section, parser=self.name,
                                          version="html-parser/0.1"),
                )
            )
        return doc


register_parser(HTMLParser())
