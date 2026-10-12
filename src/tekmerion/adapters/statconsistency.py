"""statcheck + GRIM-family adapter (Spec 008; pattern P7 —
reporting-consistency checkers).

Artifact = a manuscript's reported statistics. Independent checkers =
the statcheck R package (APA-style NHST extraction + p-value
recomputation) and the GRIM family (Brown & Heathers 2017; GRIMMER,
Anaya 2016). Registered scope claim = CLM-008-02: these checkers
establish internal arithmetic consistency of reported statistics
only — never that the data exist, that the analysis was appropriate,
or that conclusions follow. statcheck is silent on everything it
cannot parse, so no-flags is not a clean paper; a GRIM fail proves
inconsistency, not its cause.

**How each checker runs here, stated plainly:**

- *GRIM/GRIMMER* are published arithmetic methods, so the method is
  implemented natively in this module (exact rational arithmetic —
  no floating-point rounding guesses) and validated against the
  published worked examples in the scrutiny reference manual and
  against brute-force enumeration of actual integer datasets in the
  test suite. The checker identity recorded is the method + this
  implementation's version. GRIMMER is implemented as its core
  tests (mean consistency + sum-of-squares integrality with the
  equal-distribution lower bound). The parity/reconstruction test is
  NOT applied: the reference implementation's own maintainer flags
  that test as buggy in the current release (it can flag consistent
  values as inconsistent), and this adapter's omissions run in the
  safe direction — they can miss an inconsistency, never manufacture
  a false falsifier. SPRITE is not implemented: it is a plausibility
  display, not a check, and the scope claim already records that its
  reconstructions are never the real data.
- *statcheck* proper is an R package. No R runtime exists in this
  environment, so here the adapter consumes **recorded statcheck
  outputs** (hash-pinned, provenance-named) or records
  `not_runnable_here`. A live runner seam (Rscript + the statcheck
  package) is implemented for environments that have one. This
  module never recomputes p-values under statcheck's name: the
  recorded outputs' classifications are the checker's, and the
  extraction below (which results in a manuscript are APA-extractable,
  and how that compares to the p-value mentions present) is this
  adapter's own ingestion work, labeled as such.

**Mass mapping (CLM-008-03, registered here):** a GRIM/GRIMMER
impossibility attaches contradiction mass 1.00 with
`falsifier_observation` set — it is a mathematical impossibility
given the reported N and granularity, the hardest falsifier in the
survey; a statcheck decision error attaches partial contradiction
(0.50); a mere inconsistency attaches context only; a fully
consistent applicable set attaches support 0.50 for the
*reporting-consistency sub-claim only*.

**Applicability (CLM-008-04)** is checked before any mass: GRIM-family
checks run only on integer-granular data whose granularity is coarser
than the reporting precision (n·items < 10^decimals); otherwise the
adapter records `not_applicable` rather than a pass.
"""

from __future__ import annotations

import csv
import io
import json
import re
import shutil
import subprocess
from fractions import Fraction
from math import ceil, floor
from typing import Any, Optional

from ..claims import ClaimRegister, EvidenceItem
from .core import (
    NOT_RUNNABLE,
    RECORDED_OUTPUT,
    RUN_BY_US,
    AdapterRun,
    emit_adapter_evidence,
    ledger_run,
    sha256_hex,
)

__version__ = "1.0.0"

ADAPTER_ID = "statcheck-grim"
PATTERN = "P7"
SCOPE_CLAIM_ID = "CLM-008-02"
GRIM_CHECKER_NAME = ("GRIM (Brown & Heathers 2017) + GRIMMER core (Anaya 2016), "
                     "native implementation")
GRIM_CHECKER_VERSION = (
    f"tekmerion.adapters.statconsistency {__version__}; exact rational arithmetic; "
    "GRIMMER parity/reconstruction tests not applied (reference implementation's "
    "test 3 is flagged buggy by its maintainer — omissions can miss, never "
    "manufacture, an inconsistency); SPRITE not implemented (plausibility "
    "display, not a check)")
STATCHECK_CHECKER_NAME = "statcheck (R package, Nuijten et al.)"


# ------------------------------------------------------------- GRIM (exact)

