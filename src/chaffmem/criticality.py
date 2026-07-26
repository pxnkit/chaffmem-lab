from __future__ import annotations

import hashlib


def observable_criticality(content: str, importance: float, origin_id: str) -> float:
    """Produce an intentionally noisy score from observable write metadata only."""
    digest = hashlib.sha256(f"{content}|{origin_id}".encode()).digest()
    noise = int.from_bytes(digest[:8], "big") / (2**64 - 1)
    score = 0.35 + 0.35 * importance + 0.30 * noise
    return max(0.0, min(1.0, score))
