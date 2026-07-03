"""Command-line interface: ``agentcontext <command> ...``.

Two commands cover the pipeline end-to-end:

    agentcontext parse   file.pdf --to markdown
    agentcontext context "my question" --docs a.md b.pdf --k 5 --format prompt
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__, build_context_from_files, parse


def _cmd_parse(args: argparse.Namespace) -> int:
    doc = parse(args.file)
    if args.to == "json":
        print(json.dumps(doc.to_dict(), indent=2, ensure_ascii=False))
    elif args.to == "markdown":
        print(doc.to_markdown())
    else:
        print(doc.to_text())
    return 0


def _cmd_context(args: argparse.Namespace) -> int:
    pkg = build_context_from_files(
        args.query,
        args.docs,
        k=args.k,
        embedder=args.embedder,
        chunker=args.chunker,
    )
    if args.format == "json":
        print(json.dumps(pkg.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(pkg.to_prompt())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentcontext",
        description="Turn any document into AI-ready, cited context for LLMs.",
    )
    parser.add_argument("--version", action="version", version=f"agentcontext {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser("parse", help="Parse a document into the Unified Document Model.")
    p_parse.add_argument("file", help="Path to the document to parse.")
    p_parse.add_argument(
        "--to",
        choices=["text", "markdown", "json"],
        default="markdown",
        help="Output format (default: markdown).",
    )
    p_parse.set_defaults(func=_cmd_parse)

    p_ctx = sub.add_parser("context", help="Build a cited context package for a query.")
    p_ctx.add_argument("query", help="The question / retrieval query.")
    p_ctx.add_argument(
        "--docs", nargs="+", required=True, metavar="FILE", help="Source documents."
    )
    p_ctx.add_argument("--k", type=int, default=5, help="Number of chunks to retrieve.")
    p_ctx.add_argument("--embedder", default="hashing", help="Embedder name (default: hashing).")
    p_ctx.add_argument("--chunker", default="token", help="Chunker name (default: token).")
    p_ctx.add_argument(
        "--format",
        choices=["prompt", "json"],
        default="prompt",
        help="Output format (default: prompt).",
    )
    p_ctx.set_defaults(func=_cmd_context)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
