"""Export service (Spec 002 Phase 5; WS4 §4, WS5 §2/§4; T216).

One export action produces a self-describing **audit bundle**: the
study's ledger copied byte-for-byte, the frozen registration it is
bound to by hash, the claim register, evidence and origin groups, the
Phase 4 verification record, per-claim support-check coverage
(WS5 §2), verdicts, adjudication, and a manifest whose hashes make
every member file checkable. Formats are deliberately boring
(JSON + Markdown, UTF-8) — a bundle must be auditable in twenty years
with generic tools (WS4 §4).

The standalone verifier (`verify_bundle`) consumes **only the bundle**:
it re-checks every manifest hash, verifies the exported ledger with
the production Axiomere verifier (RT-1 discipline — the chain code is
not reimplemented here), requires the manifest checkpoint root to
equal the latest Merkle checkpoint root in the exported ledger, and
cross-checks the projections against the ledger they claim to
project. A bundle that fails any check is not an audit bundle.
Since Phase 7 the verdicts projection also states the run's outcome
(`valid` / `invalid` / `not-run`, audit NC-6): an invalid run appends
nothing, so without the projection a failed run was invisible from
the bundle alone.

Anchoring (AR-1): anchor receipts recorded in the ledger
(`anchor.recorded` events, appended by `tekmerion.deposit`) are
carried in the manifest, and `verify_anchor` checks a bundle against
the *public* anchor record (DN-005 layer 5 — rewriting history
becomes detectable by anyone). Two bindings are checked: the
receipt chain (a receipt the bundle carries must validate against
the record it names) and, since Spec 013 (CLM-013-02), the
**own-hash binding** — the record must state the presented bundle's
own `bundle_hash` and checkpoint root. A successor bundle presented
against its predecessor's record validates the chain but is
reported *unanchored* and does not pass: a rehashed bundle whose
hash no record states is indistinguishable from an honest one
against that record, which is the gap RTA-02 demonstrated.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .claims import Claim, ClaimRegister, EvidenceItem, RegistrationError
from .freeze import (binding_frozen_event, registration_document,
                    registration_hash)
from .marking import banner_lines, normalize_marking
from .verdicts import (evaluate_claim, evaluate_run, fixture_identity,
                      run_controls_report, swap_control_report)
from .verification import queue_state, second_review_report

BUNDLE_FORMAT = "tekmerion-audit-bundle/1"
SCHEMA_VERSIONS = {"bundle": "1", "ledger": "AXMR1", "registration": "1"}

#: Licence bases that permit redistribution of retrieved content in a
#: bundle (WS5 §4: the strictest recorded rights answer governs;
#: anything unlisted — NC/ND variants, publisher licences, unknown —
#: defaults to stub-only until researched and recorded).
_REDISTRIBUTABLE_MARKERS = (
    "creativecommons.org/licenses/by/4.0",
    "creativecommons.org/licenses/by/3.0",
    "creativecommons.org/licenses/by-sa",
    "creativecommons.org/publicdomain/zero",
    "cc0 1.0",
    "public domain",
)


class ExportError(RuntimeError):
    pass


def redistribution_permitted(license_basis: str) -> bool:
    """WS5 §4 gate, mechanized: only an asserted licence that permits
    redistribution lets content into a bundle. NC/ND elements and
    unasserted bases are stub-only."""
    lb = (license_basis or "").lower()
    if "-nc" in lb or "noncommercial" in lb or "non-commercial" in lb:
        return False
    if "-nd" in lb or "noderivatives" in lb or "no derivatives" in lb:
        return False
    return any(marker in lb for marker in _REDISTRIBUTABLE_MARKERS)


# ------------------------------------------------------------------ helpers

def _dump(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _ledger_events(ledger_bytes: bytes) -> list[dict[str, Any]]:
    """Parse the events out of an .axmr file: a magic header line
    (`AXMR1`), then one canonical-JSON event per line."""
    events = []
    for line in ledger_bytes.decode("utf-8").splitlines():
        if line.strip() and not line.startswith("AXMR"):
            events.append(json.loads(line))
    return events


def _checkpoints(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"seq": e["seq"], "upto_seq": e["payload"]["upto_seq"],
         "merkle_root": e["payload"]["merkle_root"]}
        for e in events if e["type"] == "checkpoint"
    ]


class _EventsOnlyStore:
    """Adapter so production projections (queue_state,
    second_review_report) run on events parsed from a bundle's ledger
    copy — the same code path, bundle-only input."""

    def __init__(self, events: list[dict[str, Any]]) -> None:
        self._events = events

    def events(self) -> list[dict[str, Any]]:
        return self._events


def _excluded_markers(queue: dict[str, Any]) -> list[dict[str, Any]]:
    """Exclusion markers (Spec 011): one per citation a **decided
    quarantine** item excluded — {citation_id, claim_id, queue_id,
    decision, rationale}. Grouping decisions and `variant` rulings
    are not exclusions and mint no marker; undecided items mint none.
    A marker re-admits nothing: the citation stays absent from the
    evidence files. Exporter and verifier both derive the set from
    the queue-state replay, so the projection is checked against the
    ledger, never merely asserted."""
    return [
        {"citation_id": item["citation_id"],
         "claim_id": item.get("claim_id"),
         "queue_id": item["queue_id"],
         "decision": "exclude",
         "rationale": item.get("rationale", "")}
        for item in queue.get("decided", [])
        if item.get("kind") == "quarantine"
        and item.get("decision") == "exclude"
        and item.get("citation_id")
    ]


# ------------------------------------------------------------------ coverage

def coverage_report(register: ClaimRegister, events: list[dict[str, Any]]) -> dict[str, Any]:
    """Support-check coverage per claim (WS5 §2, RT2-3): what share of
    a claim's origin groups ever had their content checked, and what
    share is metadata-only. Ignorance is a shown quantity: the numbers
    come from the Phase 4 group records (`metadata_only` per group)
    and the ledgered citation outcomes, never from inference."""
    checked = [e["payload"] for e in events if e["type"] == "citation.checked"]
    per_claim: dict[str, Any] = {}
    for cid in sorted(register.claims):
        groups = register.group_masses(cid)
        g_total = len(groups)
        g_meta = sum(1 for g in groups if g["metadata_only"])
        cits = [c for c in checked if c["claim_id"] == cid]
        per_claim[cid] = {
            "origin_groups": g_total,
            "groups_content_checked": g_total - g_meta,
            "groups_metadata_only": g_meta,
            "group_coverage": ((g_total - g_meta) / g_total) if g_total else None,
            "citations_checked": len(cits),
            "citations_content_checked": sum(
                1 for c in cits if c["content"] in ("supports", "contradicts", "contextual")),
            "citations_metadata_only": sum(1 for c in cits if c["content"] == "metadata_only"),
            "citations_unresolved": sum(1 for c in cits if c["resolution"] != "resolved"),
        }
    return {
        "basis": "origin groups from ClaimRegister.group_masses (metadata_only per group, "
                 "Phase 4); citation counts from citation.checked ledger events",
        "per_claim": per_claim,
    }


# ------------------------------------------------------------------ run outcome

def _issued_control_outcomes(controls: list, store: Any,
                             store_path: str) -> list[dict[str, Any]]:
    """Per-control outcomes for an issued (valid) run, re-executed at
    export time through the production path (`run_controls_report`)
    on the controls presented to the exporter and the study's ledger —
    the same deterministic computation the issuing run performed
    (fixture evaluation is a pure function of the fixture; the swap
    control runs on the ledger being exported).

    A fixture control whose fixture was not presented at export is
    NOT recorded as failed: the issuing run executed it with its
    fixture (an invalid run issues no verdicts), so its outcome is
    recorded as attested by the `verdict.issued` events — `passed:
    null`, never an outcome the machinery did not produce."""
    outcomes = run_controls_report(list(controls), store=store, store_path=store_path)
    adjusted: list[dict[str, Any]] = []
    for outcome in outcomes:
        if not outcome["executed"] and outcome["kind"] in ("positive", "negative"):
            outcome = {**outcome, "passed": None,
                       "detail": "fixture not presented at export; the control's "
                                 "pass is attested by the run's verdict.issued "
                                 "events (an invalid run issues none, WS3 §1)"}
        adjusted.append(outcome)
    return adjusted


def run_outcome_projection(
    store: Any,
    store_path: str,
    *,
    register: ClaimRegister,
    controls: list,
    doc: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """The run's outcome, stated inside the bundle (audit NC-6).

    An INVALID run appends nothing (WS3 §1), so without this
    projection a bundle whose run failed is indistinguishable from
    one that never ran: `verdicts.json` was `{"verdicts": []}` and
    the outcome lived only in surrounding text. The projection is
    derived, never asserted:

    - If the ledger carries `verdict.issued` events, the run was
      valid and its verdicts are those events.
    - Otherwise the run-level checks are **replayed at export time**
      through the production path (`tekmerion.verdicts.evaluate_run`)
      on a register rebuilt from the frozen document plus this
      export's evidence — the same replay the workspace performs.
      INVALID carries the engine's reasons verbatim; a clean replay
      with no issued verdicts is `not-run`.

    Since Spec 011 the projection also records **per-control
    outcomes** (`controls`): the replay's own outcomes for unissued
    runs, and a production-path re-execution for issued runs (see
    `_issued_control_outcomes`). Before that change control
    evaluation was ephemeral — a valid run silently implied success
    and no artifact recorded which controls ran (Phase 7 §4.7).

    The standalone verifier cross-checks everything about this
    projection that is decidable from the bundle alone (verdict
    counts, unverified evidence, the recorded control outcomes
    against the committed registration and the verifier's own swap
    replay on the bundle's ledger copy); fixture-dependent control
    outcomes are attested by this replay and bound by the manifest
    hashes, like every other projection the bundle carries.

    Since Spec 013 (CLM-013-03) an issued run's outcomes are the
    run's own `control.outcome` ledger events when the ledger
    carries them (`controls_recorded: true`) — the projection then
    restates the record, and the verifier compares it
    payload-for-payload. Runs predating that issuance keep the
    re-execution/attested path above and are labeled
    operator-attested in the HUMAN-README. The projection also
    states the regime (CLM-013-07): the binding registration hash
    and whether it arrived by amendment."""
    issued = [e for e in events if e["type"] == "verdict.issued"]
    registered_kinds = [c.get("kind") for c in doc.get("controls", [])]
    # The regime this run belongs to (Spec 013 CLM-013-07): the
    # binding registration the verdicts were issued under, and whether
    # it arrived by a labeled amendment.
    binding = binding_frozen_event(events)
    regime = {
        "registration_hash": registration_hash(doc),
        "regime": {
            "frozen_event_seq": binding["seq"] if binding else None,
            "amended": bool(binding and binding["type"] == "study.frozen.amended"),
        },
    }
    # Control outcomes recorded at issuance (Spec 013 CLM-013-03):
    # the `control.outcome` events following the latest `run.issued`
    # event are that run's outcomes, appended when it issued.
    recorded: list[dict[str, Any]] = []
    run_event_indexes = [i for i, e in enumerate(events)
                         if e["type"] == "run.issued"]
    if run_event_indexes:
        recorded = [e["payload"] for e in events[run_event_indexes[-1] + 1:]
                    if e["type"] == "control.outcome"]
    if issued:
        if recorded:
            # The projection covers the committed control set (the
            # Spec 011 discipline): controls the issuing run executed
            # restate its own control.outcome ledger events verbatim
            # (CLM-013-03) — the record wins over any export-time
            # re-execution — and controls it did not execute are
            # recorded as not executed, never as passed.
            base = _issued_control_outcomes(controls, store, store_path)
            by_key = {(o.get("kind"), o.get("failure_mode")): o
                      for o in recorded}
            merged: list[dict[str, Any]] = []
            used: set = set()
            for entry in base:
                key = (entry.get("kind"), entry.get("failure_mode"))
                if key in by_key:
                    merged.append(by_key[key])
                    used.add(key)
                else:
                    merged.append(entry)
            for key, payload in by_key.items():
                if key not in used:
                    merged.append(payload)
            return {
                "outcome": "valid",
                "basis": "verdict.issued events in the exported ledger "
                         "(an invalid run issues none, WS3 §1); the "
                         "control outcomes the issuing run executed are "
                         "its own control.outcome ledger events, appended "
                         "at issuance (Spec 013 CLM-013-03) and "
                         "cross-checked against them by the standalone "
                         "verifier; controls the run did not execute are "
                         "recorded as not executed",
                "mode": doc.get("mode"),
                "verdicts_issued": len(issued),
                "invalid_reasons": [],
                "controls_replayed": [o["kind"] for o in merged if o["executed"]],
                "controls_registered": registered_kinds,
                "controls": merged,
                "controls_recorded": True,
                **regime,
            }
        outcomes = _issued_control_outcomes(controls, store, store_path)
        return {
            "outcome": "valid",
            "basis": "verdict.issued events in the exported ledger "
                     "(an invalid run issues none, WS3 §1); control outcomes "
                     "re-executed at export time through the production path "
                     "(tekmerion.verdicts.run_controls_report) — the same "
                     "deterministic computation the issuing run performed",
            "mode": doc.get("mode"),
            "verdicts_issued": len(issued),
            "invalid_reasons": [],
            "controls_replayed": [o["kind"] for o in outcomes if o["executed"]],
            "controls_registered": registered_kinds,
            "controls": outcomes,
            "controls_recorded": False,
            **regime,
        }
    replay = ClaimRegister()
    for cdoc in doc.get("claims", []):
        replay.register(Claim(**cdoc))
    for cid, items in register.evidence.items():
        for item in items:
            if cid in replay.claims:
                replay.add_evidence(cid, item)
    replay.frozen = True
    result = evaluate_run(
        replay,
        mode=doc.get("mode", "confirmation"),
        controls=list(controls),
        chain_ok=True,  # export has already refused a broken chain above
        linked_exploratory=list(doc.get("linked_exploratory") or []),
        store=store,
        store_path=store_path,
    )
    replayed_kinds = [o["kind"] for o in result.control_outcomes if o["executed"]]
    if result.run_verdict == "invalid":
        return {
            "outcome": "invalid",
            "basis": "replayed at export time through tekmerion.verdicts.evaluate_run "
                     "(production path); an invalid run appends nothing, so no "
                     "verdict.issued events exist to state it; the replay's "
                     "per-control outcomes are recorded in controls",
            "mode": doc.get("mode"),
            "verdicts_issued": 0,
            "invalid_reasons": list(result.invalid_reasons),
            "controls_replayed": replayed_kinds,
            "controls_registered": registered_kinds,
            "controls": result.control_outcomes,
            "controls_recorded": False,
            **regime,
        }
    return {
        "outcome": "not-run",
        "basis": "no verdict.issued events in the exported ledger, and the "
                 "run-level checks replayed at export time found no failure; "
                 "the replay's per-control outcomes are recorded in controls",
        "mode": doc.get("mode"),
        "verdicts_issued": 0,
        "invalid_reasons": [],
        "controls_replayed": replayed_kinds,
        "controls_registered": registered_kinds,
        "controls": result.control_outcomes,
        "controls_recorded": False,
        **regime,
    }


# ------------------------------------------------------------------ export

def export_bundle(
    store: Any,
    store_path: str,
    out_dir: str,
    *,
    register: ClaimRegister,
    controls: list,
    mode: str = "confirmation",
    linked_exploratory: Optional[list[str]] = None,
    study_label: Optional[str] = None,
    retrieved: Optional[dict[str, Any]] = None,
    citations: Optional[dict[str, Any]] = None,
    marking: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Export the study at `store_path` as an audit bundle at
    `out_dir` and return the manifest. Fails closed: a broken chain,
    an unfrozen study, or a presented registration whose hash does not
    match the frozen commitment produces no bundle."""
    verification = store.verify()
    if not verification.ok:
        raise ExportError(f"study ledger fails verification ({verification.reason}); "
                          "a broken record is evidence, not an export")
    events = store.events()

    frozen_event = binding_frozen_event(events)
    if frozen_event is None:
        raise ExportError("study is not frozen — bundles export frozen registrations (WS4 §4)")
    committed_hash = frozen_event["payload"]["registration_hash"]

    # The registration this bundle binds to is the document freeze
    # committed — captured on the register at freeze time, because
    # lifecycle statuses move afterward and the document must be
    # reproducible byte-for-byte. Fall back to reconstruction (which
    # the hash check below will refuse if the register has moved on).
    doc = getattr(register, "frozen_document", None) or registration_document(
        register, controls, mode, list(linked_exploratory or []))
    if registration_hash(doc) != committed_hash:
        raise ExportError(
            "presented registration does not hash to the frozen commitment "
            f"({committed_hash}); export refused rather than misbound")

    # Fixture commitment (Spec 013 CLM-013-09): a fixture PRESENTED
    # at export must be the fixture the registration committed. A
    # fixture not presented at export is the recorded attested case
    # (see _issued_control_outcomes), not a mismatch.
    committed_fixtures: dict[tuple[Any, Any], Optional[str]] = {}
    for entry in doc.get("controls", []):
        if "fixture" not in entry:
            continue  # a pre-Spec-013 document recorded no commitment
        fixture = entry.get("fixture") or {}
        committed_fixtures[(entry.get("kind"), entry.get("failure_mode"))] = \
            fixture.get("sha256")
    for ctl in controls:
        identity = fixture_identity(ctl)
        if identity is None:
            continue
        key = (ctl.kind, ctl.failure_mode)
        if key not in committed_fixtures or committed_fixtures[key] != identity["sha256"]:
            raise ExportError(
                f"presented fixture for the {ctl.kind} control "
                f"({ctl.failure_mode}) does not match the fixture identity "
                "committed in the frozen registration (Spec 013 CLM-013-09); "
                "export refused rather than misbound")

    checkpoints = _checkpoints(events)
    if not checkpoints:
        raise ExportError("no Merkle checkpoint in the ledger — freeze the study first")

    # The root written into the manifest below is the value anchors
    # bind to, so it is confirmed against the root the verifier
    # recomputes from the ledger's events — never merely read out
    # of the checkpoint event's payload (Axiomere Spec 003
    # companion, AXM-003-15).
    pin = store.verify(
        expected_head={"checkpoint_root": checkpoints[-1]["merkle_root"]})
    if not pin.ok:
        raise ExportError(
            "the ledger's latest checkpoint root does not match the root "
            f"verification recomputes ({pin.reason}); export refused rather "
            "than misbound")

    run_outcome = run_outcome_projection(
        store, store_path, register=register, controls=controls, doc=doc, events=events)

    out = Path(out_dir)
    if out.exists() and any(out.iterdir()):
        raise ExportError(f"bundle directory {out_dir} is not empty")
    (out / "ledger").mkdir(parents=True, exist_ok=True)
    (out / "evidence" / "content").mkdir(parents=True, exist_ok=True)
    (out / "anchors").mkdir(parents=True, exist_ok=True)

    files: dict[str, bytes] = {}

    def put(rel: str, data: bytes) -> None:
        files[rel] = data

    # The record itself, faithfully (DN-005: exports carry actual
    # payloads; nothing is masked).
    put("ledger/study.axmr", Path(store_path).read_bytes())
    put("registration.json", _dump(doc))
    put("claims.json", _dump({
        "registration_hash": committed_hash,
        "claims": doc["claims"],
    }))
    put("controls.json", _dump({"controls": doc["controls"]}))

    evidence_items = [
        {"claim_id": cid, **item.as_dict()}
        for cid in sorted(register.evidence)
        for item in sorted(register.evidence[cid], key=lambda i: i.item_id)
    ]
    put("evidence/items.json", _dump({"items": evidence_items}))
    groups_doc = [
        {"claim_id": cid, **group}
        for cid in sorted(register.claims)
        for group in register.group_masses(cid)
    ]
    put("evidence/groups.json", _dump({"groups": groups_doc}))
    put("coverage.json", _dump(coverage_report(register, events)))

    checked = [e["payload"] for e in events if e["type"] == "citation.checked"]
    retrieved_doc: dict[str, Any] = {}
    substitutions: list[dict[str, Any]] = []
    for citation_id in sorted(retrieved or {}):
        item = retrieved[citation_id]
        entry = {
            "source": item.source, "source_id": item.source_id, "title": item.title,
            "authors": list(item.authors), "year": item.year, "venue": item.venue,
            "license_basis": item.license_basis, "hosted_ok": item.hosted_ok,
            "content_included": False,
        }
        if item.abstract:
            if redistribution_permitted(item.license_basis):
                rel = f"evidence/content/{citation_id.replace('/', '_')}.txt"
                put(rel, item.abstract.encode("utf-8"))
                entry["content_included"] = True
                entry["content_file"] = rel
            else:
                substitutions.append({
                    "item": citation_id,
                    "reason": f"licence basis does not permit redistribution: {item.license_basis}",
                    "substitute": "provenance stub (evidence/items.json + verification.json)",
                })
        retrieved_doc[citation_id] = entry
    verification_doc: dict[str, Any] = {
        "citation_outcomes": checked,
        "retrieved": retrieved_doc,
        "second_review": second_review_report(_EventsOnlyStore(events)),
    }
    if citations:
        # The as-cited forms — what the researcher actually typed,
        # including a fabricated DOI or a corrupted field — carried
        # beside the outcomes so the inputs can be re-inspected from
        # the bundle alone (Spec 011; Phase 7 §2.3 friction 5). Only
        # when the caller presents them: a bundle never invents
        # inputs it was not given.
        verification_doc["as_cited"] = {
            cid: (c.as_dict() if hasattr(c, "as_dict") else dict(c))
            for cid, c in sorted(citations.items())
        }
    put("verification.json", _dump(verification_doc))

    put("queries.json", _dump({
        "queries": [e["payload"] for e in events if e["type"] == "connector.query"],
    }))
    put("verdicts.json", _dump({
        "run_outcome": run_outcome,
        "verdicts": [
            {"seq": e["seq"], "actor": e["actor"], **e["payload"]}
            for e in events if e["type"] == "verdict.issued"
        ],
    }))
    state = queue_state(_EventsOnlyStore(events))
    put("adjudication.json", _dump({
        "pending": state["pending"], "decided": state["decided"],
        # Excluded citations get an explicit marker (Spec 011) rather
        # than vanishing from the evidence files unremarked.
        "excluded_citations": _excluded_markers(state),
    }))

    receipts = [e["payload"] for e in events if e["type"] == "anchor.recorded"]
    for i, receipt in enumerate(receipts):
        put(f"anchors/{i:02d}-{receipt.get('mechanism', 'anchor')}.json", _dump(receipt))

    label = study_label or Path(store_path).stem
    manifest_core: dict[str, Any] = {
        "format": BUNDLE_FORMAT,
        "schema_versions": SCHEMA_VERSIONS,
        "study": {
            "label": label,
            "ledger_file": "ledger/study.axmr",
            "event_count": len(events),
            "head_seq": events[-1]["seq"] if events else None,
            "head_hash": events[-1]["hash"] if events else None,
            "checkpoints": checkpoints,
            "checkpoint_root": checkpoints[-1]["merkle_root"],
            "registration_hash": committed_hash,
            "frozen_event_seq": frozen_event["seq"],
        },
        "complete": True,
        "content_substitutions": substitutions,
        "anchors": receipts,
        # CUI marking (Spec 005 T551): always present — the recorded
        # marking, or the explicit unmarked state. Populated from the
        # caller's recorded fields; the platform records markings,
        # it does not adjudicate them.
        "cui_marking": normalize_marking(marking),
    }
    put("HUMAN-README.md", _human_readme(manifest_core, register, state,
                                         run_outcome).encode("utf-8"))

    file_entries = [
        {"path": rel, "sha256": _sha256(data), "bytes": len(data)}
        for rel, data in sorted(files.items())
    ]
    manifest = {**manifest_core, "files": file_entries}
    manifest["bundle_hash"] = _sha256(_canonical(manifest))
    for rel, data in files.items():
        (out / rel).write_bytes(data)
    (out / "manifest.json").write_bytes(_dump(manifest))
    return manifest


def _human_readme(manifest: dict[str, Any], register: ClaimRegister,
                  queue: dict[str, Any],
                  run_outcome: Optional[dict[str, Any]] = None) -> str:
    study = manifest["study"]
    banner = banner_lines(manifest.get("cui_marking")
                          or normalize_marking(None))
    lines = [
        *banner,
        "",
        f"# Audit bundle — {study['label']}",
        "",
        "This bundle is the complete, self-describing record of one Tekmerion",
        "study run. It is designed to be audited with generic tools (JSON +",
        "Markdown, UTF-8) without the engine that produced it.",
        "",
        "## What is in here",
        "",
        "- `ledger/study.axmr` — the study's append-only ledger, copied",
        "  byte-for-byte: hash-chained, Ed25519-signed events (Axiomere).",
        "- `registration.json` — the frozen study design. Its SHA-256",
        "  registration hash is committed inside the ledger itself",
        f"  (`study.frozen` event, seq {study['frozen_event_seq']}).",
        "- `claims.json` — the full claim register, falsifiers included.",
        "- `evidence/` — evidence items, origin groups, and retrieved",
        "  content *only where the source licence permits redistribution*;",
        "  everything else is a provenance stub (see substitutions below).",
        "- `verification.json` — every citation's pipeline outcome",
        "  (resolution / agreement / content check), each citation's",
        "  as-cited form where the exporter was given the citation",
        "  inputs, and the second-review report (RT-4).",
        "- `coverage.json` — support-check coverage per claim (WS5 §2):",
        "  how many origin groups were content-checked vs metadata-only.",
        "- `verdicts.json`, `controls.json`, `adjudication.json`,",
        "  `queries.json` — the run's outcome and verdicts, controls,",
        "  human decisions, and every connector query, verbatim. The",
        "  outcome (`valid` / `invalid` / `not-run`) is stated in",
        "  `verdicts.json` itself: an invalid run issues no verdicts,",
        "  so without it the bundle could not show that the run failed.",
        "- `anchors/` — external anchor receipts, if any (see below).",
        "- `manifest.json` — the file list with SHA-256 hashes, the Merkle",
        "  checkpoint root, and the bundle hash that binds the set.",
        "",
        "## The study in numbers",
        "",
        f"- Ledger events: {study['event_count']}",
        f"- Run outcome: **{(run_outcome or {}).get('outcome', 'unknown')}**"
        + (f" — {'; '.join((run_outcome or {}).get('invalid_reasons') or [])}"
           if (run_outcome or {}).get('outcome') == "invalid" else "")
        + " (see `verdicts.json`)",
        f"- Claims in the register: {len(register.claims)}",
        f"- Adjudication items decided: {len(queue['decided'])}; "
        f"pending: {len(queue['pending'])}",
        f"- Merkle checkpoint root: `{study['checkpoint_root']}`",
        f"- Registration hash: `{study['registration_hash']}`",
        f"- Bundle hash: stated in `manifest.json` (`bundle_hash`).",
        *(
            ["- Control outcomes: **operator-attested** — this run "
             "predates control-outcome issuance events (Spec 013 "
             "CLM-013-03), so its per-control outcomes in "
             "`verdicts.json` are not cross-checked against ledger "
             "events the way a recorded run's are; they rest on the "
             "operator's attestation, bound by the manifest hashes "
             "only."]
            if (run_outcome or {}).get("outcome") == "valid"
            and (run_outcome or {}).get("controls")
            and not (run_outcome or {}).get("controls_recorded")
            else []
        ),
        "",
        "## How citation outcomes become evidence",
        "",
        "A citation's content outcome in `verification.json` and its",
        "evidence stance in `evidence/items.json` are two vocabularies",
        "for two stages; the conversion between them is fixed",
        "(`tekmerion.verification.to_evidence_item`):",
        "",
        "| content check | evidence stance | verdict mass |",
        "|---|---|---|",
        "| supports | supports | support mass |",
        "| contradicts | contradicts | contradiction mass |",
        "| contextual | contextual | none |",
        "| metadata_only | contextual | none — no content was checked (RT-5); context only, never carries a claim |",
        "| (quarantined: unresolved or metadata-disagreeing) | contextual | none — unverified; a run containing it is INVALID until adjudication |",
        "",
        "A contradicting item additionally carries",
        "`falsifier_observation` when the claim's registered falsifier",
        "names that item's resolved record (by DOI, or by first-author",
        "surname + year): the falsifier test then fires on the",
        "observation itself, not only on the interval. A citation",
        "excluded at adjudication appears in `adjudication.json`'s",
        "`excluded_citations` markers and nowhere in the evidence",
        "files.",
        "",
        "## Anchoring",
        "",
    ]
    if manifest["anchors"]:
        for receipt in manifest["anchors"]:
            lines.append(
                f"- Anchored via **{receipt.get('mechanism')}**: root "
                f"`{receipt.get('root')}` at {receipt.get('anchored_at')} — "
                f"locator: {receipt.get('locator')} (approved by "
                f"{receipt.get('approved_by')}). The receipt is also an event "
                "in the ledger (`anchor.recorded`).")
    else:
        lines += [
            "This bundle is **not externally anchored**. Its chain proves",
            "internal consistency, not history: only an external anchor",
            "(DN-005 layer 5) makes rewriting detectable by anyone. Do not",
            "rely on this bundle institutionally until it is anchored.",
        ]
    lines += ["", "## Content substitutions (WS5 §4)", ""]
    if manifest["content_substitutions"]:
        for sub in manifest["content_substitutions"]:
            lines.append(f"- `{sub['item']}`: {sub['reason']} → {sub['substitute']}")
    else:
        lines.append("None — every retrieved item with content was either "
                     "redistributable or carried no content.")
    lines += [
        "",
        "## How to verify this bundle",
        "",
        "1. Recompute the SHA-256 of every file listed in `manifest.json`",
        "   and compare — any mismatch means the bundle was altered.",
        "2. Verify the ledger with any Axiomere verifier",
        "   (`axiomere verify-file ledger/study.axmr`): the hash chain and",
        "   every signature must check out, and the latest checkpoint's",
        "   Merkle root must equal `checkpoint_root` in the manifest.",
        "3. Recompute the registration hash from `registration.json`",
        "   (canonical JSON, SHA-256) and compare it with the",
        "   `study.frozen` event inside the ledger.",
        "4. Or run the standalone verifier, which does all of the above",
        "   and the cross-checks between files:",
        "   `python -m tekmerion.export <bundle-dir>` from the Tekmerion",
        "   repository (it reads only the bundle).",
        "",
        "Projections in this bundle (claims, coverage, adjudication) are",
        "cross-checked against the ledger they project. Content that is",
        "not represented in the ledger is bound by the manifest hashes —",
        "and, once anchored, by the bundle hash stated in the public",
        "anchor record.",
        "",
        *banner,
        "",
    ]
    return "\n".join(lines)


def record_export(store: Any, manifest: dict[str, Any], *, actor: str) -> dict:
    """Append the `export.generated` event (WS4 §1) to the study
    ledger, recording that this bundle was produced from it. The
    bundle itself is a snapshot; this event belongs to the continuing
    record and appears in the *next* export's ledger copy."""
    return store.db.append(
        "export.generated",
        {"bundle_hash": manifest["bundle_hash"],
         "checkpoint_root": manifest["study"]["checkpoint_root"],
         "event_count": manifest["study"]["event_count"]},
        actor=actor,
    )


# ------------------------------------------------------------------ standalone verification

def _rederive_composite(register: ClaimRegister, parent_id: str,
                        issued: dict[str, Any], failures: list[str]) -> None:
    """Re-derive a math-layer composite verdict (Spec 003
    TheoremVerdict payload) from the bundle alone: each embedded
    sub-verdict must reproduce through verdicts.evaluate_claim on the
    sub-claim's fold, and the parent must re-compose through
    mathclaims.compose_parent from those sub-verdicts and the
    payload's own composition inputs. Appends to `failures`."""
    from . import mathclaims

    subs: dict[str, dict[str, Any]] = {}
    diffs: list[str] = []
    try:
        for role in mathclaims.ROLES:
            sid = mathclaims.subclaim_id(parent_id, role)
            if sid not in register.claims:
                diffs.append(f"sub-claim {sid} ({role}) not in the register")
                continue
            cv = evaluate_claim(register.claims[sid],
                                register.group_masses(sid))
            subs[role] = {"verdict": cv.verdict, "reason": cv.reason}
            embedded = (issued.get("sub_verdicts") or {}).get(role, {})
            if cv.verdict != embedded.get("verdict") or \
                    cv.reason != embedded.get("reason"):
                diffs.append(
                    f"sub-verdict {role}: issued {embedded.get('verdict')!r}, "
                    f"re-derived {cv.verdict!r}")
    except ValueError as exc:
        failures.append(
            f"standing verdict for {parent_id} cannot be re-derived: {exc}")
        return
    if diffs:
        failures.append(
            f"standing verdict for {parent_id} does not re-derive from "
            "the bundle's evidence: " + "; ".join(diffs))
        return
    try:
        composed = mathclaims.compose_parent(
            parent_id, subs,
            attribution_contested=issued.get("attribution") == "contested",
            remains_not_understood=issued.get("remains_not_understood", ""),
            digestion=issued.get("digestion", {}),
            lane1_verification=issued.get("lane1_verification", ""),
            lane2_acceptance=issued.get("lane2_acceptance", ""))
    except ValueError as exc:
        failures.append(
            f"standing verdict for {parent_id} cannot be re-composed "
            f"from its re-derived sub-verdicts: {exc}")
        return
    if composed.verdict != issued.get("verdict") or \
            composed.reason != issued.get("reason"):
        failures.append(
            f"standing verdict for {parent_id} does not re-derive from "
            "the bundle's evidence: composed verdict "
            f"{composed.verdict!r} / reason {composed.reason!r} vs "
            f"issued {issued.get('verdict')!r} / {issued.get('reason')!r}")


@dataclass
class BundleVerification:
    ok: bool
    failures: list[str] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)


