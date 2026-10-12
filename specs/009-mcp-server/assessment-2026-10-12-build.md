# Assessment record — build exit (2026-10-12)

Bundle v0.2.0 assessed at after_implement (AEE engine 1.0.4, threshold 0.70; `aee-assessment-after-implement.json`). Outcome: **iterate**, with exactly one claim below threshold — by design (below).

| Claim | Score | Status / stage | Basis |
|---|---|---|---|
| CLM-009-01 | 0.999 | supported / checked | full-flow test through handlers + acceptance steps 6–17 |
| CLM-009-02 | 1.000 | supported / checked | verbatim-refusal tests incl. the wire-level shell test; acceptance steps 4/8/18 read the texts off the wire |
| CLM-009-03 | 1.000 | supported / checked | matrix-identity test (TOOL_ROLES `is` PERMISSIONS); role-denial tests; acceptance steps 1/8 |
| CLM-009-04 | 0.999 | supported / checked | deposit-gate unit test (refusal + approved local path); acceptance steps 18–19 |
| CLM-009-05 | 1.000 | supported / checked | SDK-confinement AST test; core-import-with-SDK-blocked subprocess test; wheel METADATA (no core Requires-Dist) |
| CLM-009-06 | 0.988 | supported / checked | clean-room acceptance (fresh venv, three wheels + SDK only, import locality asserted); docs/install.md |
| CLM-009-07 | 0.999 | supported / checked | acceptance steps 2–17 ending in a standalone-verified bundle |
| CLM-009-08 | 1.000 | supported / checked | GRIM/Lean/checkCIF passthrough tests; acceptance step 12 (`run_by_us` + replay) |
| CLM-009-09 | 0.481 | **draft / created** | prediction; its falsifier — a skill-only study run by an agent that did not write the skill — has not happened. The coordinator's post-acceptance exercise is that run. **Not** moved on the builder's own evidence. |
| CLM-009-10 | 0.999 | supported / checked | no-delete inventory test over handlers + the 29-tool wire list |
| CLM-009-11 | 0.984 | supported / checked | the acceptance run executed the documented quickstart sequence through tools only |
| CLM-009-12 | 0.999 | supported / checked | handlers tested directly and through `server.call_tool` without transport; acceptance over stdio |

Suite at exit: 190 passed (172 shipped + 18 new in `tests/test_mcp_server.py`). Branch CI green by read-back (PR #5).

Two defects the process caught, both fixed and recorded in the acceptance record: the wheel originally shipped an unimportable `tekmerion.ui` (missing `style.css` package data — a latent defect of the installable product, not only of this spec), and SDK 2.x's masked exceptions would have silently voided verbatim refusals on the wire (shell now converts to `ToolError(str(exc))`; spec §5 records the mechanism).

**Remains not understood:** real MCP clients beyond the reference SDK client (the acceptance drove the official SDK's stdio client; Claude Desktop/Code configuration blocks in docs/install.md are the standard shapes but were not themselves executed here); behavior of the server under a second SDK major version (the pin is `mcp>=2,<3` — a future major is a new assessment, not an assumption); cross-session adapter-evidence replay remains session-scoped by design (spec §8 owner-decision candidate).
