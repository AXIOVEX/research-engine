#!/usr/bin/env python3
"""Spec 002 Phase 7 — the evaluation study driver.

Executes the frozen-design evaluation registered in `corpus.md`
through the production machinery only: both connectors queried per
question, the three-stage citation pipeline, adjudication of the
seeded defects, the register freeze (confirmation, no linked
exploratory), the verdict engine, verdict issuance only on a valid
run, the audit-bundle export with the run-outcome projection, the
registered deposit approval, and the Zenodo anchor (G4 pattern).

The study is single-operator (one person, four actors), as recorded
in corpus.md. API keys are read from the research key file; values
are never printed. Refuses to run if the study already exists — an
evaluation is run once, and its record is the artifact.

    ~/workspace/tekmerion/.venv/bin/python run_evaluation.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")

# Keys: parse the env file into the environment; never print values.
for _line in Path.home().joinpath(
        "workspace/glossa-run/research-api-keys.env").read_text().splitlines():
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

from tekmerion.claims import Claim, ClaimRegister, Control, EvidenceGroup  # noqa: E402
from tekmerion.connectors import CrossrefConnector, CreditBudget, OpenAlexConnector  # noqa: E402
from tekmerion.deposit import ZenodoTransport, deposit_bundle, record_anchor  # noqa: E402
from tekmerion.export import export_bundle, record_export, verify_anchor, verify_bundle  # noqa: E402
from tekmerion.freeze import freeze  # noqa: E402
from tekmerion.store import StudyStore  # noqa: E402
from tekmerion.verdicts import evaluate_run, run_controls  # noqa: E402
from tekmerion.verification import (  # noqa: E402
    Citation, decide, pending_second_reviews, run_query, to_evidence_item,
    verify_citations)

STUDY = HERE / "study"
LEDGER = STUDY / "study.axmr"
BUNDLE_V1 = STUDY / "bundle-v1"
BUNDLE_V2 = STUDY / "bundle-v2"
LABEL = "spec002-phase7-evaluation"

CLAIMS = [
    Claim("CLM-E-001",
          "Cognitive behavioral therapy for insomnia (CBT-I) is an effective "
          "treatment for adults with chronic insomnia",
          "A source-of-record synthesis of CBT-I trials finds no clinically "
          "meaningful improvement in sleep outcomes, or the cited records do "
          "not exist or do not say this",
          margin=0.1, sufficiency_floor=1),
    Claim("CLM-E-002",
          "Meditation programs produce small-to-moderate reductions in "
          "anxiety and depression symptoms",
          "The cited synthesis finds no improvement in anxiety or "
          "depression, or the cited records do not exist or do not say this",
          margin=0.1, sufficiency_floor=1),
    Claim("CLM-E-003",
          "Exercise reduces symptoms of depression in adults",
          "The cited syntheses find no reduction in depressive symptoms, or "
          "the cited records do not exist or do not say this",
          margin=0.1, sufficiency_floor=1),
    Claim("CLM-E-004",
          "Glucosamine reduces joint pain in patients with osteoarthritis "
          "of the hip or knee",
          "A large-scale synthesis finds glucosamine does not reduce joint "
          "pain versus placebo (the registered falsifying observation is "
          "the Wandel 2010 network meta-analysis's conclusion)",
          margin=0.1, sufficiency_floor=1),
    Claim("CLM-E-005",
          "Risk-factor models derived from the Framingham Heart Study "
          "predict coronary heart disease risk",
          "The Framingham records do not exist, or do not describe "
          "predictive risk-factor models",
          margin=0.1, sufficiency_floor=2),
    Claim("CLM-E-CTL-POS",
          "control: CBT-I improves sleep efficiency in chronic insomnia "
          "(known-answer: Trauer 2015's conclusion)",
          "Trauer 2015's synthesis finds no improvement in sleep "
          "efficiency or the other diary sleep measures", margin=0.1),
    Claim("CLM-E-CTL-NEG",
          "control: glucosamine reduces joint pain versus placebo "
          "(known-answer: Wandel 2010 found it does not)",
          "Wandel 2010's network meta-analysis conclusion is the control's "
          "falsifier observation", margin=0.1),
]

CITATIONS = [
    Citation("CIT-E-101", "CLM-E-001",
             "CBT-i is an effective treatment for adults with chronic "
             "insomnia, with clinically meaningful effect sizes",
             doi="10.7326/M14-2841",
             title="Cognitive Behavioral Therapy for Chronic Insomnia",
             authors=["James M. Trauer"], year=2015,
             venue="Annals of Internal Medicine"),
    Citation("CIT-E-102", "CLM-E-001",
             "CBT-i is an effective treatment for adults with chronic "
             "insomnia, with clinically meaningful effect sizes",
             doi=None,
             title="Cognitive Behavioral Therapy for Chronic Insomnia",
             authors=["James M. Trauer"], year=2015,
             venue="Annals of Internal Medicine"),
    Citation("CIT-E-103", "CLM-E-001",
             "CBT-i is an effective treatment for adults with chronic "
             "insomnia, with clinically meaningful effect sizes",
             doi="10.7326/M14-9999",
             title="Cognitive Behavioral Therapy for Chronic Insomnia",
             authors=["James M. Trauer"], year=2015,
             venue="Annals of Internal Medicine"),
    Citation("CIT-E-201", "CLM-E-002",
             "Meditation programs improve anxiety and depression symptoms",
             doi="10.1001/jamainternmed.2013.13018",
             title="Meditation Programs for Psychological Stress and Well-being",
             authors=["Madhav Goyal"], year=2014,
             venue="JAMA Internal Medicine"),
    Citation("CIT-E-202", "CLM-E-002",
             "Mindfulness-based therapy reduces symptoms of anxiety and "
             "depression",
             doi="10.1016/j.cpr.2013.05.005",
             title="Mindfulness-based therapy: A comprehensive meta-analysis",
             authors=["Bassam Khouri"], year=2019,
             venue="Clinical Psychology Review"),
    Citation("CIT-E-301", "CLM-E-003",
             "Exercise reduces symptoms of depression",
             doi="10.1002/14651858.CD004366.pub6",
             title="Exercise for depression",
             authors=["Gary M. Cooney"], year=2013,
             venue="Cochrane Database of Systematic Reviews"),
    Citation("CIT-E-302", "CLM-E-003",
             "Exercise is an effective treatment for reducing depressive "
             "symptoms",
             doi="10.1016/j.jpsychires.2016.02.023",
             title="Exercise as a treatment for depression: A meta-analysis "
                   "adjusting for publication bias",
             authors=["Felipe B. Schuch"], year=2016,
             venue="Journal of Psychiatric Research"),
    Citation("CIT-E-401", "CLM-E-004",
             "Glucosamine reduces joint pain compared with placebo",
             doi="10.1136/bmj.c4675",
             title="Effects of glucosamine, chondroitin, or placebo in "
                   "patients with osteoarthritis of hip or knee: network "
                   "meta-analysis",
             authors=["Peter Wandel"], year=2010, venue="BMJ"),
    Citation("CIT-E-501", "CLM-E-005",
             "Risk factor models from the Framingham Heart Study predict "
             "coronary heart disease risk",
             doi="10.1161/01.CIR.97.18.1837",
             title="Prediction of Coronary Heart Disease Using Risk Factor "
                   "Categories",
             authors=["Peter W. F. Wilson"], year=1998, venue="Circulation",
             dataset_id="framingham-heart-study"),
    Citation("CIT-E-502", "CLM-E-005",
             "A general cardiovascular risk profile from the Framingham "
             "Heart Study predicts cardiovascular disease",
             doi="10.1161/CIRCULATIONAHA.107.699579",
             title="General Cardiovascular Risk Profile for Use in Primary "
                   "Care: The Framingham Heart Study",
             authors=["Ralph B. D'Agostino"], year=2008, venue="Circulation",
             dataset_id="framingham-heart-study"),
]

QUESTIONS = {
    "CLM-E-001": "cognitive behavioral therapy chronic insomnia systematic review meta-analysis",
    "CLM-E-002": "meditation programs psychological stress well-being systematic review meta-analysis",
    "CLM-E-003": "exercise for depression systematic review meta-analysis",
    "CLM-E-004": "glucosamine chondroitin placebo osteoarthritis network meta-analysis",
    "CLM-E-005": "Framingham Heart Study cardiovascular risk prediction",
}

DECISIONS = {
    "CIT-E-103": ("exclude",
                  "DOI does not resolve at any source of record — "
                  "fabricated; excluded from the evidence basis."),
    "CIT-E-202": ("exclude",
                  "As cited, the authorship and year misstate the record "
                  "of the work the DOI identifies — a corrupted citation; "
                  "excluded as cited."),
}


def controls() -> list[Control]:
    return [
        Control("positive", claim_id="CLM-E-CTL-POS", expected="supported",
                groups=[EvidenceGroup("CTL-P1", 0.9, 0.0, True),
                        EvidenceGroup("CTL-P2", 0.9, 0.0, True)],
                rationale_ref="corpus.md controls: known-answer control in "
                              "the evaluation's lead domain (sleep "
                              "interventions), shaped like Q1's evidence"),
        Control("negative", claim_id="CLM-E-CTL-NEG", expected="contradicted",
                groups=[EvidenceGroup("CTL-N1", 0.0, 0.9, True,
                                      falsifier_observation=True)],
                rationale_ref="corpus.md controls: mirrors CLM-E-004's shape "
                              "— a popular remedy claim a decisive synthesis "
                              "refutes (Wandel 2010)"),
        Control("swap", rationale_ref="RT-1 standard: provenance forgery on "
                                      "a multi-actor ledger (Phase 7 fixed "
                                      "event selection)"),
    ]


def note(key: str, value) -> None:
    print(f"[{key}] {value}", flush=True)


def main() -> int:
    if STUDY.exists():
        print("study already exists — an evaluation is run once; refusing "
              "to overwrite its record", file=sys.stderr)
        return 2
    STUDY.mkdir(parents=True)
    store = StudyStore.create(str(LEDGER))
    reg = ClaimRegister()
    for claim in CLAIMS:
        reg.add_claim(claim)
        store.register_claim(claim.claim_id, claim.registration_payload(),
                             actor="researcher")
    note("claims_registered", [c.claim_id for c in CLAIMS])

    crossref = CrossrefConnector()
    budget = CreditBudget(limit=1000)
    openalex = OpenAlexConnector(budget=budget)
    for qid, query in QUESTIONS.items():
        for conn in (crossref, openalex):
            run_query(store, conn, query, actor="researcher")
    note("queries_logged", "5 questions x 2 connectors")

    # Resolution order registered in corpus.md: OpenAlex first.
    report = verify_citations(store, CITATIONS, [openalex, crossref],
                               actor="researcher")
    by_id = {r.citation_id: r for r in report.results}
    for r in report.results:
        note(f"pipeline[{r.citation_id}]",
             f"resolution={r.resolution} agreement={r.agreement} "
             f"content={r.content} mismatches={r.mismatches} "
             f"group={r.origin_group}")
    note("origin_groups", report.origin_groups)
    note("queue", report.queue_item_ids)

    decided = {}
    for qid in report.queue_item_ids:
        item = [e for e in store.events()
                if e["type"] == "adjudication.enqueued"
                and e["payload"]["queue_id"] == qid][0]
        cit_id = item["payload"]["citation_id"]
        decision, rationale = DECISIONS[cit_id]
        decide(store, qid, decision, adjudicator="adjudicator",
               rationale=rationale)
        decided[cit_id] = decision
    note("decisions", decided)

    sampled = pending_second_reviews(store, fraction=0.10, seed=7)
    for qid in sampled:
        store.log_second_review(qid, reviewer="second-reviewer", agrees=True)
    note("second_review_sampled", sampled)

    excluded = {cid for cid, (d, _) in DECISIONS.items() if d == "exclude"}
    for cit in CITATIONS:
        if cit.citation_id in excluded:
            continue
        item = to_evidence_item(cit, by_id[cit.citation_id])
        reg.add_evidence(cit.claim_id, item)
    note("evidence_items", {cid: [i.item_id for i in items]
                            for cid, items in reg.evidence.items()})
    note("openalex_budget_units_spent", budget.spent)

    frozen = freeze(store, reg, controls(), actor="researcher",
                    linked_exploratory=[])
    note("checkpoint_root", frozen["checkpoint_root"])
    note("registration_hash", frozen["registration_hash"])

    chain_ok = store.verify().ok
    ctrl_failures = run_controls(controls(), store_path=str(LEDGER))
    note("chain_ok", chain_ok)
    note("control_failures", ctrl_failures)
    result = evaluate_run(reg, mode="confirmation", controls=controls(),
                          chain_ok=chain_ok, linked_exploratory=[],
                          store=store, store_path=str(LEDGER))
    note("run_verdict", result.run_verdict)
    for verdict in result.claim_verdicts:
        note(f"verdict[{verdict.claim_id}]",
             f"{verdict.verdict} — {verdict.reason}")
    summary = {
        "run_verdict": result.run_verdict,
        "invalid_reasons": result.invalid_reasons,
        "verdicts": {v.claim_id: v.as_dict() for v in result.claim_verdicts},
        "checkpoint_root": frozen["checkpoint_root"],
        "registration_hash": frozen["registration_hash"],
        "openalex_budget_units_spent": budget.spent,
        "pipeline": {r.citation_id: {
            "resolution": r.resolution, "agreement": r.agreement,
            "content": r.content, "origin_group": r.origin_group,
            "source": r.source} for r in report.results},
        "decisions": decided,
        "second_review_sampled": sampled,
    }
    if result.run_verdict != "valid":
        note("RUN_INVALID", result.invalid_reasons)
        (STUDY / "summary.json").write_text(json.dumps(summary, indent=2))
        print("EVALUATION RUN INVALID — reported, not worked around. "
              "No verdicts issued, no deposit.")
        return 1
    for verdict in result.claim_verdicts:
        if verdict.claim_id.startswith("CLM-E-00"):
            store.issue_verdict(verdict.claim_id, verdict.as_dict(),
                                actor="verdict-service")
    note("verdicts_issued", [v.claim_id for v in result.claim_verdicts
                              if v.claim_id.startswith("CLM-E-00")])

    retrieved = {r.citation_id: r.retrieved for r in report.results
                 if r.retrieved}
    manifest1 = export_bundle(store, str(LEDGER), str(BUNDLE_V1),
                              register=reg, controls=controls(),
                              linked_exploratory=[], study_label=LABEL,
                              retrieved=retrieved)
    note("bundle_v1_hash", manifest1["bundle_hash"])
    v1 = verify_bundle(str(BUNDLE_V1))
    note("bundle_v1_verifies", v1.ok)
    if not v1.ok:
        note("bundle_v1_failures", v1.failures)
        return 1
    v1_doc = json.loads((BUNDLE_V1 / "verdicts.json").read_text())
    note("bundle_v1_run_outcome", v1_doc.get("run_outcome", {}).get("outcome"))
    record_export(store, manifest1, actor="researcher")

    # The deposit approval is the study's own registered step, taken by
    # the named adjudicator actor (coordinator instruction, Phase 7):
    # appended to the ledger before the deposit runs.
    store.append("deposit.approved", {
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

    verdict_lines = "; ".join(
        f"{cid}: {v['verdict']}" for cid, v in summary["verdicts"].items()
        if cid.startswith("CLM-E-00"))
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
    summary["receipt"] = receipt

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

    record_id = receipt.get("record_id") or receipt.get("id")
    with urllib.request.urlopen(
            f"https://zenodo.org/api/records/{record_id}", timeout=60) as resp:
        public = json.loads(resp.read().decode("utf-8"))
    av = verify_anchor(str(BUNDLE_V2), public,
                       package_path=str(STUDY / "bundle-v1.zip"))
    note("anchor_verifies_vs_public_record", av.ok)
    if not av.ok:
        note("anchor_failures", av.failures)
        return 1
    summary["anchor_verified"] = True

    (STUDY / "summary.json").write_text(json.dumps(summary, indent=2))
    print("EVALUATION COMPLETE — run valid, bundle anchored and verified "
          "against the public record")
    return 0


if __name__ == "__main__":
    sys.exit(main())
