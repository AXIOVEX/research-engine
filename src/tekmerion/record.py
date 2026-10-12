"""Append-only, hash-chained event store (WS4; DN-004).

Design rules implemented here, each traceable to the architecture:
- Append-only: events are never mutated or deleted by this API (WS4 §1).
- Single sequencing point: appends serialize through one lock per store
  instance and carry a monotonic ``seq`` (RED-TEAM-01 RT-2).
- Hash chain: every event carries ``prev_hash`` and ``hash`` =
  SHA-256(prev_hash + canonical JSON of the event body), so alteration,
  insertion, deletion, or reordering breaks verification at that point.
- No redaction, ever (DN-005, 2026-10-11): tombstone masking was a soft
  delete and is removed. Withdrawal is expressed by appending new
  snapshots marked dead (score 0.0, reason on the record) — in the
  Axiomere record layer this store is being migrated to (DN-007).
  Projections and exports here return events exactly as stored.
- Replay: projections are rebuilt by folding events in order; a log that
  fails verification replays as INVALID, never as partial truth (WS3 §1).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

GENESIS_HASH = "0" * 64


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _event_hash(prev_hash: str, body: dict[str, Any]) -> str:
    return hashlib.sha256((prev_hash + _canonical(body)).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class VerificationResult:
    ok: bool
    events: int = 0
    break_seq: int | None = None
    reason: str | None = None  # e.g. "hash-mismatch", "seq-gap", "fork", "prev-link-mismatch", "bad-json"


def verify_lines(lines: Iterable[str]) -> VerificationResult:
    """Verify a hash chain from raw JSONL lines. Standalone by design:
    an auditor needs nothing but the log file (WS4 §3, OQ-4.2)."""
    prev_hash = GENESIS_HASH
    expected_seq = 1
    seen_seqs: set[int] = set()
    count = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        count += 1
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            return VerificationResult(False, count, expected_seq, "bad-json")
        seq = ev.get("seq")
        if seq in seen_seqs:
            return VerificationResult(False, count, seq, "fork")
        seen_seqs.add(seq)
        if seq != expected_seq:
            return VerificationResult(False, count, seq, "seq-gap")
        if ev.get("prev_hash") != prev_hash:
            return VerificationResult(False, count, seq, "prev-link-mismatch")
        body = {k: v for k, v in ev.items() if k != "hash"}
        if ev.get("hash") != _event_hash(prev_hash, body):
            return VerificationResult(False, count, seq, "hash-mismatch")
        prev_hash = ev["hash"]
        expected_seq += 1
    return VerificationResult(True, count)


def verify_log(path: str | Path) -> VerificationResult:
    with open(path, "r", encoding="utf-8") as f:
        return verify_lines(f)


class EventStore:
    """One study's event log. All appends go through this class, which is
    the single sequencing point for the log (RT-2)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._seq, self._head = self._recover()

    def _recover(self) -> tuple[int, str]:
        if not self.path.exists():
            return 0, GENESIS_HASH
        result = verify_log(self.path)
        if not result.ok:
            raise ValueError(
                f"event log {self.path} fails verification: {result.reason} at seq {result.break_seq}"
            )
        seq, head = 0, GENESIS_HASH
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    ev = json.loads(line)
                    seq, head = ev["seq"], ev["hash"]
        return seq, head

    def append(self, event_type: str, payload: dict[str, Any], actor: str) -> dict[str, Any]:
        """Append one event, fsync, and return the stored event record."""
        with self._lock:
            body = {
                "seq": self._seq + 1,
                "type": event_type,
                "ts": _now(),
                "actor": actor,
                "payload": payload,
                "prev_hash": self._head,
            }
            ev = {**body, "hash": _event_hash(self._head, body)}
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(_canonical(ev) + "\n")
                f.flush()
                os.fsync(f.fileno())
            self._seq, self._head = ev["seq"], ev["hash"]
            return ev

    def events(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)

    def verify(self) -> VerificationResult:
        if not self.path.exists():
            return VerificationResult(True, 0)
        return verify_log(self.path)


@dataclass
class StudyProjection:
    """Derived state, rebuilt from the log. Disposable by definition."""

    valid: bool
    claims: dict[str, dict[str, Any]] = field(default_factory=dict)
    verdicts: dict[str, dict[str, Any]] = field(default_factory=dict)
    event_count: int = 0


def replay(path: str | Path) -> StudyProjection:
    """Fold a log into its projection. An unverifiable log replays as
    INVALID with no claims/verdicts surfaced (WS3 §1: a defective run
    issues no claim verdicts)."""
    result = verify_log(path)
    if not result.ok:
        return StudyProjection(valid=False, event_count=result.events)
    proj = StudyProjection(valid=True)
    store_events: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                store_events.append(json.loads(line))
    for ev in store_events:
        proj.event_count += 1
        payload = ev["payload"]
        if ev["type"] == "claim.registered":
            proj.claims[payload.get("claim_id", f"seq-{ev['seq']}")] = payload
        elif ev["type"] == "verdict.issued":
            proj.verdicts[payload.get("claim_id", f"seq-{ev['seq']}")] = payload
    return proj


def export_events(path: str | Path) -> list[dict[str, Any]]:
    """Events as they may leave the system: exactly as stored (DN-005 —
    exports never mask; a withdrawn record travels with its dead
    snapshot and reason visible, not erased)."""
    raw: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                raw.append(json.loads(line))
    return raw
