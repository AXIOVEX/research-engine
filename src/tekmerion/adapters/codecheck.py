"""CODECHECK adapter (Spec 007; pattern P3 — independent re-execution).

Artifact = a CODECHECK certificate + the `codecheck.yml` it certifies.
Independent checker = the named, unaffiliated codechecker who
performed the re-execution. Registered scope claim = CLM-007-02: a
certificate establishes only that the named checker, at that time, in
that environment, could run the supplied material and recreate the
certified outputs. It does NOT establish correctness or scientific
validity — the certificates' own standing text says a CODECHECK does
not check whether the original computational analysis is correct —
does not cover outputs outside the certified scope, and does not
establish that the code is free of bugs that produce plausible wrong
outputs.

The engine re-executes nothing under this adapter. It consumes the
public register (codecheckers/register on GitHub — public, no account)
as evidence: register row → certificate repository → `codecheck.yml`
+ deposited certificate PDF, each byte stream hash-pinned in the run
record. A certificate record missing the named codechecker, the
certificate date, the register DOI, the certified scope, or the
certified work's identifier is **context, not evidence**
(CLM-007-01) — the run is ledgered and the gap named.

Scope honesty (CLM-007-03): the certified scope is the certificate's
manifest. Where the study supplies the work's full output list and
the manifest does not cover it, the uncertified outputs are named in
the record and the evidence mass is capped as partial-scope. Where
the study supplies no full list, completeness is unknown and the cap
applies by default — a certificate never silently becomes
whole-work coverage. Masses (adapter constants; no per-study tuning):
full-scope 0.70, partial-scope 0.40 — below what a run-by-us check
earns, because the re-execution is another party's recorded work.

Lane separation (CLM-007-04): the codechecker is a named human doing
lane-1 re-execution. The record states its lane-2 effect explicitly:
none. A certificate is never explanation, acceptance, or digestion.
"""

from __future__ import annotations

import csv
import io
import re
import urllib.request
import zlib
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..claims import ClaimRegister, EvidenceItem
from ..mathclaims import USER_AGENT
from .core import (
    NOT_ATTEMPTED,
    NOT_RUNNABLE,
    RECORDED_OUTPUT,
    AdapterRun,
    emit_adapter_evidence,
    ledger_run,
    sha256_hex,
)

ADAPTER_ID = "codecheck"
PATTERN = "P3"
SCOPE_CLAIM_ID = "CLM-007-02"

REGISTER_URL = "https://raw.githubusercontent.com/codecheckers/register/master/register.csv"
RAW_BASE = "https://raw.githubusercontent.com"
REPO_BRANCHES = ("master", "main")

FULL_SCOPE_MASS = 0.70
PARTIAL_SCOPE_MASS = 0.40

# The checker's own standing disclaimer, from the current CODECHECK
# certificate template ("About CODECHECK"), retrieved 2026-10-12.
# Recorded with every ingestion; whether the text appears in the
# individual certificate's own material is recorded per certificate
# (early certificates, e.g. 2020-001, predate the template).
CERTIFICATE_DISCLAIMER = (
    "This certificate confirms that the codechecker could independently "
    "reproduce the results of a computational analysis given the data and "
    "code from a third party. A CODECHECK does not check whether the "
    "original computational analysis is correct."
)


class RegisterError(RuntimeError):
    """The public register could not be retrieved or parsed."""


def _default_fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


# ------------------------------------------------------- codecheck.yml YAML
# codecheck.yml follows the CODECHECK metadata spec: top-level scalars,
# one nested mapping (paper), and lists of flat mappings (manifest,
# codechecker, paper.authors). This is a parser for exactly that
# subset — indentation-based, no external YAML dependency (the
# framework is stdlib-only) — not a general YAML implementation.

