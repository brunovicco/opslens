#!/usr/bin/env python3
"""Verify Gate 19.5 role artifacts by rebuilding them from their pinned tree.

The retained prepublication manifest pins two artifact digests that the Gate
19.6 plan inputs and the Gate 19.7 materialization evidence both reference. The
property this gate proves is therefore:

    the retained artifact is deterministically reproducible from the tree that
    produced it, using the builder that ships today

and not "the current working tree reproduces the retained artifact". Rebuilding
from HEAD asserts the second, which proves nothing about the retained evidence
and turns every later change to packaged source into a false failure.

So the rebuild runs inside a git worktree pinned at ``_PINNED_BUILD_COMMIT``.
The builder is today's, not the pinned tree's: it is copied into the worktree
before the rebuild, so the gate exercises current build tooling against the
recorded source. A builder change that stops reproducing the retained digests
fails here, while a change that does not affect packaging passes. Its safety
controls are checked separately against the working tree.

``source_main_sha`` in the manifest is the main commit the Gate 19.5 work
branched from, not the tree that was packaged: ``src/`` changed between the two.
The packaged tree is the commit that introduced the manifest, pinned below.

```text
retained artifact identity != current source identity
historical evidence != standing authority
```
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import cast
from zipfile import ZipFile

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BUILDER = _REPO_ROOT / "scripts" / "build_phase19_async_lambda_artifacts.py"
_MANIFEST_NAME = "phase-19-gate-19-5-prepublication-manifest.json"
_CANONICAL_MANIFEST = (
    _REPO_ROOT / "labs" / "evidence" / "phase-19-gate-19-5-prepublication-v1.json"
)
_EXPECTED_SOURCE_MAIN = "a5067e05fda74aad4d95d7f1a875110fb676304a"
# The commit whose tree produced the retained artifacts. Distinct from
# _EXPECTED_SOURCE_MAIN above, which records only the main commit the Gate 19.5
# work branched from. Re-freezing the manifest means moving this pin.
_PINNED_BUILD_COMMIT = "61749bfac7b7bc9d032567e0b1870f8c1f7dedd4"
_EXPECTED_BUCKET = "opslens-dev-artifacts-487757851499-us-east-1"
_EXPECTED_ROLES = {"api", "worker"}
_EXPECTED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


class Gate19_5ArtifactBuildError(RuntimeError):
    """Raised when deterministic artifact evidence cannot be admitted."""


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_5ArtifactBuildError(f"{label} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise Gate19_5ArtifactBuildError(f"{label} keys must be strings")
    return cast(dict[str, object], raw)


def _objects(value: object, *, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise Gate19_5ArtifactBuildError(f"{label} must be an array")
    return [_object(item, label=f"{label}[]") for item in cast(list[object], value)]


def _manifest_path(root: Path) -> Path:
    return root / "dist" / _MANIFEST_NAME


def _load_manifest(root: Path) -> dict[str, object]:
    path = _manifest_path(root)
    if not path.is_file():
        raise Gate19_5ArtifactBuildError(f"builder did not create {path}")
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    return _object(raw, label="prepublication manifest")


def _load_canonical_manifest() -> dict[str, object]:
    if not _CANONICAL_MANIFEST.is_file():
        raise Gate19_5ArtifactBuildError("canonical prepublication manifest is missing")
    raw: object = json.loads(_CANONICAL_MANIFEST.read_text(encoding="utf-8"))
    return _object(raw, label="canonical prepublication manifest")


def _git(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run one git command in the repository and return the completed process."""
    return subprocess.run(
        ["git", *arguments],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _require_pinned_commit() -> None:
    """Make the pinned build commit available, fetching it when the clone is shallow."""
    probe = f"{_PINNED_BUILD_COMMIT}^{{commit}}"
    if _git("cat-file", "-e", probe).returncode == 0:
        return
    fetched = _git("fetch", "--depth", "1", "origin", _PINNED_BUILD_COMMIT)
    if fetched.returncode != 0 or _git("cat-file", "-e", probe).returncode != 0:
        raise Gate19_5ArtifactBuildError(
            "the pinned Gate 19.5 build commit is unavailable\n"
            f"commit: {_PINNED_BUILD_COMMIT}\n"
            f"stderr:\n{fetched.stderr}"
        )


@contextmanager
def _pinned_source_tree() -> Generator[Path]:
    """Materialize the exact tree the retained artifacts were built from."""
    _require_pinned_commit()
    with tempfile.TemporaryDirectory(prefix="opslens-gate19-5-src-") as directory:
        worktree = Path(directory) / "source"
        added = _git("worktree", "add", "--detach", str(worktree), _PINNED_BUILD_COMMIT)
        if added.returncode != 0:
            raise Gate19_5ArtifactBuildError(
                f"could not materialize the pinned build commit\nstderr:\n{added.stderr}"
            )
        try:
            yield worktree
        finally:
            _git("worktree", "remove", "--force", str(worktree))
            _git("worktree", "prune")


def _install_current_builder(source_root: Path) -> Path:
    """Place today's builder inside the pinned tree and return its path.

    The builder resolves every path from its own location, so running today's
    builder from inside the pinned worktree packages the pinned source. That is
    what makes the gate exercise the builder rather than merely compare its
    text: if a builder change stops reproducing the retained digests, the
    comparison against the frozen manifest fails.
    """
    pinned_builder = source_root / "scripts" / _BUILDER.name
    if not pinned_builder.is_file():
        raise Gate19_5ArtifactBuildError(
            f"the pinned build commit has no artifact builder at {pinned_builder}"
        )
    pinned_builder.write_bytes(_BUILDER.read_bytes())
    return pinned_builder


def _run_build(root: Path, source_root: Path) -> tuple[dict[str, object], str]:
    builder = source_root / "scripts" / _BUILDER.name
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(source_root / "src")
    # The pinned tree carries its own [tool.uv] required-version. That setting
    # never reaches a packaged artifact, so ignoring project configuration keeps
    # the rebuild reproducible under whichever uv the caller has installed.
    environment["UV_NO_CONFIG"] = "1"
    process = subprocess.run(
        [sys.executable, str(builder), "--output-root", str(root)],
        cwd=source_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise Gate19_5ArtifactBuildError(
            "artifact builder failed\n"
            f"stdout:\n{process.stdout}\n"
            f"stderr:\n{process.stderr}"
        )
    return _load_manifest(root), process.stdout


def _sha256(path: Path) -> tuple[str, str]:
    digest = hashlib.sha256(path.read_bytes())
    return digest.hexdigest(), base64.b64encode(digest.digest()).decode("ascii")


def _artifact_map(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    artifacts = _objects(manifest.get("artifacts"), label="manifest.artifacts")
    by_role: dict[str, dict[str, object]] = {}
    for artifact in artifacts:
        role = artifact.get("role")
        if type(role) is not str or role in by_role:
            raise Gate19_5ArtifactBuildError("artifact role inventory is invalid")
        by_role[role] = artifact
    if set(by_role) != _EXPECTED_ROLES:
        raise Gate19_5ArtifactBuildError("artifact role inventory drifted")
    return by_role


def _verify_manifest_identity(manifest: dict[str, object]) -> None:
    expected: dict[str, object] = {
        "schema_version": 1,
        "artifact_type": "phase-19-gate-19-5-async-artifact-prepublication:v1",
        "source_main_sha": _EXPECTED_SOURCE_MAIN,
        "deployment_bucket": _EXPECTED_BUCKET,
        "publication_authority": "HUMAN_ONLY_CREATE_ONLY",
        "terraform_apply_authorized": False,
        "runtime_resource_mutation_authorized": False,
        "public_enablement_authorized": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise Gate19_5ArtifactBuildError(f"prepublication manifest identity drifted: {key}")


def _verify_canonical_manifest(
    first_root: Path,
    second_root: Path,
    first_manifest: dict[str, object],
) -> None:
    canonical = _load_canonical_manifest()
    _verify_manifest_identity(canonical)
    if first_manifest != canonical:
        raise Gate19_5ArtifactBuildError(
            "deterministic rebuild does not match the frozen prepublication manifest"
        )
    canonical_bytes = _CANONICAL_MANIFEST.read_bytes()
    for root in (first_root, second_root):
        if _manifest_path(root).read_bytes() != canonical_bytes:
            raise Gate19_5ArtifactBuildError(
                "generated prepublication manifest is not byte-identical to canonical evidence"
            )


def _zip_names(path: Path) -> tuple[str, ...]:
    with ZipFile(path) as archive:
        infos = archive.infolist()
        names = tuple(info.filename for info in infos)
        if len(names) != len(set(names)):
            raise Gate19_5ArtifactBuildError(f"ZIP contains duplicate entries: {path}")
        if tuple(sorted(names)) != names:
            raise Gate19_5ArtifactBuildError(f"ZIP entry ordering is not deterministic: {path}")
        if any(info.date_time != _EXPECTED_ZIP_TIMESTAMP for info in infos):
            raise Gate19_5ArtifactBuildError(f"ZIP timestamp normalization drifted: {path}")
        if any(
            name.endswith((".pyc", ".pyo")) or "__pycache__/" in name for name in names
        ):
            raise Gate19_5ArtifactBuildError(f"ZIP contains generated bytecode: {path}")
        return names


def _required_string(mapping: dict[str, object], name: str) -> str:
    value = mapping.get(name)
    if type(value) is not str or not value:
        raise Gate19_5ArtifactBuildError(f"{name} must be a non-empty string")
    return value


def _required_int(mapping: dict[str, object], name: str) -> int:
    value = mapping.get(name)
    if type(value) is not int or value <= 0:
        raise Gate19_5ArtifactBuildError(f"{name} must be a positive integer")
    return value


def _verify_artifact(root: Path, artifact: dict[str, object]) -> tuple[str, int]:
    role = _required_string(artifact, "role")
    relative_path = _required_string(artifact, "artifact_path")
    path = root / relative_path
    if not path.is_file():
        raise Gate19_5ArtifactBuildError(f"{role} artifact is missing")

    digest, source_code_hash = _sha256(path)
    if artifact.get("artifact_sha256") != digest:
        raise Gate19_5ArtifactBuildError(f"{role} artifact SHA-256 drifted")
    if artifact.get("lambda_source_code_hash") != source_code_hash:
        raise Gate19_5ArtifactBuildError(f"{role} Lambda source_code_hash drifted")
    if artifact.get("compressed_bytes") != path.stat().st_size:
        raise Gate19_5ArtifactBuildError(f"{role} compressed byte count drifted")
    _required_int(artifact, "uncompressed_bytes")
    _required_int(artifact, "file_count")

    s3 = _object(artifact.get("s3"), label=f"{role}.s3")
    if s3.get("bucket") != _EXPECTED_BUCKET:
        raise Gate19_5ArtifactBuildError(f"{role} deployment bucket drifted")
    expected_key = (
        f"lambda/public-analysis/{role}/sha256={digest}/"
        f"opslens-public-async-{role}.zip"
    )
    if s3.get("key") != expected_key:
        raise Gate19_5ArtifactBuildError(f"{role} content-addressed S3 key drifted")
    version = _object(s3.get("version_id"), label=f"{role}.s3.version_id")
    if version != {
        "classification": "UNMEASURED",
        "value": None,
        "reason": "PENDING_HUMAN_PUBLICATION",
    }:
        raise Gate19_5ArtifactBuildError(f"{role} VersionId was fabricated before publication")

    names = set(_zip_names(path))
    facade = "opslens/public_analysis/async_lambda.py"
    if facade not in names:
        raise Gate19_5ArtifactBuildError(f"{role} artifact is missing the stable handler facade")
    if role == "api":
        required = {
            "opslens/public_analysis/async_api_lambda.py",
            "opslens/public_analysis/adapters/async_aws.py",
            "opslens/public_analysis/adapters/async_http_api.py",
        }
        forbidden = {
            "opslens/public_analysis/async_worker_lambda.py",
            "opslens/public_analysis/adapters/async_sqs_event.py",
            "opslens/public_analysis/application/async_worker_service.py",
        }
    else:
        required = {
            "opslens/public_analysis/async_worker_lambda.py",
            "opslens/public_analysis/adapters/async_sqs_event.py",
            "opslens/public_analysis/application/async_worker_service.py",
        }
        forbidden = {
            "opslens/public_analysis/async_api_lambda.py",
            "opslens/public_analysis/adapters/async_aws.py",
            "opslens/public_analysis/adapters/async_http_api.py",
            "boto3/__init__.py",
        }
    if not required.issubset(names):
        raise Gate19_5ArtifactBuildError(f"{role} artifact is missing role-specific source")
    if forbidden & names:
        raise Gate19_5ArtifactBuildError(f"{role} artifact contains forbidden opposite-role source")
    if any("representative_" in name or "knowledge_retrieval" in name for name in names):
        raise Gate19_5ArtifactBuildError(
            f"{role} artifact accidentally contains provider-heavy analysis implementation"
        )

    if role == "worker":
        with ZipFile(path) as archive:
            worker_source = archive.read(
                "opslens/public_analysis/async_worker_lambda.py"
            ).decode("utf-8")
        for marker in (
            "provider executor composition is not admitted",
            "disabled worker must not access DynamoDB",
            "disabled worker must not execute provider-heavy analysis",
        ):
            if marker not in worker_source:
                raise Gate19_5ArtifactBuildError(
                    f"disabled worker artifact is missing fail-closed marker {marker!r}"
                )

    return digest, path.stat().st_size


def _verify_builder_source() -> None:
    text = _BUILDER.read_text(encoding="utf-8")
    for marker in (
        '"--require-hashes"',
        '"--no-deps"',
        "ZIP_TIMESTAMP",
        "PENDING_HUMAN_PUBLICATION",
        "HUMAN_ONLY_CREATE_ONLY",
    ):
        if marker not in text:
            raise Gate19_5ArtifactBuildError(f"builder is missing required control {marker!r}")


def main() -> int:
    """Rebuild twice and admit only byte-identical role artifacts."""
    _verify_builder_source()
    with (
        _pinned_source_tree() as pinned_source,
        tempfile.TemporaryDirectory(prefix="opslens-gate19-5-a-") as first_dir,
        tempfile.TemporaryDirectory(prefix="opslens-gate19-5-b-") as second_dir,
    ):
        _install_current_builder(pinned_source)
        first_root = Path(first_dir)
        second_root = Path(second_dir)
        first_manifest, _first_stdout = _run_build(first_root, pinned_source)
        second_manifest, _second_stdout = _run_build(second_root, pinned_source)
        _verify_manifest_identity(first_manifest)
        _verify_manifest_identity(second_manifest)
        if first_manifest != second_manifest:
            raise Gate19_5ArtifactBuildError("prepublication manifests differ across rebuilds")
        _verify_canonical_manifest(first_root, second_root, first_manifest)

        first = _artifact_map(first_manifest)
        second = _artifact_map(second_manifest)
        summaries: list[str] = []
        for role in sorted(_EXPECTED_ROLES):
            first_digest, first_bytes = _verify_artifact(first_root, first[role])
            second_digest, second_bytes = _verify_artifact(second_root, second[role])
            first_path = first_root / _required_string(first[role], "artifact_path")
            second_path = second_root / _required_string(second[role], "artifact_path")
            if first_path.read_bytes() != second_path.read_bytes():
                raise Gate19_5ArtifactBuildError(f"{role} artifact bytes differ across rebuilds")
            if (first_digest, first_bytes) != (second_digest, second_bytes):
                raise Gate19_5ArtifactBuildError(
                    f"{role} artifact metadata differs across rebuilds"
                )
            first_s3 = _object(first[role].get("s3"), label=f"{role}.s3")
            source_code_hash = _required_string(
                first[role],
                "lambda_source_code_hash",
            )
            uncompressed_bytes = _required_int(first[role], "uncompressed_bytes")
            file_count = _required_int(first[role], "file_count")
            s3_key = _required_string(first_s3, "key")
            summaries.append(
                f"{role}_sha256={first_digest} "
                f"{role}_source_code_hash={source_code_hash} "
                f"{role}_bytes={first_bytes} "
                f"{role}_uncompressed_bytes={uncompressed_bytes} "
                f"{role}_files={file_count} "
                f"{role}_s3_key={s3_key}"
            )

    print(
        "phase19_gate19_5_artifact_build=PASS "
        f"rebuilt_from_pinned_tree={_PINNED_BUILD_COMMIT} "
        "canonical_prepublication_manifest=PASS "
        "publication_authority=HUMAN_ONLY_CREATE_ONLY "
        "terraform_apply_authorized=false "
        + " ".join(summaries)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
