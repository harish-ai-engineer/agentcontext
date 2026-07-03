"""Parser interface and format dispatch."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from ..core.model import Document
from ..core.registry import parsers


class Parser(ABC):
    """Turn a source file into a :class:`Document`.

    Subclasses declare which extensions they handle and implement ``parse``.
    """

    name: str = "base"
    extensions: tuple[str, ...] = ()

    @abstractmethod
    def parse(self, path: str) -> Document:  # pragma: no cover - interface
        ...


def register_parser(parser: Parser) -> Parser:
    """Register a parser instance under each extension it handles."""
    for ext in parser.extensions:
        parsers.register(ext.lower().lstrip("."), parser)
    return parser


def get_parser_for(path: str) -> Parser:
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext not in parsers:
        raise ValueError(
            f"No parser registered for '.{ext}'. "
            f"Supported: {', '.join('.' + n for n in parsers.names())}"
        )
    return parsers.get(ext)


def parse(path: str) -> Document:
    """Parse any supported file into the Unified Document Model."""
    return get_parser_for(path).parse(path)
