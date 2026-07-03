# AgentContext

**The open context-engineering platform: turn any document into AI-ready, cited context for LLMs and agents.**

AgentContext runs the full pipeline — **parse → chunk → embed → retrieve → context** — with **zero hard dependencies**. The default path works entirely offline (no API keys, no native libraries); swap in real embedders or parsers through the plugin system when you need production quality.

## Install

```bash
pip install agentcontext                 # core, zero dependencies
pip install "agentcontext[pdf,docx]"     # + PDF / DOCX parsers
pip install "agentcontext[openai]"       # + OpenAI embeddings
pip install "agentcontext[all]"          # everything
```

## Quick start (Python)

```python
import agentcontext as ac

pkg = ac.build_context_from_files(
    "What is the refund policy?",
    ["policy.pdf", "faq.md"],
    k=5,
)

print(pkg.to_prompt())   # citation-annotated context, ready for an LLM
for c in pkg.citations:  # every claim is traceable to its source
    print(c.to_dict())
```

Each stage is also available on its own:

```python
doc     = ac.parse("report.pdf")           # -> Document (Unified Document Model)
chunks  = ac.chunk(doc, strategy="token")  # -> list[Chunk], carrying provenance
results = ac.retrieve(chunks, "revenue", k=3)
pkg     = ac.build_context("revenue", results, documents=[doc])
```

## Quick start (CLI)

```bash
# Parse a document into Markdown / text / JSON
agentcontext parse report.pdf --to markdown

# Build a cited context package for a query
agentcontext context "What is the refund policy?" --docs policy.pdf faq.md --k 5
agentcontext context "revenue in Q3" --docs report.pdf --format json
```

## How it fits together

| Stage | Module | Built-ins |
|-------|--------|-----------|
| **parse** | `agentcontext.parsers` | text/markdown, HTML, PDF (`pypdf`), DOCX (`python-docx`) |
| **chunk** | `agentcontext.chunking` | `token` (fixed-size + overlap), `section` (structure-preserving) |
| **embed** | `agentcontext.embeddings` | `hashing` (offline default), `openai` |
| **retrieve** | `agentcontext.retrieval` | `vector` (in-memory cosine) |
| **context** | `agentcontext.context` | `build_context` → cited `ContextPackage` |

Everything flows through one **Unified Document Model** (`Document` → `Block` → `Provenance`), so a chunk returned to an agent can always be traced back to an exact source location. Each stage is a plugin registered in `agentcontext.core.registry`, so new parsers, chunkers, embedders, and retrievers drop in without touching the core.

## License

Apache-2.0
