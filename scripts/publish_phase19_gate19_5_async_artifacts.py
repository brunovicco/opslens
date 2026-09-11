#!/usr/bin/env python3
"""Human-only create-only publication for admitted Gate 19.5 Lambda artifacts."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Protocol, cast

from boto3.session import Session
from botocore.config import Config
from botocore.exceptions import ClientError

_EXPECTED_ACCOUNT = "487757851499"
_EXPECTED_REGION = "us-east-1"
_EXPECTED_BUCKET = "opslens-dev-artifacts-487757851499-us-east-1"
_EXPECTED_ARTIFACT_TYPE = "phase-19-gate-19-5-async-artifact-prepublication:v1"
_CONFIRMATION = "I_UNDERSTAND_THIS_WRITES_EXACTLY_TWO_CREATE_ONLY_S3_OBJECTS"


class ArtifactPublicationError(RuntimeError):
    """Raised when publication cannot preserve the frozen create-only contract."""


class _Body(Protocol):
    def read(self, amt: int | None = None) -> bytes:
        """Read response bytes."""
        ...

    def close(self) -> None:
        """Close the response stream."""
        ...


class _S3Client(Protocol):
    def head_object(self, **kwargs: object) -> dict[str, object]:
        """Read exact current object metadata."""
        ...

    def put_object(self, **kwargs: object) -> dict[str, object]:
        """Attempt one conditional create-only write."""
        ...

    def get_object(self, **kwargs: object) -> dict[str, object]:
        """Read one exact immutable object version."""
        ...


class _StsClient(Protocol):
    def get_caller_identity(self) -> dict[str, object]:
        """Read the current human caller identity."""
        ...


class _ClientSession(Protocol):
    def client(self, service_name: str, **kwargs: object) -> object:
        """Construct one AWS service client through the human session."""
        ...


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ArtifactPublicationError(f"{label} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise ArtifactPublicationError(f"{label} keys must be strings")
    return cast(dict[str, object], raw)


def _objects(value: object, *, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise ArtifactPublicationError(f"{label} must be an array")
    return [_object(item, label=f"{label}[]") for item in cast(list[object], value)]


def _required_string(mapping: dict[str, object], name: str) -> str:
    value = mapping.get(name)
    if type(value) is not str or not value:
        raise ArtifactPublicationError(f"{name} must be a non-empty string")
    return value


def _required_int(mapping: dict[str, object], name: str) -> int:
    value = mapping.get(name)
    if type(value) is not int or value <= 0:
        raise ArtifactPublicationError(f"{name} must be a positive integer")
    return value


def _sha256_bytes(payload: bytes) -> tuple[str, str]:
    digest = hashlib.sha256(payload)
    return digest.hexdigest(), base64.b64encode(digest.digest()).decode("ascii")


def _load_manifest(path: Path) -> dict[str, object]:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    manifest = _object(raw, label="prepublication manifest")
    if manifest.get("schema_version") != 1:
        raise ArtifactPublicationError("prepublication schema version drifted")
    if manifest.get("artifact_type") != _EXPECTED_ARTIFACT_TYPE:
        raise ArtifactPublicationError("prepublication artifact type drifted")
    if manifest.get("deployment_bucket") != _EXPECTED_BUCKET:
        raise ArtifactPublicationError("deployment bucket drifted")
    if manifest.get("publication_authority") != "HUMAN_ONLY_CREATE_ONLY":
        raise ArtifactPublicationError("publication authority drifted")
    for field in (
        "terraform_apply_authorized",
        "runtime_resource_mutation_authorized",
        "public_enablement_authorized",
    ):
        if manifest.get(field) is not False:
            raise ArtifactPublicationError(f"{field} must remain false")
    return manifest


def _verify_worktree() -> str:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise ArtifactPublicationError("working tree must be clean before publication")
    if len(head) != 40:
        raise ArtifactPublicationError("repository HEAD is not a full commit SHA")
    return head


def _artifact_payload(
    artifact_root: Path,
    artifact: dict[str, object],
) -> tuple[bytes, str, str, str, int]:
    role = _required_string(artifact, "role")
    if role not in {"api", "worker"}:
        raise ArtifactPublicationError(f"unsupported artifact role: {role}")
    relative_path = _required_string(artifact, "artifact_path")
    path = artifact_root / relative_path
    if not path.is_file():
        raise ArtifactPublicationError(f"local {role} artifact is missing: {path}")
    payload = path.read_bytes()
    digest, source_code_hash = _sha256_bytes(payload)
    if artifact.get("artifact_sha256") != digest:
        raise ArtifactPublicationError(f"local {role} artifact SHA-256 does not match manifest")
    if artifact.get("lambda_source_code_hash") != source_code_hash:
        raise ArtifactPublicationError(
            f"local {role} Lambda source_code_hash does not match manifest"
        )
    if artifact.get("compressed_bytes") != len(payload):
        raise ArtifactPublicationError(f"local {role} artifact size does not match manifest")
    _required_int(artifact, "uncompressed_bytes")
    _required_int(artifact, "file_count")
    s3 = _object(artifact.get("s3"), label=f"{role}.s3")
    if s3.get("bucket") != _EXPECTED_BUCKET:
        raise ArtifactPublicationError(f"{role} artifact bucket drifted")
    key = _required_string(s3, "key")
    expected_key = (
        f"lambda/public-analysis/{role}/sha256={digest}/"
        f"opslens-public-async-{role}.zip"
    )
    if key != expected_key:
        raise ArtifactPublicationError(f"{role} content-addressed key drifted")
    version = _object(s3.get("version_id"), label=f"{role}.version_id")
    if version != {
        "classification": "UNMEASURED",
        "value": None,
        "reason": "PENDING_HUMAN_PUBLICATION",
    }:
        raise ArtifactPublicationError(f"{role} manifest already claims a VersionId")
    return payload, role, digest, source_code_hash, len(payload)


def _error_code(exc: ClientError) -> str:
    response = cast(dict[str, object], exc.response)
    error = _object(response.get("Error"), label="AWS error")
    code = error.get("Code")
    return str(code) if code is not None else "UNKNOWN"


def _existing_version(
    s3: _S3Client,
    *,
    key: str,
    role: str,
    digest: str,
    expected_bytes: int,
) -> str | None:
    try:
        response = s3.head_object(
            Bucket=_EXPECTED_BUCKET,
            Key=key,
            ExpectedBucketOwner=_EXPECTED_ACCOUNT,
        )
    except ClientError as exc:
        code = _error_code(exc)
        if code in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise
    version_id = response.get("VersionId")
    size = response.get("ContentLength")
    metadata = response.get("Metadata")
    if type(version_id) is not str or not version_id:
        raise ArtifactPublicationError(f"existing {role} object has no immutable VersionId")
    if type(size) is not int or size != expected_bytes:
        raise ArtifactPublicationError(f"existing {role} object size differs from frozen artifact")
    if not isinstance(metadata, dict):
        raise ArtifactPublicationError(f"existing {role} object metadata is missing")
    typed_metadata = cast(dict[object, object], metadata)
    if typed_metadata.get("sha256") != digest or typed_metadata.get("role") != role:
        raise ArtifactPublicationError(
            f"existing {role} object metadata differs from frozen artifact"
        )
    return version_id


def _verify_exact_version(
    s3: _S3Client,
    *,
    key: str,
    version_id: str,
    role: str,
    digest: str,
    expected_bytes: int,
) -> dict[str, object]:
    response = s3.get_object(
        Bucket=_EXPECTED_BUCKET,
        Key=key,
        VersionId=version_id,
        ExpectedBucketOwner=_EXPECTED_ACCOUNT,
    )
    body = cast(_Body, response.get("Body"))
    try:
        payload = body.read()
    finally:
        body.close()
    observed_digest, _source_code_hash = _sha256_bytes(payload)
    if observed_digest != digest or len(payload) != expected_bytes:
        raise ArtifactPublicationError(
            f"exact S3 {role} VersionId does not match the frozen local artifact"
        )
    returned_version = response.get("VersionId")
    if returned_version != version_id:
        raise ArtifactPublicationError(f"S3 returned a different {role} VersionId")
    return {
        "version_id": version_id,
        "verified_sha256": observed_digest,
        "verified_bytes": len(payload),
        "etag": response.get("ETag"),
    }


def _publish_one(
    s3: _S3Client,
    *,
    artifact_root: Path,
    artifact: dict[str, object],
    source_head_sha: str,
) -> tuple[dict[str, object], bool]:
    payload, role, digest, source_code_hash, size = _artifact_payload(
        artifact_root,
        artifact,
    )
    s3_coordinates = _object(artifact.get("s3"), label=f"{role}.s3")
    key = _required_string(s3_coordinates, "key")

    existing = _existing_version(
        s3,
        key=key,
        role=role,
        digest=digest,
        expected_bytes=size,
    )
    mutated = False
    status = "EXISTING_EXACT"
    version_id = existing
    if version_id is None:
        try:
            response = s3.put_object(
                Bucket=_EXPECTED_BUCKET,
                Key=key,
                Body=payload,
                ContentType="application/zip",
                ChecksumSHA256=source_code_hash,
                IfNoneMatch="*",
                ExpectedBucketOwner=_EXPECTED_ACCOUNT,
                Metadata={
                    "sha256": digest,
                    "role": role,
                    "source-head-sha": source_head_sha,
                    "gate": "19.5",
                },
            )
        except ClientError as exc:
            code = _error_code(exc)
            if code in {"409", "ConditionalRequestConflict", "412", "PreconditionFailed"}:
                raise ArtifactPublicationError(
                    f"conditional create-only publication conflicted for {role}; "
                    "do not retry automatically"
                ) from exc
            raise
        raw_version = response.get("VersionId")
        if type(raw_version) is not str or not raw_version:
            raise ArtifactPublicationError(
                f"successful {role} PutObject did not return an immutable VersionId"
            )
        version_id = raw_version
        mutated = True
        status = "CREATED"

    verified = _verify_exact_version(
        s3,
        key=key,
        version_id=version_id,
        role=role,
        digest=digest,
        expected_bytes=size,
    )
    return (
        {
            "role": role,
            "artifact_sha256": digest,
            "lambda_source_code_hash": source_code_hash,
            "bytes": size,
            "bucket": _EXPECTED_BUCKET,
            "key": key,
            "version_id": verified["version_id"],
            "verified_sha256": verified["verified_sha256"],
            "verified_bytes": verified["verified_bytes"],
            "etag": verified["etag"],
            "publication_status": status,
        },
        mutated,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", default=_EXPECTED_REGION)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    return parser


def main() -> int:
    """Perform the narrow human-only publication and persist exact evidence."""
    args = _parser().parse_args()
    if args.confirm != _CONFIRMATION:
        raise ArtifactPublicationError(
            "explicit human publication confirmation is missing or incorrect"
        )
    if args.region != _EXPECTED_REGION:
        raise ArtifactPublicationError("publication Region differs from the frozen Region")
    manifest = _load_manifest(args.manifest.resolve())
    source_head_sha = _verify_worktree()
    artifacts = _objects(manifest.get("artifacts"), label="manifest.artifacts")
    if {artifact.get("role") for artifact in artifacts} != {"api", "worker"}:
        raise ArtifactPublicationError("manifest must contain exactly API and worker artifacts")

    session = Session(profile_name=args.profile, region_name=args.region)
    retry_config = Config(retries={"mode": "standard", "total_max_attempts": 1})
    client_session = cast(_ClientSession, session)
    sts = cast(_StsClient, client_session.client("sts", config=retry_config))
    s3 = cast(_S3Client, client_session.client("s3", config=retry_config))
    identity = sts.get_caller_identity()
    if identity.get("Account") != _EXPECTED_ACCOUNT:
        raise ArtifactPublicationError("caller account differs from the frozen OpsLens account")
    caller_arn = identity.get("Arn")
    if type(caller_arn) is not str or not caller_arn:
        raise ArtifactPublicationError("caller ARN is unavailable")

    evidence: list[dict[str, object]] = []
    mutation_count = 0
    try:
        for artifact in sorted(artifacts, key=lambda item: str(item.get("role"))):
            admitted, mutated = _publish_one(
                s3,
                artifact_root=args.artifact_root.resolve(),
                artifact=artifact,
                source_head_sha=source_head_sha,
            )
            evidence.append(admitted)
            mutation_count += int(mutated)
    finally:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "artifact_type": "phase-19-gate-19-5-artifact-publication:v1",
                    "source_head_sha": source_head_sha,
                    "account_id": _EXPECTED_ACCOUNT,
                    "region": _EXPECTED_REGION,
                    "bucket": _EXPECTED_BUCKET,
                    "caller_arn": caller_arn,
                    "automatic_retry_count": 0,
                    "s3_put_object_mutation_count": mutation_count,
                    "runtime_resource_mutation_count": 0,
                    "iam_mutation_count": 0,
                    "terraform_apply_count": 0,
                    "public_endpoint_enablement_count": 0,
                    "artifacts": evidence,
                },
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )

    if len(evidence) != 2:
        raise ArtifactPublicationError(
            "publication did not admit both immutable artifacts; do not retry automatically"
        )
    print(
        "phase19_gate19_5_publication=COMPLETE "
        f"s3_put_object_mutation_count={mutation_count} "
        f"output={args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())