#!/usr/bin/env python3
"""Spec 002 Phase 7 — K2 replay check, from the exported bundle ALONE.

Rebuilds the register from bundle-v2's own files (claims.json +
evidence/items.json), replays the verdict engine per claim, and
compares verdict, interval, and point estimate against the issued
verdicts in verdicts.json. Then runs two tamper cases on copies of
the bundle, each rehashed the way a competent attacker would (file
hashes and the manifest bundle hash recomputed with the exporter's
own canonicalization), so only the verifier's semantic cross-checks
can catch them:

  A. a verdict payload flipped in verdicts.json (supported ->
     contradicted), manifest rehashed;
  B. an actor field edited in the bundle's ledger copy, manifest
     rehashed.

Both must make verify_bundle fail. Prints a JSON result.

    ~/workspace/tekmerion/.venv/bin/python replay_check.py [bundle_dir]
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))

from tekmerion import export as export_mod  # noqa: E402
from tekmerion.claims import Claim, ClaimRegister, EvidenceItem  # noqa: E402
from tekmerion.export import verify_bundle  # noqa: E402
from tekmerion.verdicts import evaluate_claim  # noqa: E402

BUNDLE = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "study" / "bundle-v2"


def _filtered(cls, entry):
    fields = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in entry.items() if k in fields})


def rehash(bundle: Path) -> None:
    """Recompute file hashes + the bundle hash after an edit, using
    the exporter's own canonical form (the competent-attacker model)."""
    manifest = json.loads((bundle / "manifest.json").read_text())
    entries = []
    for path in sorted(p for p in bundle.rglob("*") if p.is_file()):
        rel = path.relative_to(bundle).as_posix()
        if rel == "manifest.json":
            continue
        data = path.read_bytes()
        entries.append({"path": rel, "sha256": export_mod._sha256(data),
                        "bytes": len(data)})
    manifest["files"] = entries
    manifest.pop("bundle_hash", None)
    manifest["bundle_hash"] = export_mod._sha256(
        export_mod._canonical(manifest))
    (bundle / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True))


def main() -> int:
    result: dict = {"bundle": str(BUNDLE)}
    base = verify_bundle(str(BUNDLE))
    result["bundle_verifies"] = base.ok
    if not base.ok:
        result["failures"] = base.failures
        print(json.dumps(result, indent=2))
        return 1

    claims_doc = json.loads((BUNDLE / "claims.json").read_text())
    items_doc = json.loads((BUNDLE / "evidence" / "items.json").read_text())
    verdicts_doc = json.loads((BUNDLE / "verdicts.json").read_text())
    result["run_outcome"] = verdicts_doc.get("run_outcome", {}).get("outcome")

    reg = ClaimRegister()
    claim_objs = {}
    for cdoc in claims_doc["claims"]:
        claim = _filtered(Claim, cdoc)
        claim_objs[claim.claim_id] = claim
        reg.register(claim)
    for entry in items_doc["items"]:
        reg.add_evidence(entry["claim_id"], _filtered(EvidenceItem, entry))

    issued = {v["claim_id"]: v for v in verdicts_doc["verdicts"]}
    replay = {}
    all_match = True
    for cid, issued_v in sorted(issued.items()):
        got = evaluate_claim(claim_objs[cid], reg.group_masses(cid))
        match = (got.verdict == issued_v["verdict"]
                 and [round(x, 6) for x in got.interval]
                 == [round(x, 6) for x in issued_v["interval"]]
                 and round(got.point, 6)
                 == round(issued_v["point"], 6))
        all_match = all_match and match
        replay[cid] = {"issued": issued_v["verdict"],
                       "replayed": got.verdict,
                       "interval_match": [round(x, 6) for x in got.interval]
                       == [round(x, 6) for x in issued_v["interval"]],
                       "point_match": round(got.point, 6)
                       == round(issued_v["point"], 6),
                       "match": match}
    result["replay"] = replay
    result["replay_all_match"] = all_match

    tamper = {}
    with tempfile.TemporaryDirectory() as td:
        # Case A: verdict payload flip, rehashed.
        case_a = Path(td) / "case-a"
        shutil.copytree(BUNDLE, case_a)
        vdoc = json.loads((case_a / "verdicts.json").read_text())
        for v in vdoc["verdicts"]:
            if v["claim_id"] == "CLM-E-001":
                v["verdict"] = "contradicted"
        (case_a / "verdicts.json").write_text(json.dumps(vdoc, indent=2))
        rehash(case_a)
        ra = verify_bundle(str(case_a))
        tamper["verdict_flip_rehashed"] = {
            "detected": not ra.ok, "failures": ra.failures[:3]}

        # Case B: ledger actor edit, rehashed.
        case_b = Path(td) / "case-b"
        shutil.copytree(BUNDLE, case_b)
        ledger = case_b / "ledger" / "study.axmr"
        lines = ledger.read_text().splitlines()
        event = json.loads(lines[1])
        event["actor"] = "mallory"
        lines[1] = json.dumps(event, sort_keys=True, separators=(",", ":"))
        ledger.write_text("\n".join(lines) + "\n")
        rehash(case_b)
        rb = verify_bundle(str(case_b))
        tamper["ledger_actor_edit_rehashed"] = {
            "detected": not rb.ok, "failures": rb.failures[:3]}
    result["tamper"] = tamper
    result["k2_pass"] = bool(base.ok and all_match
                             and all(t["detected"] for t in tamper.values()))
    print(json.dumps(result, indent=2))
    return 0 if result["k2_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
