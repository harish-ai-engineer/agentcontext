"""Benchmark harness: score parsers against the golden corpus.

Metrics (per the v0.1 spec, section "Quality bar & evaluation"):

  text        text extraction accuracy (normalized similarity vs golden)
  structure   heading level+order accuracy
  tables      table cell accuracy (% of golden cells recovered)
  provenance  sampled blocks with correct section_path / page

Adapters: agentcontext (always), markitdown / docling (scored when
installed, reported as "not installed" otherwise). Numbers are published
even where we lose — trust is the product.

Usage:  python benchmarks/harness.py [--json results.json] [--update-benchmarks-md]
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "corpus")
GOLDEN = os.path.join(CORPUS, "golden")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))


# ------------------------------------------------------------ normalizing --

def norm(s: str) -> str:
    return " ".join(s.split())


def md_to_plain(md: str) -> str:
    """Strip markdown syntax so baseline output is compared on content only."""
    out = []
    for line in md.splitlines():
        stripped = line.strip()
        if not stripped or set(stripped) <= {"-", "|", ":", " "}:  # table rules / hr
            continue
        if stripped.startswith("|"):  # table row -> handled by table metric
            continue
        stripped = re.sub(r"^#{1,6}\s+", "", stripped)
        stripped = re.sub(r"^[-*+]\s+", "", stripped)
        stripped = re.sub(r"^>\s?", "", stripped)
        stripped = stripped.replace("**", "").replace("__", "")
        out.append(stripped)
    return norm(" ".join(out))


def md_headings(md: str) -> list[tuple[int, str]]:
    heads = []
    in_code = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if m:
            heads.append((len(m.group(1)), norm(m.group(2))))
    return heads


def md_tables(md: str) -> list[list[list[str]]]:
    tables, current = [], []
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= {"-", ":", " "} for c in cells):  # separator row
                continue
            current.append(cells)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


# --------------------------------------------------------------- adapters --

class Result:
    """Extraction result in comparable form. provenance_of returns
    (section_path, page) for the block starting with a text prefix, or None
    if the parser doesn't track provenance."""

    def __init__(self, text, headings, tables, provenance_of=None):
        self.text = text
        self.headings = headings
        self.tables = tables
        self.provenance_of = provenance_of


def run_agentcontext(path: str) -> Result:
    import agentcontext as ac

    doc = ac.parse(path)
    content_blocks = [b for b in doc.blocks
                      if b.text and b.type not in (ac.BlockType.TABLE, ac.BlockType.PAGE_BREAK)]
    text = norm(" ".join(b.text for b in content_blocks))
    headings = [(b.level or 1, norm(b.text)) for b in doc.blocks
                if b.type == ac.BlockType.HEADING]
    tables = [t.to_rows() for t in doc.tables]

    def provenance_of(prefix: str):
        for b in doc.blocks:
            if norm(b.text).startswith(prefix) and b.provenance is not None:
                return b.provenance.section_path, b.provenance.page
        return None

    return Result(text, headings, tables, provenance_of)


def run_markitdown(path: str) -> Result:
    from markitdown import MarkItDown

    md = MarkItDown().convert(path).text_content
    return Result(md_to_plain(md), md_headings(md), md_tables(md), None)


def run_docling(path: str) -> Result:
    from docling.document_converter import DocumentConverter

    md = DocumentConverter().convert(path).document.export_to_markdown()
    return Result(md_to_plain(md), md_headings(md), md_tables(md), None)


ADAPTERS = {
    "agentcontext": run_agentcontext,
    "markitdown": run_markitdown,
    "docling": run_docling,
}


# ----------------------------------------------------------------- scoring --

def score(result: Result, golden: dict) -> dict:
    s: dict = {}
    s["text"] = difflib.SequenceMatcher(None, result.text, norm(golden["text"])).ratio()

    gold_heads = [(lvl, norm(t)) for lvl, t in golden["headings"]]
    if gold_heads:
        sm = difflib.SequenceMatcher(None, result.headings, gold_heads)
        s["structure"] = sm.ratio()
    else:
        s["structure"] = None  # no headings to get right

    gold_tables = golden.get("tables") or []
    if gold_tables:
        total = sum(len(r) for t in gold_tables for r in t)
        matched = 0
        for gt, et in zip(gold_tables, result.tables):
            for grow, erow in zip(gt, et):
                matched += sum(1 for g, e in zip(grow, erow) if norm(g) == norm(e))
        s["tables"] = matched / total if total else None
    else:
        s["tables"] = None

    samples = golden.get("provenance") or []
    if samples:
        if result.provenance_of is None:
            s["provenance"] = 0.0  # parser keeps no provenance at all
        else:
            ok = 0
            for sample in samples:
                got = result.provenance_of(sample["prefix"])
                if got is None:
                    continue
                sp_ok = ("section_path" not in sample
                         or got[0] == sample["section_path"])
                pg_ok = ("page" not in sample or got[1] == sample["page"])
                ok += sp_ok and pg_ok
            s["provenance"] = ok / len(samples)
    else:
        s["provenance"] = None
    return s


