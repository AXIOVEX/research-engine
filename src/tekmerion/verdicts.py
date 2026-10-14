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
    # Per-control outcomes of this run's control execution
    # (run_controls_report dicts; Spec 011 — the record the bundle's
    # run projection carries, so control results stop being ephemeral).
    control_outcomes: list[dict[str, Any]] = field(default_factory=list)


def evaluate_claim(claim: Claim, groups: list[dict[str, Any]]) -> ClaimVerdict:
    """The one production evaluation path. Controls run through this
    same function (RT-1) — a control on a divergent path certifies
    nothing."""
    n = len(groups)
    margin = claim.margin if claim.margin is not None else 0.0
    floor = claim.sufficiency_floor if claim.sufficiency_floor is not None else 1

    if n == 0:
        return ClaimVerdict(claim.claim_id, INCONCLUSIVE, "no evidence groups", 0, (0.0, 0.0), 0.0)

    if all(g.get("metadata_only", False) for g in groups):
        # RT-5 cap, mechanized: a claim whose entire supporting basis is
        # metadata-only caps at INCONCLUSIVE. A citation whose content
        # nobody checked cannot carry a claim, alone or in aggregate.
        return ClaimVerdict(claim.claim_id, INCONCLUSIVE,
                            "entire supporting basis is metadata-only — capped at inconclusive (RT-5)",
                            n, (0.0, 0.0), 0.0)

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


