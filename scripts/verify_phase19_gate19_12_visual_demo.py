#!/usr/bin/env python3
"""Verify the Gate 19.12 localhost visual-demo contract offline."""

import json
from pathlib import Path
from typing import cast

from opslens.demo.web import (
    LOCAL_DEMO_HOST,
    LOCAL_DEMO_PORT,
    build_visual_catalog,
    route_visual_request,
)

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None

_ARTIFACT = Path("labs/evidence/phase-19-gate-19-12-local-visual-demo-v1.json")
_VISUAL = Path("src/opslens/demo/visual.py")
_WEB = Path("src/opslens/demo/web.py")
_LAUNCHER = Path("scripts/demo_opslens_web.py")
_TEST = Path("tests/unit/demo/test_visual_demo.py")
_LAB = Path("labs/phase-19-gate-19-12-local-visual-demo.md")
_EXPECTED_MAIN = "0c5bbe34792406ee5c66fcc5ac4b75923512703b"
_EXPECTED_CODEQL_RUN = 34718268902
_EXPECTED_CODEQL_NUMBER = 424
_EXPECTED_SCENARIOS = (
    "material-vulnerability",
    "controlled-benign",
    "fail-closed-incomplete-evidence",
)


def _object(value: JsonValue, *, label: str) -> dict[str, JsonValue]:
    """Require one JSON object value."""
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be one JSON object")
    return value


def _load_artifact() -> dict[str, JsonValue]:
    """Load the checked-in machine-readable Gate 19.12 evidence."""
    value = cast(JsonValue, json.loads(_ARTIFACT.read_text(encoding="utf-8")))
    return _object(value, label="Gate 19.12 artifact")


def _require_file(path: Path) -> str:
    """Require one Gate 19.12 repository artifact and return its text."""
    if not path.is_file():
        raise SystemExit(f"missing Gate 19.12 artifact: {path}")
    return path.read_text(encoding="utf-8")


