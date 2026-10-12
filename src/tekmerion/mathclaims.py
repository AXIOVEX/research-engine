"""Math layer (Spec 003; DN-010 — the stage model, mechanized).

A public headline result ("X solved Y") is not one claim. It is five:
the formal statement is faithful to the original problem; the proof is
verified; the problem was genuinely open; attribution is clean; the
result is significant and explained. This module registers that
decomposition in the production claim register, ingests Lean artifacts
as hashed bytes (never as claimant descriptions), keeps digestion and
the two lanes (machine verification vs human acceptance) as separate
ledger-backed records, and composes the parent verdict so it can never
outrun its weakest load-bearing sub-claim.

Doctrine-to-mechanism map lives in DN-010; the schema and the
composition precedence are Spec 003 §2. Nothing here issues a verdict
except through tekmerion.verdicts' production path plus the
composition rule defined in the spec.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Optional

from .claims import Claim, ClaimRegister, EvidenceItem

# ---------------------------------------------------------------- constants

FAITHFUL = "faithful"
PROOF = "proof_verified"
OPEN = "genuinely_open"
ATTRIBUTION = "attribution"
SIGNIFICANCE = "significance"
ROLES = (FAITHFUL, PROOF, OPEN, ATTRIBUTION, SIGNIFICANCE)
_ROLE_SUFFIX = {FAITHFUL: "11", PROOF: "12", OPEN: "13", ATTRIBUTION: "14", SIGNIFICANCE: "15"}
_ROLE_KIND = {FAITHFUL: "interpretation", PROOF: "data", OPEN: "data",
              ATTRIBUTION: "interpretation", SIGNIFICANCE: "interpretation"}

# Compile honesty states (Spec 003 §3): a compile we did not run is
# never recorded as run, and an environment failure is not a proof failure.
RUN_BY_US = "run_by_us"
NOT_RUNNABLE = "not_runnable_here"
CLAIMED_BY_SOURCE = "claimed_by_source"
NOT_ATTEMPTED = "not_attempted"

CONTESTED = "contested"
UNEXPLAINED = "UNEXPLAINED"

USER_AGENT = "Tekmerion/0.1 (Axiovex Systems; https://axiovexsystems.com)"


class IngestionError(RuntimeError):
    """An artifact could not be fetched. That is a recorded gap in the
    study, never a detail to be filled in from narrative."""


# ------------------------------------------------------- theorem registration

def subclaim_id(parent_id: str, role: str) -> str:
    """Spec 003 §2 id scheme: parent ends in '10'; sub-claims take the
    role suffixes 11–15."""
    if not parent_id.endswith("10"):
        raise ValueError(f"theorem parent ids end in '10' (Spec 003 §2): {parent_id}")
    return parent_id[:-2] + _ROLE_SUFFIX[role]


def role_of(claim_id: str, parent_id: str) -> Optional[str]:
    for role in ROLES:
        if subclaim_id(parent_id, role) == claim_id:
            return role
    return None


_FALSIFIERS = {
    FAITHFUL: ("the pinned formal statement differs from the original problem "
               "statement in hypotheses, scope, or conclusion, adjudicated from the pinned pair"),
    PROOF: ("the artifact bytes contain sorry/admit, or fail compilation in a clean "
            "environment, or an axioms probe reports sorryAx or an unapproved axiom"),
    OPEN: ("a prior solution, or a non-open status for the problem, appears in the "
           "primary status source or in the searched literature"),
    ATTRIBUTION: ("a prior-work or priority dispute with retrieved evidence stands "
                  "registered, or prior literature the headline omits is produced"),
    SIGNIFICANCE: ("independent expert assessment retrieved that disputes the claimed "
                   "significance, or the result is shown to be a special case of a known theorem"),
}


def register_theorem(
    register: ClaimRegister,
    *,
    parent_id: str,
    headline: str,
    claimant: str,
    problem: str,
    margin: float = 0.1,
    sufficiency_floor: int = 1,
    statements: Optional[dict[str, str]] = None,
) -> dict[str, Claim]:
    """Register a theorem claim: five sub-claims first (the parent
    depends on them), then the parent. Returns {role: Claim, 'parent': Claim}."""
    out: dict[str, Claim] = {}
    sub_ids: list[str] = []
    for role in ROLES:
        cid = subclaim_id(parent_id, role)
        claim = Claim(
            claim_id=cid,
            statement=(statements or {}).get(
                role, f"[{problem}] {role} — see parent {parent_id} ({claimant})"),
            falsifier=_FALSIFIERS[role],
            kind=_ROLE_KIND[role],
            margin=margin, sufficiency_floor=sufficiency_floor,
        )
        register.register(claim)
        out[role] = claim
        sub_ids.append(cid)
    parent = Claim(
        claim_id=parent_id,
        statement=headline,
        falsifier=("a load-bearing sub-claim is contradicted, or the attribution "
                   "dispute stands unresolved (contested cap, Spec 003 §2)"),
        kind="interpretation",
        dependencies=sub_ids,
        margin=margin, sufficiency_floor=sufficiency_floor,
    )
    register.register(parent)
    out["parent"] = parent
    return out


def pin_faithfulness(store: Any, *, claim_id: str, formal_statement: str,
                     original_statement: str, original_source: str,
                     actor: str) -> dict:
    """Pin the formal statement beside the original problem statement,
    verbatim, with the original's source (Spec 003 §3). The pair — not
    anyone's paraphrase — is what the faithful sub-claim is judged from."""
    return store.db.append("math.faithfulness_pinned", {
        "claim_id": claim_id, "formal_statement": formal_statement,
        "original_statement": original_statement, "original_source": original_source,
    }, actor=actor)


