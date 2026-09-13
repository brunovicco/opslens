"""Fail-closed tests for Gate 19.7 post-apply convergence evidence."""

import json
from pathlib import Path
from typing import cast

EVIDENCE = Path(
    "labs/evidence/phase-19-gate-19-7-post-apply-convergence-v1.json"
)


def _load() -> dict[str, object]:
    raw = cast(object, json.loads(EVIDENCE.read_text(encoding="utf-8")))
    assert isinstance(raw, dict)
    return cast(dict[str, object], raw)


def test_gate19_7_convergence_source_and_state_are_exact() -> None:
    """Bind convergence evidence to the protected post-apply checkpoint."""
    evidence = _load()

    assert evidence["artifact_type"] == (
        "phase-19-gate-19-7-post-apply-convergence:v1"
    )

    source = evidence["protected_source"]
    assert isinstance(source, dict)
    typed_source = cast(dict[str, object], source)
    assert typed_source == {
        "aws_account": "487757851499",
        "aws_region": "us-east-1",
        "head_sha": "d748f0cde9b84552b2367da7a407feafdf4bf9ff",
    }

    state = evidence["terraform_state"]
    assert isinstance(state, dict)
    typed_state = cast(dict[str, object], state)
    assert typed_state == {
        "lineage_before": "6c958ab2-4cc6-7f96-a528-89535504f65c",
        "lineage_after": "6c958ab2-4cc6-7f96-a528-89535504f65c",
        "serial_before": 117,
        "serial_after": 117,
        "state_mutation_observed": False,
    }


def test_gate19_7_convergence_is_exact_zero_action_plan() -> None:
    """Require one consumed convergence plan with zero managed actions."""
    evidence = _load()
    plan = evidence["convergence_plan"]
    assert isinstance(plan, dict)
    typed_plan = cast(dict[str, object], plan)

    assert typed_plan["invocation_count"] == 1
    assert typed_plan["authorization_consumed"] is True
    assert typed_plan["retry_authorized"] is False
    assert typed_plan["lock_enabled"] is False
    assert typed_plan["refresh_enabled"] is True
    assert typed_plan["terraform_detailed_exit_code"] == 0
    assert typed_plan["managed_adds"] == 0
    assert typed_plan["managed_changes"] == 0
    assert typed_plan["managed_destroys"] == 0
    assert typed_plan["managed_replacements"] == 0
    assert typed_plan["deferred_change_count"] == 0
    assert typed_plan["saved_plan_reusable_for_apply"] is False
    assert typed_plan["result"] == (
        "NO_CHANGES_INFRASTRUCTURE_MATCHES_CONFIGURATION"
    )
    assert typed_plan["plan_binary_sha256"] == (
        "26380a6f09fc536f7738e1b855054e8a49183a24ae2e3711f6621a2c8c338157"
    )
    assert typed_plan["plan_json_sha256"] == (
        "505151c1d56f4d92483ad602185a49a89f10f1b9f6003eef9532cefcedf12f1d"
    )

    # Observed refresh drift is retained as evidence and is not rewritten as zero.
    assert typed_plan["resource_drift_entry_count"] == 5


def test_gate19_7_convergence_runtime_remains_materialized_not_enabled() -> None:
    """Require convergence without public/provider-heavy enablement."""
    evidence = _load()
    controls = evidence["materialized_controls"]
    assert isinstance(controls, dict)
    typed_controls = cast(dict[str, object], controls)

    assert typed_controls == {
        "runtime_materialized": True,
        "execute_api_endpoint_disabled": True,
        "submit_switch": "false",
        "api_reserved_concurrency": 0,
        "worker_switch": "false",
        "worker_reserved_concurrency": 0,
        "worker_event_source_mapping_state": "Disabled",
        "custom_domain_mapping_present": False,
        "provider_heavy_public_execution_path_enabled": False,
    }


def test_gate19_7_convergence_resets_all_mutation_authority_fail_closed() -> None:
    """Require no implicit Terraform, AWS, IAM, or runtime authority after plan."""
    evidence = _load()
    authority = evidence["authority_after_plan"]
    assert isinstance(authority, dict)
    typed_authority = cast(dict[str, object], authority)

    assert typed_authority["convergence_plan_authorization_consumed"] is True

    false_keys = {
        "convergence_plan_retry_authorized",
        "terraform_apply_authorized",
        "terraform_replan_authorized",
        "terraform_destroy_authorized",
        "terraform_replacement_authorized",
        "terraform_import_authorized",
        "terraform_state_rm_authorized",
        "terraform_untaint_authorized",
        "aws_mutation_authorized",
        "iam_mutation_authorized",
        "runtime_enablement_authorized",
        "public_endpoint_enablement_authorized",
        "worker_enablement_authorized",
        "event_source_enablement_authorized",
        "provider_heavy_execution_authorized",
    }

    assert false_keys <= typed_authority.keys()
    assert all(typed_authority[key] is False for key in false_keys)

    gate = evidence["gate19_7"]
    assert isinstance(gate, dict)
    typed_gate = cast(dict[str, object], gate)
    assert typed_gate["post_apply_convergence_proven"] is True
    assert typed_gate["formal_closeout_candidate"] is True
    assert typed_gate["protected_closeout_evidence_required"] is True
    assert typed_gate["runtime_remains_disabled"] is True
