"""Regression tests for direct source-layout AgentCore CLI execution."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "script_path",
    [
        "scripts/publish_agentcore_runtime_artifact.py",
        "scripts/run_agentcore_runtime_replay.py",
    ],
)
def test_agentcore_cli_imports_without_pythonpath(script_path: str) -> None:
    """The main-only workflow must not depend on an ambient PYTHONPATH."""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)

    completed = subprocess.run(
        [sys.executable, str(_PROJECT_ROOT / script_path), "--help"],
        cwd=_PROJECT_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "usage:" in completed.stdout.lower()