def faithfulness_pair(store: Any, claim_id: str) -> Optional[dict[str, Any]]:
    found = None
    for event in store.events():
        if event["type"] == "math.faithfulness_pinned" and event["payload"]["claim_id"] == claim_id:
            found = event["payload"]
    return found


# ---------------------------------------------------------------- Lean runner

class LeanRunner:
    """Compile checks over the locally installed Lean toolchain.

    Discovery: $TEKMERION_LEAN_BIN, else the newest toolchain under
    ~/.elan/toolchains. Absence is a state, not an error: callers get
    available() == False and record claimed_by_source / not_attempted.
    """

    def __init__(self, lean_bin: Optional[str] = None) -> None:
        self.lean_bin = lean_bin or os.environ.get("TEKMERION_LEAN_BIN") or self._discover()

    @staticmethod
    def _discover() -> Optional[str]:
        home = Path.home() / ".elan" / "toolchains"
        if not home.is_dir():
            return None
        candidates = sorted(home.glob("*/bin/lean"))
        return str(candidates[-1]) if candidates else None

    def available(self) -> bool:
        return self.lean_bin is not None and Path(self.lean_bin).exists()

    def version(self) -> Optional[str]:
        if not self.available():
            return None
        out = subprocess.run([self.lean_bin, "--version"], capture_output=True,
                             text=True, timeout=60)
        return out.stdout.strip().splitlines()[0] if out.stdout.strip() else None

    def check(self, source_text: str, *, theorem_name: Optional[str] = None,
              timeout: int = 180) -> dict[str, Any]:
        """Run the toolchain on the artifact bytes. Returns a compile
        record: ran/passed/axioms where the environment carried it, or
        an environment failure distinguished from a proof failure."""
        if not self.available():
            return {"ran": False, "status": NOT_ATTEMPTED,
                    "reason": "no Lean toolchain available in this environment"}
        version = self.version()
        with tempfile.TemporaryDirectory(prefix="tekmerion-lean-") as td:
            path = Path(td) / "artifact.lean"
            path.write_text(source_text, encoding="utf-8")
            try:
                proc = subprocess.run([self.lean_bin, str(path)], capture_output=True,
                                      text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                return {"ran": False, "status": NOT_RUNNABLE,
                        "reason": f"compile exceeded {timeout}s", "toolchain": version}
            output = proc.stdout + proc.stderr
            output_hash = hashlib.sha256(output.encode("utf-8")).hexdigest()
            if proc.returncode != 0:
                if _environment_failure(output):
                    return {"ran": False, "status": NOT_RUNNABLE,
                            "reason": "artifact requires an environment not present here "
                                      "(unresolved imports); not a proof failure",
                            "toolchain": version, "exit_code": proc.returncode,
                            "output_sha256": output_hash}
                return {"ran": True, "status": RUN_BY_US, "passed": False,
                        "toolchain": version, "exit_code": proc.returncode,
                        "output_sha256": output_hash}
            record: dict[str, Any] = {"ran": True, "status": RUN_BY_US, "passed": True,
                                      "toolchain": version, "exit_code": 0,
                                      "output_sha256": output_hash}
            if theorem_name:
                record["axioms"] = self._axioms(source_text, theorem_name, timeout)
            return record

    def _axioms(self, source_text: str, theorem_name: str, timeout: int) -> dict[str, Any]:
        """Probe: append `#print axioms <name>` and read the kernel's
        answer. sorryAx here is a falsifying observation for the proof
        sub-claim — from the toolchain, not from inference."""
        with tempfile.TemporaryDirectory(prefix="tekmerion-lean-ax-") as td:
            path = Path(td) / "probe.lean"
            path.write_text(source_text.rstrip() + f"\n#print axioms {theorem_name}\n",
                            encoding="utf-8")
            try:
                proc = subprocess.run([self.lean_bin, str(path)], capture_output=True,
                                      text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                return {"status": NOT_RUNNABLE, "reason": f"axioms probe exceeded {timeout}s"}
            output = proc.stdout + proc.stderr
            m = re.search(r"depends on axioms:\s*\[([^\]]*)\]", output)
            if "does not depend on any axioms" in output:
                return {"status": RUN_BY_US, "axioms": [], "output_sha256":
                        hashlib.sha256(output.encode("utf-8")).hexdigest()}
            if m:
                axioms = [a.strip() for a in m.group(1).split(",") if a.strip()]
                return {"status": RUN_BY_US, "axioms": axioms, "output_sha256":
                        hashlib.sha256(output.encode("utf-8")).hexdigest()}
            return {"status": NOT_RUNNABLE,
                    "reason": "axioms probe produced no parseable answer",
                    "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest()}


_ENV_FAILURE_MARKERS = ("unknown package", "unknown module", "object file",
                        "does not exist", "invalid import")


def _environment_failure(output: str) -> bool:
    low = output.lower()
    return any(marker in low for marker in _ENV_FAILURE_MARKERS)


# ------------------------------------------------------------------ ingestion

@dataclass
class LeanIngestion:
    url: str
    retrieved: str                       # ISO date of retrieval
    sha256: str
    byte_length: int
    sorry_count: int
    admit_count: int
    declarations: list[dict[str, Any]] = field(default_factory=list)
    compile_status: str = NOT_ATTEMPTED
    compile_detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url, "retrieved": self.retrieved, "sha256": self.sha256,
            "byte_length": self.byte_length, "sorry_count": self.sorry_count,
            "admit_count": self.admit_count, "declarations": self.declarations,
            "compile_status": self.compile_status, "compile_detail": self.compile_detail,
        }


def _default_fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _strip_comments(text: str) -> str:
    text = re.sub(r"/-.*?-/", "", text, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", "", text)


_DECL_RE = re.compile(
    r"^\s*(theorem|lemma)\s+([A-Za-z0-9_'.]+)\s*(.*?)?:=\s*(?:by\b|where\b)?",
    re.MULTILINE | re.DOTALL)


def parse_lean(source_text: str) -> tuple[int, int, list[dict[str, Any]]]:
    """Sorry/admit counts and theorem statements, from the bytes.
    Counts run over comment-stripped text; the approximation is named
    in the ingestion record's method note, not hidden."""
    stripped = _strip_comments(source_text)
    sorry = len(re.findall(r"\bsorry\b", stripped))
    admit = len(re.findall(r"\badmit\b", stripped))
    decls: list[dict[str, Any]] = []
    for m in _DECL_RE.finditer(source_text):
        statement = re.sub(r"\s+", " ", (m.group(3) or "")).strip()
        if statement.startswith(":"):
            statement = statement[1:].strip()
        decls.append({"kind": m.group(1), "name": m.group(2),
                      "statement": statement[:2000]})
    return sorry, admit, decls


def ingest_lean_artifact(
    store: Any,
    *,
    url: str,
    actor: str,
    fetcher: Optional[Callable[[str], bytes]] = None,
    runner: Optional[LeanRunner] = None,
    theorem_name: Optional[str] = None,
    source_compile_claim: Optional[dict[str, Any]] = None,
    retrieved: Optional[str] = None,
) -> LeanIngestion:
    """Fetch, hash, parse, and (where the environment carries it)
    compile a Lean artifact; append the ingestion record to the study
    ledger. Raises IngestionError when the bytes cannot be fetched —
    an unreachable artifact is a gap the study records, never a fact
    the study invents."""
    fetch = fetcher or _default_fetch
    try:
        data = fetch(url)
    except Exception as exc:
        raise IngestionError(f"could not fetch {url}: {exc}") from exc
    text = data.decode("utf-8", errors="replace")
    sorry, admit, decls = parse_lean(text)
    name = theorem_name or (decls[0]["name"] if decls else None)

    compile_status = NOT_ATTEMPTED
    detail: dict[str, Any] = {"method": "sorry/admit counted over comment-stripped bytes"}
    if runner is not None and runner.available():
        rec = runner.check(text, theorem_name=name)
        compile_status = rec.pop("status")
        detail.update(rec)
        if compile_status == RUN_BY_US and not rec.get("passed", True):
            detail["note"] = "compile ran and failed on the artifact's own errors"
    elif source_compile_claim:
        compile_status = CLAIMED_BY_SOURCE
        detail["source_claim"] = source_compile_claim
    ingestion = LeanIngestion(
        url=url, retrieved=retrieved or date.today().isoformat(),
        sha256=hashlib.sha256(data).hexdigest(), byte_length=len(data),
        sorry_count=sorry, admit_count=admit, declarations=decls,
        compile_status=compile_status, compile_detail=detail)
    store.db.append("math.lean_ingested",
                    {"artifact": ingestion.as_dict()}, actor=actor)
    return ingestion


def proof_evidence(ingestion: LeanIngestion, *, item_id: str,
                   origin_group: str) -> EvidenceItem:
    """The proof sub-claim's evidence item, built from an ingestion —
    the masses encode *whose* check it was (Spec 003 §3):

    - sorries in the bytes, a compile that ran and failed, or sorryAx
      on the probe: the falsifying observation itself.
    - our own parse + a compile we ran clean (axioms clean where
      probed): full support, and the test could have falsified.
    - our own parse, sorry-free, but the compile is the claimant's
      word or not runnable here: partial support — our sorry count is
      ours, the kernel check is not.
    - parse only, nothing else: weak support, could not have falsified
      at kernel level.
    """
    base = {"item_id": item_id, "origin_group": origin_group}
    detail = ingestion.compile_detail
    axioms = (detail.get("axioms") or {}).get("axioms") or []
    sorry_ax = any("sorryAx" in a for a in axioms)
    ran_failed = (ingestion.compile_status == RUN_BY_US
                  and detail.get("ran") and not detail.get("passed", True))
    if ingestion.sorry_count > 0 or ingestion.admit_count > 0 or sorry_ax or ran_failed:
        return EvidenceItem(stance="contradicts", contradiction_mass=0.9,
                            could_falsify=True, falsifier_observation=True, **base)
    if ingestion.compile_status == RUN_BY_US and detail.get("passed"):
        return EvidenceItem(stance="supports", support_mass=0.9,
                            could_falsify=True, **base)
    if ingestion.compile_status in (CLAIMED_BY_SOURCE, NOT_RUNNABLE):
        return EvidenceItem(stance="supports", support_mass=0.7,
                            could_falsify=True, **base)
    return EvidenceItem(stance="supports", support_mass=0.5,
                        could_falsify=False, **base)


def ingestions_for(store: Any, url_fragment: str) -> list[dict[str, Any]]:
    return [e["payload"]["artifact"] for e in store.events()
            if e["type"] == "math.lean_ingested"
            and url_fragment in e["payload"]["artifact"]["url"]]


# ------------------------------------------------------------- openness check

def _default_status_fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, body


_STATUS_WORDS = re.compile(r"(solved|open|proved|disproved|status)", re.IGNORECASE)


def openness_check(
    store: Any,
    *,
    problem: str,
    status_url: str,
    actor: str,
    connectors: tuple = (),
    queries: tuple[str, ...] = (),
    status_fetcher: Optional[Callable[[str], tuple[int, str]]] = None,
    retrieved: Optional[str] = None,
) -> dict[str, Any]:
    """Openness evidence (Spec 003 §4): the primary status source plus
    connector literature searches (queries ledgered by run_query).
    Emits an evidence record — never a verdict."""
    from .connectors import run_query

    fetch = status_fetcher or _default_status_fetch
    code, text = fetch(status_url)
    excerpt = ""
    idx = text.lower().find(problem.lower().split()[-1].lower()) if problem else -1
    if idx >= 0:
        excerpt = re.sub(r"\s+", " ", text[max(0, idx - 200): idx + 600])[:800]
    elif text:
        excerpt = re.sub(r"\s+", " ", text[:800])
    record: dict[str, Any] = {
        "problem": problem, "status_source": status_url,
        "retrieved": retrieved or date.today().isoformat(),
        "http_status": code,
        "page_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "status_excerpt": excerpt,
        "status_words_present": sorted({m.group(1).lower()
                                        for m in _STATUS_WORDS.finditer(excerpt)}),
        "searches": [],
    }
    for connector in connectors:
        for q in queries:
            items = run_query(store, connector, q, actor=actor, limit=10)
            record["searches"].append({
                "connector": connector.name, "query": q,
                "results": len(items),
                "top_titles": [i.title for i in items[:3]],
            })
    store.db.append("math.openness_checked", record, actor=actor)
    return record


# ------------------------------------------------------- attribution disputes

def register_dispute(
    store: Any,
    *,
    claim_id: str,
    parties: list[str],
    positions: dict[str, str],
    evidence: dict[str, list[dict[str, Any]]],
    actor: str,
) -> dict:
    """Register an attribution dispute with BOTH sides' retrieved
    evidence (DN-010 point 4). A dispute record carrying fewer than
    two evidenced parties is refused: a one-sided dispute record would
    be a verdict in disguise."""
    evidenced = [p for p in parties if evidence.get(p)]
    if len(evidenced) < 2:
        raise ValueError(
            "a dispute must carry retrieved evidence for at least two parties "
            f"(got evidenced parties: {evidenced}) — one-sided dispute records are refused"
        )
    return store.db.append("math.attribution_dispute", {
        "claim_id": claim_id, "parties": list(parties),
        "positions": dict(positions), "evidence": evidence,
    }, actor=actor)


def resolve_dispute(store: Any, *, claim_id: str, resolution: str,
                    evidence_ref: str, actor: str) -> dict:
    """A resolution is a further append, never an edit (Article IV)."""
    return store.db.append("math.attribution_resolved", {
        "claim_id": claim_id, "resolution": resolution,
        "evidence_ref": evidence_ref,
    }, actor=actor)


def attribution_state(store: Any, claim_id: str) -> str:
    """State as replay: 'contested' while a dispute stands with no
    later resolution append for the claim."""
    state = "undisputed"
    for event in store.events():
        payload = event["payload"]
        if payload.get("claim_id") != claim_id:
            continue
        if event["type"] == "math.attribution_dispute":
            state = "contested"
        elif event["type"] == "math.attribution_resolved":
            state = "undisputed"
    return state


# --------------------------------------------------------- digestion and lanes

def record_digestion(store: Any, *, claim_id: str, explainer: str,
                     artifact_ref: str, actor: str,
                     claimant_explanation: bool = False) -> dict:
    """A named human's explanation of the result, as a ledger event.
    Claimant self-explanation is recordable but labeled as the
    claimant's (Spec 003 §5) — it is not independent digestion."""
    return store.db.append("math.digestion", {
        "claim_id": claim_id, "explainer": explainer,
        "artifact_ref": artifact_ref,
        "claimant_explanation": claimant_explanation,
    }, actor=actor)


def record_acceptance(store: Any, *, claim_id: str, stage: str, by: str,
                      evidence_ref: str, actor: str) -> dict:
    """Lane-2 stage advancement (accepted / digested) on human
    evidence: a named human, an evidence reference, an append."""
    if stage not in ("accepted", "digested"):
        raise ValueError(f"acceptance stage must be accepted|digested, got {stage!r}")
    return store.db.append("math.acceptance", {
        "claim_id": claim_id, "stage": stage, "by": by,
        "evidence_ref": evidence_ref,
    }, actor=actor)


def digestion_state(store: Any, claim_id: str) -> dict[str, Any]:
    """UNEXPLAINED is an explicit state with a risk flag — verified
    but unexplained must never be a silence (DN-010 point 3)."""
    found = None
    for event in store.events():
        if event["type"] == "math.digestion" and event["payload"]["claim_id"] == claim_id:
            found = event["payload"]
    if found is None:
        return {"state": UNEXPLAINED, "risk_flag": True, "explainer": None,
                "artifact_ref": None}
    return {"state": "explained", "risk_flag": False,
            "explainer": found["explainer"], "artifact_ref": found["artifact_ref"],
            "claimant_explanation": found.get("claimant_explanation", False)}


_LANE2_ORDER = {"unexplained": 0, "explained": 1, "accepted": 2, "digested": 3}


def lane2_state(store: Any, claim_id: str) -> str:
    """Lane 2 (human-paced acceptance) derives ONLY from digestion and
    acceptance events — human evidence. Lane-1 activity (ingestions,
    compiles, citation checks) cannot move it (DN-010 point 6)."""
    stage = "unexplained"
    if digestion_state(store, claim_id)["state"] == "explained":
        stage = "explained"
    for event in store.events():
        if event["type"] == "math.acceptance" and event["payload"]["claim_id"] == claim_id:
            candidate = event["payload"]["stage"]
            if _LANE2_ORDER[candidate] > _LANE2_ORDER[stage]:
                stage = candidate
    return stage


def lane1_summary(store: Any, claim_id: str, *, proof_verdict: Optional[str],
                  ingestion_urls: tuple[str, ...] = ()) -> str:
    """Lane 1 (machine-speed verification) stated from the record:
    what was actually checked, and whose check it was."""
    states = []
    for event in store.events():
        if event["type"] != "math.lean_ingested":
            continue
        art = event["payload"]["artifact"]
        if ingestion_urls and not any(f in art["url"] for f in ingestion_urls):
            continue
        states.append(f"{art['compile_status']}, {art['sorry_count']} sorry")
    compile_part = "; ".join(states) if states else "no artifact ingested"
    verdict_part = f"proof sub-verdict: {proof_verdict}" if proof_verdict else "proof not evaluated"
    return f"checked — {verdict_part}; compile: {compile_part}"


# ---------------------------------------------------------------- composition

@dataclass
class TheoremVerdict:
    parent_id: str
    verdict: str                        # supported | contested | contradicted | inconclusive
    reason: str
    sub_verdicts: dict[str, dict[str, Any]]
    remains_not_understood: str
    lane1_verification: str
    lane2_acceptance: str
    digestion: dict[str, Any]
    attribution: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "parent_id": self.parent_id, "verdict": self.verdict,
            "reason": self.reason, "sub_verdicts": self.sub_verdicts,
            "remains_not_understood": self.remains_not_understood,
            "lane1_verification": self.lane1_verification,
            "lane2_acceptance": self.lane2_acceptance,
            "digestion": self.digestion, "attribution": self.attribution,
        }


def compose_parent(
    parent_id: str,
    sub_verdicts: dict[str, Any],
    *,
    attribution_contested: bool,
    remains_not_understood: str,
    digestion: dict[str, Any],
    lane1_verification: str,
    lane2_acceptance: str,
) -> TheoremVerdict:
    """The composition rule (Spec 003 §2), precedence as written:
    contested cap → contradicted → supported → inconclusive.
    Refuses to compose without remains_not_understood: a verdict that
    cannot say what remains not understood has not finished (point 5)."""
    if not remains_not_understood or not remains_not_understood.strip():
        raise ValueError(
            "no theorem verdict without remains_not_understood (DN-010 point 5)")
    subs = {role: (v if isinstance(v, dict) else {"verdict": v.verdict, "reason": v.reason})
            for role, v in sub_verdicts.items()}
    missing = [r for r in ROLES if r not in subs]
    if missing:
        raise ValueError(f"composition requires all five sub-verdicts; missing {missing}")

    if attribution_contested:
        verdict = CONTESTED
        reason = ("attribution dispute stands unresolved — parent capped at "
                  "contested (DN-010 point 4); sub-verdicts stand as recorded")
    elif any(s["verdict"] == "contradicted" for s in subs.values()):
        bad = [r for r, s in subs.items() if s["verdict"] == "contradicted"]
        verdict = "contradicted"
        reason = f"load-bearing sub-claim(s) contradicted: {', '.join(bad)} — the headline as stated fails"
    elif all(s["verdict"] == "supported" for s in subs.values()):
        verdict = "supported"
        reason = "all five sub-claims supported; no dispute stands"
    else:
        weak = [r for r, s in subs.items() if s["verdict"] != "supported"]
        verdict = "inconclusive"
        reason = f"sub-claim(s) not established: {', '.join(weak)}"
    return TheoremVerdict(
        parent_id=parent_id, verdict=verdict, reason=reason, sub_verdicts=subs,
        remains_not_understood=remains_not_understood,
        lane1_verification=lane1_verification, lane2_acceptance=lane2_acceptance,
        digestion=digestion,
        attribution="contested" if attribution_contested else "undisputed")


# ---------------------------------------------------------------- reliability

RELIABILITY_OUTCOMES = ("resolved_true", "resolved_false", "contested")


def record_reliability(store: Any, *, source_id: str, asserted_claim: str,
                       outcome: str, resolution_ref: str, actor: str) -> dict:
    """Seed a source's reliability record (Spec 003 §7). Identification
    discipline: an asserted claim and a resolution reference are both
    required — an unidentifiable case seeds nothing."""
    if outcome not in RELIABILITY_OUTCOMES:
        raise ValueError(f"outcome must be one of {RELIABILITY_OUTCOMES}")
    if not asserted_claim.strip() or not resolution_ref.strip():
        raise ValueError(
            "reliability seeding requires an identified claim and an identified "
            "resolution reference; unidentifiable cases seed nothing (Spec 003 §7)")
    return store.db.append("math.reliability", {
        "source_id": source_id, "asserted_claim": asserted_claim,
        "outcome": outcome, "resolution_ref": resolution_ref,
    }, actor=actor)


def reliability_record(store: Any, source_id: Optional[str] = None) -> dict[str, Any]:
    """Per-source reliability as a replay of math.reliability events:
    the factual track record, permanently on the record (Article IV)."""
    out: dict[str, Any] = {}
    for event in store.events():
        if event["type"] != "math.reliability":
            continue
        p = event["payload"]
        if source_id and p["source_id"] != source_id:
            continue
        rec = out.setdefault(p["source_id"], {"source_id": p["source_id"], "events": []})
        rec["events"].append({"asserted_claim": p["asserted_claim"],
                              "outcome": p["outcome"],
                              "resolution_ref": p["resolution_ref"],
                              "recorded_by": event["actor"]})
    return out


# -------------------------------------------------------------------- report

def theorem_report(
    store: Any,
    run_result: Any,
    parent_ids: list[str],
    *,
    remains_not_understood: dict[str, str],
    ingestion_urls: dict[str, tuple[str, ...]] | None = None,
) -> list[dict[str, Any]]:
    """Per-theorem verdict records for a completed run. A list of
    records, one per theorem claim — and deliberately nothing else:
    no aggregate tallies exist in this output (CLM-003-10). An INVALID
    run produces records that say so and carry no verdicts."""
    if run_result.run_verdict != "valid":
        return [{
            "parent_id": pid, "run": "invalid",
            "invalid_reasons": list(run_result.invalid_reasons),
            "verdict": None, "sub_verdicts": {},
        } for pid in parent_ids]
    by_id = {v.claim_id: v for v in run_result.claim_verdicts}
    records: list[dict[str, Any]] = []
    for pid in parent_ids:
        subs: dict[str, Any] = {}
        for role in ROLES:
            v = by_id.get(subclaim_id(pid, role))
            subs[role] = ({"verdict": v.verdict, "reason": v.reason}
                          if v else {"verdict": "inconclusive",
                                     "reason": "not evaluated in this run"})
        proof_v = subs[PROOF]["verdict"]
        tv = compose_parent(
            pid, subs,
            attribution_contested=attribution_state(store, subclaim_id(pid, ATTRIBUTION)) == "contested",
            remains_not_understood=remains_not_understood[pid],
            digestion=digestion_state(store, pid),
            lane1_verification=lane1_summary(
                store, pid, proof_verdict=proof_v,
                ingestion_urls=(ingestion_urls or {}).get(pid, ())),
            lane2_acceptance=lane2_state(store, pid),
        )
        records.append(tv.as_dict())
    return records
