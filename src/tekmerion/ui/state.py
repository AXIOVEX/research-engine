"""Workspace state for the register-first UI (Spec 002 Phase 6, T219).

Everything the UI shows is a **projection of a study's Axiomere
ledger**, rebuilt per request through the production services — the
register from `record.snapshot` state (`StudyStore.current_claims`),
the queue from `tekmerion.verification.queue_state`, verdicts from
`verdict.issued` events, anchors from `anchor.recorded` events. The
UI keeps no record of its own.

Two sidecars live beside each ledger in the workspace, both derived
data, neither of them the record:

- `meta.json` — display title + the RT-4 second-review draw
  parameters (fraction, seed) registered for the study.
- `freeze.json` — the frozen registration document, captured at
  freeze time. The ledger commits to it by hash (the `study.frozen`
  event); the workspace re-verifies that hash whenever it presents
  the document, and `tekmerion.export` refuses a mismatch anyway.
- `retrieved.json` / `citations.json` — connector responses and
  citation inputs from workspace attach actions. Retrievable data,
  cached so claim screens can show the retrieved record; the ledger
  remains what carries the outcomes.

Run presentation: a run's verdicts, once issued, are events and are
shown from them. Before any run is issued, the workspace *replays*
the run-level checks that are reconstructible from the record —
chain verification, the WS3 §1 structural checks, and the swap
control (RT-1) — through `tekmerion.verdicts.evaluate_run` itself.
An INVALID replay is displayed as INVALID with the engine's reasons.
(Phase 7 correction to this note: the swap control's event selection
was fixed — it exchanges the first pair of events with distinct
actors, or rewrites a probe actor on single-actor ledgers — so a
replay now applies the control as it stands today. The Phase 5 demo
study's INVALID was issued under the defective fixed lines-1/2
selection and stands as recorded; it is not re-derived here.)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from .. import deposit as deposit_mod
from .. import export as export_mod
from .. import verification as vf
from ..claims import Claim, ClaimRegister
from ..connectors import RetrievedItem
from ..freeze import freeze, registration_document, registration_hash
from ..store import StudyStore
from ..verdicts import Control, RunResult, evaluate_run

ROLES = ("researcher", "reviewer", "adjudicator", "integrity")
ROLE_LABELS = {
    "researcher": "Researcher",
    "reviewer": "Reviewer",
    "adjudicator": "Adjudicator",
    "integrity": "Integrity",
}

_STUDY_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class WorkspaceError(RuntimeError):
    pass


# ------------------------------------------------------------------ workspace

class Workspace:
    """A directory of studies: studies/<id>/{study.axmr, meta.json, …}."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        (self.root / "studies").mkdir(parents=True, exist_ok=True)

    def study_dir(self, study_id: str) -> Path:
        if not _STUDY_ID.match(study_id or ""):
            raise WorkspaceError(f"invalid study id {study_id!r}")
        return self.root / "studies" / study_id

    def ledger_path(self, study_id: str) -> Path:
        return self.study_dir(study_id) / "study.axmr"

    def exists(self, study_id: str) -> bool:
        return self.ledger_path(study_id).exists()

    def open(self, study_id: str) -> StudyStore:
        if not self.exists(study_id):
            raise WorkspaceError(f"no such study: {study_id}")
        return StudyStore.open(str(self.ledger_path(study_id)))

    def list_study_ids(self) -> list[str]:
        base = self.root / "studies"
        return sorted(p.name for p in base.iterdir()
                      if p.is_dir() and (p / "study.axmr").exists())

    def create_study(self, study_id: str, title: str) -> dict[str, Any]:
        d = self.study_dir(study_id)
        if self.exists(study_id):
            raise WorkspaceError(f"study {study_id} already exists")
        d.mkdir(parents=True, exist_ok=True)
        StudyStore.create(str(self.ledger_path(study_id)))
        meta = {
            "study_id": study_id,
            "title": title or study_id,
            "second_review_fraction": vf.DEFAULT_SECOND_REVIEW_FRACTION,
            "second_review_seed": 0,
        }
        self.write_sidecar(study_id, "meta.json", meta)
        return meta

    # -- sidecars ------------------------------------------------------

    def read_sidecar(self, study_id: str, name: str, default: Any = None) -> Any:
        path = self.study_dir(study_id) / name
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def write_sidecar(self, study_id: str, name: str, data: Any) -> None:
        path = self.study_dir(study_id) / name
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    def meta(self, study_id: str) -> dict[str, Any]:
        meta = self.read_sidecar(study_id, "meta.json", {}) or {}
        return {
            "study_id": study_id,
            "title": meta.get("title") or study_id,
            "second_review_fraction": meta.get(
                "second_review_fraction", vf.DEFAULT_SECOND_REVIEW_FRACTION),
            "second_review_seed": meta.get("second_review_seed", 0),
        }


