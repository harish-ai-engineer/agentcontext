# AgentContext — Project Status & Roadmap

**Vision:** _AgentContext is an open-source context-engineering platform that transforms
documents, code, images, and other data sources into structured, searchable, and
AI-ready context for LLMs and autonomous agents._

This document tracks **what is actually built today** vs. **the full platform vision**,
so the gap is always honest and visible.

Last updated: 2026-07-03

---

## TL;DR

- **~15% of the full vision is implemented.** The rest is roadmap, not code.
- What exists is a clean, zero-dependency **Phase 1 + partial Phase 2** foundation:
  `parse → chunk → embed → retrieve → context`, all offline, with real citations.
- The `ContextPackage` **shape** already matches the vision (`summary`, `chunks`,
  `tables`, `images`, `entities`, `relationships`, `citations`, `metadata`,
  `confidence`) — but several of those fields are **empty placeholders** nothing
  fills yet. The plumbing exists; the intelligence does not.

---

## Pipeline (the part that works end-to-end)

```text
parse  ->  chunk  ->  embed  ->  retrieve  ->  context
 (5 fmts)  (2 strat)  (2 prov)   (cosine)     (cited package)
```

Runs entirely offline, zero hard dependencies. Verified via `tests/test_pipeline.py`
(6 smoke tests) and the live CLI (`agentcontext parse`, `agentcontext context`).

---

## What is done ✅ / partial 🟡 / missing ❌

| # | Vision area | Status | Reality in code |
|---|-------------|--------|-----------------|
| 1 | Ingestion | 🟡 5 of ~19 | Only `txt, md, html, pdf, docx`. No pptx/xlsx/csv/json/xml/epub/images/audio/video/zip/email/code-repo/web. |
| 2 | Document Intelligence (OCR, layout, tables, forms, charts) | ❌ | None. (docx tables come from native XML, not extraction.) |
| 3 | AI Understanding (entities, topics, summary, PII, sentiment) | ❌ | Fields exist on `ContextPackage`; nothing populates them. |
| 4 | Universal Output | 🟡 3 of 10 | `to_text`, `to_markdown`, `to_dict`(JSON). No YAML/CSV/SQL/Parquet/HTML/OCR. |
| 5 | Smart Chunking | 🟡 2 of 8 | `token`, `section`. No semantic/page/sliding-window/parent-child/hierarchical. |
| 6 | Embeddings | 🟡 basic | `hashing` (offline) + `openai`. No caching/versioning/metadata layer. |
| 7 | Search | 🟡 1 of 7 | Semantic (cosine) only. No full-text/hybrid/fuzzy/metadata-filter/image/table. |
| 8 | Knowledge Graph | ❌ | None. |
| 9 | Citations | 🟢 done | `Provenance`/`Citation`: source, page, section, bbox, confidence, version. |
| 10 | Context Builder | 🟢 core done | `build_context` → cited `ContextPackage`. Tables surface only from docx; entities/relationships/images empty. |
| 11 | Agent APIs (`doc.ask()`, `doc.summary()`, …) | ❌ | Only functional API (`parse()`, `chunk()`, `retrieve()`, `build_context()`). No `Document` object API. |
| 12 | RAG Engine | 🟡 partial | Chunk→embed→retrieve→assemble works. No vector-DB connectors, no re-ranking. |
| 13 | Memory (session/persistent/knowledge) | ❌ | None. |
| 14 | Connectors (GitHub, Notion, Drive, S3, …) | ❌ | None. |
| 15 | AI Model Support | 🟡 | OpenAI embeddings only. No Anthropic/Google/VLM/chat-model adapters. |
| 16 | Plugins | 🟢 foundation | Registry pattern is first-class for parsers/chunkers/embedders/retrievers. |
| 17 | CLI | 🟡 2 of 7 | `parse`, `context`. No summarize/search/chunk/embed/graph/serve. |
| 18 | REST API | ❌ | None. |
| 19 | Web UI | ❌ | None. |
| 20 | Observability | ❌ | None. |
| 21 | Enterprise (auth, RBAC, audit, encryption) | ❌ | None. |

---

## Current file layout

```text
src/agentcontext/
├── __init__.py            # public API: parse, chunk, retrieve, build_context, ingest, build_context_from_files
├── cli.py                 # CLI: `parse`, `context`
├── core/
│   ├── model.py           # Unified Document Model: Document, Block, Provenance, Chunk, Citation, ContextPackage
│   └── registry.py        # plugin registries: parsers, chunkers, embedders, retrievers
├── parsers/               # text/md, html, pdf (lazy pypdf), docx (lazy python-docx)
├── chunking/              # token, section
├── embeddings/            # hashing (offline), openai
├── retrieval/             # vector (in-memory cosine)
└── context/               # build_context -> cited ContextPackage
tests/
└── test_pipeline.py       # 6 offline end-to-end smoke tests
```

> Note: this is a **single package**, not the multi-package ecosystem
> (`agentcontext-parser`, `-ocr`, `-vision`, …) sketched in the vision.

---

## Progress vs. the roadmap

| Phase | Scope | Done |
|-------|-------|------|
| **v0.1** | Universal parser, MD/JSON output, CLI, SDK | ~70% (parser coverage thin; SDK is functions, not `Document.x()`) |
| **v0.5** | OCR, layout, smart chunking, embeddings, search | ~20% (chunking + embeddings + vector search; no OCR/layout) |
| **v1.0** | Knowledge graph, connectors, server, plugins, context builder | ~15% (plugin registry + context builder only) |
| **v2.0** | Agent memory, multi-modal, multi-doc reasoning, enterprise | 0% |

---

## Recommended next steps (highest leverage first)

Build **one at a time**, each with tests + verification. Do not stub all at once.

1. **Agent API (§11)** — a `Document` class wrapping the pipeline
   (`.parse().chunk().search().ask().summary().citations()`). Makes the SDK match
   the vision and everything else composable. ~1 day on top of what exists. **← start here**
2. **AI Understanding (§3)** — wire an Anthropic/OpenAI chat adapter so
   `summary` / `entities` / `relationships` stop being empty. This fills the `ContextPackage`.
3. **Hybrid search (§7)** — add a stdlib BM25 retriever and fuse with the existing
   vector retriever (still zero-dependency).
4. **More formats (§1)** — csv/json/pptx/xlsx parsers (cheap, high perceived coverage).

---

## Design invariants to preserve

- **Core stays zero-dependency.** Everything heavy (pypdf, openai, OCR, VLMs) is an
  optional extra, constructed lazily.
- **Everything flows through the Unified Document Model** (`Document → Block →
  Provenance`) so any retrieved item is always traceable to an exact source location.
- **Every capability is a plugin** registered in `core/registry.py` — new parsers,
  chunkers, embedders, retrievers drop in without touching the core.
```
