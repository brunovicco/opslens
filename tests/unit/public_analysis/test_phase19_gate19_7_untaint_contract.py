"""Fail-closed tests for the Gate 19.7 controlled Terraform-state untaint boundary."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

DIAGNOSIS = Path(
    "labs/evidence/phase-19-gate-19-7-replacement-diagnosis-v1.json"
)
CONTRACT = Path("labs/evidence/phase-19-gate-19-7-untaint-contract-v1.json")
VERIFIER = Path("scripts/verify_phase19_gate19_7_untaint_contract.py")


def _load(path: Path) -> dict[str, object]:
    raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(raw, dict)
    return cast(dict[str, object], raw)


def test_gate19_7_untaint_contract_verifier_passes_offline() -> None:
    """Require the static untaint boundary to verify without AWS access."""
    result = subprocess.run(
        [sys.executable, str(VERIFIER)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "phase19_gate19_7_untaint_contract=PASS" in result.stdout
    assert "target=aws_lambda_function.public_async_api[0]" in result.stdout
    assert "taint_confirmed=true" in result.stdout
    assert "remote_config_matches=true" in result.stdout
    assert "terraform_untaint_authorized=false" in result.stdout
    assert "terraform_apply_authorized=false" in result.stdout
    assert "human_untaint_authorization_required=true" in result.stdout


def test_gate19_7_replacement_diagnosis_freezes_taint_evidence() -> None:
    """Freeze the rejected replacement and healthy matching remote Lambda evidence."""
    diagnosis = _load(DIAGNOSIS)

    assert diagnosis["artifact_type"] == (
        "phase-19-gate-19-7-replacement-diagnosis:v1"
    )
    assert diagnosis["source_head_sha"] == (
        "46fb069beffe2a49c1bde647d51ac8d7bcf4a687"
    )

    state = diagnosis["terraform_state"]
    assert isinstance(state, dict)
    typed_state = cast(dict[str, object], state)
    assert typed_state["api_lambda_instance_status"] == "tainted"
    assert typed_state["tainted"] is True

    rejected = diagnosis["rejected_recovery_plan"]
    assert isinstance(rejected, dict)
    typed_rejected = cast(dict[str, object], rejected)
    assert typed_rejected["actions"] == ["delete", "create"]
    assert typed_rejected["action_reason"] == "replace_because_tainted"
    assert typed_rejected["admitted"] is False
    assert typed_rejected["after_reserved_concurrency"] == 0

    api = diagnosis["aws_api_lambda"]
    assert isinstance(api, dict)
    typed_api = cast(dict[str, object], api)
    assert typed_api["configuration_matches_expected"] is True
    assert typed_api["state"] == "Active"
    assert typed_api["last_update_status"] == "Successful"
    assert typed_api["reserved_concurrency"] is None
    assert typed_api["reserved_concurrency_observation"] == (
        "NOT_CONFIGURED_OR_NOT_OBSERVED"
    )


def test_gate19_7_untaint_contract_requires_separate_human_authorization() -> None:
    """Keep every state, apply, destroy, and runtime authority false."""
    contract = _load(CONTRACT)

    assert contract["artifact_type"] == "phase-19-gate-19-7-untaint-contract:v1"

    target = contract["untaint_target"]
    assert isinstance(target, dict)
    typed_target = cast(dict[str, object], target)
    assert typed_target["resource_address"] == (
        "aws_lambda_function.public_async_api[0]"
    )
    assert typed_target["expected_pre_status"] == "tainted"

    design = contract["state_mutation_design"]
    assert isinstance(design, dict)
    typed_design = cast(dict[str, object], design)
    assert typed_design["operation"] == "terraform untaint"
    assert typed_design["aws_resource_mutation_expected"] is False
    assert typed_design["terraform_state_mutation_expected"] is True
    assert typed_design["state_lock_required"] is True
    assert typed_design["allow_lock_false"] is False
    assert typed_design["allow_import"] is False
    assert typed_design["allow_state_rm"] is False
    assert typed_design["allow_replace"] is False
    assert typed_design["allow_destroy"] is False
    assert typed_design["allow_apply"] is False
    assert typed_design["maximum_target_count"] == 1

    pre = contract["required_pre_authorization_evidence"]
    assert isinstance(pre, dict)
    typed_pre = cast(dict[str, object], pre)
    assert typed_pre["terraform_state_lineage_required"] is True
    assert typed_pre["terraform_state_serial_required"] is True
    assert typed_pre["target_still_tainted_required"] is True
    assert typed_pre["remote_configuration_still_matches_expected_required"] is True
    assert typed_pre["explicit_human_untaint_authorization_required"] is True

    authority = contract["authority"]
    assert isinstance(authority, dict)
    typed_authority = cast(dict[str, object], authority)
    assert all(value is False for value in typed_authority.values())


def test_gate19_7_post_untaint_still_requires_fresh_non_destructive_plan() -> None:
    """Keep post-untaint recovery bounded and stop before apply."""
    contract = _load(CONTRACT)
    post = contract["required_post_untaint_evidence"]
    assert isinstance(post, dict)
    typed_post = cast(dict[str, object], post)

    assert typed_post["target_no_longer_tainted_required"] is True
    assert typed_post["remote_configuration_unchanged_required"] is True
    assert typed_post["fresh_recovery_plan_required"] is True
    assert typed_post["fresh_recovery_plan_expected_creates"] == 5
    assert typed_post["fresh_recovery_plan_maximum_updates"] == 1
    assert typed_post["fresh_recovery_plan_allowed_update"] == (
        "aws_lambda_function.public_async_api"
    )
    assert typed_post["fresh_recovery_plan_deletes"] == 0
    assert typed_post["fresh_recovery_plan_replacements"] == 0
    assert typed_post["terraform_apply_authorized"] is False