# ------------------------------------------------------------------ projections

def _events(store: StudyStore) -> list[dict[str, Any]]:
    return store.events()


def frozen_event(store: StudyStore) -> Optional[dict[str, Any]]:
    frozen = [e for e in _events(store) if e["type"] == "study.frozen"]
    return frozen[-1] if frozen else None


def checkpoints(store: StudyStore) -> list[dict[str, Any]]:
    return [e["payload"] for e in _events(store) if e["type"] == "checkpoint"]


def freeze_checkpoint_root(store: StudyStore) -> Optional[str]:
    """The Merkle root of the checkpoint that sealed the freeze: the
    first checkpoint at or after the `study.frozen` event."""
    fe = frozen_event(store)
    if fe is None:
        return None
    for e in _events(store):
        if e["type"] == "checkpoint" and e["seq"] > fe["seq"]:
            return e["payload"]["merkle_root"]
    return None


def head_checkpoint_root(store: StudyStore) -> Optional[str]:
    cps = checkpoints(store)
    return cps[-1]["merkle_root"] if cps else None


def anchor_receipts(store: StudyStore) -> list[dict[str, Any]]:
    """Anchor receipts as the ledger holds them (CLM-002-40): payload
    plus the event's seq/actor, oldest first."""
    return [
        {**e["payload"], "_seq": e["seq"], "_actor": e["actor"]}
        for e in _events(store) if e["type"] == "anchor.recorded"
    ]


def export_events(store: StudyStore) -> list[dict[str, Any]]:
    return [
        {**e["payload"], "_seq": e["seq"], "_actor": e["actor"]}
        for e in _events(store) if e["type"] == "export.generated"
    ]


def verdicts_by_claim(store: StudyStore) -> dict[str, dict[str, Any]]:
    """Latest `verdict.issued` payload per claim (a changed verdict is
    a new event superseding by order — the latest is the current one)."""
    out: dict[str, dict[str, Any]] = {}
    for e in _events(store):
        if e["type"] == "verdict.issued":
            p = e["payload"]
            out[p["claim_id"]] = {**p, "_seq": e["seq"], "_actor": e["actor"]}
    return out


def citation_results(store: StudyStore) -> dict[str, dict[str, Any]]:
    """Latest `citation.checked` payload per citation, in check order."""
    out: dict[str, dict[str, Any]] = {}
    for e in _events(store):
        if e["type"] == "citation.checked":
            out[e["payload"]["citation_id"]] = e["payload"]
    return out


_CLAIM_FIELDS = ("claim_id", "statement", "falsifier", "kind", "dependencies",
                 "margin", "sufficiency_floor", "supersedes", "status")


def rebuild_register(store: StudyStore) -> tuple[ClaimRegister, dict[str, Any]]:
    """Rebuild the ClaimRegister from the ledger's record state.

    Claims come from the engine's own projection
    (`current_claims(include_dead=True)`): dead records keep their
    reason and 0.0 score in `info['dead']`. Evidence is derived from
    `citation.checked` events plus adjudication outcomes (see
    `derive_evidence`)."""
    register = ClaimRegister()
    info: dict[str, Any] = {"dead": {}, "order": []}

    first_seen: dict[str, int] = {}
    for e in _events(store):
        if e["type"] == "record.snapshot":
            rid = e["payload"].get("record_id", "")
            if rid.startswith("CLM-") and rid not in first_seen:
                first_seen[rid] = e["seq"]
                info["order"].append(rid)

    current = store.current_claims(include_dead=True)
    for cid in sorted(current, key=lambda c: first_seen.get(c, 1 << 30)):
        entry = current[cid]
        content = entry.get("content") or {}
        if not content.get("claim_id"):
            continue
        claim = Claim(**{k: content[k] for k in _CLAIM_FIELDS if k in content})
        if entry.get("status") == "dead":
            claim.status = "dead"
            info["dead"][cid] = {
                "reason": entry.get("reason") or "",
                "score": entry.get("score", 0.0),
            }
        register.claims[cid] = claim
        if cid not in info["order"]:
            info["order"].append(cid)
    # Supersede links, applied as the register itself applies them:
    # a superseding claim marks its target superseded (unless dead).
    for claim in register.claims.values():
        if claim.supersedes and claim.supersedes in register.claims:
            target = register.claims[claim.supersedes]
            if target.status != "dead":
                target.status = "superseded"

    fe = frozen_event(store)
    if fe is not None:
        register.frozen = True
        register.registration_hash = fe["payload"].get("registration_hash")
    return register, info


