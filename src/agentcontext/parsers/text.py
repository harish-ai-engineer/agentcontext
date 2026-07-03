"""Plain-text and Markdown parsers (stdlib only)."""

from __future__ import annotations

import re

from ..core.model import Block, BlockType, Document, Provenance
from .base import Parser, register_parser

VERSION = "text-parser/0.1"


class TextParser(Parser):
    name = "text"
    extensions = ("txt",)

    def parse(self, path: str) -> Document:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        doc = Document(source=path, meta={"parser": self.name})
        offset = 0
        for para in re.split(r"\n\s*\n", raw):
            text = para.strip()
            if not text:
                offset += len(para) + 2
                continue
            doc.add(
                Block(
                    type=BlockType.PARAGRAPH,
                    text=text,
                    provenance=Provenance(
                        source=path,
                        char_span=(offset, offset + len(para)),
                        parser=self.name,
                        version=VERSION,
                    ),
                )
            )
            offset += len(para) + 2
        return doc


class MarkdownParser(Parser):
    name = "markdown"
    extensions = ("md", "markdown")

    _heading = re.compile(r"^(#{1,6})\s+(.*)$")
    _list_item = re.compile(r"^(\s*)[-*+]\s+(.*)$")

    def parse(self, path: str) -> Document:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        doc = Document(source=path, meta={"parser": self.name})
        section = ""
        in_code = False
        code_lang = ""
        code_buf: list[str] = []
        para_buf: list[str] = []

        def flush_para() -> None:
            if para_buf:
                doc.add(
                    Block(
                        type=BlockType.PARAGRAPH,
                        text=" ".join(para_buf).strip(),
                        provenance=Provenance(source=path, section=section, parser=self.name,
                                              version="md-parser/0.1"),
                    )
                )
                para_buf.clear()

        for line in lines:
            fence = line.strip().startswith("```")
            if fence:
                if in_code:
                    doc.add(
                        Block(
                            type=BlockType.CODE,
                            text="\n".join(code_buf),
                            meta={"language": code_lang},
                            provenance=Provenance(source=path, section=section, parser=self.name),
                        )
                    )
                    code_buf, code_lang, in_code = [], "", False
                else:
                    flush_para()
                    code_lang = line.strip()[3:].strip()
                    in_code = True
                continue
            if in_code:
                code_buf.append(line)
                continue

            h = self._heading.match(line)
            if h:
                flush_para()
                level = len(h.group(1))
                title = h.group(2).strip()
                if level <= 1:
                    section = title
                doc.add(
                    Block(
                        type=BlockType.HEADING,
                        text=title,
                        level=level,
                        provenance=Provenance(source=path, section=section, parser=self.name),
                    )
                )
                continue

            li = self._list_item.match(line)
            if li:
                flush_para()
                indent = len(li.group(1))
                doc.add(
                    Block(
                        type=BlockType.LIST_ITEM,
                        text=li.group(2).strip(),
                        level=indent // 2 + 1,
                        provenance=Provenance(source=path, section=section, parser=self.name),
                    )
                )
                continue

            if line.strip():
                para_buf.append(line.strip())
            else:
                flush_para()
        flush_para()
        return doc


register_parser(TextParser())
register_parser(MarkdownParser())
