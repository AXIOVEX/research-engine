#!/usr/bin/env python3
"""Coordinator skill-only exercise, RE-RUN for CLM-009-09 (Spec 009).

Same discipline as drive.py: ONLY the corrected installed SKILL.md +
list_tools schemas; server from the re-run clean-room venv (wheel
rebuilt from the fixed branch). Deliberately probes the F1 wall
(run before freeze) before the happy path. Transcript -> transcript2.jsonl.
"""
import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
SERVER = Path.home() / "workspace/tekmerion-mcp-acceptance-rerun/venv/bin/tekmerion-mcp"
WORKSPACE = HERE / "ws2"
TRANSCRIPT = HERE / "transcript2.jsonl"

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
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "TEKMERION_ACTOR": actor,
        "TEKMERION_ROLE": role,
        "TEKMERION_WORKSPACE": str(WORKSPACE),
    }
    return StdioServerParameters(command=str(SERVER), args=[], env=env)


CONTROLS = [
    {
        "kind": "positive",
        "failure_mode": "engine fails to support a claim backed by strong agreeing evidence",
        "expected": "supported",
        "representative_rationale": "A single well-attested record with agreeing metadata mirrors this study's citation-resolution claims in domain and difficulty.",
        "fixture": {
            "claim": {
                "claim_id": "CTRL-POS",
                "statement": "Control: the fixture record resolves and agrees.",
                "falsifier": "Fixture resolution returns not_found.",
                "margin": 0.1,
                "sufficiency_floor": 1,
            },
            "groups": [
                {"origin_group": "CTRL-G1", "support_mass": 0.9,
                 "contradiction_mass": 0.0, "could_falsify": False,
                 "falsifier_observation": False}
            ],
        },
    },
    {
        "kind": "negative",
        "failure_mode": "engine supports a claim whose evidence contradicts it",
        "expected": "contradicted",
        "fixture": {
            "claim": {
                "claim_id": "CTRL-NEG",
                "statement": "Control: the fixture record resolves and agrees.",
                "falsifier": "Fixture evidence contradicts the claim.",
                "margin": 0.1,
                "sufficiency_floor": 1,
            },
            "groups": [
                {"origin_group": "CTRL-G2", "support_mass": 0.0,
                 "contradiction_mass": 0.9, "could_falsify": True,
                 "falsifier_observation": True}
            ],
        },
    },
    {
        "kind": "swap",
        "failure_mode": "provenance swap between early ledger lines goes undetected",
        "expected": None,
    },
]


