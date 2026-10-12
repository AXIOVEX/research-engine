"""Run the workspace locally:  python -m tekmerion.ui --root DIR [--port N]

Local serving only (T219): the workspace is an operator console over
study ledgers held in the workspace root. Identity arrives via the
`X-Tekmerion-Actor` / `X-Tekmerion-Role` headers (the SSO hook the
wireframes name); `?actor=` / `?role=` exist so a browser can supply
the same identity where no SSO proxy is in front.
"""

from __future__ import annotations

import argparse

from .server import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tekmerion.ui", description=__doc__)
    parser.add_argument("--root", required=True,
                        help="workspace root holding studies/ (created if absent)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    serve(args.root, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
