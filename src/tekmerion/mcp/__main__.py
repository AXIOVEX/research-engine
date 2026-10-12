"""`python -m tekmerion.mcp` — same entry point as `tekmerion-mcp`."""

from .server import main

if __name__ == "__main__":
    raise SystemExit(main())
