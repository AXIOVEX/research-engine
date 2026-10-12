#!/usr/bin/env python3
"""Coordinator skill-only exercise for CLM-009-09 (Spec 009).

Operates the Tekmerion MCP server using ONLY the installed SKILL.md
(~/workspace/skills/tekmerion/SKILL.md) Playbook A + the MCP tool
schemas as served by list_tools. No repo source consulted. Server
binaries come from the clean-room acceptance venv. Every call and
its outcome is logged to transcript.jsonl in this directory.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
SERVER = Path.home() / "workspace/tekmerion-mcp-acceptance/venv/bin/tekmerion-mcp"
WORKSPACE = HERE / "ws"
TRANSCRIPT = HERE / "transcript.jsonl"

log = []


def note(actor, tool, ok, detail):
    entry = {"actor": actor, "tool": tool, "ok": ok, "detail": str(detail)[:900]}
    log.append(entry)
    print(f"[{'OK ' if ok else 'ERR'}] {actor:18s} {tool:26s} {str(detail)[:200]}")


def result_text(res):
    parts = []
    for c in (res.content or []):
        t = getattr(c, "text", None)
        parts.append(t if t is not None else str(c))
    return " | ".join(parts)


async def call(session, actor, tool, args, expect_error=False):
    try:
        res = await session.call_tool(tool, args)
        txt = result_text(res)
        is_err = bool(getattr(res, "isError", False))
        note(actor, tool, not is_err, txt)
        return txt, is_err
    except Exception as exc:  # wire-level exception surface
        note(actor, tool, expect_error, f"exception: {exc}")
        return str(exc), True


def server_params(actor, role):
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "TEKMERION_ACTOR": actor,
        "TEKMERION_ROLE": role,
        "TEKMERION_WORKSPACE": str(WORKSPACE),
    }
    return StdioServerParameters(command=str(SERVER), args=[], env=env)


async def main():
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    study = "skill-ex-001"

    # --- Phase 1: researcher instance (Playbook A steps 1-3) ---
    async with stdio_client(server_params("cosmo-researcher", "researcher")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            note("cosmo-researcher", "list_tools", True,
                 f"{len(tools.tools)} tools served")
            txt, _ = await call(s, "cosmo-researcher", "list_studies", {})
            # Rule 2 probe: falsifier-less registration must be refused.
            txt, err = await call(s, "cosmo-researcher", "register_claim", {
                "study_id": study, "claim_id": "CLM-X-000",
                "statement": "A claim with no falsifier, offered as a probe.",
            }, expect_error=True)
            note("probe", "falsifier_refusal", "falsifier" in txt.lower(),
                 txt[:200])
            await call(s, "cosmo-researcher", "create_study", {
                "study_id": study,
                "title": "Coordinator skill exercise: citation integrity spot study",
            })
            await call(s, "cosmo-researcher", "register_claim", {
                "study_id": study, "claim_id": "CLM-X-001",
                "statement": "The record as cited (Einstein 1905, Annalen der "
                             "Physik) resolves, and its resolved metadata "
                             "agrees with the as-cited form.",
                "falsifier": "Resolution returns not_found, or the resolved "
                             "metadata disagrees with the as-cited title, "
                             "authors, or year.",
                "margin": 0.1, "sufficiency_floor": 1,
            })

    # --- Phase 2: adjudicator instance registers early (swap control) ---
    async with stdio_client(server_params("cosmo-adjudicator", "adjudicator")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            await call(s, "cosmo-adjudicator", "register_claim", {
                "study_id": study, "claim_id": "CLM-X-002",
                "statement": "The citation carrying DOI "
                             "10.9999/skill.exercise.fabricated resolves to "
                             "a real scholarly record.",
                "falsifier": "Resolution of that DOI returns not_found.",
                "margin": 0.1, "sufficiency_floor": 1,
            })

    # --- Phase 3: researcher attaches citations (Playbook A step 3) ---
    async with stdio_client(server_params("cosmo-researcher", "researcher")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            await call(s, "cosmo-researcher", "attach_citation", {
                "study_id": study, "citation_id": "CIT-X-101",
                "claim_id": "CLM-X-001",
                "proposition": "The record resolves and its metadata agrees "
                               "with the as-cited form.",
                "doi": "10.1002/andp.19053221004",
                "title": "Zur Elektrodynamik bewegter Korper",
                "authors": ["Albert Einstein"], "year": 1905,
                "venue": "Annalen der Physik",
            })
            await call(s, "cosmo-researcher", "attach_citation", {
                "study_id": study, "citation_id": "CIT-X-201",
                "claim_id": "CLM-X-002",
                "proposition": "The DOI resolves to a real record.",
                "doi": "10.9999/skill.exercise.fabricated",
                "title": "Fabricated Findings in Nonexistent Systems",
                "authors": ["J. Doe"], "year": 2024,
                "venue": "Journal of Imaginary Results",
            })

    # --- Phase 4: adjudicator works queue, freezes, runs (steps 4-7) ---
    verdicts_txt = ""
    async with stdio_client(server_params("cosmo-adjudicator", "adjudicator")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            q, _ = await call(s, "cosmo-adjudicator", "list_adjudication_queue",
                              {"study_id": study})
            # Decide every pending item the queue shows as undecided: the
            # fabricated citation must be excluded (skill step 4).
            try:
                qdoc = json.loads(q)
            except Exception:
                qdoc = {}
            items = qdoc.get("pending") or qdoc.get("items") or []
            if isinstance(qdoc, list):
                items = qdoc
            for it in items:
                if not isinstance(it, dict):
                    continue
                qid = it.get("queue_id") or it.get("id")
                if qid:
                    await call(s, "cosmo-adjudicator", "decide_adjudication", {
                        "study_id": study, "queue_id": qid,
                        "decision": "exclude",
                        "rationale": "Resolution returned not_found; the "
                                     "citation does not resolve to any real "
                                     "record (skill exercise).",
                    })
            await call(s, "cosmo-adjudicator", "freeze_study", {
                "study_id": study, "linked_exploratory": [],
            })
            await call(s, "cosmo-adjudicator", "run_evaluation",
                       {"study_id": study})
            verdicts_txt, _ = await call(s, "cosmo-adjudicator", "get_verdicts",
                                         {"study_id": study})
            status_txt, _ = await call(s, "cosmo-adjudicator", "get_study_status",
                                        {"study_id": study})

    # --- Phase 5: export + standalone verify (step 8) ---
    async with stdio_client(server_params("cosmo-researcher", "researcher")) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            exp, _ = await call(s, "cosmo-researcher", "export_bundle",
                                {"study_id": study})
            bundle_dir = None
            try:
                edoc = json.loads(exp)
                bundle_dir = edoc.get("bundle_dir") or edoc.get("path") or edoc.get("bundle")
            except Exception:
                pass
            if bundle_dir:
                await call(s, "cosmo-researcher", "verify_bundle",
                           {"bundle_dir": bundle_dir})
            else:
                note("cosmo-researcher", "verify_bundle", False,
                     f"could not parse bundle_dir from export result: {exp[:200]}")

    TRANSCRIPT.write_text("\n".join(json.dumps(e) for e in log) + "\n")
    print(f"\ntranscript: {TRANSCRIPT} ({len(log)} entries)")
    print(f"verdicts read back: {verdicts_txt[:400]}")


if __name__ == "__main__":
    asyncio.run(main())
