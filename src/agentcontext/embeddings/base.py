"""Embedding provider interface + a zero-dependency default.

The default :class:`HashingEmbedder` needs no API keys and no native deps, so
the entire pipeline runs offline out of the box. Swap in a real provider
(OpenAI, local model, etc.) through the same interface for production quality.
"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

from ..core.registry import embedders

_TOKEN = re.compile(r"[a-z0-9]+")


class EmbeddingProvider(ABC):
    name = "base"
    dim = 0

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        ...

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class HashingEmbedder(EmbeddingProvider):
    """Deterministic hashed bag-of-words embedding (the "feature hashing" trick).

    Not semantically deep, but fully local, dependency-free, reproducible, and
    good enough to make retrieval work end-to-end today. Cosine similarity on
    these vectors captures lexical overlap.
    """

    name = "hashing"

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def _tokens(self, text: str) -> list[str]:
        return _TOKEN.findall(text.lower())

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for tok in self._tokens(text):
                h = hashlib.blake2b(tok.encode(), digest_size=8).digest()
                idx = int.from_bytes(h[:4], "big") % self.dim
                sign = 1.0 if h[4] & 1 else -1.0
                vec[idx] += sign
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]
            vectors.append(vec)
        return vectors


class OpenAIEmbedder(EmbeddingProvider):
    """OpenAI-compatible embeddings (optional dependency: openai).

    Works with any OpenAI-compatible endpoint via ``base_url``.
    """

    name = "openai"

    def __init__(self, model: str = "text-embedding-3-small", **client_kwargs) -> None:
        self.model = model
        self._client_kwargs = client_kwargs
        self._client = None
        self.dim = 1536

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover
                raise ImportError(
                    'OpenAI embeddings need the openai package. '
                    'Install with: pip install "agentcontext[openai]"'
                ) from exc
            self._client = OpenAI(**self._client_kwargs)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        resp = client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in resp.data]


embedders.register("hashing", HashingEmbedder())
embedders.register("openai", OpenAIEmbedder)  # class: constructed on demand


def get_embedder(name: str = "hashing", **kwargs) -> EmbeddingProvider:
    obj = embedders.get(name)
    return obj(**kwargs) if isinstance(obj, type) else obj
