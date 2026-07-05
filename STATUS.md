# AgentContext — Project Status

**Positioning (decided 2026-07-03):** v0.1 follows the narrow spec in
`agentcontext-v0.1-spec-and-readme.md` — *a document parser that never loses
provenance*. The broader platform vision (chunking → embeddings → retrieval →
context packages) is the growth path, not the v0.1 product.

Last updated: 2026-07-03

---

## Where the code lives

| Branch | Contents |
|--------|----------|
| `main` | **Spec-strict v0.1**: four-format parser, UDM, provenance, CLI, SDK |
| `platform` | The full pipeline preview (chunking, embeddings, retrieval, context builder, `Doc` agent API, summarize, csv/json/xml/pptx/xlsx parsers, 5-command CLI). Source material for v0.2+. |

License: **Apache-2.0** (decided; supersedes the MIT line in the spec draft).

---

## v0.1 spec compliance (main)

| Spec item | Status |
|-----------|--------|
| Four input formats: PDF, DOCX, HTML, MD (+txt) | ✅ |
| UDM with `udm_version` | ✅ |
| **No block without provenance; explicit nulls, never omitted** | ✅ enforced + tested |
| Hierarchical `section_path` ("2. Methods > 2.1 Setup") | ✅ md/html/docx |
| Doc metadata: `source_path`, `sha256`, `parser_version`, title/author/created | ✅ |
| Tables first-class: inline block + doc-level `tables[]` with cells | ✅ |
| Outputs: Markdown + lossless UDM JSON only | ✅ |
| Inline citation anchors (`--cite inline`) | ✅ |
| SDK: `Document.parse()`, `.blocks`, `.tables`, `.to_markdown()`, `.to_json()` | ✅ |
| CLI: `parse` / `--json` / `--cite inline`, writes next to source | ✅ (+ `--stdout`; never clobbers the source file) |
| Parser protocol: `can_parse` + `parse`, registry | ✅ |
| Zero heavyweight deps (no torch, no CUDA, no keys) | ✅ |
| PDF bbox provenance | ⏳ null in v0.1 (text-layer only; layout analysis is v0.2) |
| Golden corpus + CI metrics | 🟡 harness + seed corpus (7 docs) live; needs real docs + CI wiring |
| Public benchmark page vs MarkItDown/Docling | 🟡 seed results published (markitdown scored; docling pending install) |
| < 5s parse for 50-page digital PDF | ✅ 0.51s measured (synthetic 50-pager, pypdf backend) |
| pip install works Linux/macOS/Windows | ✅ published as **agentcontext-core** 0.1.0; verified install+run from PyPI on Windows |

Verified: 16/16 spec-compliance tests (`tests/test_udm.py`), live CLI checked.

---

## Definition of done — remaining for v0.1 release

1. Grow the golden corpus to 25–50 **real** documents (seed harness done:
   `benchmarks/make_corpus.py` + `benchmarks/harness.py`, 4 metrics, honest
   zero-scoring for failed parses)
2. Wire the harness into CI; add Docling to the baseline row
3. ~~Perf check~~ ✅ 0.51s for a 50-page digital PDF
4. ~~Package publish~~ ✅ live on PyPI as `agentcontext-core` (plain name blocked
   by unrelated `agent-context` project); Linux/macOS install verification pending CI

## v0.2 plan

Theme: **provenance survives more formats and the first pipeline step.**
Order of work (one at a time, tests + benchmarks before the next):

1. **PPTX + XLSX parsers** — port from `platform` (stdlib zip+xml, already
   written); slides carry `page`, sheets carry `section_path`; add corpus docs
2. **Provenance-preserving chunking** — port `token`/`section` chunkers from
   `platform`; every `Chunk` keeps the provenance list of its blocks. This is
   the bridge from parser to context platform
3. **OCR adapter** — Tesseract behind the existing Parser protocol as
   `agentcontext-core[ocr]`; scanned-PDF corpus docs with lower confidence
4. **Real-document corpus** — grow to 25+ real files; publish updated numbers
5. **Docling baseline** — add to the benchmark table (CI-only install)

Launch prep (done 2026-07-05): CI on 3 OSes × py3.10/3.12 + zero-dep install
check + benchmark job; honest benchmark framing; `examples/rag_with_citations.py`;
CI/PyPI badges; Discussions + good-first-issues.

Still manual (owner): social preview image (repo Settings), demo GIF for the
README, PyPI token rotation.