def main() -> int:
    """Verify lineage, local-only routing, visual authority, and zero provider impact."""
    artifact = _load_artifact()
    if artifact.get("schema_version") != "opslens.phase19.gate19_12.local_visual_demo.v1":
        raise SystemExit("Gate 19.12 schema version drifted")
    if artifact.get("phase") != 19 or artifact.get("gate") != "19.12":
        raise SystemExit("Gate 19.12 phase/gate identity drifted")
    if artifact.get("issue") != 382:
        raise SystemExit("Gate 19.12 issue identity drifted")
    if artifact.get("source_protected_main_sha") != _EXPECTED_MAIN:
        raise SystemExit("Gate 19.12 source protected main drifted")
    if artifact.get("decision") != "LOCALHOST_STANDARD_LIBRARY_PRESENTATION_ADAPTER":
        raise SystemExit("Gate 19.12 visual adapter decision drifted")

    gate_19_11 = _object(artifact.get("gate_19_11"), label="Gate 19.11 lineage")
    expected_lineage: dict[str, JsonValue] = {
        "issue": 380,
        "pull_request": 381,
        "merge_sha": _EXPECTED_MAIN,
        "post_merge_codeql_run_id": _EXPECTED_CODEQL_RUN,
        "post_merge_codeql_run_number": _EXPECTED_CODEQL_NUMBER,
        "post_merge_codeql_conclusion": "success",
    }
    for key, expected in expected_lineage.items():
        if gate_19_11.get(key) != expected:
            raise SystemExit(f"Gate 19.12 lineage drifted for {key}")

    if artifact.get("canonical_scenario_ids") != list(_EXPECTED_SCENARIOS):
        raise SystemExit("Gate 19.12 scenario allowlist drifted")

    local_bind = _object(artifact.get("local_bind"), label="local bind")
    if local_bind.get("host") != "127.0.0.1" or local_bind.get("default_port") != 8765:
        raise SystemExit("Gate 19.12 localhost bind drifted")
    if local_bind.get("external_host_argument") is not False:
        raise SystemExit("Gate 19.12 unexpectedly admits an external host argument")

    properties = _object(artifact.get("required_properties"), label="required properties")
    expected_false = (
        "aws_credentials_required",
        "network_after_dependency_installation",
        "live_provider_execution",
        "model_execution",
        "third_party_repository_code_execution",
        "visual_projection_is_business_authority",
    )
    for key in expected_false:
        if properties.get(key) is not False:
            raise SystemExit(f"Gate 19.12 property {key} must remain false")
    for key in ("localhost_only_default_bind", "scenario_allowlist", "read_only_http_surface"):
        if properties.get(key) is not True:
            raise SystemExit(f"Gate 19.12 property {key} must remain true")

    impact = _object(artifact.get("authority_impact"), label="authority impact")
    for key, value in impact.items():
        if value != 0:
            raise SystemExit(f"Gate 19.12 authority impact must remain zero: {key}")

    visual_text = _require_file(_VISUAL)
    web_text = _require_file(_WEB)
    launcher_text = _require_file(_LAUNCHER)
    test_text = _require_file(_TEST)
    lab_text = _require_file(_LAB)

    for marker in (
        "visual projection != business authority",
        "Disabled in the V1 offline demo.",
        "Missing evidence != benign evidence.",
    ):
        if marker not in visual_text:
            raise SystemExit(f"visual projection is missing marker: {marker}")

    for marker in (
        'LOCAL_DEMO_HOST = "127.0.0.1"',
        "ThreadingHTTPServer",
        "scenario_id not in _SUPPORTED_SCENARIOS",
        "METHOD_NOT_ALLOWED",
        "Content-Security-Policy",
    ):
        if marker not in web_text:
            raise SystemExit(f"local HTTP adapter is missing marker: {marker}")

    if "--host" in launcher_text:
        raise SystemExit("local visual launcher must not expose an external bind option")
    if "test_dynamic_visual_values_are_html_escaped" not in test_text:
        raise SystemExit("Gate 19.12 HTML escaping regression test is missing")
    if "localhost demo != public service" not in lab_text:
        raise SystemExit("Gate 19.12 lab is missing the local/public authority invariant")

    forbidden_tokens = (
        "import boto3",
        "from boto3",
        "urllib.request",
        "httpx",
        "subprocess",
        "os.system",
    )
    for path, text in ((_VISUAL, visual_text), (_WEB, web_text), (_LAUNCHER, launcher_text)):
        for token in forbidden_tokens:
            if token in text:
                raise SystemExit(f"{path} unexpectedly contains provider/process token {token}")

    if LOCAL_DEMO_HOST != "127.0.0.1" or LOCAL_DEMO_PORT != 8765:
        raise SystemExit("runtime localhost constants drifted")

    catalog = build_visual_catalog()
    if tuple(item.scenario_id for item in catalog) != _EXPECTED_SCENARIOS:
        raise SystemExit("runtime visual catalog drifted from the canonical scenario allowlist")
    if tuple(item.state for item in catalog) != (
        "MATERIAL_FINDING",
        "NO_MATERIAL_FINDING",
        "REJECTED_INCOMPLETE_EVIDENCE",
    ):
        raise SystemExit("runtime visual states drifted")

    if route_visual_request("/").status != 200:
        raise SystemExit("visual index route failed")
    for scenario in _EXPECTED_SCENARIOS:
        response = route_visual_request(f"/scenario/{scenario}")
        if response.status != 200:
            raise SystemExit(f"visual scenario route failed: {scenario}")
    if route_visual_request("/scenario/not-admitted").status != 404:
        raise SystemExit("unknown visual scenario did not fail closed")
    if route_visual_request("/?repository=https://example.com").status != 400:
        raise SystemExit("query-string input unexpectedly entered the visual authority boundary")

    print("Gate 19.12 localhost visual-demo contract verified offline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
