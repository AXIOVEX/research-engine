#!/usr/bin/env python3
"""Coordinator skill-only exercise, RUN 3 (deciding run for CLM-009-09).

Discipline: the AMENDED installed SKILL.md only + list_tools schemas.
Controls argument = the skill's worked example, verbatim. Server is
launched with the FULL inherited environment (per the skill's new
Configuration note: stdio servers inherit the client's environment).
Transcript -> transcript3.jsonl.
"""
import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
SERVER = Path.home() / "workspace/tekmerion-mcp-acceptance-rerun/venv/bin/tekmerion-mcp"
WORKSPACE = HERE / "ws3"
TRANSCRIPT = HERE / "transcript3.jsonl"

log = []


def note(actor, tool, ok, detail):
    entry = {"actor": actor, "tool": tool, "ok": ok, "detail": str(detail)[:900]}
    log.append(entry)
    print(f"[{'OK ' if ok else 'ERR'}] {actor:18s} {tool:26s} {str(detail)[:190]}")


def result_text(res):
    parts = []
    for c in (res.content or []):
        t = getattr(c, "text", None)
        parts.append(t if t is not None else str(c))
    return " | ".join(parts)


async def call(session, actor, tool, args):
    try:
        res = await session.call_tool(tool, args)
        txt = result_text(res)
        note(actor, tool, not bool(getattr(res, "isError", False)), txt)
        return txt
    except Exception as exc:
        note(actor, tool, False, f"exception: {exc}")
        return str(exc)


def params(actor, role):
    env = dict(os.environ)  # full inheritance, per the skill's egress note
    env.update({
        "TEKMERION_ACTOR": actor,
        "TEKMERION_ROLE": role,
        "TEKMERION_WORKSPACE": str(WORKSPACE),
    })
    return StdioServerParameters(command=str(SERVER), args=[], env=env)


# The skill's worked example, verbatim (SKILL.md Playbook A step 6).
CONTROLS = [
    {"kind": "positive",
     "failure_mode": "engine fails to support a claim backed by strong agreeing evidence",
     "expected": "supported",
     "representative_rationale": "same domain and difficulty class as the study claims",
     "fixture": {"claim": {"claim_id": "CTRL-POS",
                           "statement": "known-true fixture claim",
                           "falsifier": "observing the fixture evidence contradict it",
                           "kind": "data", "dependencies": [],
                           "margin": 0.1, "sufficiency_floor": 2,
                           "supersedes": None, "status": "proposed"},
                 "groups": [
                     {"origin_group": "G1", "support_mass": 0.9,
                      "contradiction_mass": 0.0, "could_falsify": True,
                      "falsifier_observation": False,
                      "verified": True, "items": 1},
                     {"origin_group": "G2", "support_mass": 0.9,
                      "contradiction_mass": 0.0, "could_falsify": True,
                      "falsifier_observation": False,
                      "verified": True, "items": 1}]}},
    {"kind": "negative",
     "failure_mode": "engine fails to contradict a claim whose evidence contradicts it",
     "expected": "contradicted",
     "representative_rationale": "",
     "fixture": {"claim": {"claim_id": "CTRL-NEG",
                           "statement": "fixture claim its own evidence contradicts",
                           "falsifier": "observing the fixture evidence contradict it",
                           "kind": "data", "dependencies": [],
                           "margin": 0.1, "sufficiency_floor": 2,
                           "supersedes": None, "status": "proposed"},
                 "groups": [
                     {"origin_group": "G9", "support_mass": 0.0,
                      "contradiction_mass": 0.9, "could_falsify": True,
                      "falsifier_observation": True,
                      "verified": True, "items": 1},
                     {"origin_group": "G8", "support_mass": 0.0,
                      "contradiction_mass": 0.9, "could_falsify": True,
                      "falsifier_observation": True,
                      "verified": True, "items": 1}]}},
    {"kind": "swap",
     "failure_mode": "provenance swap between early ledger lines goes undetected",
     "expected": None, "representative_rationale": "",
     "fixture": None},
]


