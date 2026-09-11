from __future__ import annotations

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


def test_gate19_6_exact_plan_fixture_is_admitted() -> None:
    result = _run(_FIXTURE)

    assert result.returncode == 0, result.stderr
    assert "phase19_gate19_6_plan=PASS" in result.stdout
    assert "managed_creates=21" in result.stdout
    assert "terraform_apply_authorized=false" in result.stdout


def test_gate19_6_rejects_unrelated_managed_create(tmp_path: Path) -> None:
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
    payload = _load_fixture()
    changes = cast(list[object], payload["resource_changes"])
    for raw_entry in changes:
        entry = cast(dict[str, object], raw_entry)
        if entry.get("address") != "aws_lambda_event_source_mapping.public_async_worker[0]":
            continue
        change = cast(dict[str, object], entry["change"])
        after = cast(dict[str, object], change["after"])
        after["enabled"] = True
        break
    else:  # pragma: no cover - fixture contract guard
        raise AssertionError("worker event source fixture entry is missing")

    result = _run(_write(tmp_path, payload))

    assert result.returncode != 0
    assert "event source mapping must remain disabled" in result.stderr


def test_gate19_6_rejects_immutable_artifact_coordinate_drift(tmp_path: Path) -> None:
    payload = deepcopy(_load_fixture())
    variables = cast(dict[str, object], payload["variables"])
    version = cast(dict[str, object], variables["public_async_api_artifact_version_id"])
    version["value"] = "drifted-version"

    result = _run(_write(tmp_path, payload))

    assert result.returncode != 0
    assert "differs from frozen Gate 19.6 input" in result.stderr
