"""PDF parser (optional dependency: pypdf).

Install with:  pip install "agentcontext[pdf]"
"""

from __future__ import annotations

import re

from ..core.model import Block, BlockType, Document, Provenance
from .base import Parser, register_parser


class PDFParser(Parser):
    name = "pdf"
    extensions = ("pdf",)

    def parse(self, path: str) -> Document:
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ImportError(
                "PDF parsing needs pypdf. Install with: pip install \"agentcontext[pdf]\""
            ) from exc

        reader = PdfReader(path)
        doc = Document(source=path, meta={"parser": self.name, "pages": len(reader.pages)})
        info = getattr(reader, "metadata", None)
        if info and info.title:
            doc.meta["title"] = str(info.title)

        for page_no, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for para in re.split(r"\n\s*\n", text):
                para = para.strip()
                if not para:
                    continue
                doc.add(
                    Block(
                        type=BlockType.PARAGRAPH,
                        text=" ".join(para.split()),
                        provenance=Provenance(
                            source=path,
                            page=page_no,
                            parser=self.name,
                            version="pdf-parser/0.1",
                            confidence=0.9,  # extracted text; OCR path would set lower
                        ),
                    )
                )
            doc.add(Block(type=BlockType.PAGE_BREAK, provenance=Provenance(source=path, page=page_no)))
        return doc


register_parser(PDFParser())
