#!/usr/bin/env python3
"""Admit a fresh Gate 19.7 Terraform plan while keeping apply authority false."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

_GATE19_7_CONTRACT_VERIFIER = Path(
    "scripts/verify_phase19_gate19_7_materialization_contract.py"
)
_GATE19_6_PLAN_VERIFIER = Path("scripts/verify_phase19_gate19_6_exact_plan.py")
_GATE19_7_PLAN_INPUT = Path("labs/evidence/phase-19-gate-19-7-plan-input-v1.tfvars.json")
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class Gate19_7FreshPlanError(RuntimeError):
    """Raised when a fresh Gate 19.7 plan cannot be admitted."""


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_7FreshPlanError(f"{label} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise Gate19_7FreshPlanError(f"{label} keys must be strings")
    return cast(dict[str, object], raw)


def _load(path: Path) -> dict[str, object]:
    try:
        raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise Gate19_7FreshPlanError(f"cannot read {path}: {exc}") from exc
    return _object(raw, label=str(path))


def _sha256(path: Path) -> str:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise Gate19_7FreshPlanError(f"cannot read {path}: {exc}") from exc
    if not payload:
        raise Gate19_7FreshPlanError(f"{path} must not be empty")
    return hashlib.sha256(payload).hexdigest()


def _git_head() -> str:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise Gate19_7FreshPlanError("cannot resolve repository HEAD") from exc
    if _FULL_SHA.fullmatch(head) is None:
        raise Gate19_7FreshPlanError("repository HEAD is not a full lowercase SHA")
    return head


def _run_offline(command: list[str], *, label: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise Gate19_7FreshPlanError(f"cannot execute {label}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown failure"
        raise Gate19_7FreshPlanError(f"{label} failed: {detail}")
    return result


def _verify_source_head(expected_source_head: str) -> str:
    if _FULL_SHA.fullmatch(expected_source_head) is None:
        raise Gate19_7FreshPlanError("--expected-source-head must be a full lowercase SHA")
    actual = _git_head()
    if actual != expected_source_head:
        raise Gate19_7FreshPlanError(
            f"repository HEAD {actual} differs from reviewed source {expected_source_head}"
        )
    return actual


def _verify_inherited_admission(
    summary: dict[str, object], *, expected_source_head: str
) -> None:
    if summary.get("artifact_type") != "phase-19-gate-19-6-plan-admission:v1":
        raise Gate19_7FreshPlanError("retained exact-plan verifier returned wrong artifact type")
    if summary.get("source_head_sha") != expected_source_head:
        raise Gate19_7FreshPlanError("retained plan admission source head drifted")
    if summary.get("managed_create_count") != 21:
        raise Gate19_7FreshPlanError("fresh Gate 19.7 plan must contain exactly 21 creates")
    safety = _object(summary.get("safety"), label="retained_plan.safety")
    expected_safety: dict[str, object] = {
        "iam_mutations": 0,
        "plan_only": True,
        "provider_heavy_public_executions": 0,
        "public_endpoint_enablements": 0,
        "remote_state_lock_disabled": True,
        "runtime_resources_mutated": 0,
        "terraform_apply_authorized": False,
    }
    if safety != expected_safety:
        raise Gate19_7FreshPlanError("retained exact-plan safety result drifted")


def _write_summary(
    output: Path,
    *,
    source_head_sha: str,
    plan_binary: Path,
    retained_summary: dict[str, object],
) -> None:
    summary = {
        "schema_version": 1,
        "artifact_type": "phase-19-gate-19-7-fresh-plan-admission:v1",
        "source_head_sha": source_head_sha,
        "plan_binary_sha256": _sha256(plan_binary),
        "plan_json_sha256": retained_summary.get("plan_json_sha256"),
        "terraform_format_version": retained_summary.get("terraform_format_version"),
        "terraform_version": retained_summary.get("terraform_version"),
        "selected_design": retained_summary.get("selected_design"),
        "managed_create_count": retained_summary.get("managed_create_count"),
        "managed_create_inventory": retained_summary.get("managed_create_inventory"),
        "account_id": retained_summary.get("account_id"),
        "region": retained_summary.get("region"),
        "artifacts": retained_summary.get("artifacts"),
        "plan_observability": retained_summary.get("plan_observability"),
        "authority": {
            "fresh_plan": True,
            "retained_gate19_6_exact_plan_engine_pass": True,
            "gate19_6_binary_plan_reuse_forbidden": True,
            "materialized_not_enabled": True,
            "explicit_human_apply_authorization_required": True,
            "terraform_apply_authorized": False,
            "apply_authorization_status": "PENDING_EXPLICIT_HUMAN_AUTHORIZATION",
        },
        "safety": {
            "remote_state_lock_disabled_during_plan": True,
            "runtime_resources_mutated": 0,
            "iam_mutations": 0,
            "public_endpoint_enablements": 0,
            "provider_heavy_public_executions": 0,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-json", type=Path, required=True)
    parser.add_argument("--plan-binary", type=Path, required=True)
    parser.add_argument("--expected-source-head", required=True)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    """Admit one fresh plan entirely offline after the human Terraform plan completes."""
    args = _parser().parse_args()
    source_head = _verify_source_head(args.expected_source_head)

    _run_offline(
        [sys.executable, str(_GATE19_7_CONTRACT_VERIFIER)],
        label="Gate 19.7 materialization contract verifier",
    )

    with tempfile.TemporaryDirectory(prefix="opslens-gate19-7-") as temp_dir:
        retained_output = Path(temp_dir) / "retained-plan-admission.json"
        result = _run_offline(
            [
                sys.executable,
                str(_GATE19_6_PLAN_VERIFIER),
                "--plan-json",
                str(args.plan_json),
                "--plan-input",
                str(_GATE19_7_PLAN_INPUT),
                "--output",
                str(retained_output),
            ],
            label="retained Gate 19.6 exact-plan verifier",
        )
        if "phase19_gate19_6_plan=PASS" not in result.stdout:
            raise Gate19_7FreshPlanError(
                "retained exact-plan verifier did not emit its PASS marker"
            )
        retained_summary = _load(retained_output)

    _verify_inherited_admission(retained_summary, expected_source_head=source_head)
    plan_binary_sha256 = _sha256(args.plan_binary)
    if args.output is not None:
        _write_summary(
            args.output,
            source_head_sha=source_head,
            plan_binary=args.plan_binary,
            retained_summary=retained_summary,
        )

    print(
        "phase19_gate19_7_plan=PASS "
        "managed_creates=21 updates=0 deletes=0 replacements=0 "
        f"plan_binary_sha256={plan_binary_sha256} "
        "materialized_not_enabled=true terraform_apply_authorized=false "
        "human_apply_authorization_required=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
