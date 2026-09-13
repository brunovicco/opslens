"""Command-line entry point for the deterministic OpsLens V1 demo suite evaluation.

The parser lives inside the package rather than in `scripts/` so the installed
console script and the repository script are the same code path. The evaluation
is a projection of retained scenario results and creates no new authority.
"""

import argparse
import sys
from collections.abc import Sequence
from typing import Final, cast

from opslens.demo.evaluation import build_demo_suite_evaluation

SUPPORTED_FORMATS: Final = ("text", "json")


def build_parser() -> argparse.ArgumentParser:
    """Build the bounded suite-evaluation parser."""
    parser = argparse.ArgumentParser(
        description="Evaluate the deterministic offline OpsLens V1 demo suite.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=SUPPORTED_FORMATS,
        default="text",
        help="reviewer output projection",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the deterministic suite evaluation and emit one supported projection.

    Args:
        argv: Command-line arguments, or None to read `sys.argv`.

    Returns:
        The process exit status.

    Raises:
        AssertionError: If argparse admits a projection this function cannot render.
    """
    namespace = build_parser().parse_args(list(argv) if argv is not None else None)
    output_format = cast(str, namespace.output_format)
    evaluation = build_demo_suite_evaluation()
    if output_format == "text":
        sys.stdout.write(evaluation.to_text())
        return 0
    if output_format == "json":
        sys.stdout.write(evaluation.canonical_json.decode("utf-8") + "\n")
        return 0
    raise AssertionError("argparse admitted an unsupported suite output format")


__all__ = ["SUPPORTED_FORMATS", "build_parser", "main"]