def derive_evidence(store: StudyStore, register: ClaimRegister,
                    retrieved: dict[str, Any]) -> dict[str, list[Any]]:
    """Fold the ledger's citation outcomes into register evidence.

    The mapping is `verification.to_evidence_item`'s, with the
    adjudication outcomes applied: `exclude` removes the item from
    the evidence basis; `variant` lets it stand with its recorded
    content outcome; a grouping `same_origin` decision merges the
    pair's groups; an undecided quarantined item stays unverified —
    a run containing it is INVALID (WS5 §1.2)."""
    results = citation_results(store)
    queue = vf.queue_state(store)
    decided_by_citation: dict[str, dict[str, Any]] = {}
    grouping_unions: list[tuple[str, str]] = []
    for item in queue["decided"]:
        if item.get("kind") == "quarantine" and item.get("citation_id"):
            decided_by_citation[item["citation_id"]] = item
        elif item.get("kind") == "grouping" and item.get("citation_ids"):
            if item.get("decision") == "same_origin":
                grouping_unions.append(tuple(item["citation_ids"]))

    items_by_claim: dict[str, list[Any]] = {}
    raw_items: dict[str, Any] = {}
    for cid, payload in results.items():
        claim_id = payload.get("claim_id")
        if claim_id not in register.claims:
            continue
        decision_item = decided_by_citation.get(cid)
        if decision_item and decision_item.get("decision") == "exclude":
            continue  # excluded from the evidence basis by adjudication
        res = vf.CitationResult(
            citation_id=cid, claim_id=claim_id,
            resolution=payload.get("resolution") or vf.ERROR,
            agreement=payload.get("agreement"),
            mismatches=list(payload.get("mismatches") or []),
            content=payload.get("content"),
            origin_group=payload.get("origin_group") or "",
            extractor=payload.get("extractor") or "",
            source=payload.get("source"), source_id=payload.get("source_id"),
            detail=payload.get("detail") or "",
        )
        if decision_item and decision_item.get("decision") == "variant":
            res.agreement = vf.AGREE  # ruled a legitimate variant: it stands
        rec = retrieved.get(cid)
        if rec:
            res.retrieved = RetrievedItem(
                source=rec.get("source") or "", source_id=rec.get("source_id") or "",
                title=rec.get("title") or "", authors=list(rec.get("authors") or []),
                year=rec.get("year"), venue=rec.get("venue"),
                abstract=None, license_basis=rec.get("license_basis") or "",
                hosted_ok=bool(rec.get("hosted_ok", True)),
            )
        citation = vf.Citation(citation_id=cid, claim_id=claim_id, proposition="")
        item = vf.to_evidence_item(citation, res)
        raw_items[cid] = item
        items_by_claim.setdefault(claim_id, []).append(item)

    for a, b in grouping_unions:
        if a in raw_items and b in raw_items:
            raw_items[b].origin_group = raw_items[a].origin_group

    for claim_id, items in items_by_claim.items():
        for item in items:
            register.add_evidence(claim_id, item)
    return items_by_claim