def verify_bundle(bundle_dir: str) -> BundleVerification:
    """Verify a bundle using only the bundle. Every check that can
    fail is collected; `ok` requires all of them to pass."""
    root = Path(bundle_dir)
    failures: list[str] = []
    checks: dict[str, Any] = {}

    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return BundleVerification(False, ["manifest.json missing"], checks)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return BundleVerification(False, [f"manifest.json does not parse: {exc}"], checks)
    if manifest.get("format") != BUNDLE_FORMAT:
        failures.append(f"unknown bundle format {manifest.get('format')!r}")
    checks["format"] = manifest.get("format")

    # -- manifest self-consistency -------------------------------------
    core = {k: v for k, v in manifest.items() if k != "bundle_hash"}
    recomputed = _sha256(_canonical(core))
    if recomputed != manifest.get("bundle_hash"):
        failures.append("bundle hash mismatch: manifest does not bind this file set")
    checks["bundle_hash"] = manifest.get("bundle_hash")

    listed: dict[str, dict[str, Any]] = {}
    for entry in manifest.get("files", []):
        listed[entry["path"]] = entry
        path = root / entry["path"]
        if not path.exists():
            failures.append(f"listed file missing: {entry['path']}")
            continue
        data = path.read_bytes()
        if len(data) != entry["bytes"]:
            failures.append(f"size mismatch: {entry['path']}")
        if _sha256(data) != entry["sha256"]:
            failures.append(f"sha256 mismatch: {entry['path']}")
    checks["files_listed"] = len(listed)

    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*") if p.is_file()
    } - {"manifest.json"}
    for rel in sorted(actual - set(listed)):
        failures.append(f"unlisted file present in bundle: {rel}")
    for rel in sorted(set(listed) - actual):
        if (root / rel).exists() is False and f"listed file missing: {rel}" not in failures:
            failures.append(f"listed file missing: {rel}")

    def load_json(rel: str) -> Any:
        try:
            return json.loads((root / rel).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            failures.append(f"{rel} does not parse: {exc}")
            return None

    # -- the ledger, via the production verifier -------------------------
    study = manifest.get("study", {})
    ledger_rel = study.get("ledger_file", "ledger/study.axmr")
    ledger_path = root / ledger_rel
    events: list[dict[str, Any]] = []
    if ledger_path.exists():
        import axiomere as ax

        result = ax.verify_file(str(ledger_path))
        checks["ledger_verify"] = {
            "ok": result.ok, "events": result.events, "reason": result.reason,
            # The signature state rides in the verification record
            # (Axiomere Spec 003): an honestly unsigned ledger is a
            # visible state here, never a silent pass.
            "signatures_checked": result.signatures_checked,
            "signatures_failed": result.signatures_failed,
            "unsigned_events": list(result.unsigned_events),
            "untrusted_actors": list(result.untrusted_actors),
        }
        if not result.ok:
            failures.append(f"ledger fails production verification: {result.reason}")
        if result.events != study.get("event_count"):
            failures.append(
                f"ledger event count {result.events} != manifest {study.get('event_count')}")
        try:
            events = _ledger_events(ledger_path.read_bytes())
        except (ValueError, UnicodeDecodeError) as exc:
            failures.append(f"ledger does not parse as JSONL: {exc}")
    if events:
        if events[-1]["hash"] != study.get("head_hash"):
            failures.append("manifest head hash does not match the exported ledger head")
        checkpoints = _checkpoints(events)
        if checkpoints != study.get("checkpoints"):
            failures.append("manifest checkpoints do not match the exported ledger")
        if not checkpoints or checkpoints[-1]["merkle_root"] != study.get("checkpoint_root"):
            failures.append("manifest checkpoint root is not the ledger's latest checkpoint root")
        checks["checkpoint_root"] = study.get("checkpoint_root")

        # Recomputed-root binding (Axiomere Spec 003 companion,
        # AXM-003-15): the manifest's checkpoint root and head hash
        # are also pinned through the production verifier, which
        # compares them against the values it recomputes from the
        # ledger's events. A root transplanted from another study's
        # ledger fails here even when the presented file's chain and
        # signatures are internally consistent — the comparison
        # above, payload against payload, cannot see that lie.
        pin_spec: dict[str, Any] = {}
        if study.get("checkpoint_root"):
            pin_spec["checkpoint_root"] = study["checkpoint_root"]
        if study.get("head_hash"):
            pin_spec["head_hash"] = study["head_hash"]
        if pin_spec and result.ok:
            pinned = ax.verify_file(str(ledger_path), expected_head=pin_spec)
            checks["ledger_head_pin"] = {"ok": pinned.ok, "reason": pinned.reason}
            if not pinned.ok:
                failures.append(
                    "manifest head does not match the recomputed head: "
                    f"{pinned.reason}")

    frozen = [e for e in events if e["type"] == "study.frozen"]
    if not frozen:
        failures.append("no study.frozen event in the exported ledger")
        frozen_event = None
    else:
        # Consumers bind through binding_frozen_event (Spec 013
        # CLM-013-07): a labeled amendment when one exists, else the
        # binding freeze — see that function for the legacy
        # multi-freeze rule and its recorded limitation.
        frozen_event = binding_frozen_event(events)

    # -- registration binding ---------------------------------------------
    registration = load_json("registration.json")
    claims_doc = load_json("claims.json")
    if registration is not None:
        digest = registration_hash(registration)
        if digest != study.get("registration_hash"):
            failures.append("registration.json does not hash to the manifest registration hash")
        if frozen_event is not None and digest != frozen_event["payload"]["registration_hash"]:
            failures.append("registration.json is not the registration committed in the ledger")
    if claims_doc is not None:
        claim_ids = sorted(c["claim_id"] for c in claims_doc.get("claims", []))
        if frozen_event is not None and claim_ids != sorted(frozen_event["payload"]["claims"]):
            failures.append("claims.json register does not match the frozen claim set in the ledger")
        if registration is not None:
            reg_claims = sorted(
                (c["claim_id"], json.dumps(c, sort_keys=True))
                for c in registration.get("claims", []))
            bundle_claims = sorted(
                (c["claim_id"], json.dumps(c, sort_keys=True))
                for c in claims_doc.get("claims", []))
            if reg_claims != bundle_claims:
                failures.append("claims.json and registration.json disagree on the register")
        for c in claims_doc.get("claims", []):
            if not (c.get("falsifier") or "").strip():
                failures.append(f"claim {c.get('claim_id')} in bundle has no falsifier (Article II)")
    checks["claims"] = len(claims_doc.get("claims", [])) if claims_doc else 0

    # -- projection cross-checks against the ledger -------------------------
    def count_events(kind: str) -> int:
        return sum(1 for e in events if e["type"] == kind)

    def projection_matches(entries: Any, kind: str, *, envelope: bool) -> bool:
        """A projection file's entries must equal the ledger's own
        events of that kind — payload for payload, not just in count.
        (Phase 7 K2 finding: a count-only check let a flipped verdict
        string in verdicts.json pass verification on a rehashed
        bundle; the ledger copy inside the bundle is the ground truth
        the projection is checked against.)"""
        if not isinstance(entries, list):
            return False
        expected = [
            ({"seq": e["seq"], "actor": e["actor"], **e["payload"]}
             if envelope else dict(e["payload"]))
            for e in events if e["type"] == kind
        ]
        canon = lambda lst: sorted(json.dumps(x, sort_keys=True) for x in lst)
        return canon(entries) == canon(expected)

    queries = load_json("queries.json")
    if queries is not None and not projection_matches(queries.get("queries"), "connector.query", envelope=False):
        failures.append("queries.json does not match the ledger's connector.query events")
    verdicts = load_json("verdicts.json")
    if verdicts is not None and not projection_matches(verdicts.get("verdicts"), "verdict.issued", envelope=True):
        failures.append("verdicts.json does not match the ledger's verdict.issued events")

    # -- CUI marking (Spec 005 T551): where the manifest carries a
    # marking block, the HUMAN-README must carry its banner/footer —
    # the marking a human sees is the marking the manifest records.
    # Bundles exported before T551 carry no block; absence is noted,
    # not failed (their manifests predate the field).
    marking_block = manifest.get("cui_marking")
    if marking_block is not None:
        readme_path = root / "HUMAN-README.md"
        if readme_path.exists():
            readme_lines = [ln for ln in readme_path.read_text(
                encoding="utf-8").splitlines() if ln.strip()]
            expected = banner_lines(marking_block)
            if not readme_lines or readme_lines[0] not in expected \
                    or readme_lines[-1] not in expected:
                failures.append(
                    "HUMAN-README does not carry the manifest's CUI "
                    "marking banner/footer (T551)")
            checks["cui_marking"] = marking_block.get("status")
    else:
        checks["cui_marking"] = "absent (pre-T551 bundle)"

    # -- run-outcome projection (NC-6): cross-check what the bundle alone
    # can decide. Bundles exported before the projection existed carry
    # no `run_outcome`; absence is visible and not a failure — the
    # projection's claims, where present, must not contradict the
    # bundle's own record.
    run_outcome = verdicts.get("run_outcome") if verdicts is not None else None
    if run_outcome is not None:
        checks["run_outcome"] = run_outcome.get("outcome")
        n_issued = count_events("verdict.issued")
        if run_outcome.get("verdicts_issued") != n_issued:
            failures.append(
                "verdicts.json run_outcome.verdicts_issued "
                f"({run_outcome.get('verdicts_issued')}) does not match the ledger's "
                f"verdict.issued events ({n_issued})")
        stated = run_outcome.get("outcome")
        reasons = run_outcome.get("invalid_reasons") or []
        items_doc = load_json("evidence/items.json")
        unverified = [i for i in (items_doc or {}).get("items", [])
                      if i.get("verified") is False]
        swap_detected: Optional[bool] = None
        if events and ledger_path.exists():
            swap_detected = swap_control_report(str(ledger_path))["detected"]
        if stated == "valid" and n_issued == 0:
            failures.append(
                "verdicts.json run_outcome claims a valid run but the ledger "
                "carries no verdict.issued events")
        if stated in ("invalid", "not-run") and n_issued > 0:
            failures.append(
                f"verdicts.json run_outcome claims {stated} but the ledger "
                "carries verdict.issued events")
        if stated == "invalid":
            if not reasons:
                failures.append(
                    "verdicts.json run_outcome is invalid but states no reasons")
            if any("unverified citation" in r for r in reasons) and not unverified:
                failures.append(
                    "verdicts.json run_outcome cites unverified citations but "
                    "evidence/items.json carries none")
            if (any("swap control failed" in r for r in reasons)
                    and swap_detected is True):
                failures.append(
                    "verdicts.json run_outcome cites a swap-control failure but "
                    "the swap control replayed on the bundle's ledger detects "
                    "the tamper")
        if stated == "not-run":
            if unverified:
                failures.append(
                    "verdicts.json run_outcome claims not-run but the bundle "
                    "carries unverified evidence — a replayed run would be "
                    "invalid")
            if swap_detected is False:
                failures.append(
                    "verdicts.json run_outcome claims not-run but the swap "
                    "control replayed on the bundle's ledger does not detect "
                    "its tamper — a replayed run would be invalid")
        # -- per-control outcomes (Spec 011): checked against everything
        # the bundle alone can decide — the committed registration's
        # control set, the stated run outcome, and the verifier's own
        # swap replay. Absent in pre-Spec-011 bundles: noted, not failed.
        outcomes = run_outcome.get("controls")
        if outcomes is None:
            checks["control_outcomes"] = "absent (pre-Spec-011 bundle)"
        elif not isinstance(outcomes, list) or not all(
                isinstance(o, dict) for o in outcomes):
            failures.append("verdicts.json run_outcome controls is not a list of objects")
        else:
            checks["control_outcomes"] = len(outcomes)
            if registration is not None:
                canon = lambda lst: sorted(
                    _canonical([o.get("kind"), o.get("failure_mode"),
                                o.get("expected")]) for o in lst)
                if canon(outcomes) != canon(registration.get("controls", [])):
                    failures.append(
                        "verdicts.json run_outcome controls do not match the "
                        "registration's committed control set")
                # Fixture identities committed in the registration
                # (Spec 013 CLM-013-09): an outcome that names a
                # fixture must name the committed one. Registrations
                # predating the commitment carry no fixture field —
                # nothing to check against, noted not failed.
                committed_fixtures = {}
                for entry in registration.get("controls", []):
                    if "fixture" in entry:
                        fixture = entry.get("fixture") or {}
                        committed_fixtures[
                            (entry.get("kind"), entry.get("failure_mode"))] = \
                            fixture.get("sha256")
                for o in outcomes:
                    key = (o.get("kind"), o.get("failure_mode"))
                    fixture = o.get("fixture") or {}
                    if key in committed_fixtures and fixture.get("sha256") is not None \
                            and fixture["sha256"] != committed_fixtures[key]:
                        failures.append(
                            "verdicts.json run_outcome records a fixture "
                            "identity for the "
                            f"{key[0]} control that differs from the "
                            "registration's committed fixture (CLM-013-09)")
            # Control outcomes recorded at issuance (Spec 013
            # CLM-013-03): when the ledger carries control.outcome
            # events for the latest run, the projection's EXECUTED
            # outcomes must equal them payload-for-payload — the K2
            # discipline, extended to outcomes (the projection also
            # carries not-executed entries for committed controls the
            # run never executed; those are projection statements, not
            # record). Bundles of runs predating the issuance carry
            # no such events: their outcomes are the operator-attested
            # case, visible in checks, not failed.
            run_indexes = [i for i, e in enumerate(events)
                           if e["type"] == "run.issued"]
            recorded_outcomes: list[dict[str, Any]] = []
            if run_indexes:
                recorded_outcomes = [
                    e["payload"] for e in events[run_indexes[-1] + 1:]
                    if e["type"] == "control.outcome"]
            if recorded_outcomes:
                checks["control_outcomes_recorded"] = len(recorded_outcomes)
                canon = lambda lst: sorted(_canonical(o) for o in lst)
                executed_outcomes = [o for o in outcomes if o.get("executed")]
                if canon(executed_outcomes) != canon(recorded_outcomes):
                    failures.append(
                        "verdicts.json run_outcome executed controls do "
                        "not match the ledger's control.outcome events "
                        "(CLM-013-03)")
                if not run_outcome.get("controls_recorded"):
                    failures.append(
                        "verdicts.json run_outcome does not mark its "
                        "control outcomes as ledger-recorded but the "
                        "ledger carries control.outcome events for the "
                        "run (CLM-013-03)")
            elif run_outcome.get("controls_recorded"):
                failures.append(
                    "verdicts.json run_outcome claims ledger-recorded "
                    "control outcomes but the ledger carries no "
                    "control.outcome events for the run (CLM-013-03)")
            else:
                checks["control_outcomes_recorded"] = 0
            failed_outcomes = [o for o in outcomes if o.get("passed") is False]
            if stated == "valid" and failed_outcomes:
                failures.append(
                    "verdicts.json run_outcome claims a valid run but records "
                    "a failed control outcome")
            if stated == "not-run" and failed_outcomes:
                failures.append(
                    "verdicts.json run_outcome claims not-run but records a "
                    "failed control outcome — a replayed run would be invalid")
            if stated == "invalid":
                if any("control" in r for r in reasons) and not failed_outcomes:
                    failures.append(
                        "verdicts.json run_outcome cites a control failure "
                        "but records no failed control outcome")
                for o in failed_outcomes:
                    if o.get("detail") and o["detail"] not in reasons:
                        failures.append(
                            "verdicts.json run_outcome records a control "
                            "failure that is not among the stated invalid "
                            "reasons")
            if swap_detected is not None:
                for o in outcomes:
                    if o.get("kind") == "swap" and o.get("executed"):
                        if o.get("passed") is not swap_detected:
                            failures.append(
                                "verdicts.json run_outcome records a swap "
                                "control outcome that disagrees with the swap "
                                "replayed on the bundle's ledger")

    verification_doc = load_json("verification.json")
    if verification_doc is not None:
        outcomes = verification_doc.get("citation_outcomes", [])
        if len(outcomes) != count_events("citation.checked"):
            failures.append("verification.json outcomes do not match citation.checked events")
        ledger_outcomes = [e["payload"] for e in events if e["type"] == "citation.checked"]
        if outcomes != ledger_outcomes:
            failures.append("verification.json outcomes differ from the ledgered outcomes")
        # -- as-cited forms (Spec 011): each must key-match and agree
        # with the ledger on the citation's claim linkage. Absent when
        # the exporter was not given citation inputs: noted, not failed.
        as_cited = verification_doc.get("as_cited")
        if as_cited is None:
            checks["as_cited"] = "absent"
        elif not isinstance(as_cited, dict):
            failures.append("verification.json as_cited is not an object")
        else:
            checks["as_cited"] = len(as_cited)
            outcome_by_id = {o.get("citation_id"): o for o in ledger_outcomes}
            for cid_key, form in as_cited.items():
                if not isinstance(form, dict) or form.get("citation_id") != cid_key:
                    failures.append(
                        f"verification.json as_cited entry {cid_key} does not "
                        "carry its own citation id")
                    continue
                outcome = outcome_by_id.get(cid_key)
                if outcome is None:
                    failures.append(
                        f"verification.json as_cited carries {cid_key} but the "
                        "ledger has no citation.checked outcome for it")
                elif form.get("claim_id") != outcome.get("claim_id"):
                    failures.append(
                        f"verification.json as_cited claim for {cid_key} "
                        "disagrees with the ledger's citation.checked outcome")
        adapter = _EventsOnlyStore(events)
        if verification_doc.get("second_review") != second_review_report(adapter):
            failures.append("verification.json second-review report does not match the ledger")
        # content inclusion must obey the rights gate (WS5 §4)
        content_dir = root / "evidence" / "content"
        present = {p.name for p in content_dir.glob("*")} if content_dir.exists() else set()
        for citation_id, stub in verification_doc.get("retrieved", {}).items():
            fname = f"{citation_id.replace('/', '_')}.txt"
            if stub.get("content_included"):
                if fname not in present:
                    failures.append(f"content file missing for {citation_id}")
                if not redistribution_permitted(stub.get("license_basis", "")):
                    failures.append(
                        f"content included for {citation_id} without redistribution rights")
            elif fname in present:
                failures.append(f"content file present for {citation_id} but marked stub-only")
        for sub in manifest.get("content_substitutions", []):
            if f"{sub['item'].replace('/', '_')}.txt" in present:
                failures.append(f"substituted item {sub['item']} nevertheless has a content file")

    adjudication = load_json("adjudication.json")
    if adjudication is not None and events:
        state = queue_state(_EventsOnlyStore(events))
        mine = {i["queue_id"]: i for i in state["pending"] + state["decided"]}
        theirs = {i["queue_id"]: i for i in
                  adjudication.get("pending", []) + adjudication.get("decided", [])}
        if set(mine) != set(theirs):
            failures.append("adjudication.json item set does not match the ledger replay")
        else:
            for qid, item in mine.items():
                other = theirs[qid]
                if (item["status"], item.get("decision")) != (other["status"], other.get("decision")):
                    failures.append(f"adjudication item {qid} disagrees with the ledger replay")
        # -- exclusion markers (Spec 011): the set the replay derives
        # vs the set the bundle carries, and no marked citation back
        # in the evidence files. Absent pre-Spec-011: noted, not failed.
        markers = adjudication.get("excluded_citations")
        if markers is None:
            checks["excluded_citations"] = "absent (pre-Spec-011 bundle)"
        elif not isinstance(markers, list):
            failures.append("adjudication.json excluded_citations is not a list")
        else:
            checks["excluded_citations"] = len(markers)
            expected_markers = _excluded_markers(state)
            canon = lambda lst: sorted(_canonical(m) for m in lst
                                       if isinstance(m, dict))
            if len(canon(markers)) != len(markers) or canon(markers) != canon(expected_markers):
                failures.append(
                    "adjudication.json excluded_citations do not match the "
                    "ledger replay")
            items_doc = load_json("evidence/items.json")
            evidence_ids = {i.get("item_id") for i in (items_doc or {}).get("items", [])}
            for marker in markers:
                if isinstance(marker, dict) and marker.get("citation_id") in evidence_ids:
                    failures.append(
                        f"excluded citation {marker.get('citation_id')} is "
                        "nevertheless present in evidence/items.json")

    coverage = load_json("coverage.json")
    groups_doc = load_json("evidence/groups.json")
    if coverage is not None and groups_doc is not None:
        per_claim = coverage.get("per_claim", {})
        for cid, entry in per_claim.items():
            groups = [g for g in groups_doc.get("groups", []) if g["claim_id"] == cid]
            g_meta = sum(1 for g in groups if g["metadata_only"])
            if (entry["origin_groups"], entry["groups_metadata_only"]) != (len(groups), g_meta):
                failures.append(f"coverage for {cid} disagrees with evidence/groups.json")
            cites = [e["payload"] for e in events
                     if e["type"] == "citation.checked" and e["payload"]["claim_id"] == cid]
            if entry["citations_checked"] != len(cites):
                failures.append(f"coverage citation count for {cid} disagrees with the ledger")
        checks["coverage_claims"] = len(per_claim)

    # -- evidence fold + verdict re-derivation (Spec 013 CLM-013-01;
    # RTA-01). The K2 discipline that binds verdicts.json and
    # queries.json payload-for-payload extends to the evidence
    # projections: the fold of evidence/items.json through the
    # production register must reproduce evidence/groups.json
    # field-for-field, and every standing verdict (the latest
    # verdict.issued per claim; superseded verdicts stay bound by the
    # projection cross-check above) must re-derive from claims.json +
    # the fold through the production verdict path. Citation-path
    # verdicts re-derive through verdicts.evaluate_claim; the math
    # layer's composite (TheoremVerdict) payloads re-derive per
    # sub-claim through evaluate_claim and re-compose through
    # mathclaims.compose_parent — the same functions that issued
    # them. Before this check, items.json was bound only by the
    # manifest hash: flipping an item's stance and rehashing the
    # manifest produced a verifier-approved bundle whose own evidence
    # re-derives the opposite verdict.
    items_doc = None
    if claims_doc is not None and groups_doc is not None and \
            (root / "evidence" / "items.json").exists():
        items_doc = load_json("evidence/items.json")
    if items_doc is not None:
        claim_fields = set(Claim.__dataclass_fields__)
        item_fields = set(EvidenceItem.__dataclass_fields__)
        register: Optional[ClaimRegister] = ClaimRegister()
        try:
            for c in claims_doc.get("claims", []):
                register.register(Claim(
                    **{k: c[k] for k in claim_fields if k in c}))
            for it in items_doc.get("items", []):
                register.add_evidence(it.get("claim_id"), EvidenceItem(
                    **{k: it[k] for k in item_fields if k in it}))
        except (RegistrationError, TypeError, KeyError) as exc:
            failures.append(
                "bundle register cannot be reconstructed from claims.json "
                f"+ evidence/items.json: {exc}")
            register = None
        if register is not None:
            folded: dict[tuple, dict[str, Any]] = {}
            for cid in register.claims:
                for g in register.group_masses(cid):
                    folded[(cid, g["origin_group"])] = g
            filed: dict[tuple, dict[str, Any]] = {}
            for g in groups_doc.get("groups", []):
                filed[(g.get("claim_id"), g.get("origin_group"))] = g
            checks["evidence_fold_groups"] = len(filed)
            if set(folded) != set(filed):
                failures.append(
                    "evidence/groups.json group set does not match the "
                    "fold of evidence/items.json "
                    f"(fold only: {sorted(set(folded) - set(filed), key=str)}; "
                    f"file only: {sorted(set(filed) - set(folded), key=str)})")
            for key in sorted(set(folded) & set(filed), key=str):
                for fname, fval in folded[key].items():
                    if filed[key].get(fname) != fval:
                        failures.append(
                            f"evidence/groups.json {key} field {fname} is "
                            f"{filed[key].get(fname)!r} but the fold of "
                            f"evidence/items.json gives {fval!r}")
                        break
            if verdicts is not None:
                standing: dict[str, dict[str, Any]] = {}
                for v in verdicts.get("verdicts", []):
                    cid = v.get("claim_id")
                    if cid not in standing or \
                            v.get("seq", 0) >= standing[cid].get("seq", 0):
                        standing[cid] = v
                checks["verdicts_rederived"] = 0
                for cid, issued in sorted(standing.items()):
                    if cid not in register.claims:
                        failures.append(
                            f"verdicts.json issues a verdict for {cid}, "
                            "which is not in the bundle's claim register")
                        continue
                    if "sub_verdicts" in issued:
                        _rederive_composite(
                            register, cid, issued, failures)
                    else:
                        derived = evaluate_claim(
                            register.claims[cid], register.group_masses(cid))
                        diffs = []
                        if derived.verdict != issued.get("verdict"):
                            diffs.append(
                                f"verdict: issued {issued.get('verdict')!r}, "
                                f"re-derived {derived.verdict!r}")
                        if "reason" in issued and derived.reason != issued["reason"]:
                            diffs.append("reason differs")
                        if "origin_groups" in issued and \
                                derived.groups != issued["origin_groups"]:
                            diffs.append(
                                f"origin_groups: issued "
                                f"{issued['origin_groups']}, re-derived "
                                f"{derived.groups}")
                        if "interval" in issued and \
                                list(derived.interval) != list(issued["interval"]):
                            diffs.append(
                                f"interval: issued {issued['interval']}, "
                                f"re-derived {list(derived.interval)}")
                        if "point" in issued and derived.point != issued["point"]:
                            diffs.append(
                                f"point: issued {issued['point']}, "
                                f"re-derived {derived.point}")
                        if diffs:
                            failures.append(
                                f"standing verdict for {cid} does not "
                                "re-derive from the bundle's evidence: "
                                + "; ".join(diffs))
                    checks["verdicts_rederived"] += 1

    # -- anchors -------------------------------------------------------------
    anchor_events = [e["payload"] for e in events if e["type"] == "anchor.recorded"]
    manifest_anchors = manifest.get("anchors", [])
    if sorted(_canonical(a) for a in anchor_events) != sorted(_canonical(a) for a in manifest_anchors):
        failures.append("manifest anchors do not match the ledger's anchor.recorded events")
    checkpoint_roots = {c["merkle_root"] for c in study.get("checkpoints", [])}
    for receipt in manifest_anchors:
        for field_name in ("mechanism", "root", "locator", "anchored_at", "approved_by"):
            if not receipt.get(field_name):
                failures.append(f"anchor receipt missing {field_name}")
        if receipt.get("root") not in checkpoint_roots:
            failures.append("anchor receipt root is not a checkpoint root of this ledger")
    checks["anchors"] = len(manifest_anchors)

    return BundleVerification(ok=not failures, failures=failures, checks=checks)


# ------------------------------------------------------------------ anchor verification

@dataclass
class AnchorVerification:
    ok: bool
    failures: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def verify_anchor(bundle_dir: str, public_record: dict[str, Any], *,
                  package_path: Optional[str] = None) -> AnchorVerification:
    """Check a bundle against the public anchor record (e.g. the
    Zenodo record JSON). Two bindings, both required:

    (a) **Own-hash binding (Spec 013 CLM-013-02).** The record must
    state the *presented* bundle's own `bundle_hash` and checkpoint
    root. The outcome is named in `details["own_hash_anchor"]`
    ("anchored" / "unanchored"). Before this binding, the check
    validated only an earlier bundle's receipt the presented bundle
    happened to carry, so a rehashed bundle passed against a record
    that anchors a different bundle entirely (RTA-02).

    (b) **Receipt chain.** A receipt the bundle carries that names
    this record must validate against it: its root must be a
    checkpoint root of the bundle's ledger — the anchored root
    existed at the record's creation time, and the record is the
    external party's, its timestamp not the operator's to backdate —
    and the record must state the receipt's root and hash, with the
    deposited file's checksum matching the receipt (and the local
    package, when presented).

    A bundle carrying no receipt for this record is not failed for
    that alone: a bundle's own deposit receipt is appended to the
    study ledger only after deposit, so the deposited bundle itself
    never carries it (it rides in the next export). When no carried
    receipt names this record, the record is treated as the bundle's
    own deposit record and a presented package is bound by the
    record's own file list."""
    failures: list[str] = []
    details: dict[str, Any] = {}

    bundle = verify_bundle(bundle_dir)
    if not bundle.ok:
        failures.append(f"bundle itself does not verify: {bundle.failures}")
        return AnchorVerification(False, failures, details)
    manifest = json.loads((Path(bundle_dir) / "manifest.json").read_text(encoding="utf-8"))

    record_id = public_record.get("id")
    record_doi = public_record.get("doi")
    metadata = public_record.get("metadata", {})
    stated = json.dumps(metadata, ensure_ascii=False)
    created = public_record.get("created")
    if not created:
        failures.append("public record carries no creation timestamp")
    details["record_created"] = created
    details["record_doi"] = record_doi
    files = {f.get("key"): f for f in public_record.get("files", [])}

    # (a) own-hash binding
    own_hash = manifest.get("bundle_hash")
    own_root = manifest.get("study", {}).get("checkpoint_root")
    details["bundle_hash"] = own_hash
    details["checkpoint_root"] = own_root
    if own_hash and own_hash in stated and own_root and own_root in stated:
        details["own_hash_anchor"] = "anchored"
    else:
        details["own_hash_anchor"] = "unanchored"
        failures.append(
            "presented bundle's own bundle_hash is not anchored in this "
            f"record: the record does not state this bundle's bundle_hash "
            f"({own_hash}) and checkpoint root ({own_root}) — it anchors "
            "a different bundle, so a rehashed bundle is indistinguishable "
            "from this one against this record (CLM-013-02)")

    # (b) receipt chain, for a carried receipt naming this record
    receipts = manifest.get("anchors", [])
    receipt = next(
        (r for r in receipts
         if (record_doi and r.get("doi") == record_doi)
         or (record_id is not None and str(r.get("record_id")) == str(record_id))),
        None)
    details["receipt"] = receipt
    if receipt is not None:
        checkpoint_roots = {c["merkle_root"] for c in manifest["study"]["checkpoints"]}
        if receipt.get("root") not in checkpoint_roots:
            failures.append("anchored root is not a checkpoint root of the bundle's ledger")
        if receipt.get("root") not in stated:
            failures.append("public record does not state the anchored root")
        if receipt.get("bundle_hash") not in stated:
            failures.append("public record does not state the deposited bundle's hash")
        receipt_file = receipt.get("file", {})
        entry = files.get(receipt_file.get("name"))
        if entry is None:
            failures.append("deposited file not present in the public record")
        else:
            checksum = (entry.get("checksum") or "").removeprefix("md5:")
            if checksum and receipt_file.get("md5") and checksum != receipt_file["md5"]:
                failures.append("public record file checksum does not match the receipt")
            if package_path is not None:
                data = Path(package_path).read_bytes()
                if hashlib.md5(data).hexdigest() != receipt_file.get("md5"):
                    failures.append("local package does not match the receipt's deposited file")
                details["package_md5"] = hashlib.md5(data).hexdigest()
    elif package_path is not None:
        data = Path(package_path).read_bytes()
        package_md5 = hashlib.md5(data).hexdigest()
        details["package_md5"] = package_md5
        checksums = {(f.get("checksum") or "").removeprefix("md5:")
                     for f in files.values()}
        if package_md5 not in checksums:
            failures.append("local package does not match any file in the public record")
    return AnchorVerification(ok=not failures, failures=failures, details=details)


def _main(argv: list[str]) -> int:
    import sys

    if len(argv) != 2:
        print("usage: python -m tekmerion.export <bundle-dir>", file=sys.stderr)
        return 2
    result = verify_bundle(argv[1])
    print(json.dumps({"ok": result.ok, "failures": result.failures,
                      "checks": result.checks}, indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    import sys

    sys.exit(_main(sys.argv))