def _decimals(value_str: str) -> int:
    s = value_str.strip()
    return len(s.split(".", 1)[1]) if "." in s else 0


def _rounding_interval(value_str: str) -> tuple[Fraction, Fraction]:
    """The interval of true values that round to the reported value
    at its reported precision. Closed at both ends: ties are accepted
    either way, mirroring scrutiny's default (the reporting software's
    tie convention is unknowable, so a tie is not an inconsistency)."""
    x = Fraction(value_str.strip())
    half = Fraction(1, 2 * 10 ** _decimals(value_str))
    return x - half, x + half


def grim_consistent(mean_str: str, n: int, items: int = 1) -> bool:
    """The GRIM test (Brown & Heathers 2017): with integer-granular
    data (each score a multiple of 1/items), the reported mean is
    consistent iff some integer total T has T/(n·items) rounding to
    the reported mean at its reported precision."""
    lo, hi = _rounding_interval(mean_str)
    denom = n * items
    return ceil(lo * denom) <= floor(hi * denom)


def _grim_totals(mean_str: str, n: int, items: int = 1) -> list[int]:
    lo, hi = _rounding_interval(mean_str)
    denom = n * items
    return list(range(ceil(lo * denom), floor(hi * denom) + 1))


def _min_sum_of_squares(total: int, n: int) -> int:
    """Smallest possible Σx² for n integers summing to `total`
    (values as equal as possible) — the GRIMMER lower bound."""
    q, r = divmod(total, n)
    return r * (q + 1) ** 2 + (n - r) * q ** 2


def grimmer_core_consistent(mean_str: str, sd_str: str, n: int) -> tuple[bool, dict[str, Any]]:
    """GRIMMER core tests (Anaya 2016), single-item integer data:
    (1) the mean passes GRIM; (2) some GRIM-consistent total S and
    some integer sum-of-squares Q ≥ the equal-distribution minimum
    for S reproduce the reported SD at its reported precision
    (sample SD, denominator n−1). All arithmetic is exact
    (Fraction); the SD comparison is squared, never rooted."""
    detail: dict[str, Any] = {"tests_applied": ["grim_mean", "sum_of_squares_integrality"]}
    totals = _grim_totals(mean_str, n, items=1)
    detail["grim_consistent_totals"] = totals
    if not totals:
        detail["failed"] = "grim_mean"
        return False, detail
    if n < 2:
        detail["failed"] = "n_too_small_for_sd"
        return False, detail
    sd_lo, sd_hi = _rounding_interval(sd_str)
    sd_lo = max(sd_lo, Fraction(0))
    for s_total in totals:
        q_min = _min_sum_of_squares(s_total, n)
        base = Fraction(s_total * s_total, n)
        q_lo = ceil((n - 1) * sd_lo ** 2 + base)
        q_hi = floor((n - 1) * sd_hi ** 2 + base)
        if max(q_lo, q_min) <= q_hi:
            detail["witness"] = {"total": s_total, "sum_of_squares_at_least": q_min,
                                 "q_window": [max(q_lo, q_min), q_hi]}
            return True, detail
    detail["failed"] = "sum_of_squares_integrality"
    return False, detail


def grim_applicability(*, n: int, mean_str: str, items: int = 1,
                       data_kind: str = "integer") -> tuple[bool, str]:
    """CLM-008-04: is the GRIM-family test informative here at all?
    Uninformative regimes are recorded as not_applicable, never as
    passes — the test's power is zero when the achievable-mean
    spacing (1/(n·items)) is at or finer than the reporting
    precision (10^-decimals), and the method does not apply to
    continuous data at all."""
    if data_kind != "integer":
        return False, (f"data kind {data_kind!r} is not integer-granular; "
                       "GRIM-family tests do not apply")
    if n < 1:
        return False, "no observations"
    if n * items >= 10 ** _decimals(mean_str):
        return False, (f"granularity 1/({n}·{items}) is at or finer than the "
                       f"reporting precision 10^-{_decimals(mean_str)}: every "
                       "reportable mean is achievable, so the test has no power here")
    return True, ""


# ------------------------------------------------------- statcheck ingestion