def _yaml_scalar(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def _split_kv(text: str) -> tuple[Optional[str], Optional[str]]:
    if text.endswith(":"):
        return text[:-1].strip(), None
    idx = text.find(": ")
    if idx == -1:
        return None, None
    return text[:idx].strip(), text[idx + 2:]


def _parse_block(lines: list[tuple[int, str]], i: int, indent: int):
    if i >= len(lines):
        return None, i
    if lines[i][1].startswith("- ") or lines[i][1] == "-":
        items: list[Any] = []
        while (i < len(lines) and lines[i][0] == indent
               and (lines[i][1].startswith("- ") or lines[i][1] == "-")):
            first = lines[i][1][2:] if lines[i][1].startswith("- ") else ""
            item_indent = indent + 2
            sub: list[tuple[int, str]] = []
            if first:
                sub.append((item_indent, first))
            i += 1
            while i < len(lines) and lines[i][0] >= item_indent:
                sub.append(lines[i])
                i += 1
            if not sub:
                items.append(None)
            elif len(sub) == 1 and _split_kv(sub[0][1])[0] is None:
                items.append(_yaml_scalar(sub[0][1]))
            else:
                obj, _ = _parse_block(sub, 0, item_indent)
                items.append(obj)
        return items, i
    obj: dict[str, Any] = {}
    last_key: Optional[str] = None
    while (i < len(lines) and lines[i][0] == indent
           and not lines[i][1].startswith("- ")):
        key, val = _split_kv(lines[i][1])
        if key is None:
            # Folded continuation of a plain scalar value.
            if last_key is not None and isinstance(obj.get(last_key), str):
                obj[last_key] = obj[last_key] + " " + lines[i][1].strip()
            i += 1
            continue
        last_key = key
        i += 1
        if val:
            obj[key] = _yaml_scalar(val)
        elif i < len(lines) and lines[i][0] > indent:
            obj[key], i = _parse_block(lines, i, lines[i][0])
        else:
            obj[key] = None
    return obj, i


def parse_codecheck_yml(text: str) -> dict[str, Any]:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, raw.strip()))
    if not lines:
        return {}
    obj, _ = _parse_block(lines, 0, lines[0][0])
    return obj if isinstance(obj, dict) else {}


# ------------------------------------------------------------- the register

def parse_register(csv_bytes: bytes) -> list[dict[str, str]]:
    try:
        text = csv_bytes.decode("utf-8")
        rows = list(csv.DictReader(io.StringIO(text)))
    except Exception as exc:
        raise RegisterError(f"register snapshot did not parse as CSV: {exc}") from exc
    if not rows or "Certificate" not in (rows[0] or {}):
        raise RegisterError("register snapshot has no Certificate column")
    return rows


@dataclass
class CertificateRecord:
    certificate_id: str
    checkers: list[dict[str, Any]] = field(default_factory=list)
    check_time: Optional[str] = None
    report_doi: Optional[str] = None
    paper: dict[str, Any] = field(default_factory=dict)
    manifest: list[dict[str, Any]] = field(default_factory=list)
    summary: Optional[str] = None
    repository: Optional[str] = None
    spec_version: Optional[str] = None
    missing: list[str] = field(default_factory=list)

    @property
    def work_identifier(self) -> Optional[str]:
        return (self.paper or {}).get("reference") or self.repository

    def as_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id, "checkers": self.checkers,
            "check_time": self.check_time, "report_doi": self.report_doi,
            "paper": self.paper, "manifest": self.manifest,
            "summary": self.summary, "repository": self.repository,
            "spec_version": self.spec_version, "missing": self.missing,
            "work_identifier": self.work_identifier,
        }


def certificate_record(yml: dict[str, Any], certificate_id: str) -> CertificateRecord:
    rec = CertificateRecord(certificate_id=certificate_id)
    rec.checkers = [c for c in (yml.get("codechecker") or []) if isinstance(c, dict)]
    rec.check_time = yml.get("check_time")
    report = yml.get("report") or ""
    m = re.search(r"10\.\d{4,9}/\S+", str(report))
    rec.report_doi = m.group(0).rstrip(").,") if m else None
    rec.paper = yml.get("paper") or {}
    rec.manifest = [e for e in (yml.get("manifest") or []) if isinstance(e, dict)]
    rec.summary = yml.get("summary")
    rec.repository = yml.get("repository")
    rec.spec_version = yml.get("version")
    # CLM-007-01: any of these missing demotes the record to context.
    if not any(c.get("name") for c in rec.checkers):
        rec.missing.append("named codechecker")
    if not rec.check_time:
        rec.missing.append("certificate date (check_time)")
    if not rec.report_doi:
        rec.missing.append("register DOI (report)")
    if not rec.manifest:
        rec.missing.append("certified scope (manifest)")
    if not rec.work_identifier:
        rec.missing.append("certified work identifier (paper reference / repository)")
    return rec


