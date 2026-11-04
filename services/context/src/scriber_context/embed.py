import hashlib
import math
import re
from typing import Protocol

from ollama import Client


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    def __init__(self, dim: int = 256) -> None:
        self.name = f"hash-{dim}"
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in re.findall(r"\w+", text.lower()):
            h = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "little")
            vector[h % self.dim] += 1.0 if (h >> 32) & 1 else -1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]


class OllamaEmbedder:
    def __init__(self, model: str = "qwen3-embedding:0.6b", host: str = "http://127.0.0.1:11434", dim: int = 1024, batch: int = 32) -> None:
        self.name = model
        self.dim = dim
        self.batch = batch
        self._client = Client(host=host)

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            response = self._client.embed(model=self.name, input=texts[i : i + self.batch], dimensions=self.dim)
            out.extend([float(x) for x in v] for v in response.embeddings)
        if any(len(v) != self.dim for v in out):
            raise ValueError(f"{self.name} returned vectors that are not {self.dim}-dimensional")
        return out


def cosine(a: list[float], b: list[float]) -> float:
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / norm if norm else 0.0
