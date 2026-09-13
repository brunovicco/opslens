"""Fail-closed tests for Gate 19.7 recovery-v2 apply authority."""

import json
from pathlib import Path
from typing import cast

EVIDENCE = Path(
    "labs/evidence/phase-19-gate-19-7-recovery-v2-authority-v1.json"
)


def _load() -> dict[str, object]:
    raw = cast(object, json.loads(EVIDENCE.read_text(encoding="utf-8")))
    assert isinstance(raw, dict)
    return cast(dict[str, object], raw)


def test_recovery_v2_apply_authority_is_pending_and_hash_bound() -> None:
    """Require a later explicit HUMAN authorization bound to all plan identities."""
    evidence = _load()

    assert evidence["artifact_type"] == (
        "phase-19-gate-19-7-recovery-v2-authority:v1"
    )
    assert evidence["protected_source_head_sha"] == (
        "d6546e9d48253694e3e276940ebd2388f301d8ad"
    )
    assert evidence["plan_binary_sha256"] == (
        "48cb15a8466cc0ce77fdbe1d827b5a0aebb88460b8e8151d8c88d3c85eb9ea55"
    )
    assert evidence["plan_json_sha256"] == (
        "8a1f95ab8cbcbf96c708c6ced0d0127d862391a6f8e72c250fe5e7499d2a0bf7"
    )

    authority = evidence["authority"]
    assert isinstance(authority, dict)
    typed_authority = cast(dict[str, object], authority)
    assert typed_authority["terraform_apply_authorized"] is False
    assert typed_authority["explicit_human_apply_authorization_required"] is True
    assert typed_authority["authorization_must_bind_source_head_sha"] is True
    assert typed_authority["authorization_must_bind_plan_binary_sha256"] is True
    assert typed_authority["authorization_must_bind_plan_json_sha256"] is True


def test_recovery_v2_authority_freezes_non_destructive_shape() -> None:
    """Reject any future authorization that broadens the admitted action shape."""
    evidence = _load()
    shape = evidence["admitted_shape"]
    assert isinstance(shape, dict)
    typed_shape = cast(dict[str, object], shape)

    assert typed_shape["managed_creates"] == 5
    assert typed_shape["managed_updates"] == 1
    assert typed_shape["managed_deletes"] == 0
    assert typed_shape["managed_replacements"] == 0
    assert typed_shape["allowed_existing_resource_update"] == (
        "aws_lambda_function.public_async_api"
    )
    assert typed_shape["api_reserved_concurrency_after"] == 0
    assert typed_shape["worker_reserved_concurrency_after"] == 0
