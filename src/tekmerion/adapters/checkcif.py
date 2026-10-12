"""checkCIF adapter (Spec 006; pattern P2 — automated validation suite).

Artifact = a CIF (+ optional structure-factor file). Independent
checker = PLATON's check.def suite, as run by a local PLATON binary or
by the IUCr checkCIF service. Registered scope claim = CLM-006-02: a
clean checkCIF result establishes only internal consistency under the
check.def suite — never chemical correctness, never genuineness (IUCr
states the absence-of-alerts caveat in every report it issues).

Invocation reality, recorded plainly: PLATON is author-distributed
(© A. L. Spek) and **not OSI-licensed**, and the IUCr checkCIF web
service is a *submission* service — automating submissions is an
operator action, not something this adapter does. So the adapter has
three honest modes:

- a local PLATON binary is present → run `platon -u` ourselves
  (`run_by_us`);
- a recorded checkCIF/PLATON output is supplied (an operator ran the
  service or PLATON and deposited the output) → parse the recorded
  bytes (`recorded_output`), hash-pinned like any other artifact;
- neither → `not_runnable_here`, ledgered, no evidence.

The alert parser is validated against recorded real outputs (IUCr
service HTML reports and PLATON `.chk` files) held as fixtures with
provenance in tests/fixtures/adapters/checkcif/.

Alert→mass mapping (CLM-006-03 — registered here, monotone, and not
tunable per study):

| alerts present | stance      | contradiction mass | falsifier observation |
|----------------|-------------|--------------------|-----------------------|
| ≥ 1 level A    | contradicts | 1.00               | yes                   |
| ≥ 1 level B    | contradicts | 0.50               | no                    |
| only C / G     | contextual  | 0                  | no                    |
| none           | contextual  | 0                  | no                    |

An A alert is checkCIF's own "serious problem" finding on the
artifact, so it is recorded as the falsifying observation for a
structure sub-claim whose falsifier names serious validation alerts.
C/G alerts are context: they neither support nor contradict, and a
clean run is likewise context only — per CLM-006-02 a pass is not
supporting evidence for a structure's correctness.
"""

from __future__ import annotations

import hashlib
import html as html_mod
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
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

ADAPTER_ID = "checkcif"
PATTERN = "P2"
SCOPE_CLAIM_ID = "CLM-006-02"
CHECKER_NAME_LIVE = "PLATON (local binary)"
CHECKER_NAME_RECORDED = "checkCIF/PLATON (recorded output)"

NO_CHECKER_REASON = (
    "no local PLATON binary found (checked $TEKMERION_PLATON_BIN and PATH); "
    "PLATON is author-distributed and not OSI-licensed, and the IUCr checkCIF "
    "web service is a submission service this adapter does not automate — "
    "supply a recorded checkCIF/PLATON output or install PLATON under its "
    "license terms (open item, Spec 006 build record)"
)


# ------------------------------------------------------------------- parser

# Alert codes: <prefix><number>_ALERT_<type>_<level>, e.g.
# PLAT417_ALERT_2_A (service HTML), STRVA01_ALERT_4_C (2-digit number),
# or the bare numeric form 048_ALERT_1_G (PLATON .chk files).
_ALERT_LINE = re.compile(
    r"((?:[A-Z]{2,6}\d{2,3}|\d{3})_ALERT_(\d)_([ABCG]))\s*(.*?)\s*$")

_CHK_VERSION = re.compile(
    r"PLATON/CHECK-\(\s*(\d+)\)\s*versus check\.def version(?: of)?\s*(\d+)")
_HTML_VERSION = re.compile(
    r"PLATON version of ([\d/]+);\s*check\.def file version of ([\d/]+)")
_HTML_SUMMARY = re.compile(r"(\d+)\s*ALERT level ([ABCG])")
_CHK_SUMMARY = re.compile(r"(\d+)\s+ALERT_Level_([A-Z])\b")


@dataclass
class CheckCIFParse:
    alerts: list[dict[str, Any]] = field(default_factory=list)
    platon_version: Optional[str] = None
    checkdef_version: Optional[str] = None
    datablock: Optional[str] = None
    syntax_errors_found: Optional[bool] = None
    reported_summary_counts: dict[str, int] = field(default_factory=dict)

    @property
    def counts(self) -> dict[str, int]:
        out = {"A": 0, "B": 0, "C": 0, "G": 0}
        for alert in self.alerts:
            out[alert["level"]] += 1
        return out

    @property
    def version_complete(self) -> bool:
        """CLM-006-01: an alert record without the checker identity and
        the PLATON + check.def versions is not evidence."""
        return bool(self.platon_version and self.checkdef_version)

    def as_dict(self) -> dict[str, Any]:
        return {
            "alert_counts": self.counts, "alerts": self.alerts,
            "platon_version": self.platon_version,
            "checkdef_version": self.checkdef_version,
            "datablock": self.datablock,
            "syntax_errors_found": self.syntax_errors_found,
            "reported_summary_counts": self.reported_summary_counts,
            "summary_agrees_with_alerts":
                (self.reported_summary_counts == self.counts)
                if self.reported_summary_counts else None,
        }


