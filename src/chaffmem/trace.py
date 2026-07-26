from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from .schemas import EventKind, TraceEvent

GENESIS_HASH = "0" * 64


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def calculate_event_hash(
    previous_hash: str,
    step: int,
    kind: EventKind,
    action: str,
    payload: dict[str, Any],
) -> str:
    body = canonical_json(
        {
            "previous_hash": previous_hash,
            "step": step,
            "kind": kind.value,
            "action": action,
            "payload": payload,
        }
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class TraceRecorder:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    @property
    def digest(self) -> str:
        return self.events[-1].event_hash if self.events else GENESIS_HASH

    def append(
        self,
        step: int,
        kind: EventKind,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> TraceEvent:
        safe_payload = payload or {}
        previous_hash = self.digest
        event_hash = calculate_event_hash(previous_hash, step, kind, action, safe_payload)
        event = TraceEvent(
            event_id=f"event-{len(self.events) + 1:06d}",
            step=step,
            kind=kind,
            action=action,
            payload=safe_payload,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        self.events.append(event)
        return event


def verify_trace(events: Iterable[TraceEvent]) -> tuple[bool, str]:
    previous_hash = GENESIS_HASH
    expected_index = 1
    for event in events:
        if event.event_id != f"event-{expected_index:06d}":
            return False, f"unexpected event id at position {expected_index}"
        if event.previous_hash != previous_hash:
            return False, f"previous hash mismatch at {event.event_id}"
        expected_hash = calculate_event_hash(
            previous_hash,
            event.step,
            event.kind,
            event.action,
            event.payload,
        )
        if event.event_hash != expected_hash:
            return False, f"event hash mismatch at {event.event_id}"
        previous_hash = event.event_hash
        expected_index += 1
    return True, previous_hash
