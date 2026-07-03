# AgentContext

**Document parsing that never loses the plot — or the page number.**

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](https://github.com/harish-ai-engineer/agentcontext/releases)
[![Zero dependencies](https://img.shields.io/badge/core%20deps-zero-brightgreen.svg)](./pyproject.toml)

AgentContext converts documents into clean Markdown and structured JSON, and unlike other converters, **every block of output carries provenance**: source, page, hierarchical section path, and character span. When your agent cites something, you can prove where it came from.

```
PDF / DOCX / HTML / Markdown  →  Markdown + JSON, fully traceable
```

## Why another parser?

Tools like MarkItDown and Docling produce good Markdown — and then throw away most of what an AI agent needs to be trustworthy:

| | MarkItDown | Docling | **AgentContext** |
|---|---|---|---|
| Clean Markdown | ✅ | ✅ | ✅ |
| Structured JSON model | ❌ | ✅ | ✅ |
| Page-level provenance on every block | ❌ | partial | ✅ |
| Hierarchical section path per block | ❌ | ❌ | ✅ |
| Inline citation anchors in Markdown | ❌ | ❌ | ✅ |
| Bounding boxes | ❌ | partial | 🔜 v0.2 |
| Built for downstream RAG citations | ❌ | ❌ | ✅ |

If your LLM answer says *"revenue grew 12%"*, AgentContext lets you point at **page 7, section "3. Financials > 3.2 Revenue"** — automatically. (Bounding boxes land in v0.2 with layout analysis.)

## Install

Not on PyPI yet — install straight from GitHub:

```bash
# core: txt / md / html parsing, zero dependencies
pip install git+https://github.com/harish-ai-engineer/agentcontext.git

# with PDF + DOCX support
pip install "agentcontext[pdf,docx] @ git+https://github.com/harish-ai-engineer/agentcontext.git"
```

No GPU. No torch. No API keys. Pure parsing.

## Quickstart

```python
from agentcontext import Document

doc = Document.parse("report.pdf")

print(doc.to_markdown())              # clean, structured markdown
print(doc.to_json())                  # full document model, lossless

for block in doc.blocks:
    print(block.text[:60], "→ page", block.provenance.page)

for table in doc.tables:
    print(table.to_rows())            # structured cells, with provenance
```

Or from the command line:

```bash
agentcontext parse report.pdf                # writes report.md next to the source
agentcontext parse report.pdf --json         # writes report.json (full document model)
agentcontext parse report.pdf --cite inline  # markdown with provenance anchors
```

## What the output looks like

`--cite inline` gives you Markdown that renders normally but carries its receipts:

```markdown
# Refund Policy <!-- src: policy.md | Refund Policy -->

Customers may request a full refund within 30 days
of purchase. <!-- src: policy.md | Refund Policy -->

## Exceptions <!-- src: policy.md | Refund Policy > Exceptions -->

Digital goods are excluded. <!-- src: policy.md | Refund Policy > Exceptions -->
```

`--json` gives you the full Unified Document Model. Unknown provenance fields are **explicit `null`, never omitted** — a block without provenance is a bug:

```json
{
  "udm_version": "0.1",
  "metadata": {
    "title": null, "author": null, "created": null,
    "source_path": "/abs/path/report.pdf",
    "sha256": "444cd23e4ba2b0a1…",
    "parser": "pdf", "parser_version": "pdf-parser/0.1"
  },
  "blocks": [
    {
      "type": "paragraph",
      "text": "Revenue grew 12% year over year...",
      "level": null,
      "provenance": {
        "source": "report.pdf",
        "page": 7,
        "section_path": "3. Financials > 3.2 Revenue",
        "bbox": null,
        "char_span": null,
        "confidence": 0.9,
        "parser": "pdf",
        "version": "pdf-parser/0.1"
      }
    }
  ],
  "tables": [ ... ]
}
```

## Supported formats (v0.1)

- **PDF** (digital / text-layer)
- **DOCX**
- **HTML**
- **Markdown** (normalization + provenance) and plain text

OCR for scanned documents, PPTX, and XLSX are next on the [roadmap](#roadmap).

## Benchmarks

A public benchmark against MarkItDown and Docling on a golden corpus (papers, reports, contracts, invoices) — measuring text accuracy, structure accuracy, table cell accuracy, and provenance accuracy — is under construction: see [BENCHMARKS.md](./BENCHMARKS.md).

We will publish the numbers even where we lose. Trust is the product.

## Roadmap

- **v0.1 (now):** PDF/DOCX/HTML/MD → Markdown + JSON with full provenance. CLI + Python SDK.
- **v0.2:** OCR for scanned documents, PPTX/XLSX parsers, provenance-preserving chunking.
- **v0.3:** Embedding adapters, citation-aware retrieval helpers.
- **Later:** Context packages for agents — retrieval that returns not just chunks, but summaries, tables, entities, and citations in one structured payload.

The long-term vision is a full open context-engineering layer for AI agents (a working preview of the whole pipeline lives on the [`platform`](https://github.com/harish-ai-engineer/agentcontext/tree/platform) branch). The short-term promise is simpler: **the most trustworthy parser you can put in a RAG pipeline.**

## Design principles

1. **Provenance is not optional.** A block without a source location is a bug.
2. **Small core, pluggable edges.** Parsers, OCR engines, and exporters implement a small protocol.
3. **No heavyweight dependencies in core.** `pip install` and go.
4. **Honest benchmarks.** Measured in CI, published publicly.

## Contributing

The `Parser` protocol makes new formats easy to add:

```python
from agentcontext import Document, Parser, register_parser

class EpubParser(Parser):
    name = "epub"
    version = "epub-parser/0.1"
    extensions = ("epub",)

    def parse(self, path: str) -> Document:
        ...

register_parser(EpubParser())
```

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## Author

Built by **Harish** — [@harish-ai-engineer](https://github.com/harish-ai-engineer)

## License

Apache-2.0