def _pdf_disclaimer_present(pdf_bytes: bytes) -> bool:
    """Whether the certificate's own material carries the standing
    disclaimer. PDF text is searched raw and in decompressed streams;
    a non-detection is recorded as such (early certificates predate
    the template), never papered over."""
    needle = b"does not check whether"
    if needle in pdf_bytes:
        return True
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", pdf_bytes, re.DOTALL):
        try:
            if needle in zlib.decompress(m.group(1)):
                return True
        except Exception:
            continue
    return False


# ---------------------------------------------------------------------- run

def ingest_codecheck_certificate(
    store: Any,
    *,
    certificate_id: str,
    actor: str,
    claim_id: Optional[str] = None,
    register: Optional[ClaimRegister] = None,
    item_id: Optional[str] = None,
    origin_group: Optional[str] = None,
    work_outputs: Optional[list[str]] = None,
    fetcher: Optional[Callable[[str], bytes]] = None,
    retrieved: Optional[str] = None,
) -> AdapterRun:
    """Ingest one CODECHECK certificate from the public register as
    scoped lane-1 evidence. Every retrieval failure and every
    incomplete record is a ledgered state with the gap named — never
    an exception escaping the study, never a fabricated certificate."""
    from datetime import date

    fetch = fetcher or _default_fetch
    run = AdapterRun(
        adapter_id=ADAPTER_ID, pattern=PATTERN, scope_claim_id=SCOPE_CLAIM_ID,
        outcome=NOT_ATTEMPTED, checker_name="CODECHECK (public register)",
        checker_version=None, artifact_sha256=None,
        artifact_label=f"CODECHECK certificate {certificate_id}",
    )
    run.extra["retrieved"] = retrieved or date.today().isoformat()
    run.extra["lane"] = "lane-1"
    run.extra["lane2_effect"] = (
        "none — a certificate is lane-1 re-execution evidence, never "
        "explanation, acceptance, or digestion (CLM-007-04)")

    try:
        register_bytes = fetch(REGISTER_URL)
        rows = parse_register(register_bytes)
    except Exception as exc:
        run.outcome = NOT_RUNNABLE
        run.reason = f"public CODECHECK register could not be retrieved/parsed: {exc}"
        ledger_run(store, run, actor=actor)
        return run
    run.extra["register_snapshot_sha256"] = sha256_hex(register_bytes)

    row = next((r for r in rows if (r.get("Certificate") or "").strip() == certificate_id),
               None)
    if row is None:
        run.reason = (f"certificate {certificate_id} is not in the public register "
                      f"(snapshot sha256 {run.extra['register_snapshot_sha256'][:12]}…)")
        ledger_run(store, run, actor=actor)
        return run
    run.extra["register_row"] = {k: v for k, v in row.items()}

    repo_field = (row.get("Repository") or "").strip()
    slug = repo_field.split("::", 1)[-1] if "::" in repo_field else repo_field
    if not slug or "/" not in slug:
        run.reason = f"register row for {certificate_id} names no GitHub repository: {repo_field!r}"
        ledger_run(store, run, actor=actor)
        return run

    yml_bytes: Optional[bytes] = None
    branch_used: Optional[str] = None
    for branch in REPO_BRANCHES:
        try:
            yml_bytes = fetch(f"{RAW_BASE}/{slug}/{branch}/codecheck.yml")
            branch_used = branch
            break
        except Exception:
            continue
    if yml_bytes is None:
        run.outcome = NOT_RUNNABLE
        run.reason = f"codecheck.yml for {certificate_id} could not be fetched from {slug}"
        ledger_run(store, run, actor=actor)
        return run
    run.extra["codecheck_yml_sha256"] = sha256_hex(yml_bytes)
    run.extra["source_repository"] = f"github.com/{slug}@{branch_used}"

    pdf_bytes: Optional[bytes] = None
    try:
        pdf_bytes = fetch(f"{RAW_BASE}/{slug}/{branch_used}/codecheck/codecheck.pdf")
    except Exception:
        pdf_bytes = None
    if pdf_bytes is not None:
        run.artifact_sha256 = sha256_hex(pdf_bytes)
        run.artifact_byte_length = len(pdf_bytes)
        run.artifact_label = f"CODECHECK certificate {certificate_id} (codecheck/codecheck.pdf)"
        run.extra["certificate_pdf_sha256"] = run.artifact_sha256
    else:
        run.artifact_sha256 = sha256_hex(yml_bytes)
        run.artifact_byte_length = len(yml_bytes)
        run.artifact_label = f"CODECHECK certificate {certificate_id} (codecheck.yml; certificate PDF not retrieved)"
        run.extra["certificate_pdf_missing"] = True

    yml = parse_codecheck_yml(yml_bytes.decode("utf-8", errors="replace"))
    rec = certificate_record(yml, certificate_id)
    run.extra["certificate"] = rec.as_dict()
    run.extra["disclaimer"] = {
        "text": CERTIFICATE_DISCLAIMER,
        "source": "CODECHECK certificate template (About CODECHECK), codecheck.org.uk",
        "present_in_certificate_material":
            _pdf_disclaimer_present(pdf_bytes) if pdf_bytes is not None else False,
    }
    run.findings = [
        {"kind": "certified_output", "file": e.get("file"), "comment": e.get("comment")}
        for e in rec.manifest
    ]
    run.outcome = RECORDED_OUTPUT
    checker_desc = "; ".join(
        c.get("name", "?") + (f" (ORCID {c['ORCID']})" if c.get("ORCID") else "")
        for c in rec.checkers) or "unnamed"
    run.checker_name = f"CODECHECK codechecker {checker_desc}"
    run.checker_version = (
        f"codecheck.yml spec {rec.spec_version}; certificate {certificate_id}; "
        f"register snapshot {run.extra['register_snapshot_sha256'][:12]}")
    run.raw_output_sha256 = run.extra["codecheck_yml_sha256"]

    # Scope assessment (CLM-007-03).
    certified_files = [e.get("file") for e in rec.manifest if e.get("file")]
    if work_outputs is None:
        uncertified: Optional[list[str]] = None
        partial = True
        scope_basis = ("certified scope is the certificate manifest; the study "
                       "supplied no full output list, so completeness is unknown "
                       "and the partial-scope cap applies (CLM-007-03)")
    else:
        uncertified = sorted(set(work_outputs) - set(certified_files))
        partial = len(uncertified) > 0
        scope_basis = ("study supplied the work's full output list; "
                       "uncertified outputs named in this record (CLM-007-03)")
    run.extra["scope"] = {
        "certified_outputs": certified_files,
        "uncertified_outputs": uncertified,
        "partial_scope": partial,
        "basis": scope_basis,
        "certificate_summary": rec.summary,
    }

    wants_evidence = claim_id is not None and register is not None and item_id is not None
    if wants_evidence:
        if rec.missing:
            run.extra["evidence_withheld"] = (
                "certificate record is incomplete — missing: "
                + ", ".join(rec.missing)
                + "; an incomplete certificate record is context, not evidence (CLM-007-01)")
            ledger_run(store, run, actor=actor)
            return run
        item = EvidenceItem(
            item_id=item_id, origin_group=origin_group or f"EVG-{item_id}",
            stance="supports",
            support_mass=PARTIAL_SCOPE_MASS if partial else FULL_SCOPE_MASS,
            contradiction_mass=0.0, could_falsify=True,
            falsifier_observation=False, verified=True, hosted_ok=True,
            metadata_only=False)
        emit_adapter_evidence(store, run=run, register=register,
                              claim_id=claim_id, item=item, actor=actor)
        return run
    ledger_run(store, run, actor=actor)
    return run