_NHST_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("F", re.compile(
        r"\bF\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*=\s*(\d+(?:\.\d+)?)\s*,\s*"
        r"p\s*([<>=])\s*(\d+(?:\.\d+)?|\.\d+)")),
    ("t", re.compile(
        r"\bt\s*\(\s*(\d+)\s*\)\s*=\s*(-?\d+(?:\.\d+)?)\s*,\s*"
        r"p\s*([<>=])\s*(\d+(?:\.\d+)?|\.\d+)")),
    ("r", re.compile(
        r"\br\s*\(\s*(\d+)\s*\)\s*=\s*(-?(?:\d+\.\d+|\.\d+))\s*,\s*"
        r"p\s*([<>=])\s*(\d+(?:\.\d+)?|\.\d+)")),
    ("chi2", re.compile(
        r"(?:χ²|χ2|chi2|X²|X2)\s*\(\s*(\d+)\s*\)\s*=\s*(\d+(?:\.\d+)?)\s*,\s*"
        r"p\s*([<>=])\s*(\d+(?:\.\d+)?|\.\d+)")),
    ("Q", re.compile(
        r"\bQ\s*\(\s*(\d+)\s*\)\s*=\s*(\d+(?:\.\d+)?)\s*,\s*"
        r"p\s*([<>=])\s*(\d+(?:\.\d+)?|\.\d+)")),
    ("z", re.compile(
        r"\bz\s*=\s*(-?\d+(?:\.\d+)?)\s*,\s*"
        r"p\s*([<>=])\s*(\d+(?:\.\d+)?|\.\d+)")),
]
_P_MENTION = re.compile(r"\bp\s*[<>=]\s*(?:\d+(?:\.\d+)?|\.\d+)")


def extract_nhst(text: str) -> list[dict[str, Any]]:
    """Extract APA-style NHST results from manuscript text — this
    adapter's own ingestion (the same extraction problem statcheck
    solves; what the checker adds is the recomputation). Results are
    returned in text order with their raw strings, so a study can see
    exactly what was and was not extractable."""
    hits: list[tuple[int, dict[str, Any]]] = []
    for test_type, pattern in _NHST_PATTERNS:
        for m in pattern.finditer(text):
            groups = m.groups()
            if test_type == "F":
                df1, df2, stat, cmp_, p = int(groups[0]), int(groups[1]), groups[2], groups[3], groups[4]
            elif test_type == "z":
                df1 = df2 = None
                stat, cmp_, p = groups[0], groups[1], groups[2]
            else:
                df1, df2, stat, cmp_, p = int(groups[0]), None, groups[1], groups[2], groups[3]
            hits.append((m.start(), {
                "raw": m.group(0), "test_type": test_type, "df1": df1, "df2": df2,
                "statistic": stat, "p_comparison": cmp_, "p_reported": p,
            }))
    hits.sort(key=lambda h: h[0])
    return [h[1] for h in hits]


def extraction_coverage(text: str) -> dict[str, Any]:
    """CLM-008-01's coverage record: how many results were
    extractable vs present. 'Present' = p-value mentions in the text
    (any format); the gap between the two numbers is statcheck's
    known silence (non-APA formats, tables, model-based results) —
    recorded, never smoothed into a clean bill."""
    extracted = extract_nhst(text)
    present = len(_P_MENTION.findall(text))
    return {
        "extracted": len(extracted), "present_p_mentions": present,
        "extracted_results": extracted,
        "note": ("extraction covers APA-style in-text NHST results only; "
                 "p-value mentions in other formats are counted as present "
                 "but are outside the checker's reach (CLM-008-02)"),
    }


def parse_statcheck_csv(text: str) -> list[dict[str, Any]]:
    """Parse a recorded statcheck output (the R function's result
    frame as CSV). A recorded output without the computed p-values
    and the two classification columns is not a statcheck record —
    it is refused as unverifiable rather than parsed charitably."""
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise ValueError("recorded statcheck output has no rows")
    cols = {c.lower(): c for c in rows[0].keys()}
    required = ["test_type", "reported_p", "computed_p", "error", "decision_error"]
    missing = [c for c in required if c not in cols]
    if missing:
        raise ValueError(f"recorded statcheck output lacks columns: {missing}")

    def _bool(v: str) -> bool:
        return str(v).strip().upper() in ("TRUE", "T", "1", "YES")

    out: list[dict[str, Any]] = []
    for row in rows:
        out.append({
            "source": row.get(cols.get("source", ""), "") if "source" in cols else "",
            "test_type": row[cols["test_type"]],
            "df1": row.get(cols["df1"]) if "df1" in cols else None,
            "df2": row.get(cols["df2"]) if "df2" in cols else None,
            "test_value": row.get(cols["test_value"]) if "test_value" in cols else None,
            "reported_p": float(row[cols["reported_p"]]),
            "computed_p": float(row[cols["computed_p"]]),
            "error": _bool(row[cols["error"]]),
            "decision_error": _bool(row[cols["decision_error"]]),
        })
    return out


