"""Verdict service (Spec 002 Phase 3; WS3).

The taxonomy is mechanical (WS3 §1): a verdict is a function of the
frozen registration, the evidence groups, the falsifier test, and the
controls. Two load-bearing properties:

- INVALID attaches to the *run*, not the claim: a defective run issues
  no claim verdicts at all.
- SUPPORTED requires the falsifier test to have been *capable* of
  firing: evidence that could not have contradicted the claim makes
  the verdict INCONCLUSIVE ("untested"), never SUPPORTED.

Scoring is interval-valued (WS3 §6): per origin group, support mass,
contradiction mass, and ignorance mass (1 - s - c). The margin test
consumes the interval of net support, [S - (C + I), (S + I) - C]
averaged over groups — never a bare point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .claims import Claim, ClaimRegister

SUPPORTED = "supported"
CONTRADICTED = "contradicted"
INCONCLUSIVE = "inconclusive"
INVALID = "invalid"


@dataclass
class ClaimVerdict:
    claim_id: str
    verdict: str
    reason: str
    groups: int
    interval: tuple[float, float]
    point: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id, "verdict": self.verdict, "reason": self.reason,
            "origin_groups": self.groups, "interval": list(self.interval),
            "point": self.point,
        }


@dataclass
class RunResult:
    run_verdict: str                       # "valid" | "invalid"
    invalid_reasons: list[str] = field(default_factory=list)
    claim_verdicts: list[ClaimVerdict] = field(default_factory=list)  # empty when invalid
    mode: str = "exploratory"
    disclosure: list[str] = field(default_factory=list)


def evaluate_claim(claim: Claim, groups: list[dict[str, Any]]) -> ClaimVerdict:
    """The one production evaluation path. Controls run through this
    same function (RT-1) — a control on a divergent path certifies
    nothing."""
    n = len(groups)
    margin = claim.margin if claim.margin is not None else 0.0
    floor = claim.sufficiency_floor if claim.sufficiency_floor is not None else 1

    if n == 0:
        return ClaimVerdict(claim.claim_id, INCONCLUSIVE, "no evidence groups", 0, (0.0, 0.0), 0.0)

    s = sum(g["support_mass"] for g in groups) / n
    c = sum(g["contradiction_mass"] for g in groups) / n
    i = max(0.0, 1.0 - s - c)
    interval = (s - (c + i), (s + i) - c)
    point = s - c

    # The falsifier test fired: the registered falsifying observation is
    # present with contradiction mass at or beyond the margin.
    if any(g["falsifier_observation"] for g in groups) and c >= margin:
        return ClaimVerdict(claim.claim_id, CONTRADICTED,
                            "falsifier test fired: registered falsifying observation present",
                            n, interval, point)

    if n < floor:
        return ClaimVerdict(claim.claim_id, INCONCLUSIVE,
                            f"evidence groups {n} below sufficiency floor {floor}",
                            n, interval, point)

    if not any(g["could_falsify"] for g in groups):
        return ClaimVerdict(claim.claim_id, INCONCLUSIVE,
                            "untested: no evidence group could have contradicted the claim",
                            n, interval, point)

    if interval[0] > margin:
        return ClaimVerdict(claim.claim_id, SUPPORTED,
                            "falsifier test ran, did not fire; interval clears the margin",
                            n, interval, point)
    if interval[1] < -margin:
        return ClaimVerdict(claim.claim_id, CONTRADICTED,
                            "interval clears the margin in the contradicting direction",
                            n, interval, point)
    return ClaimVerdict(claim.claim_id, INCONCLUSIVE,
                        "interval straddles the margin", n, interval, point)


@dataclass
class Control:
    """A control is specified by its failure mode first (WS3 §2): the
    first field is the defect it exists to catch."""
    failure_mode: str
    kind: str                     # "positive" | "negative" | "swap"
    claim: Optional[Claim] = None
    groups: Optional[list[dict[str, Any]]] = None
    expected: Optional[str] = None  # expected verdict for positive/negative
    representative_rationale: str = ""


def run_controls(controls: list[Control], store: Any = None, store_path: Optional[str] = None) -> list[str]:
    """Execute controls through the production paths. Returns failure
    reasons (empty = all controls behaved). Positive/negative controls
    evaluate synthetic claims through `evaluate_claim` itself; the swap
    control tampers a *copy* of the study ledger and requires the
    production Axiomere verifier to catch it (RT-1: same code path,
    same build, named in the record by the caller's freeze event)."""
    failures: list[str] = []
    for ctl in controls:
        if ctl.kind in ("positive", "negative"):
            if ctl.claim is None or ctl.groups is None or ctl.expected is None:
                failures.append(f"control missing claim/groups/expected: {ctl.failure_mode}")
                continue
            got = evaluate_claim(ctl.claim, ctl.groups).verdict
            if got != ctl.expected:
                failures.append(
                    f"{ctl.kind} control failed ({ctl.failure_mode}): expected {ctl.expected}, got {got}"
                )
        elif ctl.kind == "swap":
            failures.extend(_swap_control(store_path))
        else:
            failures.append(f"unknown control kind {ctl.kind}")
    return failures


def _swap_control(store_path: Optional[str]) -> list[str]:
    if not store_path:
        return ["swap control requires the study ledger path"]
    import shutil
    import tempfile
    from pathlib import Path

    import axiomere as ax

    src = Path(store_path)
    with tempfile.TemporaryDirectory() as td:
        copy = Path(td) / src.name
        shutil.copyfile(src, copy)
        text = copy.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) < 3:
            return ["swap control: ledger too short to swap provenance stubs"]
        # Exchange two events' actor fields (provenance stubs) in the copy.
        import json as _json
        e1 = _json.loads(lines[1])
        e2 = _json.loads(lines[2])
        e1["actor"], e2["actor"] = e2["actor"], e1["actor"]
        lines[1] = _json.dumps(e1, sort_keys=True, separators=(",", ":"))
        lines[2] = _json.dumps(e2, sort_keys=True, separators=(",", ":"))
        copy.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok, _count, _reason = ax.verify_file(str(copy))
        if ok:
            return ["swap control failed: provenance swap NOT detected by production verification"]
    return []


