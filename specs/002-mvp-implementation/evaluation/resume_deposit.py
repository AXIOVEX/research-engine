#!/usr/bin/env python3
"""Spec 002 Phase 7 — deposit-leg resume.

The evaluation driver (`run_evaluation.py`) completed the frozen run
(valid; verdicts issued; bundle-v1 exported and verified) and then
stopped on a driver bug in the deposit leg (`StudyStore` has no
generic append — the production path is `store.db.append`). This
script performs ONLY the remaining post-run steps, rebuilding its
working state from bundle-v1 itself:

  1. append the registered `deposit.approved` step (adjudicator);
  2. deposit bundle-v1 to Zenodo (G4 pattern) and record the anchor;
  3. checkpoint, export bundle-v2, verify it standalone;
  4. verify the anchor against the independently fetched public
     record;
  5. write summary.json, reconstructed from the ledger and bundles.

It never re-runs the pipeline, the freeze, or the verdict engine.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
sys.path.insert(0, str(HERE))

from run_evaluation import LABEL, controls  # noqa: E402

from tekmerion.claims import Claim, ClaimRegister, EvidenceItem  # noqa: E402
from tekmerion.connectors import RetrievedItem  # noqa: E402
from tekmerion.deposit import ZenodoTransport, deposit_bundle, record_anchor  # noqa: E402
from tekmerion.export import export_bundle, verify_anchor, verify_bundle  # noqa: E402
from tekmerion.store import StudyStore  # noqa: E402

STUDY = HERE / "study"
LEDGER = STUDY / "study.axmr"
BUNDLE_V1 = STUDY / "bundle-v1"
BUNDLE_V2 = STUDY / "bundle-v2"


def _filtered(cls, entry):
    fields = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in entry.items() if k in fields})


def note(key, value):
    print(f"[{key}] {value}", flush=True)


def main() -> int:
    store = StudyStore.open(str(LEDGER))
    if any(e["type"] == "anchor.recorded" for e in store.events()):
        print("anchor already recorded — nothing to resume", file=sys.stderr)
        return 2
    v1 = verify_bundle(str(BUNDLE_V1))
    note("bundle_v1_verifies", v1.ok)
    if not v1.ok:
        note("bundle_v1_failures", v1.failures)
        return 1
    manifest1 = json.loads((BUNDLE_V1 / "manifest.json").read_text())
    doc = json.loads((BUNDLE_V1 / "registration.json").read_text())

    # Rebuild the register exactly as frozen, from the bundle alone.
    reg = ClaimRegister()
    for cdoc in doc["claims"]:
        reg.register(_filtered(Claim, cdoc))
    items = json.loads((BUNDLE_V1 / "evidence" / "items.json").read_text())
    for entry in items["items"]:
        reg.add_evidence(entry["claim_id"], _filtered(EvidenceItem, entry))
    reg.frozen_document = doc
    reg.frozen = True
    reg.registration_hash = manifest1["study"]["registration_hash"]
    verif = json.loads((BUNDLE_V1 / "verification.json").read_text())
    retrieved = {cid: _filtered(RetrievedItem, entry)
                 for cid, entry in verif["retrieved"].items()}

    store.db.append("deposit.approved", {
        "bundle": "bundle-v1", "bundle_hash": manifest1["bundle_hash"],
        "approved_by": "adjudicator (named adjudicator actor in this "
                       "study; the Phase 7 evaluation's registered "
                       "approval step, 2026-10-12)",
        "basis": "run valid; bundle verifies standalone; deposit under "
                 "the owner's standing G4 authorization",
    }, actor="adjudicator")
    note("deposit_approved", "adjudicator (registered ledger step)")

    def hook(req):
        from dynamic_credentials import add_surrogate_to_request
        add_surrogate_to_request(req, "custom.zenodo",
                                 allowed_hosts=["zenodo.org"])

    verdicts_doc = json.loads((BUNDLE_V1 / "verdicts.json").read_text())
    verdict_lines = "; ".join(
        f"{v['claim_id']}: {v['verdict']}" for v in verdicts_doc["verdicts"])
    receipt = deposit_bundle(
        str(BUNDLE_V1), ZenodoTransport(auth_hook=hook),
        approved_by="adjudicator (named adjudicator actor in the study; "
                    "Phase 7 evaluation registered approval step, "
                    "2026-10-12)",
        title="Tekmerion Spec 002 Phase 7 evaluation — audit bundle "
              "(frozen run vs kill criteria K1–K5)",
        description_extra=(
            "Evaluation audit bundle for Tekmerion Spec 002 Phase 7 "
            "(the K1 kill-criterion evaluation of citation resolution, "
            "CLM-002-10), deposited 2026-10-12. Five evidence questions "
            "from the systematic-review workflow were registered with "
            "eleven citations — including a seeded fabricated DOI, a "
            "seeded corrupted citation, a duplicate citation, and a "
            "shared-dataset pair — frozen, and run through the "
            "production pipeline only. The run was VALID and verdicts "
            f"were issued: {verdict_lines}. The bundle itself states "
            "the run outcome (verdicts.json run_outcome projection) "
            "and carries the full evidence trail; its Merkle "
            "checkpoint root and bundle hash are stated above so any "
            "auditor can verify the bundle against this public "
            "record."),
        package_out=str(STUDY / "bundle-v1.zip"))
    note("receipt_doi", receipt.get("doi"))

    record_anchor(store, receipt, actor="adjudicator")
    store.freeze(actor="adjudicator")
    manifest2 = export_bundle(store, str(LEDGER), str(BUNDLE_V2),
                              register=reg, controls=controls(),
                              linked_exploratory=[], study_label=LABEL,
                              retrieved=retrieved)
    note("bundle_v2_hash", manifest2["bundle_hash"])
    note("bundle_v2_anchors", manifest2["anchors"])
    v2 = verify_bundle(str(BUNDLE_V2))
    note("bundle_v2_verifies", v2.ok)
    if not v2.ok:
        note("bundle_v2_failures", v2.failures)
        return 1

    with urllib.request.urlopen(
            f"https://zenodo.org/api/records/{receipt['record_id']}",
            timeout=60) as resp:
        public = json.loads(resp.read().decode("utf-8"))
    av = verify_anchor(str(BUNDLE_V2), public,
                       package_path=str(STUDY / "bundle-v1.zip"))
    note("anchor_verifies_vs_public_record", av.ok)
    if not av.ok:
        note("anchor_failures", av.failures)
        return 1

    events = store.events()
    frozen_event = [e for e in events if e["type"] == "study.frozen"][0]
    summary = {
        "run_verdict": "valid",
        "run_outcome_in_bundle": verdicts_doc.get("run_outcome"),
        "verdicts": {e["payload"]["claim_id"]: e["payload"]["verdict"]
                     for e in events if e["type"] == "verdict.issued"},
        "checkpoint_root": manifest1["study"]["checkpoint_root"],
        "registration_hash": frozen_event["payload"]["registration_hash"],
        "openalex_budget_units_spent": 14,  # driver-reported at freeze time
        "pipeline": {e["payload"]["citation_id"]: {
            "resolution": e["payload"]["resolution"],
            "agreement": e["payload"]["agreement"],
            "content": e["payload"]["content"],
            "origin_group": e["payload"]["origin_group"],
            "source": e["payload"]["source"]}
            for e in events if e["type"] == "citation.checked"},
        "decisions": {e["payload"]["queue_id"]: e["payload"]["decision"]
                      for e in events if e["type"] == "adjudication.decided"},
        "second_review_sampled": [e["payload"]["queue_id"] for e in events
                                  if e["type"] == "adjudication.second_review"],
        "receipt": receipt,
        "bundle_v1_hash": manifest1["bundle_hash"],
        "bundle_v2_hash": manifest2["bundle_hash"],
        "anchor_verified": True,
        "execution_note": "run_evaluation.py executed the frozen run and "
                          "stopped on a driver bug in the deposit leg; "
                          "resume_deposit.py performed the deposit, anchor, "
                          "and v2 export only (see EVALUATION-REPORT.md).",
    }
    (STUDY / "summary.json").write_text(json.dumps(summary, indent=2))
    print("RESUME COMPLETE — bundle deposited, anchored, and verified "
          "against the public record")
    return 0


if __name__ == "__main__":
    sys.exit(main())