def _statcheck_findings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings = []
    for row in rows:
        if row["decision_error"]:
            kind, severity = "decision_error", "partial_contradiction"
        elif row["error"]:
            kind, severity = "inconsistency", "context"
        else:
            kind, severity = "consistent", "none"
        findings.append({**row, "kind": kind, "severity": severity})
    return findings


# ------------------------------------------------------------------- runner

class StatcheckRunner:
    """Live seam: Rscript + the statcheck R package, where an
    environment has them. Absent here (no R runtime) — absence is
    the recorded state, and the recorded-output path carries the
    build in this environment."""

    def __init__(self, rscript: Optional[str] = None) -> None:
        self.rscript = rscript or shutil.which("Rscript")

    def available(self) -> bool:
        from pathlib import Path
        return bool(self.rscript) and Path(self.rscript).exists()

    def version(self) -> Optional[str]:
        if not self.available():
            return None
        try:
            out = subprocess.run(
                [self.rscript, "-e", "cat(as.character(packageVersion('statcheck')))"],
                capture_output=True, text=True, timeout=60)
            return out.stdout.strip() or None
        except Exception:
            return None

    def run(self, text: str) -> list[dict[str, Any]]:
        """Run statcheck on manuscript text; return parsed rows.
        Raises RuntimeError on any environment failure — a failed run
        is not a finding about the manuscript."""
        if not self.available():
            raise RuntimeError("no Rscript available")
        script = (
            "args <- commandArgs(trailingOnly=TRUE); "
            "txt <- paste(readLines(args[1], warn=FALSE), collapse='\\n'); "
            "res <- statcheck::statcheck(txt, messages=FALSE); "
            "out <- data.frame(source='manuscript', test_type=res$Statistic, "
            "df1=res$df1, df2=res$df2, test_value=res$Value, "
            "reported_p=res$Reported.P.Value, computed_p=res$Computed, "
            "error=res$Error, decision_error=res$DecisionError); "
            "write.csv(out, args[2], row.names=FALSE)"
        )
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(prefix="tekmerion-statcheck-") as td:
            src, dst = Path(td) / "manuscript.txt", Path(td) / "out.csv"
            src.write_text(text, encoding="utf-8")
            proc = subprocess.run([self.rscript, "-e", script, str(src), str(dst)],
                                  capture_output=True, text=True, timeout=600)
            if proc.returncode != 0 or not dst.exists():
                raise RuntimeError(
                    f"statcheck run failed: {(proc.stderr or proc.stdout)[-400:]}")
            return parse_statcheck_csv(dst.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------- runs

def _emit_or_ledger(store, run: AdapterRun, *, claim_id, register, item, actor):
    if item is not None and claim_id is not None and register is not None:
        emit_adapter_evidence(store, run=run, register=register,
                              claim_id=claim_id, item=item, actor=actor)
    else:
        ledger_run(store, run, actor=actor)
    return run


def run_grim_family(
    store: Any,
    *,
    cases: list[dict[str, Any]],
    actor: str,
    claim_id: Optional[str] = None,
    register: Optional[ClaimRegister] = None,
    item_id: Optional[str] = None,
    origin_group: Optional[str] = None,
    data_kind: str = "integer",
) -> AdapterRun:
    """Run the GRIM-family checks over reported summary statistics.
    `cases`: [{label, mean (str — precision is data), sd (str,
    optional), n, items}]. Impossibilities are falsifier
    observations; all-not-applicable emits no evidence at all
    (CLM-008-04)."""
    artifact_bytes = json.dumps(cases, sort_keys=True).encode("utf-8")
    run = AdapterRun(
        adapter_id=ADAPTER_ID, pattern=PATTERN, scope_claim_id=SCOPE_CLAIM_ID,
        outcome=RUN_BY_US, checker_name=GRIM_CHECKER_NAME,
        checker_version=GRIM_CHECKER_VERSION,
        artifact_sha256=sha256_hex(artifact_bytes),
        artifact_label="reported summary statistics (GRIM family cases)",
        artifact_byte_length=len(artifact_bytes),
    )
    findings: list[dict[str, Any]] = []
    any_applicable = False
    any_impossible = False
    for case in cases:
        mean_str, n = str(case["mean"]), int(case["n"])
        items = int(case.get("items", 1))
        finding: dict[str, Any] = {
            "label": case.get("label", ""), "mean": mean_str,
            "sd": case.get("sd"), "n": n, "items": items,
        }
        applicable, why = grim_applicability(
            n=n, mean_str=mean_str, items=items, data_kind=data_kind)
        if not applicable:
            finding.update(kind="not_applicable", reason=why)
            findings.append(finding)
            continue
        any_applicable = True
        if not grim_consistent(mean_str, n, items):
            finding.update(kind="grim_impossibility", severity="falsifier",
                           test="GRIM")
            any_impossible = True
            findings.append(finding)
            continue
        sd_str = case.get("sd")
        if sd_str is not None and items == 1 and n >= 2:
            ok, detail = grimmer_core_consistent(mean_str, str(sd_str), n)
            finding["grimmer_detail"] = detail
            if not ok:
                finding.update(kind="grimmer_impossibility",
                               severity="falsifier", test="GRIMMER core")
                any_impossible = True
                findings.append(finding)
                continue
        elif sd_str is not None:
            finding["grimmer_detail"] = {
                "tests_applied": [],
                "note": "GRIMMER core implemented for single-item integer data; "
                        "this case was GRIM-checked only"}
        finding.update(kind="consistent", severity="none")
        findings.append(finding)
    run.findings = findings
    run.raw_output_sha256 = sha256_hex(
        json.dumps(findings, sort_keys=True).encode("utf-8"))
    run.extra["cases"] = cases
    run.extra["data_kind"] = data_kind

    item: Optional[EvidenceItem] = None
    if any_impossible:
        item = EvidenceItem(
            item_id=item_id or "EV-GRIM", origin_group=origin_group or "EVG-GRIM",
            stance="contradicts", support_mass=0.0, contradiction_mass=1.00,
            could_falsify=True, falsifier_observation=True,
            verified=True, hosted_ok=True, metadata_only=False)
    elif any_applicable:
        item = EvidenceItem(
            item_id=item_id or "EV-GRIM", origin_group=origin_group or "EVG-GRIM",
            stance="supports", support_mass=0.50, contradiction_mass=0.0,
            could_falsify=True, falsifier_observation=False,
            verified=True, hosted_ok=True, metadata_only=False)
    else:
        run.extra["evidence_withheld"] = (
            "every case was not_applicable — an uninformative regime is "
            "recorded, never converted into a pass (CLM-008-04)")
    return _emit_or_ledger(store, run, claim_id=claim_id, register=register,
                           item=item, actor=actor)


def run_statcheck(
    store: Any,
    *,
    text: Optional[str] = None,
    actor: str,
    claim_id: Optional[str] = None,
    register: Optional[ClaimRegister] = None,
    item_id: Optional[str] = None,
    origin_group: Optional[str] = None,
    runner: Optional[StatcheckRunner] = None,
    recorded_output: Optional[bytes] = None,
    recorded_provenance: Optional[str] = None,
) -> AdapterRun:
    """Run (or ingest the recorded output of) statcheck over a
    manuscript. Decision errors attach partial contradiction;
    inconsistencies attach context; a fully consistent extracted set
    attaches capped support to the reporting-consistency sub-claim —
    always with the extraction coverage in the record (CLM-008-01)."""
    run = AdapterRun(
        adapter_id=ADAPTER_ID, pattern=PATTERN, scope_claim_id=SCOPE_CLAIM_ID,
        outcome=NOT_RUNNABLE, checker_name=STATCHECK_CHECKER_NAME,
        checker_version=None, artifact_sha256=None,
        artifact_label="manuscript text" if text is not None else "recorded statcheck output",
    )
    if text is not None:
        text_bytes = text.encode("utf-8")
        run.artifact_sha256 = sha256_hex(text_bytes)
        run.artifact_byte_length = len(text_bytes)
        run.extra["coverage"] = extraction_coverage(text)
    rows: Optional[list[dict[str, Any]]] = None
    runner = runner if runner is not None else StatcheckRunner()
    if text is not None and runner.available():
        try:
            rows = runner.run(text)
            run.outcome = RUN_BY_US
            version = runner.version()
            run.checker_version = f"statcheck {version}" if version else "statcheck (R package)"
        except RuntimeError as exc:
            run.reason = f"live statcheck run failed: {exc}"
    if rows is None and recorded_output is not None:
        try:
            rows = parse_statcheck_csv(recorded_output.decode("utf-8", errors="replace"))
        except ValueError as exc:
            run.extra["output_unverifiable"] = str(exc)
            ledger_run(store, run, actor=actor)
            return run
        run.outcome = RECORDED_OUTPUT
        run.raw_output_sha256 = sha256_hex(recorded_output)
        if run.artifact_sha256 is None:
            run.artifact_sha256 = sha256_hex(recorded_output)
            run.artifact_byte_length = len(recorded_output)
        if recorded_provenance:
            run.checker_version = (f"statcheck (R package), recorded output — "
                                   f"{recorded_provenance}")
            run.extra["recorded_provenance"] = recorded_provenance
        if "coverage" not in run.extra:
            run.extra["coverage"] = {
                "extracted": len(rows), "present_p_mentions": len(rows),
                "note": ("coverage as recorded by the source run; the "
                         "manuscript was not supplied to this ingestion")}
    if rows is None:
        if not run.reason:
            run.reason = (
                "no R runtime with the statcheck package in this environment "
                "and no recorded statcheck output supplied — statcheck's "
                "recomputation is the checker's, and this adapter does not "
                "recompute p-values under its name")
        ledger_run(store, run, actor=actor)
        return run

    run.findings = _statcheck_findings(rows)
    if run.raw_output_sha256 is None:
        run.raw_output_sha256 = sha256_hex(
            json.dumps(run.findings, sort_keys=True).encode("utf-8"))
    decision_errors = [f for f in run.findings if f["kind"] == "decision_error"]
    inconsistencies = [f for f in run.findings if f["kind"] == "inconsistency"]
    run.extra["summary"] = {
        "results": len(rows), "decision_errors": len(decision_errors),
        "inconsistencies": len(inconsistencies),
        "consistent": len(rows) - len(decision_errors) - len(inconsistencies),
    }

    item: Optional[EvidenceItem] = None
    if decision_errors:
        item = EvidenceItem(
            item_id=item_id or "EV-SC", origin_group=origin_group or "EVG-SC",
            stance="contradicts", support_mass=0.0, contradiction_mass=0.50,
            could_falsify=True, falsifier_observation=False,
            verified=True, hosted_ok=True, metadata_only=False)
    elif inconsistencies:
        item = EvidenceItem(
            item_id=item_id or "EV-SC", origin_group=origin_group or "EVG-SC",
            stance="contextual", support_mass=0.0, contradiction_mass=0.0,
            could_falsify=True, falsifier_observation=False,
            verified=True, hosted_ok=True, metadata_only=False)
    elif rows:
        item = EvidenceItem(
            item_id=item_id or "EV-SC", origin_group=origin_group or "EVG-SC",
            stance="supports", support_mass=0.50, contradiction_mass=0.0,
            could_falsify=True, falsifier_observation=False,
            verified=True, hosted_ok=True, metadata_only=False)
    if (item is not None and claim_id is not None and register is not None
            and not run.checker_version):
        # A recorded output without provenance cannot name its checker
        # version — findings stand, evidence is withheld (Spec 004 §2).
        run.extra["evidence_withheld"] = (
            "recorded statcheck output supplied without provenance; the "
            "record cannot name the checker + version an evidence item "
            "must carry")
        item = None
    return _emit_or_ledger(store, run, claim_id=claim_id, register=register,
                           item=item, actor=actor)
