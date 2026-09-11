#!/usr/bin/env python3
"""Verify one persisted Gate 19.2 live-measurement artifact without provider I/O."""

from __future__ import annotations

import argparse
from pathlib import Path

from opslens.public_analysis.application.representative_live_measurement_review import (
    RepresentativeLiveMeasurementReviewError,
    review_representative_live_measurement_artifact,
)

_DEFAULT_ARTIFACT = Path("labs/evidence/phase-19-gate-19-2-live-measurement-v1.json")


def _parser() -> argparse.ArgumentParser:
    """Build the read-only post-run review CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=_DEFAULT_ARTIFACT)
    parser.add_argument("--expected-opslens-commit-sha", required=True)
    return parser


def main() -> int:
    """Fail closed unless persisted evidence is canonical and frozen-anchor exact."""
    args = _parser().parse_args()
    artifact_path = args.artifact.resolve()
    try:
        serialized = artifact_path.read_bytes()
    except OSError as exc:
        raise SystemExit(f"could not read live measurement artifact {artifact_path}") from exc

    try:
        artifact = review_representative_live_measurement_artifact(
            serialized,
            expected_opslens_commit_sha=args.expected_opslens_commit_sha,
        )
    except RepresentativeLiveMeasurementReviewError as exc:
        raise SystemExit(str(exc)) from exc

    print(
        "phase19_gate19_2_live_measurement=PASS "
        f"run_id={artifact.run_id} "
        f"opslens_commit_sha={artifact.opslens_commit_sha} "
        f"end_to_end_duration_ms={artifact.end_to_end_duration_ms} "
        f"serialized_result_bytes={artifact.serialized_result_bytes} "
        "topology_evaluation_allowed=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
