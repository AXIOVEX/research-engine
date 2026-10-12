"""The shared adapter seam (Specs 006–008; Spec 004 §2 interface).

Every adapter run — whatever the checker — produces one `adapter.run`
event in the study ledger carrying the full provenance record, and at
most one `EvidenceItem` in the claim register. The seam enforces the
two rules no adapter may evade:

1. **Scope-claim attachment is mechanical.** An evidence item is
   emitted only through `emit_adapter_evidence`, which refuses a run
   whose registered blind-spot scope claim id is missing: evidence
   that does not name what its check cannot establish is not emitted,
   full stop.

2. **Checker honesty states** (inherited from Spec 003 §3): a check
   this process actually ran is `run_by_us`; a checker output produced
   elsewhere and ingested as a recorded artifact is
   `recorded_output`; an environment that cannot run the checker is
   `not_runnable_here`. A check that did not run is never recorded as
   run, and an unavailable checker produces a ledgered run with no
   evidence item — never silence, never a fabricated pass.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

from ..claims import ClaimRegister, EvidenceItem

# Invocation honesty states (Spec 003 §3, extended with the recorded-
# output state the adapter program needs: the output is real and
# hash-pinned, but it was produced by the checker elsewhere, not by us).
RUN_BY_US = "run_by_us"
RECORDED_OUTPUT = "recorded_output"
NOT_RUNNABLE = "not_runnable_here"
NOT_ATTEMPTED = "not_attempted"

OUTCOMES = (RUN_BY_US, RECORDED_OUTPUT, NOT_RUNNABLE, NOT_ATTEMPTED)


class AdapterEvidenceError(ValueError):
    """An adapter tried to emit evidence its record cannot support."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class AdapterRun:
    """One adapter invocation, as it is ledgered. `findings` are the
    checker's graded observations (their mapping to evidence masses is
    each adapter spec's registered table, never per-study tuning);
    `extra` carries adapter-specific record content."""

    adapter_id: str                       # e.g. "checkcif"
    pattern: str                          # "P2" | "P3" | "P7"
    scope_claim_id: str                   # the registered blind-spot claim
    outcome: str                          # one of OUTCOMES
    checker_name: str                     # who/what the independent checker is
    checker_version: Optional[str]        # version pins, as recorded by the output
    artifact_sha256: Optional[str]
    artifact_label: str = ""
    artifact_byte_length: Optional[int] = None
    raw_output_sha256: Optional[str] = None
    findings: list[dict[str, Any]] = field(default_factory=list)
    reason: str = ""                      # why outcome is not a completed check
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id, "pattern": self.pattern,
            "scope_claim_id": self.scope_claim_id, "outcome": self.outcome,
            "checker": {"name": self.checker_name, "version": self.checker_version},
            "artifact": {"sha256": self.artifact_sha256, "label": self.artifact_label,
                         "byte_length": self.artifact_byte_length},
            "raw_output_sha256": self.raw_output_sha256,
            "findings": self.findings, "reason": self.reason,
            "extra": self.extra,
        }


def ledger_run(store: Any, run: AdapterRun, *, actor: str) -> dict:
    """Append the run record without evidence (unavailable checker,
    unverifiable output, context-only record). The run happened; the
    ledger says so; no evidence item exists."""
    return store.db.append("adapter.run", run.as_dict(), actor=actor)


def emit_adapter_evidence(
    store: Any,
    *,
    run: AdapterRun,
    register: ClaimRegister,
    claim_id: str,
    item: EvidenceItem,
    actor: str,
) -> dict:
    """Ledger a completed run AND attach its evidence item — the only
    path by which adapter evidence reaches the register.

    Refusals (AdapterEvidenceError), each one a seeded-defect target:
    - the run names no registered scope claim (blind spots unattached);
    - the run's outcome is an unavailable state (no check, no evidence);
    - the run lacks the artifact hash, checker version, or raw-output
      hash an evidence item must carry (Spec 004 §2 output shape).
    """
    if not run.scope_claim_id or not run.scope_claim_id.strip():
        raise AdapterEvidenceError(
            f"{run.adapter_id}: evidence refused — no registered scope claim "
            "attached; an adapter result that does not name what its check "
            "cannot establish is not evidence (Spec 004 §2)"
        )
    if item is None:
        raise AdapterEvidenceError(f"{run.adapter_id}: evidence refused — no item")
    if run.outcome in (NOT_RUNNABLE, NOT_ATTEMPTED):
        raise AdapterEvidenceError(
            f"{run.adapter_id}: evidence refused — outcome {run.outcome} means "
            "the check did not produce output; unavailable is a state, not evidence"
        )
    if not run.artifact_sha256:
        raise AdapterEvidenceError(
            f"{run.adapter_id}: evidence refused — no artifact SHA-256 recorded"
        )
    if not run.checker_version:
        raise AdapterEvidenceError(
            f"{run.adapter_id}: evidence refused — no checker version recorded"
        )
    if not run.raw_output_sha256:
        raise AdapterEvidenceError(
            f"{run.adapter_id}: evidence refused — no raw-output SHA-256 recorded"
        )
    event = ledger_run(store, run, actor=actor)
    register.add_evidence(claim_id, item)
    return event


def adapter_runs(store: Any, adapter_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Replay: every adapter run record in the ledger, provenance
    intact (the assertions studies and audits make over adapter work
    are replays of this list, never of in-memory state)."""
    out = []
    for event in store.events():
        if event["type"] != "adapter.run":
            continue
        payload = event["payload"]
        if adapter_id and payload["adapter_id"] != adapter_id:
            continue
        out.append(payload)
    return out
