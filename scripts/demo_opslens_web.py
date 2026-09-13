#!/usr/bin/env python3
"""Launch the localhost-only OpsLens V1 visual demonstration."""

import argparse
from collections.abc import Sequence
from typing import cast

from _bootstrap import ensure_repository_src_on_path

ensure_repository_src_on_path()

from opslens.demo.web import LOCAL_DEMO_PORT, serve_local_demo  # noqa: E402


def _parse_port(value: str) -> int:
    """Parse one bounded localhost TCP port."""
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65_535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def _parser() -> argparse.ArgumentParser:
    """Build the local visual-demo parser without an external bind option."""
    parser = argparse.ArgumentParser(
        description="Serve the deterministic OpsLens V1 demo on IPv4 loopback only.",
    )
    parser.add_argument(
        "--port",
        type=_parse_port,
        default=LOCAL_DEMO_PORT,
        help=f"localhost port (default: {LOCAL_DEMO_PORT})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the localhost-only visual demo and return a process exit status."""
    namespace = _parser().parse_args(list(argv) if argv is not None else None)
    port = cast(int, namespace.port)
    serve_local_demo(port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