def coverage(register: ClaimRegister) -> dict[str, Any]:
    """Per-claim and total content coverage (WS5 §2): origin groups
    whose content was actually checked vs metadata-only groups."""
    per_claim: dict[str, dict[str, int]] = {}
    total_groups = 0
    checked_groups = 0
    for cid in register.claims:
        groups = register.group_masses(cid)
        checked = sum(1 for g in groups if not g.get("metadata_only"))
        per_claim[cid] = {"groups": len(groups), "checked": checked}
        total_groups += len(groups)
        checked_groups += checked
    return {"per_claim": per_claim, "groups": total_groups, "checked": checked_groups}


def queue_view(store: StudyStore, meta: dict[str, Any]) -> dict[str, Any]:
    state = vf.queue_state(store)
    report = vf.second_review_report(store)
    sampled = vf.pending_second_reviews(
        store, fraction=meta["second_review_fraction"],
        seed=meta["second_review_seed"])
    reviews = sum(len(i["second_reviews"]) for i in state["items"].values())
    disagreements = sum(
        1 for i in state["items"].values()
        for r in i["second_reviews"] if not r["agrees"])
    return {
        "pending": state["pending"], "decided": state["decided"],
        "report": report, "sampled_unreviewed": sampled,
        "reviews": reviews, "disagreements": disagreements,
    }


def control_objects(control_fields: list[dict[str, Any]]) -> list[Control]:
    """Registration-field control dicts → Control objects. A field
    dict may carry a `fixture` ({claim, groups}) — the known-answer
    evaluation fixture the run executes through `evaluate_claim`
    (present for controls registered with one; the swap control
    needs none, it works on the ledger itself)."""
    controls: list[Control] = []
    for f in control_fields:
        fixture = f.get("fixture") or {}
        claim = None
        if fixture.get("claim"):
            claim = Claim(**{k: fixture["claim"][k]
                             for k in _CLAIM_FIELDS if k in fixture["claim"]})
        controls.append(Control(
            failure_mode=f.get("failure_mode", ""), kind=f.get("kind", ""),
            claim=claim, groups=fixture.get("groups"),
            expected=f.get("expected"),
            representative_rationale=f.get("representative_rationale", ""),
        ))
    return controls


def run_controls_for(store_path: str, control_fields: list[dict[str, Any]]) -> list[Control]:
    """The controls a workspace run/replay executes: the swap control
    (always — it needs only the ledger) plus any registered control
    carrying an evaluation fixture."""
    controls = []
    swap_fields = next((f for f in control_fields if f.get("kind") == "swap"), None)
    controls.append(Control(
        failure_mode=(swap_fields or {}).get(
            "failure_mode",
            "integrity machinery decorative: provenance swap undetected"),
        kind="swap"))
    for f in control_fields:
        if f.get("kind") in ("positive", "negative") and f.get("fixture"):
            controls.extend(control_objects([f]))
    return controls


def evaluate_workspace_run(store: StudyStore, register: ClaimRegister,
                           store_path: str,
                           control_fields: list[dict[str, Any]]) -> RunResult:
    """The production run evaluation, driven from the record: frozen
    mode + linked-exploratory disclosure from the `study.frozen`
    event, chain state from the production verifier, controls as
    above — all through `evaluate_run` itself (RT-1).

    The workspace run is the verdict-issuing run, and verdicts are
    issued only against a frozen registration: with no `study.frozen`
    event in the ledger the run is INVALID and issues nothing. The
    mode is read from the freeze event, never inferred from its
    absence — an earlier version defaulted an unfrozen study to
    "exploratory" here, which silently re-moded a run whose
    confirmation freeze had been refused and stranded the study
    (verdicts issued, export refused as unfrozen). Exploratory
    *evaluation* remains available at the engine level
    (`evaluate_run(mode="exploratory")`, which appends nothing); a
    study frozen in exploratory mode runs in that mode, against its
    recorded freeze, and exports with the mode on its registration."""
    fe = frozen_event(store)
    if fe is None:
        return RunResult(
            run_verdict="invalid",
            invalid_reasons=[
                "confirmation run without a frozen registration (WS3 §4 "
                "wall): no study.frozen event in the ledger — freeze the "
                "study before running; verdicts are issued only against "
                "a frozen registration"],
            mode="confirmation", disclosure=[])
    mode = fe["payload"].get("mode", "confirmation")
    linked = fe["payload"].get("linked_exploratory", [])
    return evaluate_run(
        register, mode=mode,
        controls=run_controls_for(store_path, control_fields),
        chain_ok=store.verify().ok, linked_exploratory=linked,
        store=store, store_path=store_path)


