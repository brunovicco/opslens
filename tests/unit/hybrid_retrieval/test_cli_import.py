"""Fresh-interpreter regressions for bounded hybrid runtime CLIs."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "module_name",
    (
        (
            "opslens.hybrid_retrieval.cli."
            "run_bedrock_hybrid_synthesis_evaluation"
        ),
        (
            "opslens.hybrid_retrieval.cli."
            "run_bedrock_hybrid_synthesis_optimization_experiment"
        ),
    ),
)
def test_hybrid_runtime_cli_imports_cleanly_in_fresh_interpreter(
    module_name: str,
) -> None:
    """Import each runtime CLI without initializing an AWS provider call."""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(_REPOSITORY_ROOT / "src")

    completed = subprocess.run(
        [sys.executable, "-c", f"import {module_name}"],
        cwd=_REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
