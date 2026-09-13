#!/usr/bin/env python3
"""Evaluate the three canonical deterministic offline OpsLens V1 scenarios."""

from _bootstrap import ensure_repository_src_on_path

ensure_repository_src_on_path()

from opslens.demo.evaluation_cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
