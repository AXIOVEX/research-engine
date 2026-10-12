"""Served-artifact identity for the admin console (Spec 005, E5).

Standing rule (owner, 2026-10-12): a deployment is verified by the
identity of the served artifact, never by liveness. The console
therefore stamps every page footer and a machine-readable endpoint
(`/build-id`) with a BUILD_ID computed from the artifact actually
being served:

- a **source stamp** — SHA-256 over this package's own sources and
  stylesheet, recomputed at process start. If the served tree
  changes, the stamp changes; a stamp that matches the build is
  proof the new build is the one answering.
- a **git stamp** — the checkout's HEAD, when the server runs from
  a git worktree (development). Absent outside one; the source
  stamp stands on its own.

The stamp asserts what is served, not what was intended: the
`/build-id` endpoint recomputes nothing and caches nothing beyond
the process-start computation, so a mismatched stamp is visible
exactly where a deploy check looks for it.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

_PACKAGE = Path(__file__).parent
_REPO = _PACKAGE.parents[2]


def source_stamp(paths: list[Path] | None = None) -> str:
    """SHA-256 (first 12 hex) over the console package's sources.

    `paths` is injectable so the currency mechanism itself is
    testable: edit any stamped file and the stamp moves."""
    if paths is None:
        paths = sorted(_PACKAGE.glob("*.py")) + [_PACKAGE / "console.css"]
    h = hashlib.sha256()
    for p in paths:
        h.update(p.name.encode("utf-8"))
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def _git_stamp() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(_REPO), "rev-parse", "--short=12", "HEAD"],
            capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return f"git-{out.stdout.strip()}"
    except Exception:  # noqa: BLE001 — no git is a state, not an error
        pass
    return "nogit"


def compute_build_id() -> str:
    return f"{_git_stamp()}+src-{source_stamp()}"


#: The stamp of the artifact this process serves. Computed once, at
#: import: a restarted process re-stamps, a running one never drifts.
BUILD_ID = compute_build_id()
