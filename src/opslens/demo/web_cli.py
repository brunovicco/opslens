"""Command-line entry point for the localhost-only OpsLens V1 visual demonstration.

The parser lives inside the package rather than in `scripts/` so the installed
console script and the repository script are the same code path. The viewer
binds structurally to loopback and deliberately exposes no `--host` option:
there is nothing here to point at a routable interface.
"""

import argparse
from collections.abc import Sequence
from typing import cast

from opslens.demo.web import LOCAL_DEMO_PORT, serve_local_demo


def parse_port(value: str) -> int:
    """Parse one bounded localhost TCP port.

    Args:
        value: The raw command-line value.

    Returns:
        The validated port number.

    Raises:
        argparse.ArgumentTypeError: If the value is not an integer in range.
    """
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65_535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def build_parser() -> argparse.ArgumentParser:
    """Build the local visual-demo parser without an external bind option."""
    parser = argparse.ArgumentParser(
        description="Serve the deterministic OpsLens V1 demo on IPv4 loopback only.",
    )
    parser.add_argument(
        "--port",
        type=parse_port,
        default=LOCAL_DEMO_PORT,
        help=f"localhost port (default: {LOCAL_DEMO_PORT})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the localhost-only visual demo and return a process exit status.

    Args:
        argv: Command-line arguments, or None to read `sys.argv`.

    Returns:
        The process exit status.
    """
    namespace = build_parser().parse_args(list(argv) if argv is not None else None)
    port = cast(int, namespace.port)
    serve_local_demo(port=port)
    return 0


__all__ = ["build_parser", "main", "parse_port"]
