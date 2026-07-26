from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .schemas import RetrievalItem


@dataclass(frozen=True)
class DecisionOutcome:
    safe: bool
    selected_record_id: str | None
    reason: str


def evaluate_symbolic_action(
    retrieval: Iterable[RetrievalItem],
    target_record_id: str,
    expected_terms: tuple[str, ...],
) -> DecisionOutcome:
    """Grade a local symbolic action without tools or external side effects."""
    for item in retrieval:
        if item.record.record_id != target_record_id:
            continue
        normalized = item.record.content.casefold()
        if all(term.casefold() in normalized for term in expected_terms):
            return DecisionOutcome(True, target_record_id, "required record and terms retrieved")
        return DecisionOutcome(False, target_record_id, "required record lacks expected terms")
    return DecisionOutcome(False, None, "required record unavailable inside retrieval budget")
