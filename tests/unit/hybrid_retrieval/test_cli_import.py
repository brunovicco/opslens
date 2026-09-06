"""Fresh-interpreter regression tests for the Gate 8.4 CLI import boundary."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_gate84_cli_imports_cleanly_in_fresh_interpreter() -> None:
    """Import the real CLI module without initializing an AWS provider call."""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(_REPOSITORY_ROOT / "src")

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import "
                "opslens.hybrid_retrieval.cli."
                "run_bedrock_hybrid_synthesis_evaluation"
            ),
        ],
        cwd=_REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
