"""Build deterministic Gate 19.5 API and worker Lambda deployment artifacts."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import shutil
import stat
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
UV_LOCK: Final = PROJECT_ROOT / "uv.lock"
PYTHON_VERSION: Final = "3.13"
PYTHON_PLATFORM: Final = "x86_64-manylinux_2_28"
ZIP_TIMESTAMP: Final = (1980, 1, 1, 0, 0, 0)
MEBIBYTE: Final = 1024 * 1024
LAMBDA_UNZIPPED_LIMIT_BYTES: Final = 250 * MEBIBYTE
MAX_COMPRESSED_BYTES: Final = 50 * MEBIBYTE
DEPLOYMENT_BUCKET: Final = "opslens-dev-artifacts-487757851499-us-east-1"

_PACKAGE_INIT = '"""Minimal role-specific Lambda package namespace."""\n'
_INSTALLATION_METADATA_FILES = ("INSTALLER", "REQUESTED", "direct_url.json")

_API_PINS: Final = (
    "aws-lambda-powertools==3.34.0",
    "boto3==1.43.72",
    "botocore==1.43.72",
    "jmespath==1.1.0",
    "python-dateutil==2.9.0.post0",
    "s3transfer==0.19.2",
    "six==1.17.0",
    "typing-extensions==4.16.0",
    "urllib3==2.7.0",
)
_WORKER_PINS: Final = (
    "aws-lambda-powertools==3.34.0",
    "jmespath==1.1.0",
    "typing-extensions==4.16.0",
)

_COMMON_SOURCES: Final = (
    "src/opslens/__init__.py",
    "src/opslens/public_analysis/__init__.py",
    "src/opslens/public_analysis/async_lambda.py",
    "src/opslens/public_analysis/async_runtime_config.py",
    "src/opslens/public_analysis/application/async_job_admission.py",
    "src/opslens/public_analysis/application/async_job_service.py",
    "src/opslens/public_analysis/domain/async_job.py",
    "src/opslens/public_analysis/domain/errors.py",
    "src/opslens/public_analysis/domain/request.py",
)
_API_SOURCES: Final = _COMMON_SOURCES + (
    "src/opslens/public_analysis/async_api_lambda.py",
    "src/opslens/public_analysis/adapters/async_aws.py",
    "src/opslens/public_analysis/adapters/async_http_api.py",
    "src/opslens/public_analysis/application/request_admission.py",
)
_WORKER_SOURCES: Final = _COMMON_SOURCES + (
    "src/opslens/public_analysis/async_worker_lambda.py",
    "src/opslens/public_analysis/adapters/async_sqs_event.py",
    "src/opslens/public_analysis/application/async_worker_service.py",
)


@dataclass(frozen=True, slots=True)
class _RoleSpec:
    name: str
    artifact_name: str
    required_handler: str
    forbidden_source: str
    pins: tuple[str, ...]
    sources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _LockedPackage:
    name: str
    version: str
    wheel_hashes: tuple[str, ...]


_ROLE_SPECS: Final = (
    _RoleSpec(
        name="api",
        artifact_name="opslens-public-async-api.zip",
        required_handler="opslens/public_analysis/async_api_lambda.py",
        forbidden_source="opslens/public_analysis/async_worker_lambda.py",
        pins=_API_PINS,
        sources=_API_SOURCES,
    ),
    _RoleSpec(
        name="worker",
        artifact_name="opslens-public-async-worker.zip",
        required_handler="opslens/public_analysis/async_worker_lambda.py",
        forbidden_source="opslens/public_analysis/async_api_lambda.py",
        pins=_WORKER_PINS,
        sources=_WORKER_SOURCES,
    ),
)


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be an object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise RuntimeError(f"{label} keys must be strings")
    return cast(dict[str, object], raw)


def _objects(value: object, *, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise RuntimeError(f"{label} must be an array")
    return [_object(item, label=f"{label}[]") for item in cast(list[object], value)]


def _normalized_distribution(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def _locked_packages() -> dict[str, _LockedPackage]:
    with UV_LOCK.open("rb") as handle:
        raw_root: object = tomllib.load(handle)
    root = _object(raw_root, label="uv.lock")
    packages = _objects(root.get("package"), label="uv.lock.package")
    locked: dict[str, _LockedPackage] = {}
    for package in packages:
        name = package.get("name")
        version = package.get("version")
        if type(name) is not str or type(version) is not str:
            raise RuntimeError("uv.lock package entry is missing name/version")
        raw_wheels = package.get("wheels")
        wheel_entries = (
            [] if raw_wheels is None else _objects(raw_wheels, label=f"uv.lock package {name} wheels")
        )
        wheel_hashes: list[str] = []
        for wheel in wheel_entries:
            digest = wheel.get("hash")
            if type(digest) is not str or not digest.startswith("sha256:"):
                raise RuntimeError(f"uv.lock wheel for {name} is missing a SHA-256 hash")
            wheel_hashes.append(digest)
        normalized = _normalized_distribution(name)
        locked[normalized] = _LockedPackage(
            name=normalized,
            version=version,
            wheel_hashes=tuple(sorted(set(wheel_hashes))),
        )
    return locked


def _validated_pin_packages(
    spec: _RoleSpec,
    locked: dict[str, _LockedPackage],
) -> tuple[_LockedPackage, ...]:
    selected: list[_LockedPackage] = []
    seen: set[str] = set()
    for pin in spec.pins:
        if "==" not in pin:
            raise RuntimeError(f"{spec.name} runtime dependency is not exactly pinned: {pin}")
        raw_name, raw_version = pin.split("==", maxsplit=1)
        name = _normalized_distribution(raw_name)
        if name in seen:
            raise RuntimeError(f"{spec.name} runtime dependency is duplicated: {name}")
        seen.add(name)
        package = locked.get(name)
        if package is None or package.version != raw_version:
            observed = None if package is None else package.version
            raise RuntimeError(
                f"{spec.name} runtime pin {pin} does not match uv.lock version {observed!r}"
            )
        if not package.wheel_hashes:
            raise RuntimeError(f"{spec.name} runtime dependency {name} has no locked wheel hash")
        selected.append(package)
    return tuple(selected)


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def _prepare(role_root: Path) -> Path:
    shutil.rmtree(role_root, ignore_errors=True)
    package_dir = role_root / "package"
    package_dir.mkdir(parents=True)
    return package_dir


def _write_hashed_requirements(
    role_root: Path,
    packages: tuple[_LockedPackage, ...],
) -> Path:
    path = role_root / "requirements.txt"
    lines: list[str] = []
    for package in sorted(packages, key=lambda item: item.name):
        hashes = " ".join(f"--hash={digest}" for digest in package.wheel_hashes)
        lines.append(f"{package.name}=={package.version} {hashes}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _install_dependencies(requirements: Path, package_dir: Path) -> None:
    _run(
        [
            "uv",
            "pip",
            "install",
            "--requirements",
            str(requirements),
            "--require-hashes",
            "--target",
            str(package_dir),
            "--python",
            PYTHON_VERSION,
            "--python-platform",
            PYTHON_PLATFORM,
            "--only-binary",
            ":all:",
            "--no-deps",
        ]
    )


def _is_installation_record_entry(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized.startswith("bin/") or normalized.endswith(
        tuple(f"/{name}" for name in _INSTALLATION_METADATA_FILES)
    )


def _normalize_installed_dependencies(package_dir: Path) -> None:
    shutil.rmtree(package_dir / "bin", ignore_errors=True)
    for dist_info in sorted(package_dir.glob("*.dist-info")):
        if not dist_info.is_dir():
            continue
        for name in _INSTALLATION_METADATA_FILES:
            (dist_info / name).unlink(missing_ok=True)
        record_path = dist_info / "RECORD"
        if not record_path.is_file():
            continue
        with record_path.open("r", encoding="utf-8", newline="") as record_file:
            rows = list(csv.reader(record_file))
        retained = [row for row in rows if row and not _is_installation_record_entry(row[0])]
        with record_path.open("w", encoding="utf-8", newline="") as record_file:
            csv.writer(record_file, lineterminator="\n").writerows(retained)


def _destination_for_source(source: Path) -> Path:
    return source.relative_to(PROJECT_ROOT / "src")


def _copy_sources(spec: _RoleSpec, package_dir: Path) -> None:
    for source_value in spec.sources:
        source = PROJECT_ROOT / source_value
        if not source.is_file():
            raise FileNotFoundError(f"{spec.name} source entry is missing: {source_value}")
        destination = package_dir / _destination_for_source(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    for namespace in (
        "opslens/public_analysis/adapters/__init__.py",
        "opslens/public_analysis/application/__init__.py",
        "opslens/public_analysis/domain/__init__.py",
    ):
        path = package_dir / namespace
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_PACKAGE_INIT, encoding="utf-8")


def _remove_generated_bytecode(package_dir: Path) -> None:
    for path in package_dir.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path)
    for pattern in ("*.pyc", "*.pyo"):
        for path in package_dir.rglob(pattern):
            path.unlink()


def _installed_distributions(package_dir: Path) -> set[str]:
    result: set[str] = set()
    for path in package_dir.glob("*.dist-info"):
        stem = path.name.removesuffix(".dist-info")
        distribution, separator, _version = stem.rpartition("-")
        if not separator:
            raise RuntimeError(f"cannot identify installed distribution from {path.name}")
        result.add(_normalized_distribution(distribution))
    return result


def _validate_package(
    spec: _RoleSpec,
    package_dir: Path,
    packages: tuple[_LockedPackage, ...],
) -> None:
    required = {
        "opslens/public_analysis/async_lambda.py",
        "opslens/public_analysis/async_runtime_config.py",
        spec.required_handler,
    }
    missing = sorted(path for path in required if not (package_dir / path).is_file())
    if missing:
        raise RuntimeError(f"{spec.name} artifact is missing required source: {', '.join(missing)}")
    if (package_dir / spec.forbidden_source).exists():
        raise RuntimeError(f"{spec.name} artifact contains opposite-role composition source")

    expected_distributions = {package.name for package in packages}
    installed = _installed_distributions(package_dir)
    if installed != expected_distributions:
        raise RuntimeError(
            f"{spec.name} installed distributions drifted: expected={sorted(expected_distributions)} "
            f"observed={sorted(installed)}"
        )


def _normalized_permissions(path: Path) -> int:
    return 0o755 if path.stat().st_mode & stat.S_IXUSR else 0o644


def _write_zip(package_dir: Path, artifact_path: Path) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.unlink(missing_ok=True)
    files = sorted(path for path in package_dir.rglob("*") if path.is_file())
    with ZipFile(
        artifact_path,
        mode="w",
        compression=ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            info = ZipInfo(
                filename=path.relative_to(package_dir).as_posix(),
                date_time=ZIP_TIMESTAMP,
            )
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = _normalized_permissions(path) << 16
            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=ZIP_DEFLATED,
                compresslevel=9,
            )


def _sha256(path: Path) -> tuple[str, str]:
    digest = hashlib.sha256(path.read_bytes())
    return digest.hexdigest(), base64.b64encode(digest.digest()).decode("ascii")


def _package_stats(package_dir: Path) -> tuple[int, int]:
    files = [path for path in package_dir.rglob("*") if path.is_file()]
    return len(files), sum(path.stat().st_size for path in files)


def _build_role(
    spec: _RoleSpec,
    output_root: Path,
    locked: dict[str, _LockedPackage],
) -> dict[str, object]:
    packages = _validated_pin_packages(spec, locked)
    role_root = output_root / "build" / spec.name
    package_dir = _prepare(role_root)
    requirements = _write_hashed_requirements(role_root, packages)
    _install_dependencies(requirements, package_dir)
    _normalize_installed_dependencies(package_dir)
    _copy_sources(spec, package_dir)
    _remove_generated_bytecode(package_dir)
    _validate_package(spec, package_dir, packages)

    file_count, uncompressed_bytes = _package_stats(package_dir)
    if uncompressed_bytes > LAMBDA_UNZIPPED_LIMIT_BYTES:
        raise RuntimeError(
            f"{spec.name} package exceeds Lambda uncompressed limit: {uncompressed_bytes}"
        )

    artifact = output_root / "dist" / spec.artifact_name
    _write_zip(package_dir, artifact)
    compressed_bytes = artifact.stat().st_size
    if compressed_bytes > MAX_COMPRESSED_BYTES:
        raise RuntimeError(
            f"{spec.name} package exceeds Gate 19.5 compressed bound: {compressed_bytes}"
        )
    digest, source_code_hash = _sha256(artifact)
    key = f"lambda/public-analysis/{spec.name}/sha256={digest}/{spec.artifact_name}"
    return {
        "role": spec.name,
        "artifact_path": artifact.relative_to(output_root).as_posix(),
        "artifact_sha256": digest,
        "lambda_source_code_hash": source_code_hash,
        "compressed_bytes": compressed_bytes,
        "uncompressed_bytes": uncompressed_bytes,
        "file_count": file_count,
        "s3": {
            "bucket": DEPLOYMENT_BUCKET,
            "key": key,
            "version_id": {
                "classification": "UNMEASURED",
                "value": None,
                "reason": "PENDING_HUMAN_PUBLICATION",
            },
        },
    }


def build_all(output_root: Path) -> dict[str, object]:
    """Build both role artifacts and return their deterministic pre-publication manifest."""
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    locked = _locked_packages()
    artifacts = [_build_role(spec, output_root, locked) for spec in _ROLE_SPECS]
    return {
        "schema_version": 1,
        "artifact_type": "phase-19-gate-19-5-async-artifact-prepublication:v1",
        "source_main_sha": "a5067e05fda74aad4d95d7f1a875110fb676304a",
        "deployment_bucket": DEPLOYMENT_BUCKET,
        "publication_authority": "HUMAN_ONLY_CREATE_ONLY",
        "terraform_apply_authorized": False,
        "runtime_resource_mutation_authorized": False,
        "public_enablement_authorized": False,
        "artifacts": artifacts,
    }


def _write_manifest(output_root: Path, manifest: dict[str, object]) -> Path:
    path = output_root / "dist" / "phase-19-gate-19-5-prepublication-manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Root receiving build/ and dist/ directories.",
    )
    return parser


def _manifest_artifacts(manifest: dict[str, object]) -> list[dict[str, object]]:
    return _objects(manifest.get("artifacts"), label="manifest.artifacts")


def main() -> None:
    """Build both artifacts and print stable machine-readable coordinates."""
    args = _parser().parse_args()
    output_root = args.output_root.resolve()
    manifest = build_all(output_root)
    manifest_path = _write_manifest(output_root, manifest)
    print(f"manifest={manifest_path}")
    for artifact in _manifest_artifacts(manifest):
        s3 = _object(artifact.get("s3"), label="artifact.s3")
        role = artifact.get("role")
        digest = artifact.get("artifact_sha256")
        source_code_hash = artifact.get("lambda_source_code_hash")
        compressed_bytes = artifact.get("compressed_bytes")
        key = s3.get("key")
        if (
            type(role) is not str
            or type(digest) is not str
            or type(source_code_hash) is not str
            or type(compressed_bytes) is not int
            or type(key) is not str
        ):
            raise RuntimeError("internal artifact manifest is invalid")
        print(
            f"role={role} "
            f"sha256={digest} "
            f"source_code_hash={source_code_hash} "
            f"compressed_bytes={compressed_bytes} "
            f"s3_key={key}"
        )


if __name__ == "__main__":
    main()
