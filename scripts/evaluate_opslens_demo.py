#!/usr/bin/env python3
"""Evaluate the three canonical deterministic offline OpsLens V1 scenarios."""

import argparse
import sys
from collections.abc import Sequence
from typing import cast

from _bootstrap import ensure_repository_src_on_path

ensure_repository_src_on_path()

from opslens.demo import build_demo_suite_evaluation  # noqa: E402

_SUPPORTED_FORMATS = ("text", "json")


def _parser() -> argparse.ArgumentParser:
    """Build the bounded suite-evaluation CLI parser."""
    parser = argparse.ArgumentParser(
        description="Evaluate the deterministic offline OpsLens V1 demo suite.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=_SUPPORTED_FORMATS,
        default="text",
        help="reviewer output projection",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the deterministic suite evaluation and emit one supported projection."""
    namespace = _parser().parse_args(list(argv) if argv is not None else None)
    output_format = cast(str, namespace.output_format)
    evaluation = build_demo_suite_evaluation()
    if output_format == "text":
        sys.stdout.write(evaluation.to_text())
        return 0
    if output_format == "json":
        sys.stdout.write(evaluation.canonical_json.decode("utf-8") + "\n")
        return 0
    raise AssertionError("argparse admitted an unsupported suite output format")


if __name__ == "__main__":
    raise SystemExit(main())
