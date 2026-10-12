"""Run the admin console locally:

    python -m tekmerion.console --root DIR [--port N] [--fixture]

--root is the platform root (the directory holding deployment.axmr
and the per-tenant ledgers); it is created if absent. A root with no
platform admin bootstrapped can only show the sign-in screen's
refusals — bootstrap is an out-of-band deployment act
(`PlatformService.bootstrap_platform_admin`), never a console one.

--fixture builds a labeled specimen world instead (see
`tekmerion.console.fixture`): two tenants, both IdP protocols
configured, keys, a declared break-glass policy, seeded compliance
records — every screen reachable, all of it specimen data in a
throwaway root. Fixture mode is for evaluation and screenshots;
it is never a deployment.
"""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tekmerion.console", description=__doc__)
    parser.add_argument("--root", default=None,
                        help="platform root directory (default: a fresh temp dir in --fixture mode; required otherwise)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--fixture", action="store_true",
                        help="build the labeled fixture world and serve it")
    args = parser.parse_args(argv)
    from .server import serve
    serve(args.root, host=args.host, port=args.port, fixture=args.fixture)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
