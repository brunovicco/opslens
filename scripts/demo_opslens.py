#!/usr/bin/env python3
"""Run the canonical deterministic offline OpsLens V1 demonstration."""

from _bootstrap import ensure_repository_src_on_path

ensure_repository_src_on_path()

from opslens.demo.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
