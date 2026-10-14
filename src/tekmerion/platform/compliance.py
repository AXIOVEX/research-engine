"""SPRS-input control states and DoD scoring (Spec 005 §13, T552;
CLM-005-29).

The machinery an operator's NIST SP 800-171 self-assessment is
computed *from*: for every one of the 110 requirements, a state, the
DoD Assessment Methodology weighted deduction class, and an evidence
link (or an explicit gap marker) — maintained as events in a scope's
platform ledger, with the score computed deterministically from the
recorded inputs. The platform never submits anything to SPRS; the
submission is the operator's act, and nothing here performs it.

Scoring follows the **NIST SP 800-171 DoD Assessment Methodology,
Version 1.2.1 (June 24, 2020)**, §5 and Annex A:

- the score starts at 110; each unimplemented requirement deducts
  its weight (5, 3, or 1) — 44 requirements weigh 5, 14 weigh 3,
  51 weigh 1, so a fully unimplemented record scores 110 − 313 =
  **−203**, the methodology's floor;
- §3.12.4 (system security plan) carries **no deduction value**
  (Annex A: "NA") — its absence is an assessment-blocking finding
  under §5(g), not a deduction, so it is recorded here as unscored;
- two requirements have a defined partial deduction (§5(e)):
  §3.5.3 (MFA) deducts 3 when MFA covers remote and privileged
  users only, and §3.13.11 (FIPS) deducts 3 when encryption is
  employed but not FIPS-validated — both deduct 5 when absent
  outright. No other partial implementation is credited: a
  partially implemented requirement elsewhere deducts in full,
  exactly as the methodology scores it.

Seed states are *derived mechanically from the responsibility
matrix* (CLM-005-24's maintained record), never hand-tuned:

- **Platform** → `implemented`: the requirement is satisfied by the
  platform's construction when operated as designed; the evidence
  link names the matrix row and the implementing machinery.
- **Supports** → `not_implemented` with an operator-remainder gap
  marker: the platform provides the mechanism or the evidence; the
  remainder is the operating organization's, and its state is the
  organization's to set on its own evidence (a state-set event).
- **Organizational** → `not_implemented` with an organizational gap
  marker: outside product scope by the matrix's own classification.
- **§3.13.11** is the seeded exception that proves the rule is
  evidence-driven, not class-driven: `partially_implemented` —
  encryption is employed everywhere in the platform, and no
  inventoried operation uses a FIPS 140-3 validated module
  (crypto-inventory.md) — so the §5(e) partial deduction of 3
  lands in the computed score, with the seeded POA&M item (T553)
  named as its gap marker.

A computed score is an *output of this machinery over a recorded
input set* — it is never evidence of any organization's compliance,
and the seed score in particular measures the platform's inputs
alone, with every operator-side remainder unimplemented.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from .ledger import (
    AUDIT_EXPORTED,
    COMPLIANCE_STATE_SET,
    COMPLIANCE_STATES_SEEDED,
    LEGAL_HOLD_PLACED,
    POAM_ITEM_CREATED,
    PlatformLedger,
)
from .matrix_data import MATRIX_CLASSES

METHODOLOGY = "NIST SP 800-171 DoD Assessment Methodology, Version 1.2.1 (2020-06-24)"
SEED_VERSION = "e6-seed-1"
MATRIX_REF = "specs/005-enterprise-platform/cmmc-responsibility-matrix.md"
CRYPTO_INVENTORY_REF = "specs/005-enterprise-platform/crypto-inventory.md"

IMPLEMENTED = "implemented"
PARTIALLY_IMPLEMENTED = "partially_implemented"
NOT_IMPLEMENTED = "not_implemented"
STATES = frozenset({IMPLEMENTED, PARTIALLY_IMPLEMENTED, NOT_IMPLEMENTED})

# -- DoD weights (Methodology §5(d) lists + Annex A values) --------------
#
# §5(d)(i) names the 5-point Basic and Derived requirements; §5(e)
# adds 3.5.3 and 3.13.11, whose *maximum* deduction is likewise 5.
# §5(d)(ii) names the 3-point set. Every remaining requirement is a
# 1-point Derived requirement (§5(d)(iii)) except 3.12.4, which
# Annex A values "NA" (unscored — see the module docstring).
_FIVE = frozenset({
    "3.1.1", "3.1.2", "3.1.12", "3.1.13", "3.1.16", "3.1.17", "3.1.18",
    "3.2.1", "3.2.2", "3.3.1", "3.3.5",
    "3.4.1", "3.4.2", "3.4.5", "3.4.6", "3.4.7", "3.4.8",
    "3.5.1", "3.5.2", "3.5.3", "3.5.10",
    "3.6.1", "3.6.2", "3.7.2", "3.7.5", "3.8.3", "3.8.7",
    "3.9.2", "3.10.1", "3.10.2", "3.11.2",
    "3.12.1", "3.12.3",
    "3.13.1", "3.13.2", "3.13.5", "3.13.6", "3.13.11", "3.13.15",
    "3.14.1", "3.14.2", "3.14.3", "3.14.4", "3.14.6",
})
_THREE = frozenset({
    "3.1.5", "3.1.19", "3.3.2", "3.7.1", "3.7.4", "3.8.1", "3.8.2",
    "3.8.8", "3.9.1", "3.11.1", "3.12.2", "3.13.8", "3.14.5", "3.14.7",
})
UNSCORED = frozenset({"3.12.4"})

DOD_WEIGHTS: dict[str, Optional[int]] = {
    req: (None if req in UNSCORED else 5 if req in _FIVE else 3 if req in _THREE else 1)
    for req in MATRIX_CLASSES
}

#: §5(e): the only two requirements with a defined partial deduction.
PARTIAL_DEDUCTIONS: dict[str, int] = {"3.5.3": 3, "3.13.11": 3}

#: Implementing machinery for the Platform-classified rows — the
#: evidence link's second half. Paths are repo-relative and pinned
#: by test (a state may not cite machinery that does not exist).
PLATFORM_MACHINERY: dict[str, list[str]] = {
    "3.1.1": ["src/tekmerion/platform/gate.py", "src/tekmerion/platform/service.py"],
    "3.1.2": ["src/tekmerion/platform/authz.py"],
    "3.1.5": ["src/tekmerion/platform/authz.py"],
    "3.1.7": ["src/tekmerion/platform/gate.py", "src/tekmerion/platform/ledger.py"],
    "3.1.11": ["src/tekmerion/platform/baseline.py"],
    "3.3.1": ["src/tekmerion/platform/ledger.py"],
    "3.3.2": ["src/tekmerion/platform/ledger.py"],
    "3.3.8": ["src/tekmerion/platform/ledger.py"],
    "3.3.9": ["src/tekmerion/platform/authz.py"],
    "3.4.6": ["src/tekmerion/platform/authz.py"],
    "3.5.1": ["src/tekmerion/platform/directory.py"],
    "3.5.2": ["src/tekmerion/platform/oidc.py", "src/tekmerion/platform/saml.py"],
    "3.5.4": ["src/tekmerion/platform/oidc.py", "src/tekmerion/platform/saml.py"],
    "3.5.11": ["src/tekmerion/platform/errors.py"],
    "3.13.3": ["src/tekmerion/platform/authz.py"],
    "3.13.9": ["src/tekmerion/platform/baseline.py"],
    "3.13.10": ["src/tekmerion/platform/keys.py"],
}

SUPPORTS_GAP = (
    "operator remainder: the platform supports this requirement "
    "(mechanism and/or evidence); the operating organization owns "
    "the remainder and sets this state on its own evidence"
)
ORGANIZATIONAL_GAP = (
    "organizational: outside product scope by the responsibility "
    "matrix's classification; the operating organization owns this "
    "requirement outright"
)
FIPS_GAP = (
    "OPEN GAP: encryption is employed, but no operation in the "
    "cryptographic inventory uses a FIPS 140-3 validated module; "
    "seeded POA&M item POAM-0001 carries the remediation record"
)


def _req_key(req: str) -> list[int]:
    return [int(part) for part in req.split(".")]


def deduction_for(requirement: str, state: str) -> int:
    """The deduction one recorded state contributes, per §5. An
    unscored requirement (3.12.4) never deducts; a partial state
    deducts its §5(e) partial value where one is defined and the
    full weight otherwise (the methodology credits no other
    partial implementation)."""
    weight = DOD_WEIGHTS[requirement]
    if weight is None or state == IMPLEMENTED:
        return 0
    if state == PARTIALLY_IMPLEMENTED and requirement in PARTIAL_DEDUCTIONS:
        return PARTIAL_DEDUCTIONS[requirement]
    return weight


def seed_states() -> dict[str, dict[str, Any]]:
    """The seed input set, derived mechanically from the matrix
    classification of each requirement (see the module docstring
    for the rule and its one evidence-driven exception)."""
    states: dict[str, dict[str, Any]] = {}
    for req in sorted(MATRIX_CLASSES, key=_req_key):
        cls = MATRIX_CLASSES[req]
        record: dict[str, Any] = {
            "requirement": req,
            "matrix_class": cls,
            "evidence_link": f"{MATRIX_REF}#{req}",
            "gap_marker": None,
            "machinery": [],
            "set_by": "seed",
            "seq": None,
        }
        if req == "3.13.11":
            record.update({
                "state": PARTIALLY_IMPLEMENTED,
                "evidence_link": f"{CRYPTO_INVENTORY_REF}#3.13.11",
                "gap_marker": FIPS_GAP,
                "poam_ref": "POAM-0001",
            })
        elif cls == "Platform":
            record.update({
                "state": IMPLEMENTED,
                "machinery": list(PLATFORM_MACHINERY.get(req, [])),
            })
        elif cls == "Supports":
            record.update({"state": NOT_IMPLEMENTED, "gap_marker": SUPPORTS_GAP})
        else:  # Organizational
            record.update({"state": NOT_IMPLEMENTED, "gap_marker": ORGANIZATIONAL_GAP})
        if req == "3.12.2":
            # The register machinery is the platform's contribution;
            # the seed state remains the operator's remainder.
            record["machinery"] = ["src/tekmerion/platform/poam.py"]
        states[req] = record
    return states


def seed_set_hash(states: Optional[dict[str, dict[str, Any]]] = None) -> str:
    """SHA-256 over the canonical SPRS-input form of a state set —
    the value the `compliance.states_seeded` event binds."""
    form = sprs_input_form(states if states is not None else seed_states())
    canonical = json.dumps(form, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sprs_input_form(states: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """The SPRS-input record: one entry per requirement, in
    requirement order — state, deduction class (the DoD weight),
    the deduction the state actually applies, evidence link, and
    gap marker. This is the form an operator transcribes into
    SPRS; the platform computes it and never submits it."""
    form = []
    for req in sorted(states, key=_req_key):
        record = states[req]
        form.append({
            "requirement": req,
            "matrix_class": record["matrix_class"],
            "state": record["state"],
            "deduction_class": DOD_WEIGHTS[req],
            "deduction_applied": deduction_for(req, record["state"]),
            "evidence_link": record.get("evidence_link"),
            "gap_marker": record.get("gap_marker"),
            "machinery": list(record.get("machinery", [])),
            "poam_ref": record.get("poam_ref"),
        })
    return form


def compute_score(states: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """110 minus the recorded deductions — a pure function of the
    input set, so the same inputs always produce the same score
    (the determinism the T552 battery pins)."""
    deductions = {
        req: deduction_for(req, states[req]["state"])
        for req in sorted(states, key=_req_key)
    }
    total = sum(deductions.values())
    return {
        "score": 110 - total,
        "total_deduction": total,
        "deductions": {req: pts for req, pts in deductions.items() if pts},
        "unscored": sorted((r for r in states if DOD_WEIGHTS[r] is None), key=_req_key),
        "methodology": METHODOLOGY,
    }


def completeness_failures(states: dict[str, dict[str, Any]]) -> list[str]:
    """F-005-29's evidence half: no state without a basis — every
    recorded state carries an evidence link or an explicit gap
    marker, and every one of the 110 requirements is present."""
    failures = []
    for req in sorted(MATRIX_CLASSES, key=_req_key):
        if req not in states:
            failures.append(f"{req}: no state recorded")
            continue
        record = states[req]
        if not record.get("evidence_link") and not record.get("gap_marker"):
            failures.append(f"{req}: state has neither an evidence link nor a gap marker")
        if record.get("state") not in STATES:
            failures.append(f"{req}: unknown state {record.get('state')!r}")
    for req in states:
        if req not in MATRIX_CLASSES:
            failures.append(f"{req}: state recorded for an unknown requirement")
    return failures


def agreement_failures(states: dict[str, dict[str, Any]]) -> list[str]:
    """F-005-29's named failure: a matrix classification and a
    SPRS-form state that disagree. The checkable disagreement is in
    the **platform-asserted** layer — the seed records the platform
    itself stands behind:

    - an **Organizational** requirement the seed records as
      anything but not-implemented (the platform cannot implement
      what the matrix places outside its scope);
    - a **Platform** requirement the seed records not-implemented
      with no gap marker (the construction satisfies it; an
      unimplemented seed state must name its gap);
    - a **Supports** requirement the seed records implemented (the
      platform's contribution alone never implements a Supports
      requirement — the remainder is the operator's).

    Operator-set records are the operating organization's own
    statements about its own implementation (for an organizational
    requirement, the organization is exactly who may record it
    implemented); they are constrained by the completeness rule —
    an evidence link or a gap marker — not by the matrix, which
    classifies the *platform's* responsibility, not the operator's
    posture.
    """
    failures = []
    for req, record in states.items():
        if record.get("set_by") != "seed":
            continue
        cls = record.get("matrix_class") or MATRIX_CLASSES.get(req)
        if cls == "Organizational" and record.get("state") != NOT_IMPLEMENTED:
            failures.append(
                f"{req}: classified Organizational but the seed records "
                f"{record.get('state')} — the platform cannot implement "
                "an out-of-scope requirement")
        if cls == "Platform" and record.get("state") == NOT_IMPLEMENTED \
                and not record.get("gap_marker"):
            failures.append(
                f"{req}: classified Platform but the seed records it "
                "not implemented with no gap marker naming why")
        if cls == "Supports" and record.get("state") == IMPLEMENTED:
            failures.append(
                f"{req}: classified Supports but the seed records it "
                "implemented — a Supports remainder is the operator's "
                "to close, never the seed's to claim")
    return failures


# -- Evidence-link resolution (Spec 013 CLM-013-25) ---------------------
#
# An evidence link is a *reference*, and a reference that claims a
# platform-recorded target must resolve: the named target exists in
# the same scope's ledger and matches the identity the link claims.
# Three link forms claim platform targets:
#
#   poam:<item-id>     a POA&M item created in this scope's ledger
#   export:<export-id> an audit export recorded in this scope's ledger
#   hold:<hold-id>     a legal hold placed in this scope's ledger
#   <doc>#<req>        an anchor into a platform document (the
#                      responsibility matrix or the crypto
#                      inventory); the anchor must name the very
#                      requirement the link is offered as evidence
#                      for — a link to a different requirement's row
#                      is a different claim, not evidence for this one
#
# Any other whitespace-free token (conventionally `org/...`) is the
# operating organization's own evidence reference: the platform
# cannot verify the organization's store, so such a link is recorded
# and reported as *operator-attested* — visibly distinct from a
# resolved link in the computed record, never silently equivalent.
# A value with whitespace, or an empty value, is not a reference at
# all: it is a bare assertion, and the SPRS machinery refuses it —
# the score cannot be moved by assertion alone (red-team probe p12).

_PLATFORM_DOC_REFS = frozenset({MATRIX_REF, CRYPTO_INVENTORY_REF})
_PLATFORM_ID_PREFIXES = ("poam:", "export:", "hold:")


def _platform_form(link: str) -> bool:
    return link.startswith(_PLATFORM_ID_PREFIXES) or "#" in link


def evidence_link_problem(requirement: str, link: str,
                          known_ids: dict[str, set]) -> Optional[str]:
    """Why `link` cannot stand as evidence for `requirement`, or
    None when it can. `known_ids` maps "poam"/"export"/"hold" to the
    ids recorded in the scope's ledger."""
    if not link or any(ch.isspace() for ch in link):
        return (f"evidence link {link!r} is not a reference: an "
                "evidence link names a record (a single reference "
                "token), not an assertion")
    if link.startswith("poam:"):
        if link[5:] not in known_ids.get("poam", set()):
            return (f"evidence link {link!r} names no POA&M item "
                    "recorded in this scope")
        return None
    if link.startswith("export:"):
        if link[7:] not in known_ids.get("export", set()):
            return (f"evidence link {link!r} names no audit export "
                    "recorded in this scope")
        return None
    if link.startswith("hold:"):
        if link[5:] not in known_ids.get("hold", set()):
            return (f"evidence link {link!r} names no legal hold "
                    "recorded in this scope")
        return None
    if "#" in link:
        path, _, anchor = link.rpartition("#")
        if path not in _PLATFORM_DOC_REFS:
            return (f"evidence link {link!r} anchors into a document "
                    "the platform does not maintain")
        if anchor != requirement:
            return (f"evidence link {link!r} anchors requirement "
                    f"{anchor}, not the requirement it is offered "
                    f"for ({requirement})")
        return None
    return None


def evidence_link_status(requirement: str, link: Optional[str],
                         known_ids: dict[str, set]) -> str:
    """The recorded standing of one input's evidence link:
    "resolved" (a platform-form link whose target was verified),
    "unresolved" (a platform-form link whose target does not
    exist or does not match), "operator-attested" (the
    organization's own reference, not platform-verifiable), or
    "none" (no link — the state rests on a gap marker)."""
    if not link:
        return "none"
    if not _platform_form(link):
        return "operator-attested"
    return ("unresolved" if evidence_link_problem(requirement, link, known_ids)
            else "resolved")


class ControlStateStore:
    """Control states as ledger events over one scope's platform
    ledger (deployment scope in the deployment ledger, tenant scope
    in the tenant's own ledger). Current state is a replay: the
    recorded seed, then each `compliance.state_set` in order.
    Nothing is edited in place; a correction is a later event."""

    def __init__(self, ledger: PlatformLedger) -> None:
        self.ledger = ledger

    def is_seeded(self) -> bool:
        return any(e["type"] == COMPLIANCE_STATES_SEEDED for e in self.ledger.events())

    def _known_ids(self) -> dict[str, set]:
        """The platform-recorded ids in this scope's ledger that an
        evidence link can resolve against (Spec 013 CLM-013-25)."""
        known: dict[str, set] = {"poam": set(), "export": set(), "hold": set()}
        for event in self.ledger.events():
            payload = event["payload"]
            if event["type"] == POAM_ITEM_CREATED and payload.get("item_id"):
                known["poam"].add(payload["item_id"])
            elif event["type"] == AUDIT_EXPORTED and payload.get("export_id"):
                known["export"].add(payload["export_id"])
            elif event["type"] == LEGAL_HOLD_PLACED and payload.get("hold_id"):
                known["hold"].add(payload["hold_id"])
        return known

    def ensure_seeded(self, *, actor_id: str) -> bool:
        """Record the seed event once. Returns True when this call
        appended it. The seed *content* is the deterministic table
        above; the event binds its version + hash so a later reader
        can tell exactly which input set a replay started from."""
        if self.is_seeded():
            return False
        self.ledger.record(
            COMPLIANCE_STATES_SEEDED, actor_id=actor_id, target="compliance:states",
            seed_version=SEED_VERSION, seed_set_hash=seed_set_hash(),
            requirement_count=len(MATRIX_CLASSES), methodology=METHODOLOGY)
        return True

    def set_state(self, *, actor_id: str, requirement: str, state: str,
                  evidence_link: Optional[str] = None,
                  gap_marker: Optional[str] = None,
                  note: str = "") -> dict:
        """Append one state-set event. Validation failures raise
        before anything is recorded (the service layer ledgers the
        refusal for attributable attempts): unknown requirement,
        unknown state, or a state with neither an evidence link nor
        a gap marker — the completeness rule is enforced at write
        time, not merely checked after the fact."""
        if requirement not in MATRIX_CLASSES:
            raise ValueError(f"unknown requirement {requirement!r}")
        if state not in STATES:
            raise ValueError(f"unknown control state {state!r}")
        if not evidence_link and not gap_marker:
            raise ValueError(
                "a control state requires an evidence link or an explicit "
                "gap marker (CLM-005-29 completeness)")
        if evidence_link:
            # Spec 013 CLM-013-25: a link that claims a platform
            # target must resolve, at write time, loudly.
            problem = evidence_link_problem(
                requirement, evidence_link, self._known_ids())
            if problem:
                raise ValueError(problem)
        return self.ledger.record(
            COMPLIANCE_STATE_SET, actor_id=actor_id,
            target=f"requirement:{requirement}",
            requirement=requirement, state=state,
            evidence_link=evidence_link, gap_marker=gap_marker, note=note)

    def current_states(self) -> dict[str, dict[str, Any]]:
        """Replay: seed, then state-set events in sequence order.
        Raises if the scope was never seeded — an unseeded scope
        has no input set, and inventing one silently is exactly
        what this machinery exists to refuse."""
        events = self.ledger.events()
        seeded = [e for e in events if e["type"] == COMPLIANCE_STATES_SEEDED]
        if not seeded:
            raise ValueError("control states are not seeded for this scope")
        states = seed_states()
        for event in events:
            if event["type"] != COMPLIANCE_STATE_SET:
                continue
            payload = event["payload"]
            req = payload["requirement"]
            states[req] = {
                "requirement": req,
                "matrix_class": MATRIX_CLASSES[req],
                "state": payload["state"],
                "evidence_link": payload.get("evidence_link"),
                "gap_marker": payload.get("gap_marker"),
                "machinery": list(states[req].get("machinery", [])),
                "poam_ref": states[req].get("poam_ref"),
                "set_by": payload.get("actor_id"),
                "seq": event["seq"],
            }
        return states

    def sprs_report(self) -> dict[str, Any]:
        """The scope's full SPRS-input record: per-requirement form,
        the computed score, and the standing checks (completeness,
        matrix agreement, and evidence resolution — Spec 013
        CLM-013-25) evaluated over the same inputs."""
        states = self.current_states()
        score = compute_score(states)
        # Spec 013 CLM-013-25: every input's evidence link carries
        # its resolution standing in the parallel "evidence" section
        # (the inputs themselves stay the pure, replayable form the
        # export verifier recomputes — evidence standing is derived
        # from the same ledger and travels alongside, never inside),
        # and a platform-form link whose target no longer resolves
        # is a named check failure — the evidenced and the merely
        # attested are never presented as the same thing.
        known_ids = self._known_ids()
        inputs = sprs_input_form(states)
        evidence: dict[str, str] = {}
        evidence_failures = []
        for entry in inputs:
            status = evidence_link_status(
                entry["requirement"], entry.get("evidence_link"), known_ids)
            evidence[entry["requirement"]] = status
            if status == "unresolved":
                evidence_failures.append(
                    f"{entry['requirement']}: evidence link does not "
                    f"resolve: {entry.get('evidence_link')!r}")
        return {
            "seed_version": SEED_VERSION,
            "methodology": METHODOLOGY,
            "inputs": inputs,
            "score": score["score"],
            "total_deduction": score["total_deduction"],
            "deductions": score["deductions"],
            "unscored": score["unscored"],
            "completeness_failures": completeness_failures(states),
            "agreement_failures": agreement_failures(states),
            "evidence": evidence,
            "evidence_failures": evidence_failures,
            "submission": "operator's act — the platform computes and "
                          "maintains these inputs; it never submits to SPRS",
        }
