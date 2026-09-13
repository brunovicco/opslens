#!/usr/bin/env python3
"""Launch the localhost-only OpsLens V1 visual demonstration."""

from _bootstrap import ensure_repository_src_on_path

ensure_repository_src_on_path()

from opslens.demo.web_cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
