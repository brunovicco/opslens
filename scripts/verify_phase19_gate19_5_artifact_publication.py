#!/usr/bin/env python3
"""Verify persisted Gate 19.5 immutable artifact publication evidence offline."""

import argparse
import json
from pathlib import Path
from typing import cast

_EXPECTED_ACCOUNT = "487757851499"
_EXPECTED_REGION = "us-east-1"
_EXPECTED_BUCKET = "opslens-dev-artifacts-487757851499-us-east-1"
_EXPECTED_PREPUBLICATION_TYPE = "phase-19-gate-19-5-async-artifact-prepublication:v1"
_EXPECTED_PUBLICATION_TYPE = "phase-19-gate-19-5-artifact-publication:v1"
_EXPECTED_SOURCE_HEAD_SHA = "94af45036ba33007f45ddb69e9e6c3fa7d31d715"
_EXPECTED_ROLES = {"api", "worker"}
_EXPECTED_PUT_MUTATION_COUNT = 2


class Gate19_5PublicationVerificationError(RuntimeError):
    """Raised when persisted publication evidence cannot be admitted."""


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_5PublicationVerificationError(f"{label} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise Gate19_5PublicationVerificationError(f"{label} keys must be strings")
    return cast(dict[str, object], raw)


def _objects(value: object, *, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise Gate19_5PublicationVerificationError(f"{label} must be an array")
    return [_object(item, label=f"{label}[]") for item in cast(list[object], value)]


def _load(path: Path) -> dict[str, object]:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    return _object(raw, label=str(path))


def _by_role(root: dict[str, object], *, label: str) -> dict[str, dict[str, object]]:
    artifacts = _objects(root.get("artifacts"), label=f"{label}.artifacts")
    result: dict[str, dict[str, object]] = {}
    for artifact in artifacts:
        role = artifact.get("role")
        if type(role) is not str or role in result:
            raise Gate19_5PublicationVerificationError(f"{label} role inventory is invalid")
        result[role] = artifact
    if set(result) != _EXPECTED_ROLES:
        raise Gate19_5PublicationVerificationError(f"{label} must contain API and worker")
    return result


def _required_string(mapping: dict[str, object], field: str) -> str:
    value = mapping.get(field)
    if type(value) is not str or not value:
        raise Gate19_5PublicationVerificationError(f"{field} must be a non-empty string")
    return value


def _required_int(mapping: dict[str, object], field: str) -> int:
    value = mapping.get(field)
    if type(value) is not int or value < 0:
        raise Gate19_5PublicationVerificationError(f"{field} must be a non-negative integer")
    return value


def _verify_prepublication(root: dict[str, object]) -> dict[str, dict[str, object]]:
    if root.get("schema_version") != 1:
        raise Gate19_5PublicationVerificationError("prepublication schema drifted")
    if root.get("artifact_type") != _EXPECTED_PREPUBLICATION_TYPE:
        raise Gate19_5PublicationVerificationError("prepublication type drifted")
    if root.get("deployment_bucket") != _EXPECTED_BUCKET:
        raise Gate19_5PublicationVerificationError("prepublication bucket drifted")
    if root.get("publication_authority") != "HUMAN_ONLY_CREATE_ONLY":
        raise Gate19_5PublicationVerificationError("prepublication authority drifted")
    for field in (
        "terraform_apply_authorized",
        "runtime_resource_mutation_authorized",
        "public_enablement_authorized",
    ):
        if root.get(field) is not False:
            raise Gate19_5PublicationVerificationError(f"{field} must remain false")
    return _by_role(root, label="prepublication")


def _verify_publication_identity(root: dict[str, object]) -> None:
    if root.get("schema_version") != 1:
        raise Gate19_5PublicationVerificationError("publication schema drifted")
    if root.get("artifact_type") != _EXPECTED_PUBLICATION_TYPE:
        raise Gate19_5PublicationVerificationError("publication type drifted")
    if root.get("account_id") != _EXPECTED_ACCOUNT:
        raise Gate19_5PublicationVerificationError("publication account drifted")
    if root.get("region") != _EXPECTED_REGION:
        raise Gate19_5PublicationVerificationError("publication Region drifted")
    if root.get("bucket") != _EXPECTED_BUCKET:
        raise Gate19_5PublicationVerificationError("publication bucket drifted")
    if _required_string(root, "source_head_sha") != _EXPECTED_SOURCE_HEAD_SHA:
        raise Gate19_5PublicationVerificationError("publication source reviewed head drifted")
    _required_string(root, "caller_arn")
    if _required_int(root, "automatic_retry_count") != 0:
        raise Gate19_5PublicationVerificationError("automatic publication retries are forbidden")
    if _required_int(root, "s3_put_object_mutation_count") != _EXPECTED_PUT_MUTATION_COUNT:
        raise Gate19_5PublicationVerificationError("canonical publication must preserve two writes")
    for field in (
        "runtime_resource_mutation_count",
        "iam_mutation_count",
        "terraform_apply_count",
        "public_endpoint_enablement_count",
    ):
        if _required_int(root, field) != 0:
            raise Gate19_5PublicationVerificationError(f"{field} must remain zero")


def _verify_artifact_pair(
    role: str,
    pre: dict[str, object],
    published: dict[str, object],
) -> str:
    if published.get("role") != role:
        raise Gate19_5PublicationVerificationError(f"{role} publication role drifted")
    pre_s3 = _object(pre.get("s3"), label=f"prepublication.{role}.s3")
    frozen_fields = {
        "artifact_sha256": pre.get("artifact_sha256"),
        "lambda_source_code_hash": pre.get("lambda_source_code_hash"),
        "bytes": pre.get("compressed_bytes"),
        "bucket": pre_s3.get("bucket"),
        "key": pre_s3.get("key"),
    }
    for field, expected in frozen_fields.items():
        if published.get(field) != expected:
            raise Gate19_5PublicationVerificationError(
                f"published {role} field {field} differs from prepublication evidence"
            )
    version_id = _required_string(published, "version_id")
    digest = _required_string(published, "artifact_sha256")
    if published.get("verified_sha256") != digest:
        raise Gate19_5PublicationVerificationError(f"published {role} exact GET hash drifted")
    if published.get("verified_bytes") != published.get("bytes"):
        raise Gate19_5PublicationVerificationError(f"published {role} exact GET size drifted")
    status = published.get("publication_status")
    if status not in {"CREATED", "EXISTING_EXACT"}:
        raise Gate19_5PublicationVerificationError(f"published {role} status is invalid")
    return version_id


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepublication", type=Path, required=True)
    parser.add_argument("--publication", type=Path, required=True)
    return parser


def main() -> int:
    """Admit persisted publication evidence without AWS access."""
    args = _parser().parse_args()
    pre_root = _load(args.prepublication)
    publication_root = _load(args.publication)
    pre = _verify_prepublication(pre_root)
    _verify_publication_identity(publication_root)
    published = _by_role(publication_root, label="publication")

    statuses = [artifact.get("publication_status") for artifact in published.values()]
    if statuses.count("CREATED") != _EXPECTED_PUT_MUTATION_COUNT:
        raise Gate19_5PublicationVerificationError(
            "canonical publication statuses contradict the two admitted writes"
        )

    versions = {
        role: _verify_artifact_pair(role, pre[role], published[role])
        for role in sorted(_EXPECTED_ROLES)
    }
    print(
        "phase19_gate19_5_publication=PASS "
        f"api_version_id={versions['api']} "
        f"worker_version_id={versions['worker']} "
        "s3_put_object_mutation_count=2 "
        "terraform_plan_input_ready=true "
        "terraform_apply_authorized=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
