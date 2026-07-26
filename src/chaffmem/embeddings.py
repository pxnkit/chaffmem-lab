from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from itertools import pairwise
from typing import cast

import numpy as np
from numpy.typing import NDArray

TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)


def normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


class FeatureHashEmbedding:
    """Stable signed feature hashing with no process-randomized state."""

    backend_id = "feature-hash-v1"

    def __init__(self, dimension: int = 128) -> None:
        if dimension < 8:
            raise ValueError("dimension must be at least 8")
        self.dimension = dimension

    def features(self, text: str) -> list[str]:
        normalized = normalize_text(text)
        tokens = TOKEN_PATTERN.findall(normalized)
        bigrams = [f"{left}::{right}" for left, right in pairwise(tokens)]
        return tokens + bigrams

    def encode(self, text: str) -> NDArray[np.float64]:
        vector = np.zeros(self.dimension, dtype=np.float64)
        for feature in self.features(text):
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimension
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign
        norm = float(np.linalg.norm(vector))
        if norm > 0.0:
            vector /= norm
        if not np.isfinite(vector).all():
            raise ValueError("embedding produced non-finite values")
        return vector

    def encode_list(self, text: str) -> list[float]:
        return cast(list[float], self.encode(text).tolist())

    def similarity(self, left: NDArray[np.float64], right: NDArray[np.float64]) -> float:
        if left.shape != right.shape:
            raise ValueError("embedding dimension mismatch")
        if not np.isfinite(left).all() or not np.isfinite(right).all():
            raise ValueError("similarity inputs must be finite")
        denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
        if denominator == 0.0:
            return 0.0
        score = float(np.dot(left, right) / denominator)
        if not math.isfinite(score):
            raise ValueError("similarity produced a non-finite value")
        return max(-1.0, min(1.0, score))

    def semantic_cell(self, vector: NDArray[np.float64]) -> str:
        if vector.shape != (self.dimension,):
            raise ValueError("embedding dimension mismatch")
        strongest = np.argsort(np.abs(vector))[-3:]
        parts = [f"{int(index)}:{1 if vector[index] >= 0 else -1}" for index in sorted(strongest)]
        return "|".join(parts)
