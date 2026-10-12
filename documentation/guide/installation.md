# Installation

Tekmerion's MCP server lets an agent (or any MCP client) run a study end
to end — register claims with falsifiers, verify citations, adjudicate,
freeze, evaluate, export, deposit — against the same production services
as the web UI, with the same refusals.

## Install from PyPI

```bash
pip install tekmerion          # the engine; core has no third-party dependencies
pip install "tekmerion[mcp]"   # adds the MCP server (the `mcp` SDK is the only extra)
```

The server also needs the Axiomere record layer: the `axiomere` Python
package and its native Rust extension (`axiomere_py`). There is **no
pure-Python fallback, by design** — a ledger that cannot load its real
core must fail loudly, not silently degrade. If the prebuilt bindings do
not cover your platform, build the wheel set from the three public
repositories:

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

Prerequisites for the source build: Python 3.12 (the prebuilt bindings
wheel is tagged `cp312`; other versions need the bindings built for that
interpreter), a Rust toolchain (<https://rustup.rs>), and `git`.

## Configure one instance = one actor

A server instance runs as **one named actor with one WS6 role**; every
record it appends carries that identity. Multi-actor work (the normal
shape — a researcher and an adjudicator) means multiple configured
instances against the same workspace directory.

```bash
export TEKMERION_ACTOR="your-name"          # required — the server refuses to start without it
export TEKMERION_ROLE=researcher            # researcher | reviewer | adjudicator | integrity
export TEKMERION_WORKSPACE="$PWD/tekmerion-workspace"
tekmerion-mcp                               # stdio server; normally launched by your MCP client
```

Optional, per deployment: `OPENALEX_API_KEY` (adds OpenAlex to citation
checks; Crossref works without a key), `TEKMERION_DEPOSIT_ROOT=/path`
(local deposit transport) or `ZENODO_ACCESS_TOKEN` (Zenodo transport).
Deposit *approval* is never configuration — it is a per-call decision the
engine's gate checks on every deposit.

!!! note "Network egress"
    `attach_citation` performs **live** resolution (Crossref / OpenAlex /
    CORE) inside the server process. A stdio server inherits its
    **client's** environment, not your shell's — proxy variables and
    connector API keys must be present in the environment the client
    launches the server with, or resolution fails even though the same
    lookup works from your shell.

## Client configuration (copy-paste)

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

Claude Desktop: paste the generic JSON into `claude_desktop_config.json`
(Settings → Developer → Edit Config).

Two instances are the quickstart shape, not an advanced one: freeze, run,
adjudication decisions, and deposit are adjudicator-only actions, and the
integrity swap control needs early ledger events from **different**
actors to bite — register the study's first claims from both instances
(see the [quickstart](quickstart.md)).

## The agent skill

The repository ships an agent skill (`skill/SKILL.md`) that teaches the
full operating playbooks — evidence-question studies, adapter flows,
math-claim flows — and the honesty rules for reporting what the machinery
issued: never report a verdict the machinery didn't issue, refusals are
final, and lane-1 output is never presented as lane-2 progress.
