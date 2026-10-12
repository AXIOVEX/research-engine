# Design Note 006 — The Framework Has a Name: Tekmerion

**Date:** 2026-10-11 · **Status:** Owner directive executed · **Decided by:** Tristen Pierson ("the framework must have a name as well")
**Supersedes:** DN-001's decision to keep the descriptive name `research-engine`.

## The name

**Tekmerion** (τεκμήριον, *tek-MEER-ee-on*) — the classical Greek term for *conclusive evidence: a sure sign by which a thing is proved*. It names what this framework produces. Tools in this category produce summaries; Tekmerion produces evidence that can carry a verdict — registered before outcomes are seen, falsifier attached, provenance intact.

Uniqueness checks (2026-10-11, recorded in AXIOVEX/axiomere `docs/NAMING.md`): no PyPI package; a handful of small, unrelated GitHub repositories; no software product carries the name. Rejected: **Elenchus** (already multiple software projects, incl. an MCP reasoning tool and a Rust SAT checker) and **Basanos** (PyPI taken).

## What changed

- Repository: `AXIOVEX/research-engine` → **`AXIOVEX/tekmerion`** (GitHub rename; the old URL redirects).
- Python package: `research_engine` → **`tekmerion`** (`src/tekmerion/`), distribution name likewise.
- Living documents (README, constitution title, pyproject) carry the new name; README now also names the record layer, Axiomere (DN-007).
- **History is not rewritten.** DN-001–DN-005 and Spec 001 (`specs/001-research-engine/`) keep their original names and text — they are the record of what was decided when, under the name the project then had. A rename that edited the archive would violate the principle this repository exists to embody.

## Pairing

**Tekmerion** (the framework — evidence that proves) runs on **Axiomere** (the truth ledger — records that cannot be deleted). One produces the verdict; the other guarantees the record it rests on.