def run_projection(store: StudyStore, register: ClaimRegister, store_path: str,
                   control_fields: list[dict[str, Any]]) -> dict[str, Any]:
    """What the workspace presents as the study's latest run.

    Issued verdicts are events and win. Otherwise, if the study is
    frozen, the run-level checks are replayed from the record: an
    INVALID replay is presented as INVALID with the engine's reasons;
    a clean replay with no issued verdicts is 'not-run'."""
    issued = verdicts_by_claim(store)
    if issued:
        return {"state": "valid", "issued": True, "verdicts": issued, "reasons": []}
    if frozen_event(store) is None:
        return {"state": "none", "issued": False, "verdicts": {}, "reasons": []}
    result = evaluate_workspace_run(store, register, store_path, control_fields)
    if result.run_verdict == "invalid":
        return {"state": "invalid", "issued": False, "verdicts": {},
                "reasons": result.invalid_reasons}
    return {"state": "not-run", "issued": False, "verdicts": {}, "reasons": []}


# ------------------------------------------------------------------ actions

def action_register_claim(store: StudyStore, register: ClaimRegister,
                          claim: Claim, actor: str) -> Claim:
    """Register through the engine first (its RegistrationError is
    the refusal, raised before anything is appended — CLM-002-32),
    then append the snapshot(s)."""
    supersedes = claim.supersedes
    register.register(claim)
    store.register_claim(claim.claim_id, claim.as_dict(), actor=actor)
    if supersedes and supersedes in register.claims:
        old = register.claims[supersedes]
        store.register_claim(old.claim_id, old.as_dict(), actor=actor)
    return claim


def action_attach_citation(store: StudyStore, ws: Workspace, study_id: str,
                           citation: vf.Citation, connectors: list,
                           actor: str) -> vf.CitationResult:
    """Run the production pipeline for one citation (outcomes +
    quarantine enqueues are ledger appends), then cache the citation
    input and any retrieved record as workspace sidecars."""
    report = vf.verify_citations(store, [citation], connectors, actor=actor)
    result = report.results[0]
    citations = ws.read_sidecar(study_id, "citations.json", {}) or {}
    citations[citation.citation_id] = citation.as_dict()
    ws.write_sidecar(study_id, "citations.json", citations)
    if result.retrieved is not None:
        retrieved = ws.read_sidecar(study_id, "retrieved.json", {}) or {}
        rec = result.retrieved.as_dict()
        retrieved[citation.citation_id] = {
            **rec,
            "content_included": bool(rec["abstract"])
            and export_mod.redistribution_permitted(rec["license_basis"]),
        }
        ws.write_sidecar(study_id, "retrieved.json", retrieved)
    return result


def retrieved_items(ws: Workspace, study_id: str) -> dict[str, RetrievedItem]:
    """Sidecar records back into RetrievedItem objects, the shape
    `tekmerion.export.export_bundle` consumes."""
    out: dict[str, RetrievedItem] = {}
    for cid, rec in (ws.read_sidecar(study_id, "retrieved.json", {}) or {}).items():
        out[cid] = RetrievedItem(
            source=rec.get("source") or "", source_id=rec.get("source_id") or "",
            title=rec.get("title") or "", authors=list(rec.get("authors") or []),
            year=rec.get("year"), venue=rec.get("venue"),
            abstract=rec.get("abstract"),
            license_basis=rec.get("license_basis") or "",
            hosted_ok=bool(rec.get("hosted_ok", True)),
        )
    return out


def action_freeze(store: StudyStore, register: ClaimRegister, ws: Workspace,
                  study_id: str, actor: str, *, mode: str,
                  linked_exploratory: list[str],
                  control_fields: list[dict[str, Any]],
                  deployment_shape: str = "hosted") -> dict[str, Any]:
    """Freeze through the production workflow (FreezeError is the
    refusal). On success the frozen document is captured in the
    freeze sidecar, where its hash is the ledger's commitment."""
    controls = control_objects(control_fields)
    result = freeze(store, register, controls, actor=actor, mode=mode,
                    linked_exploratory=linked_exploratory,
                    deployment_shape=deployment_shape)
    ws.write_sidecar(study_id, "freeze.json", {
        "document": register.frozen_document,
        "controls": control_fields,
        "deployment_shape": deployment_shape,
    })
    return result


