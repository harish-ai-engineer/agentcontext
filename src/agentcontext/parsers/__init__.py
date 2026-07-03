"""Parser plugins. Importing this package registers all built-in parsers."""

from __future__ import annotations

from .base import Parser, get_parser_for, parse, register_parser

# Import side effects register each parser in the global registry.
from . import text  # noqa: F401  (txt, md)
from . import html  # noqa: F401
from . import pdf  # noqa: F401  (lazy: pypdf only needed at parse time)
from . import docx  # noqa: F401  (lazy: python-docx only needed at parse time)

__all__ = ["Parser", "parse", "get_parser_for", "register_parser"]
