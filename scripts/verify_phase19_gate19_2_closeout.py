"""Verify Gate 19.2 live evidence and the evidence-backed async closeout."""

import json
from hashlib import sha256
from pathlib import Path
from typing import cast

from _bootstrap import ensure_repository_src_on_path

ensure_repository_src_on_path()

from opslens.public_analysis.application.representative_live_measurement_review import (  # noqa: E402
    review_representative_live_measurement_artifact,
)

_LIVE_ARTIFACT = Path("labs/evidence/phase-19-gate-19-2-live-measurement-v1.json")
_CLOSEOUT_ARTIFACT = Path("labs/evidence/phase-19-gate-19-2-closeout-v1.json")
_EXPECTED_LIVE_SHA256 = "04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114"
_EXPECTED_SOURCE_MAIN_SHA = "e45ba419414e6dd77ecad68f4d2312e9123c2223"
_EXPECTED_RUN_ID = "gate19.2-live-20260911T131121Z"
_EXPECTED_DECISION = "ASYNC_SUBMIT_STATUS_RESULT"
_REFERENCE_SYNC_ENVELOPE_MS = 30_000


class Gate19_2CloseoutVerificationError(ValueError):
    """Reject contradictory or drifted Gate 19.2 closeout evidence."""


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_2CloseoutVerificationError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _integer(value: object, *, label: str) -> int:
    if type(value) is not int:
        raise Gate19_2CloseoutVerificationError(f"{label} must be an integer")
    return value


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise Gate19_2CloseoutVerificationError(f"{label} must be a string")
    return value