def _plain_text(text: str) -> str:
    # Tag-stripping only for actual HTML reports: PLATON .chk text uses
    # '>>>' section markers and '<' in prose, and treating those as tags
    # would eat alert lines.
    if re.search(r"<!DOCTYPE|<html[\s>]", text, re.IGNORECASE):
        text = re.sub(r"<[^>]+>", " ", text)
    return html_mod.unescape(text)


def parse_checkcif_output(text: str) -> CheckCIFParse:
    """Parse a checkCIF/PLATON report (IUCr service HTML or PLATON
    .chk plain text) into alert records. Alert lines govern; the
    report's own summary counts are recorded verbatim as a cross-check
    (they can disagree with the alert listing — PLATON's .chk summary
    is known to bucket levels differently — and the disagreement is
    part of the record, never silently resolved)."""
    plain = _plain_text(text)
    parse = CheckCIFParse()
    seen: set[tuple[str, str]] = set()
    for line in plain.splitlines():
        m = _ALERT_LINE.search(line)
        if m:
            code, atype, level, message = m.group(1), int(m.group(2)), m.group(3), m.group(4)
            message = re.sub(r"\s+", " ", message).strip()
            key = (code, message)
            if key not in seen:
                seen.add(key)
                parse.alerts.append({
                    "code": code, "alert_type": atype, "level": level,
                    "message": message,
                })
        for sm in _HTML_SUMMARY.finditer(line):
            parse.reported_summary_counts[sm.group(2)] = int(sm.group(1))
        for sm in _CHK_SUMMARY.finditer(line):
            parse.reported_summary_counts[sm.group(2)] = int(sm.group(1))
    vm = _CHK_VERSION.search(plain) or _HTML_VERSION.search(plain)
    if vm:
        parse.platon_version, parse.checkdef_version = vm.group(1), vm.group(2)
    dm = re.search(r"Datablock:\s*(\S+)", plain) or re.search(r"[Ee]ntry:\s*(\S+)", plain)
    if dm:
        parse.datablock = dm.group(1)
    if "No syntax errors found" in plain:
        parse.syntax_errors_found = False
    elif re.search(r"syntax error", plain, re.IGNORECASE):
        parse.syntax_errors_found = True
    return parse


# ------------------------------------------------------------------ mapping

def map_alert_counts(counts: dict[str, int]) -> dict[str, Any]:
    """The registered CLM-006-03 mapping, as a pure function of the
    parsed counts. `rule` names the row applied, for the record."""
    if counts.get("A", 0) >= 1:
        return {"stance": "contradicts", "support_mass": 0.0,
                "contradiction_mass": 1.00, "falsifier_observation": True,
                "rule": "A>=1: serious problem — full contradiction, falsifying observation"}
    if counts.get("B", 0) >= 1:
        return {"stance": "contradicts", "support_mass": 0.0,
                "contradiction_mass": 0.50, "falsifier_observation": False,
                "rule": "B>=1: potentially serious — partial contradiction"}
    return {"stance": "contextual", "support_mass": 0.0,
            "contradiction_mass": 0.0, "falsifier_observation": False,
            "rule": "C/G only or clean: context only — a pass is not support (CLM-006-02)"}


def checkcif_evidence(parse: CheckCIFParse, *, item_id: str,
                      origin_group: str) -> EvidenceItem:
    mapping = map_alert_counts(parse.counts)
    return EvidenceItem(
        item_id=item_id, origin_group=origin_group,
        stance=mapping["stance"], support_mass=mapping["support_mass"],
        contradiction_mass=mapping["contradiction_mass"],
        could_falsify=True, falsifier_observation=mapping["falsifier_observation"],
        verified=True, hosted_ok=True, metadata_only=False,
    )


# ------------------------------------------------------------------- runner

class PlatonRunError(RuntimeError):
    pass


