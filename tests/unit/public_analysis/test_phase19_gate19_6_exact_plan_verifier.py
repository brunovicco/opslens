"""Fail-closed tests for the Gate 19.6 offline Terraform-plan verifier."""

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import cast

_FIXTURE = Path("tests/fixtures/phase19/gate19-6-exact-plan-pass.json")
_VERIFIER = Path("scripts/verify_phase19_gate19_6_exact_plan.py")


def _load_fixture() -> dict[str, object]:
    raw: object = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return cast(dict[str, object], raw)


def _run(plan_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_VERIFIER), "--plan-json", str(plan_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _resource_change(
    payload: dict[str, object], address: str
) -> dict[str, object]:
    changes = cast(list[object], payload["resource_changes"])
    for raw_entry in changes:
        entry = cast(dict[str, object], raw_entry)
        if entry.get("address") == address:
            return cast(dict[str, object], entry["change"])
    raise AssertionError(f"fixture resource entry is missing: {address}")


def test_gate19_6_exact_plan_fixture_is_admitted() -> None:
    """Admit the synthetic exact 21-create plan with all disabled controls retained."""
    result = _run(_FIXTURE)

    assert result.returncode == 0, result.stderr
    assert "phase19_gate19_6_plan=PASS" in result.stdout
    assert "managed_creates=21" in result.stdout
    assert "terraform_apply_authorized=false" in result.stdout


def test_gate19_6_admits_provider_unknown_environment_map(tmp_path: Path) -> None:
    """Admit provider-unknown env maps only with explicit after_unknown markers."""
    payload = deepcopy(_load_fixture())

    for address in (
        "aws_lambda_function.public_async_api[0]",
        "aws_lambda_function.public_async_worker[0]",
    ):
        change = _resource_change(payload, address)
        after = cast(dict[str, object], change["after"])
        after["environment"] = [{"variables": None}]
        change["after_unknown"] = {"environment": [{"variables": True}]}

    result = _run(_write(tmp_path, payload))

    assert result.returncode == 0, result.stderr
    assert "phase19_gate19_6_plan=PASS" in result.stdout


def test_gate19_6_rejects_unknown_environment_without_marker(tmp_path: Path) -> None:
    """Reject missing env values when Terraform does not mark them as unknown."""
    payload = deepcopy(_load_fixture())
    change = _resource_change(payload, "aws_lambda_function.public_async_api[0]")
    after = cast(dict[str, object], change["after"])
    after["environment"] = [{"variables": None}]
    change.pop("after_unknown", None)

    result = _run(_write(tmp_path, payload))

    assert result.returncode != 0
    assert "missing without an unknown marker" in result.stderr


def test_gate19_6_rejects_unrelated_managed_create(tmp_path: Path) -> None:
    """Reject any managed non-no-op change outside the frozen Gate 19.4 inventory."""
    payload = _load_fixture()
    changes = cast(list[object], payload["resource_changes"])
    changes.append(
        {
            "address": "aws_s3_bucket.unrelated",
            "mode": "managed",
            "type": "aws_s3_bucket",
            "name": "unrelated",
            "change": {"actions": ["create"], "after": {}},
        }
    )

    result = _run(_write(tmp_path, payload))

    assert result.returncode != 0
    assert "unrelated managed non-no-op changes are forbidden" in result.stderr


def test_gate19_6_rejects_worker_event_source_enablement(tmp_path: Path) -> None:
    """Reject a plan that would enable SQS dispatch to the worker."""
    payload = _load_fixture()
    change = _resource_change(
        payload, "aws_lambda_event_source_mapping.public_async_worker[0]"
    )
    after = cast(dict[str, object], change["after"])
    after["enabled"] = True

    result = _run(_write(tmp_path, payload))

    assert result.returncode != 0
    assert "event source mapping must remain disabled" in result.stderr


def test_gate19_6_rejects_immutable_artifact_coordinate_drift(tmp_path: Path) -> None:
    """Reject plan variables that drift from frozen immutable artifact coordinates."""
    payload = deepcopy(_load_fixture())
    variables = cast(dict[str, object], payload["variables"])
    version = cast(dict[str, object], variables["public_async_api_artifact_version_id"])
    version["value"] = "drifted-version"

    result = _run(_write(tmp_path, payload))

    assert result.returncode != 0
    assert "differs from frozen Gate 19.6 input" in result.stderr


def test_gate19_6_rejects_safety_output_drift(tmp_path: Path) -> None:
    """Reject a plan whose retained safety outputs no longer match disabled state."""
    payload = deepcopy(_load_fixture())
    outputs = cast(dict[str, object], payload["output_changes"])
    submit = cast(dict[str, object], outputs["public_async_submit_enabled"])
    submit["after"] = True

    result = _run(_write(tmp_path, payload))

    assert result.returncode != 0
    assert "public_async_submit_enabled differs" in result.stderr
