# Spec 009 — MCP Server, Agent Skill, and Easy Install — tasks

- [x] T1 Spec + claims bundle v0.1.0 + assessor run at after_specify. (spec.md, plan.md, aee-claims.json, aee-assessment.json, assessment-2026-10-12.md)
- [x] T2 Server package: `src/tekmerion/mcp/` — env configuration (actor required), session layer over `tekmerion.ui.state` actions with the imported WS6 matrix, all tools of spec §4, verbatim-refusal error mapping.
- [x] T3 Packaging: `pyproject.toml` gains the `mcp` extra (`mcp>=2,<3`) and the `tekmerion-mcp` entry point; core dependencies stay empty.
- [x] T4 Tool-layer tests: `tests/test_mcp_server.py` — refusals verbatim (falsifier, freeze, deposit gate), identity attached to events, role denials (freeze/run/decide/deposit under researcher; register under reviewer), adapter + Lean state passthrough, matrix identity with `tekmerion.ui.server.PERMISSIONS`. Full suite green.
- [x] T5 Wheel set built into `dist/`: Axiomere bindings (maturin), axiomere (build), tekmerion (build).
- [x] T6 `docs/install.md`: prerequisites, the wheel-set install (one venv, one command sequence), per-instance configuration, copy-paste client configs (generic stdio JSON + Claude Code / Claude Desktop shapes), quickstart pointer.
- [x] T7 `skill/SKILL.md`: orientation, configuration, playbooks (full study flow; math study flow; adapter evidence; export/verify; deposit with approval), honesty rules as operating instructions, troubleshooting keyed to the real refusal texts.
- [x] T8 Clean-room acceptance per spec §7: fresh venv outside the repo, artifacts only, two configured instances, scripted MCP client over stdio, the full scripted flow incl. both refusal paths; flaws fixed and the run repeated from clean; transcript recorded in acceptance-2026-10-12.md.
- [x] T9 Skill installed to `~/workspace/skills/tekmerion/SKILL.md`; claims re-assessed at after_implement on the acceptance + test evidence; assessment record addendum written (assessment-2026-10-12-build.md); branch CI green by read-back.