async def main():
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    study = "skill-ex-002"

    # Phase 1: researcher — identity, falsifier probes, create, claim 1.
    async with stdio_client(params("cosmo-researcher", "researcher")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            await call(s, "cosmo-researcher", "list_studies", {})
            t = await call(s, "cosmo-researcher", "register_claim", {
                "study_id": study, "claim_id": "CLM-Y-000",
                "statement": "Probe: no falsifier field at all.",
            })
            note("probe", "omit_falsifier_shape", "Field required" in t, t[:150])
            t = await call(s, "cosmo-researcher", "register_claim", {
                "study_id": study, "claim_id": "CLM-Y-000",
                "statement": "Probe: empty falsifier.", "falsifier": "",
                "margin": 0.1, "sufficiency_floor": 1,
            })
            note("probe", "empty_falsifier_shape", "no falsifier" in t, t[:150])
            await call(s, "cosmo-researcher", "create_study", {
                "study_id": study,
                "title": "Coordinator skill exercise re-run: citation integrity",
            })
            await call(s, "cosmo-researcher", "register_claim", {
                "study_id": study, "claim_id": "CLM-Y-001",
                "statement": "The record as cited (Einstein 1905, Annalen der Physik) resolves, and its resolved metadata agrees with the as-cited form.",
                "falsifier": "Resolution returns not_found, or the resolved metadata disagrees with the as-cited title, authors, or year.",
                "margin": 0.1, "sufficiency_floor": 1,
            })

    # Phase 2: adjudicator registers claim 2 early + F1 wall probe.
    async with stdio_client(params("cosmo-adjudicator", "adjudicator")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            await call(s, "cosmo-adjudicator", "register_claim", {
                "study_id": study, "claim_id": "CLM-Y-002",
                "statement": "The citation carrying DOI 10.9999/skill.exercise.fabricated resolves to a real scholarly record.",
                "falsifier": "Resolution of that DOI returns not_found.",
                "margin": 0.1, "sufficiency_floor": 1,
            })
            t = await call(s, "cosmo-adjudicator", "run_evaluation", {"study_id": study})
            note("probe", "f1_wall_on_unfrozen_run",
                 "frozen" in t.lower() and "invalid" in t.lower(), t[:220])
            t = await call(s, "cosmo-adjudicator", "get_verdicts", {"study_id": study})
            note("probe", "f1_no_verdicts_issued", '"issued": false' in t or '"issued":false' in t, t[:220])

    # Phase 3: researcher attaches citations.
    async with stdio_client(params("cosmo-researcher", "researcher")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            await call(s, "cosmo-researcher", "attach_citation", {
                "study_id": study, "citation_id": "CIT-Y-101",
                "claim_id": "CLM-Y-001",
                "proposition": "The record resolves and its metadata agrees with the as-cited form.",
                "doi": "10.1002/andp.19053221004",
                "title": "Zur Elektrodynamik bewegter Korper",
                "authors": ["Albert Einstein"], "year": 1905,
                "venue": "Annalen der Physik",
            })
            await call(s, "cosmo-researcher", "attach_citation", {
                "study_id": study, "citation_id": "CIT-Y-201",
                "claim_id": "CLM-Y-002",
                "proposition": "The DOI resolves to a real record.",
                "doi": "10.9999/skill.exercise.fabricated",
                "title": "Fabricated Findings in Nonexistent Systems",
                "authors": ["J. Doe"], "year": 2024,
                "venue": "Journal of Imaginary Results",
            })

    # Phase 4: adjudicator clears queue, freezes (controls explicit), runs.
    verdicts_txt = ""
    async with stdio_client(params("cosmo-adjudicator", "adjudicator")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            q = await call(s, "cosmo-adjudicator", "list_adjudication_queue", {"study_id": study})
            try:
                qdoc = json.loads(q)
                items = qdoc.get("pending") or []
            except Exception:
                items = []
            for it in items:
                qid = it.get("queue_id")
                cit = it.get("citation_id", "")
                kind = str(it.get("kind", ""))
                if cit == "CIT-Y-201":
                    decision, why = "exclude", "Resolution returned not_found; fabricated DOI (skill exercise re-run)."
                elif "origin" in kind or "group" in kind:
                    decision, why = "separate_origin", f"Queue kind {kind}; ruled a separate origin on the record."
                else:
                    decision, why = "exclude", f"Queue kind {kind} with reason {it.get('reason')!r}; excluded on the record."
                await call(s, "cosmo-adjudicator", "decide_adjudication", {
                    "study_id": study, "queue_id": qid,
                    "decision": decision, "rationale": why,
                })
            await call(s, "cosmo-adjudicator", "freeze_study", {
                "study_id": study, "linked_exploratory": [], "controls": CONTROLS,
            })
            await call(s, "cosmo-adjudicator", "run_evaluation", {"study_id": study})
            verdicts_txt = await call(s, "cosmo-adjudicator", "get_verdicts", {"study_id": study})
            await call(s, "cosmo-adjudicator", "get_study_status", {"study_id": study})
            t = await call(s, "cosmo-adjudicator", "deposit_bundle", {"study_id": study})
            note("probe", "deposit_gate_refusal",
                 "refus" in t.lower() or " approv" in t.lower(), t[:200])

    # Phase 5: researcher exports + standalone verify.
    async with stdio_client(params("cosmo-researcher", "researcher")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            exp = await call(s, "cosmo-researcher", "export_bundle", {"study_id": study})
            bundle_dir = None
            try:
                edoc = json.loads(exp)
                bundle_dir = edoc.get("bundle_dir") or edoc.get("path") or edoc.get("bundle")
            except Exception:
                pass
            if bundle_dir:
                await call(s, "cosmo-researcher", "verify_bundle", {"bundle_dir": bundle_dir})
            else:
                note("cosmo-researcher", "verify_bundle", False,
                     f"could not parse bundle_dir from: {exp[:200]}")

    TRANSCRIPT.write_text("\n".join(json.dumps(e) for e in log) + "\n")
    print(f"\ntranscript: {TRANSCRIPT} ({len(log)} entries)")
    print(f"verdicts: {verdicts_txt[:500]}")


if __name__ == "__main__":
    asyncio.run(main())
