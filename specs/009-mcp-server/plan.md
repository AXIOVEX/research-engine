# Spec 009 — Plan

**Sequence:** claims (v0.1.0, after_specify) → server package → unit/integration tests → wheel set + install docs + skill → clean-room acceptance (§7 of spec.md) → claims re-assessed at after_implement on the acceptance evidence only.

## Design choices made at specify time

- **SDK, not hand-rolled JSON-RPC.** The official MCP Python SDK (`mcp` 2.3.0) was probed in this environment before the spec was written: it installs cleanly, and its server API (`mcp.server.mcpserver.MCPServer`, decorator-registered tools, `run(transport="stdio")`) covers the design with no shim. The extra pins `mcp>=2,<3` so the next major's API changes arrive as a deliberate upgrade, not a surprise. A stdlib JSON-RPC fallback was the alternative; it was rejected because protocol compatibility with real MCP clients is the product surface here, and an almost-compatible subset is a defect this project does not ship.
- **Reuse the UI's orchestration, import the UI's permission matrix.** `tekmerion.ui.state` already contains the production action paths (register, attach, freeze, run, export, deposit) with the sidecar discipline the export path depends on (freeze.json captured at freeze, retrieved.json for the bundle's retrieved set). The MCP layer drives those actions rather than re-implementing them; the WS6 role matrix is imported from `tekmerion.ui.server.PERMISSIONS` so the two surfaces cannot drift (a test asserts identity).
- **Session register for adapter evidence.** Adapters attach evidence by mutating a register (`emit_adapter_evidence`); Specs 006–008 ship replay of run *records*, not of register evidence. The MCP server therefore keeps a per-study session register: rebuilt from the ledger whenever the ledger head has moved since the session last loaded it (another instance may have appended), with the session's adapter-attached items re-applied after each rebuild. Cross-session adapter-evidence folding stays an adapter-seam question (spec §8), recorded, not invented here.
- **Two instances in acceptance, deliberately.** The swap control needs distinct actors in the tampered window to bite (Phase 5's lesson: a single-actor ledger made it a no-op and the demo run INVALID). The acceptance study is registered by two configured instances (researcher + adjudicator), which is also the designed multi-actor shape (WS6) — and it exercises role denial in the same run (researcher freeze attempt refused before the adjudicator freezes).

## Build shape

- `src/tekmerion/mcp/__init__.py` — package docstring; no SDK import at package import time (CLM-009-05).
- `src/tekmerion/mcp/server.py` — configuration (`ServerConfig.from_env`), the session/workspace layer (`Session`), tool handlers, `build_server()`, `main()` entry point. Tool handlers are plain functions over `Session` (CLM-009-12); the SDK registration is a thin shell at the bottom.
- `pyproject.toml` — `mcp` extra + `tekmerion-mcp` script entry point. Nothing else changes.
- `tests/test_mcp_server.py` — tool-layer tests through the handlers (refusals verbatim, identity on events, role denials, deposit gate, state passthrough), run in the repo venv like every other suite.
- `docs/install.md` + `skill/SKILL.md` — written against the built artifacts, then exercised by the acceptance run; any doc step the run contradicts is a defect in the doc, fixed before the run counts.

## Wheel set

Built under `~/workspace/tekmerion-mcp/dist/` (build artifacts, not committed):

1. Axiomere bindings: `maturin build -m ~/workspace/axiomere/crates/axiomere-py/Cargo.toml` (core at its current main, which carries the float-roundtrip parser fix).
2. `axiomere` pure-Python wheel: `python -m build ~/workspace/axiomere-python`.
3. `tekmerion` wheel: `python -m build` in this worktree.

The acceptance venv installs 1–3 plus `mcp` from the public index (the SDK is the only index install; it is a normal public package dependency, per spec §2).