class PlatonRunner:
    """Local PLATON invocation (`platon -u <cif>` writes a .chk file).

    Discovery: explicit path, else $TEKMERION_PLATON_BIN, else PATH.
    Absence is a state the caller records (`not_runnable_here`),
    never an exception and never a pass.
    """

    def __init__(self, binary: Optional[str] = None) -> None:
        self.binary = (binary or os.environ.get("TEKMERION_PLATON_BIN")
                       or shutil.which("platon"))

    def available(self) -> bool:
        return bool(self.binary) and Path(self.binary).exists()

    def run(self, cif_bytes: bytes, cif_name: str, *, timeout: int = 300) -> str:
        """Run the checker on the artifact bytes; return the .chk
        text. Raises PlatonRunError on any environment failure —
        distinguished from an alert outcome: a failed run is not a
        finding about the artifact."""
        if not self.available():
            raise PlatonRunError("no PLATON binary available")
        with tempfile.TemporaryDirectory(prefix="tekmerion-checkcif-") as td:
            work = Path(td)
            cif_path = work / cif_name
            cif_path.write_bytes(cif_bytes)
            try:
                subprocess.run(
                    [self.binary, "-u", cif_name], cwd=td,
                    stdin=subprocess.DEVNULL, capture_output=True,
                    text=True, timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                raise PlatonRunError(f"PLATON run exceeded {timeout}s") from exc
            chk_files = sorted(work.glob("*.chk"))
            if not chk_files:
                raise PlatonRunError(
                    "PLATON produced no .chk output file in the run directory")
            return chk_files[0].read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------- run

def run_checkcif(
    store: Any,
    *,
    cif_bytes: Optional[bytes] = None,
    cif_label: str = "",
    actor: str,
    claim_id: Optional[str] = None,
    register: Optional[ClaimRegister] = None,
    item_id: Optional[str] = None,
    origin_group: Optional[str] = None,
    runner: Optional[PlatonRunner] = None,
    recorded_output: Optional[bytes] = None,
    recorded_provenance: Optional[str] = None,
) -> AdapterRun:
    """Run (or ingest the recorded output of) checkCIF on a CIF and
    ledger the run; attach evidence when a study context is given and
    the record is complete (CLM-006-01). Returns the run record either
    way — an unavailable checker or an incomplete record is a state in
    the ledger, not an exception and not a pass."""
    run = AdapterRun(
        adapter_id=ADAPTER_ID, pattern=PATTERN, scope_claim_id=SCOPE_CLAIM_ID,
        outcome=NOT_RUNNABLE, checker_name=CHECKER_NAME_RECORDED,
        checker_version=None,
        artifact_sha256=sha256_hex(cif_bytes) if cif_bytes is not None else None,
        artifact_label=cif_label,
        artifact_byte_length=len(cif_bytes) if cif_bytes is not None else None,
    )
    output_text: Optional[str] = None
    runner = runner if runner is not None else PlatonRunner()
    if cif_bytes is not None and runner.available():
        run.checker_name = CHECKER_NAME_LIVE
        try:
            output_text = runner.run(cif_bytes, cif_label or "artifact.cif")
            run.outcome = RUN_BY_US
        except PlatonRunError as exc:
            run.reason = f"PLATON run failed: {exc}"
    if output_text is None and recorded_output is not None:
        output_text = recorded_output.decode("utf-8", errors="replace")
        run.outcome = RECORDED_OUTPUT
        if recorded_provenance:
            run.extra["recorded_provenance"] = recorded_provenance
    if output_text is None:
        if not run.reason:
            run.reason = NO_CHECKER_REASON
        ledger_run(store, run, actor=actor)
        return run

    output_bytes = output_text.encode("utf-8")
    run.raw_output_sha256 = hashlib.sha256(output_bytes).hexdigest()
    parse = parse_checkcif_output(output_text)
    run.findings = parse.alerts
    run.extra["parse"] = parse.as_dict()
    if parse.version_complete:
        run.checker_version = f"PLATON {parse.platon_version}; check.def {parse.checkdef_version}"

    wants_evidence = claim_id is not None and register is not None and item_id is not None
    if wants_evidence:
        if not parse.version_complete:
            run.extra["evidence_withheld"] = (
                "recorded output carries no complete PLATON/check.def version "
                "pair — an alert record without checker identity and versions "
                "is not evidence (CLM-006-01)")
            ledger_run(store, run, actor=actor)
            return run
        if cif_bytes is None:
            run.extra["evidence_withheld"] = (
                "artifact bytes not supplied — the evidence item cannot carry "
                "the CIF SHA-256 (CLM-006-01); parsed alerts stand as context")
            ledger_run(store, run, actor=actor)
            return run
        item = checkcif_evidence(parse, item_id=item_id,
                                 origin_group=origin_group or f"EVG-{item_id}")
        emit_adapter_evidence(store, run=run, register=register,
                              claim_id=claim_id, item=item, actor=actor)
        return run
    ledger_run(store, run, actor=actor)
    return run