async def main():
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    study = "skill-ex-003"

    async with stdio_client(params("cosmo-researcher", "researcher")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            await call(s, "cosmo-researcher", "list_studies", {})
            await call(s, "cosmo-researcher", "create_study", {
                "study_id": study,
                "title": "Coordinator skill exercise run 3: citation integrity",
            })
            t = await call(s, "cosmo-researcher", "register_claim", {
                "study_id": study, "claim_id": "CLM-Z-000",
                "statement": "Probe: falsifier field omitted.",
            })
            note("probe", "omit_falsifier_shape", "Field required" in t, t[:150])
            t = await call(s, "cosmo-researcher", "register_claim", {
                "study_id": study, "claim_id": "CLM-Z-000",
                "statement": "Probe: empty falsifier.", "falsifier": "",
                "margin": 0.1, "sufficiency_floor": 1,
            })
            note("probe", "empty_falsifier_shape",
                 "no falsifier" in t and "Article II" in t, t[:200])
            await call(s, "cosmo-researcher", "register_claim", {
                "study_id": study, "claim_id": "CLM-Z-001",
                "statement": "The record as cited (Einstein 1905, Annalen der Physik) resolves, and its resolved metadata agrees with the as-cited form.",
                "falsifier": "Resolution returns not_found, or the resolved metadata disagrees with the as-cited title, authors, or year.",
                "margin": 0.1, "sufficiency_floor": 1,
            })

    async with stdio_client(params("cosmo-adjudicator", "adjudicator")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            await call(s, "cosmo-adjudicator", "register_claim", {
                "study_id": study, "claim_id": "CLM-Z-002",
                "statement": "The citation carrying DOI 10.9999/skill.exercise.fabricated resolves to a real scholarly record.",
                "falsifier": "Resolution of that DOI returns not_found.",
                "margin": 0.1, "sufficiency_floor": 1,
            })
            t = await call(s, "cosmo-adjudicator", "run_evaluation", {"study_id": study})
            note("probe", "f1_wall_on_unfrozen_run",
                 "frozen" in t.lower() and "invalid" in t.lower(), t[:220])
            t = await call(s, "cosmo-adjudicator", "get_verdicts", {"study_id": study})
            note("probe", "f1_no_verdicts_issued", '"issued": false' in t, t[:220])

    async with stdio_client(params("cosmo-researcher", "researcher")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            t = await call(s, "cosmo-researcher", "attach_citation", {
                "study_id": study, "citation_id": "CIT-Z-101",
                "claim_id": "CLM-Z-001",
                "proposition": "The record resolves and its metadata agrees with the as-cited form.",
                "doi": "10.1002/andp.19053221004",
                "title": "Zur Elektrodynamik bewegter Korper",
                "authors": ["Albert Einstein"], "year": 1905,
                "venue": "Annalen der Physik",
            })
            note("probe", "real_doi_resolution",
                 '"resolution": "resolved"' in t or '"resolution":"resolved"' in t,
                 t[:250])
            await call(s, "cosmo-researcher", "attach_citation", {
                "study_id": study, "citation_id": "CIT-Z-201",
                "claim_id": "CLM-Z-002",
                "proposition": "The DOI resolves to a real record.",
                "doi": "10.9999/skill.exercise.fabricated",
                "title": "Fabricated Findings in Nonexistent Systems",
                "authors": ["J. Doe"], "year": 2024,
                "venue": "Journal of Imaginary Results",
            })

    verdicts_txt = ""
    async with stdio_client(params("cosmo-adjudicator", "adjudicator")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            q = await call(s, "cosmo-adjudicator", "list_adjudication_queue", {"study_id": study})
            try:
                items = json.loads(q).get("pending") or []
            except Exception:
                items = []
            for it in items:
                qid, cit, kind = it.get("queue_id"), it.get("citation_id", ""), str(it.get("kind", ""))
                if cit == "CIT-Z-201":
                    decision, why = "exclude", "Resolution returned not_found; fabricated DOI (skill exercise run 3)."
                elif kind == "grouping":
                    decision, why = "separate_origin", "Grouping item; ruled separate origins on the record."
                elif kind == "quarantine":
                    decision, why = "exclude", f"Quarantine reason {it.get('reason')!r}; excluded on the record."
                else:
                    decision, why = "variant", f"Queue kind {kind}; ruled a legitimate variant on the record."
                await call(s, "cosmo-adjudicator", "decide_adjudication", {
                    "study_id": study, "queue_id": qid,
                    "decision": decision, "rationale": why,
                })
            await call(s, "cosmo-adjudicator", "freeze_study", {
                "study_id": study, "linked_exploratory": [], "controls": CONTROLS,
            })
            t = await call(s, "cosmo-adjudicator", "run_evaluation", {"study_id": study})
            note("probe", "run_valid", '"run_verdict": "valid"' in t, t[:250])
            verdicts_txt = await call(s, "cosmo-adjudicator", "get_verdicts", {"study_id": study})
            await call(s, "cosmo-adjudicator", "get_study_status", {"study_id": study})
            t = await call(s, "cosmo-adjudicator", "deposit_bundle", {"study_id": study})
            note("probe", "deposit_gate_refusal", "refus" in t.lower() or "transport" in t.lower(), t[:200])

    async with stdio_client(params("cosmo-researcher", "researcher")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            exp = await call(s, "cosmo-researcher", "export_bundle", {"study_id": study})
            bundle_dir = None
            try:
                bundle_dir = json.loads(exp).get("bundle_dir")
            except Exception:
                pass
            if bundle_dir:
                t = await call(s, "cosmo-researcher", "verify_bundle", {"bundle_dir": bundle_dir})
                note("probe", "bundle_standalone_ok", '"ok": true' in t and '"failures": []' in t, t[:200])
            else:
                note("cosmo-researcher", "verify_bundle", False,
                     f"could not parse bundle_dir from: {exp[:250]}")

    TRANSCRIPT.write_text("\n".join(json.dumps(e) for e in log) + "\n")
    print(f"\ntranscript: {TRANSCRIPT} ({len(log)} entries)")
    print(f"verdicts: {verdicts_txt[:600]}")


if __name__ == "__main__":
    asyncio.run(main())