def _boolean(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise Gate19_2CloseoutVerificationError(f"{label} must be a boolean")
    return value


def _require_exact_keys(
    value: dict[str, object], *, expected: frozenset[str], label: str
) -> None:
    if frozenset(value) != expected:
        raise Gate19_2CloseoutVerificationError(
            f"{label} must preserve the exact frozen field set"
        )


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        parsed = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Gate19_2CloseoutVerificationError(
            f"could not load canonical JSON from {path}"
        ) from exc
    return _object(parsed, label=str(path))


def main() -> int:
    """Verify immutable live bytes and derive the async decision without providers."""
    repo_root = Path(__file__).resolve().parents[1]
    live_path = repo_root / _LIVE_ARTIFACT
    closeout_path = repo_root / _CLOSEOUT_ARTIFACT

    try:
        live_bytes = live_path.read_bytes()
    except OSError as exc:
        raise Gate19_2CloseoutVerificationError(
            "Gate 19.2 live measurement artifact is missing"
        ) from exc

    live_digest = sha256(live_bytes).hexdigest()
    if live_digest != _EXPECTED_LIVE_SHA256:
        raise Gate19_2CloseoutVerificationError(
            "Gate 19.2 live measurement bytes drifted from the admitted human artifact"
        )

    live = review_representative_live_measurement_artifact(
        live_bytes,
        expected_opslens_commit_sha=_EXPECTED_SOURCE_MAIN_SHA,
    )
    if live.run_id != _EXPECTED_RUN_ID:
        raise Gate19_2CloseoutVerificationError("live run id drifted")

    closeout = _load_json_object(closeout_path)
    _require_exact_keys(
        closeout,
        expected=frozenset(
            {
                "artifact_type",
                "authorization",
                "closeout_issue",
                "decision",
                "decision_basis",
                "live_measurement_artifact_path",
                "live_measurement_artifact_sha256",
                "live_measurement_run_id",
                "next_boundary",
                "provider_semantics",
                "safety",
                "schema_version",
                "source_issue",
                "source_main_sha",
            }
        ),
        label="Gate 19.2 closeout",
    )

    if _string(closeout["artifact_type"], label="artifact_type") != (
        "phase-19-gate-19-2-closeout:v1"
    ):
        raise Gate19_2CloseoutVerificationError("closeout artifact identity drifted")
    if _integer(closeout["schema_version"], label="schema_version") != 1:
        raise Gate19_2CloseoutVerificationError("closeout schema version drifted")
    if _integer(closeout["source_issue"], label="source_issue") != 295:
        raise Gate19_2CloseoutVerificationError("source issue drifted")
    if _integer(closeout["closeout_issue"], label="closeout_issue") != 346:
        raise Gate19_2CloseoutVerificationError("closeout issue drifted")
    if _string(closeout["source_main_sha"], label="source_main_sha") != (
        _EXPECTED_SOURCE_MAIN_SHA
    ):
        raise Gate19_2CloseoutVerificationError("source protected-main SHA drifted")
    if _string(closeout["decision"], label="decision") != _EXPECTED_DECISION:
        raise Gate19_2CloseoutVerificationError("Gate 19.2 runtime decision drifted")
    if _string(
        closeout["live_measurement_artifact_path"],
        label="live_measurement_artifact_path",
    ) != str(_LIVE_ARTIFACT):
        raise Gate19_2CloseoutVerificationError("live artifact path drifted")
    if _string(
        closeout["live_measurement_artifact_sha256"],
        label="live_measurement_artifact_sha256",
    ) != _EXPECTED_LIVE_SHA256:
        raise Gate19_2CloseoutVerificationError("live artifact SHA-256 drifted")
    if _string(closeout["live_measurement_run_id"], label="live_measurement_run_id") != (
        _EXPECTED_RUN_ID
    ):
        raise Gate19_2CloseoutVerificationError("closeout live run id drifted")

    provider_totals = dict(live.provider_totals)
    measured = _object(
        _object(closeout["decision_basis"], label="decision_basis")["measured"],
        label="decision_basis.measured",
    )
    _require_exact_keys(
        measured,
        expected=frozenset(
            {
                "bedrock_model_client_elapsed_ms",
                "bedrock_model_latency_ms",
                "bedrock_retrieve_client_elapsed_ms",
                "end_to_end_duration_ms",
                "github_http_request_count",
                "retry_count",
                "serialized_result_bytes",
            }
        ),
        label="decision_basis.measured",
    )

    expected_measured = {
        "end_to_end_duration_ms": live.end_to_end_duration_ms,
        "bedrock_retrieve_client_elapsed_ms": provider_totals[
            "bedrock_retrieve_client_elapsed_ms"
        ],
        "bedrock_model_client_elapsed_ms": provider_totals[
            "bedrock_model_client_elapsed_ms"
        ],
        "bedrock_model_latency_ms": provider_totals["bedrock_model_latency_ms"],
        "github_http_request_count": provider_totals["github_http_request_count"],
        "retry_count": provider_totals["retry_count"],
        "serialized_result_bytes": live.serialized_result_bytes,
    }
    for name, expected_value in expected_measured.items():
        if _integer(measured[name], label=f"decision_basis.measured.{name}") != expected_value:
            raise Gate19_2CloseoutVerificationError(
                f"measured closeout value {name} contradicts live evidence"
            )

    decision_basis = _object(closeout["decision_basis"], label="decision_basis")
    _require_exact_keys(
        decision_basis,
        expected=frozenset({"derived_retry_safety", "measured"}),
        label="decision_basis",
    )
    derived = _object(
        decision_basis["derived_retry_safety"], label="derived_retry_safety"
    )
    _require_exact_keys(
        derived,
        expected=frozenset(
            {
                "classification",
                "one_additional_model_equivalent_ms",
                "one_additional_retrieve_and_model_equivalent_ms",
                "reference_sync_envelope_ms",
            }
        ),
        label="derived_retry_safety",
    )
    if _string(derived["classification"], label="derived.classification") != "DERIVED":
        raise Gate19_2CloseoutVerificationError(
            "retry-safety scenario must remain explicitly DERIVED"
        )

    model_retry_ms = live.end_to_end_duration_ms + provider_totals[
        "bedrock_model_client_elapsed_ms"
    ]
    retrieve_and_model_retry_ms = model_retry_ms + provider_totals[
        "bedrock_retrieve_client_elapsed_ms"
    ]
    if _integer(
        derived["one_additional_model_equivalent_ms"],
        label="derived.one_additional_model_equivalent_ms",
    ) != model_retry_ms:
        raise Gate19_2CloseoutVerificationError("derived model retry scenario drifted")
    if _integer(
        derived["one_additional_retrieve_and_model_equivalent_ms"],
        label="derived.one_additional_retrieve_and_model_equivalent_ms",
    ) != retrieve_and_model_retry_ms:
        raise Gate19_2CloseoutVerificationError(
            "derived Retrieve + model retry scenario drifted"
        )
    if _integer(
        derived["reference_sync_envelope_ms"],
        label="derived.reference_sync_envelope_ms",
    ) != _REFERENCE_SYNC_ENVELOPE_MS:
        raise Gate19_2CloseoutVerificationError("reference sync envelope drifted")
    if live.end_to_end_duration_ms >= _REFERENCE_SYNC_ENVELOPE_MS:
        raise Gate19_2CloseoutVerificationError(
            "closeout must not claim the successful measured baseline timed out"
        )
    if retrieve_and_model_retry_ms <= _REFERENCE_SYNC_ENVELOPE_MS:
        raise Gate19_2CloseoutVerificationError(
            "derived retry-safety evidence no longer supports async isolation"
        )

    provider_semantics = _object(
        closeout["provider_semantics"], label="provider_semantics"
    )
    if provider_semantics != {
        "athena_bytes_scanned": "NOT_APPLICABLE",
        "athena_query_count": "NOT_APPLICABLE",
        "retry_count": "MEASURED",
        "throttle_count": "UNMEASURED",
    }:
        raise Gate19_2CloseoutVerificationError("provider evidence semantics drifted")

    classifications = dict(live.provider_classifications)
    for metric, classification in provider_semantics.items():
        if classifications[metric] != classification:
            raise Gate19_2CloseoutVerificationError(
                f"provider classification for {metric} contradicts live evidence"
            )

    safety = _object(closeout["safety"], label="safety")
    expected_safety = {
        "new_aws_resource_count": live.new_aws_resource_count,
        "new_iam_role_policy_count": live.new_iam_role_policy_count,
        "public_endpoint_count": live.public_endpoint_count,
        "third_party_repository_code_execution_count": (
            live.third_party_repository_code_execution_count
        ),
    }
    if safety != expected_safety or any(value != 0 for value in expected_safety.values()):
        raise Gate19_2CloseoutVerificationError("Gate 19.2 safety invariants drifted")

    authorization = _object(closeout["authorization"], label="authorization")
    _require_exact_keys(
        authorization,
        expected=frozenset(
            {
                "concrete_aws_topology_selected",
                "new_aws_resources_authorized",
                "new_iam_authority_authorized",
                "pr_89_modifications",
                "public_runtime_deployment_authorized",
                "selected_interaction_pattern",
            }
        ),
        label="authorization",
    )
    for field in (
        "concrete_aws_topology_selected",
        "new_aws_resources_authorized",
        "new_iam_authority_authorized",
        "public_runtime_deployment_authorized",
    ):
        if _boolean(authorization[field], label=f"authorization.{field}"):
            raise Gate19_2CloseoutVerificationError(f"{field} must remain false")
    if _integer(authorization["pr_89_modifications"], label="pr_89_modifications") != 0:
        raise Gate19_2CloseoutVerificationError("PR #89 must remain untouched")
    if _string(
        authorization["selected_interaction_pattern"],
        label="selected_interaction_pattern",
    ) != _EXPECTED_DECISION:
        raise Gate19_2CloseoutVerificationError("selected interaction pattern drifted")

    print(
        "phase19_gate19_2_closeout=PASS "
        f"decision={_EXPECTED_DECISION} "
        f"measured_end_to_end_ms={live.end_to_end_duration_ms} "
        f"derived_retry_safety_ms={retrieve_and_model_retry_ms} "
        f"live_artifact_sha256={live_digest} "
        "public_deployment_authorized=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