def frozen_document(ws: Workspace, study_id: str,
                    store: StudyStore) -> Optional[dict[str, Any]]:
    """The study's frozen registration document from the sidecar,
    returned only if it hashes to the ledger's commitment."""
    sidecar = ws.read_sidecar(study_id, "freeze.json")
    if not sidecar or not sidecar.get("document"):
        return None
    fe = frozen_event(store)
    if fe is None:
        return None
    doc = sidecar["document"]
    if registration_hash(doc) != fe["payload"].get("registration_hash"):
        return None
    return doc


def freeze_control_fields(ws: Workspace, study_id: str,
                          store: StudyStore) -> list[dict[str, Any]]:
    """The study's registered control field dicts. When the frozen
    document checks out against the ledger, the sidecar's richer
    field dicts (which may carry run fixtures) are authoritative for
    display/execution; otherwise the document's own projection."""
    sidecar = ws.read_sidecar(study_id, "freeze.json") or {}
    doc = frozen_document(ws, study_id, store)
    if doc is not None:
        return list(sidecar.get("controls") or doc.get("controls") or [])
    return list(sidecar.get("controls") or [])


def action_run(store: StudyStore, register: ClaimRegister, store_path: str,
               control_fields: list[dict[str, Any]],
               actor: str) -> RunResult:
    """Drive an evaluation run. A valid run's claim verdicts are
    appended as `verdict.issued` events (skipping dead claims — a
    dead record takes no verdict); an INVALID run appends nothing
    (WS3 §1)."""
    result = evaluate_workspace_run(store, register, store_path, control_fields)
    if result.run_verdict == "valid":
        for verdict in result.claim_verdicts:
            claim = register.claims.get(verdict.claim_id)
            if claim is not None and claim.status == "dead":
                continue
            store.issue_verdict(verdict.claim_id, verdict.as_dict(), actor=actor)
    return result


def action_export(store: StudyStore, register: ClaimRegister, ws: Workspace,
                  study_id: str, actor: str) -> tuple[dict[str, Any], Any, Path]:
    """Export through the production bundle service (ExportError is
    the refusal), record the export in the ledger, then run the
    standalone verifier on the produced bundle."""
    doc = frozen_document(ws, study_id, store)
    if doc is not None:
        register.frozen_document = doc
    fe = frozen_event(store)
    mode = fe["payload"].get("mode", "confirmation") if fe else "confirmation"
    linked = fe["payload"].get("linked_exploratory", []) if fe else []
    controls = control_objects(freeze_control_fields(ws, study_id, store))
    exports_dir = ws.study_dir(study_id) / "exports"
    exports_dir.mkdir(exist_ok=True)
    existing = sorted(p.name for p in exports_dir.iterdir() if p.is_dir())
    out = exports_dir / f"bundle-{len(existing) + 1:03d}"
    manifest = export_mod.export_bundle(
        store, str(ws.ledger_path(study_id)), str(out), register=register,
        controls=controls, mode=mode, linked_exploratory=linked,
        study_label=ws.meta(study_id)["title"],
        retrieved=retrieved_items(ws, study_id))
    export_mod.record_export(store, manifest, actor=actor)
    verification = export_mod.verify_bundle(str(out))
    return manifest, verification, out


def action_deposit(store: StudyStore, ws: Workspace, study_id: str,
                   bundle_dir: Path, transport: Any, *,
                   approved_by: str, actor: str) -> dict[str, Any]:
    """Deposit through the production deposit service (DepositError
    is the refusal — including its mechanical adjudicator-approval
    gate) and append the receipt to the ledger."""
    receipt = deposit_mod.deposit_bundle(str(bundle_dir), transport,
                                         approved_by=approved_by)
    deposit_mod.record_anchor(store, receipt, actor=actor)
    return receipt


def held_bundles(ws: Workspace, study_id: str) -> list[Path]:
    exports_dir = ws.study_dir(study_id) / "exports"
    if not exports_dir.exists():
        return []
    return sorted(p for p in exports_dir.iterdir()
                  if p.is_dir() and (p / "manifest.json").exists())
