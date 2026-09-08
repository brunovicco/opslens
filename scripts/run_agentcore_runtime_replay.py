#!/usr/bin/env python3
"""Replay the frozen Phase 11 corpus through one authenticated AgentCore Runtime."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from botocore.config import Config
from botocore.session import Session

from opslens.agent_baseline.application.reasoning_evaluation import (
    load_agent_reasoning_evaluation_dataset,
)
from opslens.agentcore_runtime.replay import (
    AgentCoreRuntimeInvokeClient,
    execute_agentcore_runtime_replay,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DATASET = (
    _PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "agent_baseline"
    / "golden_single_agent_reasoning_v1.json"
)


def _parse_args() -> argparse.Namespace:
    """Parse exact runtime identity and evidence-binding inputs."""
    parser = argparse.ArgumentParser(
        description=(
            "Invoke one already-deployed bounded AgentCore Runtime with the unchanged "
            "Phase 11 six-case reasoning corpus. No capability execution is performed."
        )
    )
    parser.add_argument("--runtime-arn", required=True)
    parser.add_argument("--source-head-sha", required=True)
    parser.add_argument(
        "--replay-run-id",
        default=os.environ.get("GITHUB_RUN_ID"),
        help="Stable replay-run identity; defaults to GITHUB_RUN_ID when available.",
    )
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--dataset", type=Path, default=_DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def _agentcore_client(*, region: str) -> AgentCoreRuntimeInvokeClient:
    """Create the data-plane client with application-level retries disabled."""
    session = Session()
    client = session.create_client(
        "bedrock-agentcore",
        region_name=region,
        config=Config(
            connect_timeout=10,
            read_timeout=300,
            retries={"total_max_attempts": 1, "mode": "standard"},
        ),
    )
    return cast(AgentCoreRuntimeInvokeClient, client)


def _exit_code(report: Mapping[str, object]) -> int:
    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping):
        return 3
    passed = cast(Mapping[object, object], metrics).get("passed_cases")
    total = cast(Mapping[object, object], metrics).get("total_cases")
    if type(passed) is not int or type(total) is not int:
        return 3
    return 0 if total == 6 and passed == total else 2


def main() -> int:
    """Execute the authenticated replay and write one content-minimized JSON report."""
    args = _parse_args()
    runtime_arn = cast(str, args.runtime_arn)
    source_head_sha = cast(str, args.source_head_sha)
    replay_run_id = cast(str | None, args.replay_run_id)
    region = cast(str, args.region)
    dataset_path = cast(Path, args.dataset)
    output = cast(Path | None, args.output)
    if replay_run_id is None or not replay_run_id.strip():
        raise ValueError("--replay-run-id is required outside GitHub Actions")

    dataset = load_agent_reasoning_evaluation_dataset(dataset_path)
    report = execute_agentcore_runtime_replay(
        client=_agentcore_client(region=region),
        runtime_arn=runtime_arn,
        source_head_sha=source_head_sha,
        replay_run_id=replay_run_id,
        dataset=dataset,
    )
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(serialized, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
        print(json.dumps({"output": str(output), "report_id": report["report_id"]}))
    return _exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