def aggregate(per_doc: dict[str, dict]) -> dict:
    agg = {}
    for metric in ("text", "structure", "tables", "provenance"):
        vals = [d[metric] for d in per_doc.values()
                if isinstance(d, dict) and d.get(metric) is not None]
        agg[metric] = sum(vals) / len(vals) if vals else None
    return agg


# -------------------------------------------------------------------- run --

def run() -> dict:
    docs = sorted(f for f in os.listdir(CORPUS)
                  if os.path.isfile(os.path.join(CORPUS, f)))
    results: dict = {"corpus_size": len(docs), "parsers": {}}
    for name, adapter in ADAPTERS.items():
        per_doc: dict = {}
        for doc_name in docs:
            stem = os.path.splitext(doc_name)[0]
            with open(os.path.join(GOLDEN, stem + ".json"), encoding="utf-8") as fh:
                golden = json.load(fh)
            try:
                res = adapter(os.path.join(CORPUS, doc_name))
                per_doc[doc_name] = score(res, golden)
            except ImportError:
                results["parsers"][name] = {"status": "not installed"}
                per_doc = None
                break
            except Exception as exc:  # noqa: BLE001 - a baseline crashing on a doc is a result
                # A failed parse scores zero on every metric the doc measures —
                # excluding it would silently inflate the parser's aggregate.
                per_doc[doc_name] = {
                    "error": f"{type(exc).__name__}: {exc}",
                    "text": 0.0,
                    "structure": 0.0 if golden["headings"] else None,
                    "tables": 0.0 if golden.get("tables") else None,
                    "provenance": 0.0 if golden.get("provenance") else None,
                }
        if per_doc is not None:
            errors = {k: v for k, v in per_doc.items() if "error" in v}
            results["parsers"][name] = {
                "status": "ok",
                "aggregate": aggregate(per_doc),
                "per_doc": per_doc,
                "errors": len(errors),
            }
    return results


def fmt(v) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.1f}%"


def to_table(results: dict) -> str:
    lines = [
        "| Parser | Text | Structure | Table cells | Provenance |",
        "|--------|------|-----------|-------------|------------|",
    ]
    for name, r in results["parsers"].items():
        if r.get("status") != "ok":
            lines.append(f"| {name} | *{r['status']}* | | | |")
            continue
        a = r["aggregate"]
        row = (f"| **{name}** | {fmt(a['text'])} | {fmt(a['structure'])} "
               f"| {fmt(a['tables'])} | {fmt(a['provenance'])} |")
        if r.get("errors"):
            row = row[:-1] + f" ({r['errors']} doc(s) errored) |"
        lines.append(row)
    return "\n".join(lines)


def update_benchmarks_md(results: dict) -> None:
    path = os.path.join(os.path.dirname(HERE), "BENCHMARKS.md")
    start, end = "<!-- BENCH:START -->", "<!-- BENCH:END -->"
    section = (
        f"{start}\n\n## Current results (seed corpus, "
        f"{results['corpus_size']} documents)\n\n"
        "Generated by `python benchmarks/harness.py --update-benchmarks-md`.\n\n"
        "**Read this honestly:** the seed corpus is synthetic and clean, so "
        "any good converter sits at or near the ceiling on text/structure/"
        "tables — parity there is expected, not a win. The differentiating "
        "column is **Provenance**: baselines score 0% because they do not "
        "track source locations at all, not because they parse badly. "
        "Real-document results (messy PDFs, scans, complex layouts) will "
        "replace these numbers as the corpus grows toward 25–50 documents.\n\n"
        + to_table(results) + f"\n\n{end}"
    )
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    if start in content:
        content = re.sub(re.escape(start) + ".*?" + re.escape(end),
                         section, content, flags=re.S)
    else:
        content = content.rstrip() + "\n\n" + section + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    print(f"updated {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", metavar="FILE", help="Write full results as JSON.")
    ap.add_argument("--update-benchmarks-md", action="store_true",
                    help="Rewrite the results section of BENCHMARKS.md.")
    args = ap.parse_args()

    results = run()
    print(to_table(results))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2, ensure_ascii=False)
        print(f"wrote {args.json}")
    if args.update_benchmarks_md:
        update_benchmarks_md(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