def fixture_identity(ctl: Control) -> Optional[dict[str, Any]]:
    """Identify a fixture control's evaluation fixture: the fixture
    claim's id plus the SHA-256 of the canonical fixture (claim +
    groups), so a reader holding a fixture can tell whether it is the
    fixture that ran. None when the fixture is incomplete — there is
    no executable fixture to identify."""
    if ctl.claim is None or ctl.groups is None:
        return None
    import hashlib
    import json as _json

    canonical = _json.dumps(
        {"claim": ctl.claim.as_dict(), "groups": ctl.groups},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {"claim_id": ctl.claim.claim_id,
            "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest()}


def run_controls_report(controls: list[Control], store: Any = None,
                        store_path: Optional[str] = None) -> list[dict[str, Any]]:
    """Execute controls through the production paths and report one
    outcome per control, in order. Positive/negative controls evaluate
    synthetic claims through `evaluate_claim` itself; the swap control
    tampers a *copy* of the study ledger and requires the production
    Axiomere verifier to catch it (RT-1: same code path, same build).

    Each outcome: {kind, failure_mode, expected, observed, passed,
    executed, fixture, detail}. `observed` is the verdict string for
    fixture controls and "detected"/"not_detected" for the swap
    control. `detail` carries the
    exact failure string `run_controls` has always produced for a
    failed control ("" when it passed) — `run_controls` below is the
    failure-projection of this report, so the legacy contract and the
    structured record are one execution, never two (Spec 011)."""
    outcomes: list[dict[str, Any]] = []
    for ctl in controls:
        base: dict[str, Any] = {"kind": ctl.kind, "failure_mode": ctl.failure_mode,
                                "expected": ctl.expected, "observed": None,
                                "passed": False, "executed": False,
                                "fixture": None, "detail": ""}
        if ctl.kind in ("positive", "negative"):
            if ctl.claim is None or ctl.groups is None or ctl.expected is None:
                base["detail"] = f"control missing claim/groups/expected: {ctl.failure_mode}"
                outcomes.append(base)
                continue
            got = evaluate_claim(ctl.claim, ctl.groups).verdict
            base.update(executed=True, observed=got, passed=got == ctl.expected,
                        fixture=fixture_identity(ctl))
            if got != ctl.expected:
                base["detail"] = (
                    f"{ctl.kind} control failed ({ctl.failure_mode}): "
                    f"expected {ctl.expected}, got {got}")
            outcomes.append(base)
        elif ctl.kind == "swap":
            report = swap_control_report(store_path)
            failures = report["failures"]
            # `expected` stays the registered value (null for swap
            # controls — a swap has no expected verdict); its operative
            # expectation, detection, is what observed/passed record.
            base.update(executed=True,
                        observed="detected" if report["detected"] else "not_detected",
                        passed=report["detected"] and not failures,
                        fixture=({"construction": report["construction"]}
                                 if report["construction"] else None),
                        detail=failures[0] if failures else "")
            outcomes.append(base)
        else:
            base["detail"] = f"unknown control kind {ctl.kind}"
            outcomes.append(base)
    return outcomes


def run_controls(controls: list[Control], store: Any = None, store_path: Optional[str] = None) -> list[str]:
    """Execute controls through the production paths. Returns failure
    reasons (empty = all controls behaved) — the failure-projection of
    `run_controls_report`, with the same strings in the same order the
    inline implementation always produced (CLM-011-02)."""
    return [o["detail"] for o in run_controls_report(controls, store=store, store_path=store_path)
            if not o["passed"]]


#: Actor written by the swap control when a ledger has no two events
#: with distinct actors to exchange (single-actor ledgers, Phase 7 fix).
SWAP_PROBE_ACTOR = "rt1-swap-probe"


def _swap_tamper(lines: list[str]) -> Optional[tuple[list[str], str]]:
    """Construct the swap control's tampered copy of a ledger's lines.

    Returns (tampered lines, construction) or None when the ledger is
    too short to tamper with. The construction is deterministic:

    - **Distinct-actor exchange (preferred):** the first event line
      and the first later event line whose `actor` differs — their
      actor fields (provenance stubs) are exchanged.
    - **Probe rewrite (single-actor ledgers):** no distinct pair
      exists, so exchanging actors would change nothing — the defect
      that made the Phase 5 demo study's control a no-op (its first
      events share one actor, so the historical fixed lines-1/2
      exchange swapped identical values and the verifier correctly
      saw an intact chain). Instead the first event's actor is
      rewritten to a probe actor: a genuine provenance forgery the
      production verifier must catch.

    Either way the tamper alters signed bytes; a verifier that still
    reports the copy intact has failed the control."""
    import json as _json

    event_lines: list[tuple[int, dict[str, Any]]] = []
    for idx, line in enumerate(lines):
        try:
            parsed = _json.loads(line)
        except ValueError:
            continue  # the AXMR magic header line, blanks
        if isinstance(parsed, dict) and "actor" in parsed:
            event_lines.append((idx, parsed))
    if len(event_lines) < 2:
        return None

    def render(event: dict[str, Any]) -> str:
        return _json.dumps(event, sort_keys=True, separators=(",", ":"))

    first_idx, first = event_lines[0]
    for idx, other in event_lines[1:]:
        if other["actor"] != first["actor"]:
            tampered = list(lines)
            swapped_first = dict(first)
            swapped_other = dict(other)
            swapped_first["actor"], swapped_other["actor"] = other["actor"], first["actor"]
            tampered[first_idx] = render(swapped_first)
            tampered[idx] = render(swapped_other)
            construction = (
                f"actor exchange between ledger lines {first_idx + 1} and {idx + 1} "
                f"(distinct actors {first['actor']!r} / {other['actor']!r})"
            )
            return tampered, construction

    tampered = list(lines)
    forged = dict(first)
    forged["actor"] = SWAP_PROBE_ACTOR
    tampered[first_idx] = render(forged)
    construction = (
        f"probe rewrite on ledger line {first_idx + 1}: single-actor ledger "
        f"(every event actor is {first['actor']!r}), so no distinct pair exists "
        f"to exchange; the first event's actor was rewritten to {SWAP_PROBE_ACTOR!r}"
    )
    return tampered, construction


def swap_control_report(store_path: Optional[str]) -> dict[str, Any]:
    """Run the swap control and report what it did: whether the
    production verifier detected the tamper, and the construction
    used (see `_swap_tamper`). `run_controls` consumes the failures;
    callers that keep records (freeze, evaluation) use this report so
    the construction is named in the record, not just the outcome."""
    if not store_path:
        return {"detected": False, "construction": "",
                "failures": ["swap control requires the study ledger path"]}
    import shutil
    import tempfile
    from pathlib import Path

    import axiomere as ax

    src = Path(store_path)
    with tempfile.TemporaryDirectory() as td:
        copy = Path(td) / src.name
        shutil.copyfile(src, copy)
        lines = copy.read_text(encoding="utf-8").splitlines()
        built = _swap_tamper(lines)
        if built is None:
            return {"detected": False, "construction": "",
                    "failures": ["swap control: ledger too short to swap provenance stubs"]}
        tampered, construction = built
        copy.write_text("\n".join(tampered) + "\n", encoding="utf-8")
        result = ax.verify_file(str(copy))
        if result.ok:
            return {"detected": False, "construction": construction,
                    "failures": ["swap control failed: provenance swap NOT detected by "
                                 f"production verification (construction: {construction})"]}
    return {"detected": True, "construction": construction, "failures": []}


def _swap_control(store_path: Optional[str]) -> list[str]:
    return swap_control_report(store_path)["failures"]


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
    outcomes = run_controls_report(controls, store=store, store_path=store_path)
    invalid.extend(o["detail"] for o in outcomes if not o["passed"])

    disclosure = list(linked_exploratory or [])
    if invalid:
        return RunResult(run_verdict=INVALID, invalid_reasons=invalid, mode=mode,
                         disclosure=disclosure, control_outcomes=outcomes)

    verdicts = [
        evaluate_claim(claim, register.group_masses(cid))
        for cid, claim in register.claims.items()
        if claim.status != "superseded"
    ]
    return RunResult(run_verdict="valid", claim_verdicts=verdicts, mode=mode,
                     disclosure=disclosure, control_outcomes=outcomes)
