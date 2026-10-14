# Installing Tekmerion and running the MCP server

Tekmerion's MCP server lets an agent (or any MCP client) run a study
end to end — register claims with falsifiers, verify citations,
adjudicate, freeze, evaluate, export, deposit — against the same
production services as the web UI, with the same refusals. This page
is the exact path from a clean machine to a running server. It was
executed verbatim in the Spec 009 clean-room acceptance
(`specs/009-mcp-server/acceptance-2026-10-12.md`).

**Status:** the packages are not on PyPI yet (publication is an owner
decision). You install from wheels you build from the three public
repositories — five commands, below.

**Correction (2026-10-13):** the status above is out of date. Both packages
**are** on PyPI, at version **0.1.0**: `tekmerion` and `axiomere`. One part
of the install is still build-from-source, honestly stated: Tekmerion's
record layer needs the compiled Axiomere verification extension
(`axiomere_py`), and prebuilt extension wheels are not published yet — so
that one piece is built from the `axiomere` repository exactly as in step 1
below, and Tekmerion's own error message says so if it is missing. With the
extension wheel installed, `pip install tekmerion axiomere` works. The full
from-source path below remains accurate and is the path the acceptance run
used.

## Prerequisites

- Python 3.12 (the prebuilt bindings wheel is tagged `cp312`; other
  Python versions need the bindings built for that interpreter —
  same command, your toolchain targets it automatically).
- A Rust toolchain for the Axiomere bindings build
  (<https://rustup.rs>).
- `git`.

## 1. Build the wheel set

```bash
git clone https://github.com/AXIOVEX/axiomere
git clone https://github.com/AXIOVEX/axiomere-python
git clone https://github.com/AXIOVEX/tekmerion

python3 -m venv build-env
build-env/bin/pip install maturin build

mkdir -p wheelhouse
build-env/bin/maturin build -m axiomere/crates/axiomere-py/Cargo.toml --out wheelhouse
build-env/bin/python -m build --outdir wheelhouse axiomere-python
build-env/bin/python -m build --outdir wheelhouse tekmerion
```

You now have three wheels in `wheelhouse/`: `axiomere_py-*.whl`
(the Rust record layer — there is no pure-Python fallback, by
design), `axiomere-*.whl` (its Python API), `tekmerion-*.whl` (the
engine + MCP server).

## 2. Install

```bash
python3 -m venv tekmerion-env
tekmerion-env/bin/pip install wheelhouse/axiomere_py-*.whl \
    wheelhouse/axiomere-*.whl wheelhouse/tekmerion-*.whl "mcp>=2,<3"
```

The core `tekmerion` package has no third-party dependencies; the
MCP SDK is the only added package, and only the server needs it.

## 3. Configure one instance = one actor

A server instance runs as **one named actor with one WS6 role**;
every record it appends carries that identity. Multi-actor work
(the normal shape — a researcher and an adjudicator) means multiple
configured instances against the same workspace directory.

```bash
export TEKMERION_ACTOR="your-name"          # required — the server refuses to start without it
export TEKMERION_ROLE=researcher            # researcher | reviewer | adjudicator | integrity
export TEKMERION_WORKSPACE="$PWD/tekmerion-workspace"
tekmerion-env/bin/tekmerion-mcp             # stdio server; normally launched by your MCP client
```

Optional, per deployment: `OPENALEX_API_KEY` (adds OpenAlex to
citation checks; Crossref works without a key),
`TEKMERION_DEPOSIT_ROOT=/path` (local deposit transport) or
`ZENODO_ACCESS_TOKEN` (Zenodo transport). Deposit *approval* is
never configuration — it is a per-call decision the engine's gate
checks on every deposit.

## 4. Client configuration (copy-paste)

Generic MCP client (stdio):

```json
{
  "mcpServers": {
    "tekmerion-researcher": {
      "command": "/path/to/tekmerion-env/bin/tekmerion-mcp",
      "env": {
        "TEKMERION_ACTOR": "your-name",
        "TEKMERION_ROLE": "researcher",
        "TEKMERION_WORKSPACE": "/path/to/tekmerion-workspace"
      }
    },
    "tekmerion-adjudicator": {
      "command": "/path/to/tekmerion-env/bin/tekmerion-mcp",
      "env": {
        "TEKMERION_ACTOR": "your-name",
        "TEKMERION_ROLE": "adjudicator",
        "TEKMERION_WORKSPACE": "/path/to/tekmerion-workspace"
      }
    }
  }
}
```

Claude Code:

```bash
claude mcp add tekmerion-researcher \
  -e TEKMERION_ACTOR=your-name -e TEKMERION_ROLE=researcher \
  -e TEKMERION_WORKSPACE=/path/to/tekmerion-workspace \
  -- /path/to/tekmerion-env/bin/tekmerion-mcp
```

Claude Desktop: paste the generic JSON into
`claude_desktop_config.json` (Settings → Developer → Edit Config).

Two instances are the quickstart shape, not an advanced one:
freeze, run, adjudication decisions, and deposit are
adjudicator-only actions, and the integrity swap control needs
early ledger events from **different** actors to bite — register
the study's first claims from both instances (see the skill's
playbook).

## 5. Quickstart (through your client, tools only)

1. `create_study` — `{"study_id": "demo", "title": "Demo study"}` (either instance).
2. `register_claim` from the researcher instance, then a second
   claim from the adjudicator instance — each with a real
   falsifier, a `margin` (e.g. `0.1`) and a `sufficiency_floor`
   (e.g. `1`). Try one registration *without* a falsifier first if
   you want to see the point of the system: the engine refuses,
   verbatim, and appends nothing.
3. `attach_citation` with a real DOI; watch it resolve and get
   content-checked. Attach a fabricated DOI and watch it land in
   the adjudication queue as `not_found`.
4. `decide_adjudication` from the adjudicator instance
   (`exclude`, with a rationale).
5. `freeze_study` (adjudicator; `linked_exploratory: []`, the
   default controls are fine for a demo), then `run_evaluation`,
   then `get_verdicts`.
6. `export_bundle`, then `verify_bundle` on the exported directory
   — the verifier consumes only the bundle.

The agent skill (`skill/SKILL.md` in this repository) teaches the
full playbooks, including the math-claims and adapter flows, and
the honesty rules for reporting what the machinery issued.