def evaluate_run(
    register: ClaimRegister,
    *,
    mode: str,
    controls: list[Control],
    chain_ok: bool = True,
    deviations: Optional[list[str]] = None,
    linked_exploratory: Optional[list[str]] = None,
    store: Any = None,
    store_path: Optional[str] = None,
) -> RunResult:
    """Run-level verdict first (WS3 §1): any control failure, unverified
    citation, chain break, or deviation from the frozen registration
    makes the run INVALID and no claim verdicts are issued."""
    invalid: list[str] = []

    if mode == "confirmation" and not register.frozen:
        invalid.append("confirmation run without a frozen registration (WS3 §4 wall)")
    if not chain_ok:
        invalid.append("hash chain failed verification on replay")
    for d in deviations or []:
        invalid.append(f"deviation from frozen registration: {d}")
    for cid, items in register.evidence.items():
        for item in items:
            if not item.verified:
                invalid.append(f"unverified citation in evidence for {cid}: {item.item_id}")
    invalid.extend(run_controls(controls, store=store, store_path=store_path))

    disclosure = list(linked_exploratory or [])
    if invalid:
        return RunResult(run_verdict=INVALID, invalid_reasons=invalid, mode=mode, disclosure=disclosure)

    verdicts = [
        evaluate_claim(claim, register.group_masses(cid))
        for cid, claim in register.claims.items()
        if claim.status != "superseded"
    ]
    return RunResult(run_verdict="valid", claim_verdicts=verdicts, mode=mode, disclosure=disclosure)
