"""End-to-end smoke tests: parse -> chunk -> embed -> retrieve -> context.

These exercise the offline default path only, so they need no optional
dependencies and no network.
"""

from __future__ import annotations

import agentcontext as ac
from agentcontext.retrieval import VectorRetriever, cosine


SAMPLE_MD = """\
# Refund Policy

Customers may request a full refund within 30 days of purchase. Refunds are
processed to the original payment method within five business days.

# Shipping

Orders ship within two business days. International shipping can take up to
three weeks depending on customs.

# Support

Contact support@example.com for any questions about your order or account.
"""


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_parse_produces_blocks_with_provenance(tmp_path):
    path = _write(tmp_path, "doc.md", SAMPLE_MD)
    doc = ac.parse(path)
    assert doc.blocks
    headings = doc.blocks_of(ac.BlockType.HEADING)
    assert {b.text for b in headings} == {"Refund Policy", "Shipping", "Support"}
    assert all(b.provenance is None or b.provenance.source == path for b in doc.blocks)


def test_chunk_carries_provenance(tmp_path):
    path = _write(tmp_path, "doc.md", SAMPLE_MD)
    doc = ac.parse(path)
    chunks = ac.chunk(doc, strategy="section")
    assert len(chunks) == 3
    assert all(c.provenance for c in chunks)


def test_retrieve_ranks_relevant_chunk_first(tmp_path):
    path = _write(tmp_path, "doc.md", SAMPLE_MD)
    doc = ac.parse(path)
    chunks = ac.chunk(doc, strategy="section")
    results = ac.retrieve(chunks, "how do I get my money back?", k=3)
    assert results
    assert "refund" in results[0].chunk.text.lower()
    # cosine similarity is in [-1, 1]; results must be sorted descending.
    assert all(-1.0 <= r.score <= 1.0 for r in results)
    assert [r.score for r in results] == sorted((r.score for r in results), reverse=True)


def test_build_context_from_files_is_cited(tmp_path):
    path = _write(tmp_path, "doc.md", SAMPLE_MD)
    pkg = ac.build_context_from_files("refund policy", [path], k=2, chunker="section")
    assert isinstance(pkg, ac.ContextPackage)
    assert pkg.chunks
    assert pkg.citations
    assert pkg.citations[0].source == path
    assert pkg.confidence > 0.0
    prompt = pkg.to_prompt()
    assert "refund" in prompt.lower()
    assert path in prompt


def test_cosine_bounds():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_empty_retriever_returns_nothing():
    assert VectorRetriever().index([]).search("anything") == []
