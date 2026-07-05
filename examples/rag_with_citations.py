"""RAG with citations in ~60 lines — no dependencies, no API keys.

Shows the point of provenance-first parsing: retrieved context arrives with
page/section receipts, so whatever your LLM answers can be traced back.

Run:  python examples/rag_with_citations.py path/to/document.pdf "your question"
      (works with .pdf/.docx/.html/.md/.txt; defaults to a demo doc + query)
"""

from __future__ import annotations

import re
import sys
import tempfile

from agentcontext import Document

DEMO_DOC = """\
# Employee Handbook

## Time Off

Employees accrue 1.75 vacation days per month, capped at 30 days.

## Remote Work

Employees may work remotely up to three days per week with manager approval.

## Equipment

The company provides a laptop and a 400 USD peripherals budget every two years.
"""


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def main() -> None:
    if len(sys.argv) >= 3:
        path, question = sys.argv[1], sys.argv[2]
    else:
        path = tempfile.mktemp(suffix=".md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(DEMO_DOC)
        question = "how many days can I work from home?"
        print(f"(demo mode — using a sample handbook)\n")

    doc = Document.parse(path)

    # 1. Chunk at block level — every chunk carries its own provenance,
    #    including the full hierarchical section path.
    chunks = [(b.text, b.provenance) for b in doc.blocks
              if b.text and b.type.value not in ("heading", "page_break")]

    # 2. Retrieve: keyword overlap stands in for your embedding model.
    q = tokenize(question)
    ranked = sorted(chunks, key=lambda c: len(q & tokenize(c[0])), reverse=True)
    top = ranked[:2]

    # 3. Build the prompt context WITH receipts.
    print(f"Question: {question}\n")
    print("Context to send to your LLM:")
    for i, (text, prov) in enumerate(top, 1):
        cite = ""
        if prov is not None:
            where = prov.section_path or (f"p.{prov.page}" if prov.page else "?")
            cite = f"  [source: {prov.source} | {where}]"
        print(f"  [{i}]{cite}\n      {text[:120]}")

    # 4. Whatever the LLM answers, you can point at the exact source location.
    best = top[0][1]
    if best is not None:
        print(f"\nAnswer is backed by: {best.source}"
              f" — section '{best.section_path}'"
              + (f", page {best.page}" if best.page else ""))


if __name__ == "__main__":
    main()
