#!/usr/bin/env python3
"""Build the bounded AgentCore direct-code ZIP from the exact OpsLens lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

_PACKAGE_ARTIFACT_VERSION = "agentcore-runtime-package:v1"
_RUNTIME = "PYTHON_3_13"
_PLATFORM = "aarch64-manylinux2014"
_ENTRY_POINT = ("main.py",)
_ROOT_DEPENDENCY = "botocore"
_MAX_COMPRESSED_BYTES = 250_000_000
_MAX_UNCOMPRESSED_BYTES = 750_000_000
_FORBIDDEN_DISTRIBUTIONS = frozenset(
    {
        "aws-lambda-powertools",
        "boto3",
        "mcp",
        "mcp-types",
        "pyarrow",
        "s3transfer",
    }
)
_NATIVE_SUFFIXES = (".so", ".pyd", ".dylib")
_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_RUNTIME_SOURCE_FILES = (
    "opslens/__init__.py",
    "opslens/agent_baseline/__init__.py",
    "opslens/agent_baseline/adapters/bedrock_reasoning.py",
    "opslens/agent_baseline/application/authorization.py",
    "opslens/agent_baseline/application/reasoning.py",
    "opslens/agent_baseline/domain/errors.py",
    "opslens/agent_baseline/domain/models.py",
    "opslens/agent_baseline/domain/reasoning.py",
    "opslens/agent_baseline/ports/reasoning.py",
    "opslens/agentcore_runtime/application.py",
    "opslens/agentcore_runtime/domain.py",
    "opslens/agentcore_runtime/http_adapter.py",
    "opslens/agentcore_runtime/server.py",
)
_RUNTIME_EMPTY_PACKAGE_DIRS = (
    "opslens/agent_baseline/adapters",
    "opslens/agent_baseline/application",
    "opslens/agent_baseline/domain",
    "opslens/agent_baseline/ports",
    "opslens/agentcore_runtime",
)


@dataclass(frozen=True, slots=True)
class LockedPackage:
    """Represent one exact registry package from uv.lock."""

    name: str
    version: str
    dependencies: tuple[str, ...]


def _parse_args() -> argparse.Namespace:
    """Parse the bounded output location without changing dependency authority."""
    parser = argparse.ArgumentParser(
        description=(
            "Build the Gate 14.2 Python 3.13/arm64 AgentCore direct-code package "
            "from the exact committed uv.lock dependency closure."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist/agentcore-runtime"),
        help="Directory for the ZIP and deterministic package manifest.",
    )
    return parser.parse_args()


def _required_string(mapping: Mapping[str, object], key: str, *, context: str) -> str:
    value = mapping.get(key)
    if type(value) is not str or not value:
        raise RuntimeError(f"{context}.{key} must be a non-empty string")
    return value


def _load_locked_packages(lock_path: Path) -> dict[str, LockedPackage]:
    """Load exact registry package identities and dependency edges from uv.lock."""
    document = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    root = cast(Mapping[str, object], document)
    raw_packages = root.get("package")
    if not isinstance(raw_packages, Sequence) or isinstance(raw_packages, (str, bytes)):
        raise RuntimeError("uv.lock package list is missing")

    packages: dict[str, LockedPackage] = {}
    for index, raw_package in enumerate(cast(Sequence[object], raw_packages)):
        if not isinstance(raw_package, Mapping):
            raise RuntimeError(f"uv.lock package[{index}] must be a mapping")
        package = cast(Mapping[str, object], raw_package)
        name = _required_string(package, "name", context=f"package[{index}]")
        version = _required_string(package, "version", context=f"package[{index}]")

        source = package.get("source")
        if not isinstance(source, Mapping):
            raise RuntimeError(f"locked package {name} must declare one source")
        typed_source = cast(Mapping[str, object], source)
        if type(typed_source.get("registry")) is not str:
            continue

        dependency_names: list[str] = []
        raw_dependencies = package.get("dependencies", [])
        if not isinstance(raw_dependencies, Sequence) or isinstance(
            raw_dependencies, (str, bytes)
        ):
            raise RuntimeError(f"locked package {name} dependencies must be an array")
        for raw_dependency in cast(Sequence[object], raw_dependencies):
            if not isinstance(raw_dependency, Mapping):
                raise RuntimeError(f"locked package {name} has malformed dependency metadata")
            dependency = cast(Mapping[str, object], raw_dependency)
            dependency_names.append(
                _required_string(dependency, "name", context=f"dependency of {name}")
            )

        if name in packages:
            raise RuntimeError(
                f"runtime package builder does not admit duplicate lock entry {name}"
            )
        packages[name] = LockedPackage(
            name=name,
            version=version,
            dependencies=tuple(dependency_names),
        )
    return packages


def _dependency_closure(
    packages: Mapping[str, LockedPackage],
    root_name: str,
) -> tuple[LockedPackage, ...]:
    """Resolve the exact transitive lock closure for one runtime root dependency."""
    pending = [root_name]
    admitted: dict[str, LockedPackage] = {}
    while pending:
        name = pending.pop()
        if name in admitted:
            continue
        package = packages.get(name)
        if package is None:
            raise RuntimeError(f"uv.lock does not contain required runtime package {name}")
        admitted[name] = package
        pending.extend(package.dependencies)
    return tuple(admitted[name] for name in sorted(admitted))


def _copy_runtime_sources(*, repository_root: Path, stage: Path) -> None:
    """Copy only source files reachable by the retained bounded reasoning path."""
    source_root = repository_root / "src"
    for relative in _RUNTIME_SOURCE_FILES:
        source = source_root / relative
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    for relative in _RUNTIME_EMPTY_PACKAGE_DIRS:
        init_path = stage / relative / "__init__.py"
        init_path.parent.mkdir(parents=True, exist_ok=True)
        init_path.write_text(
            '"""Runtime-minimized package boundary."""\n',
            encoding="utf-8",
        )

    shutil.copy2(repository_root / "runtime/agentcore/main.py", stage / "main.py")


def _install_locked_dependencies(
    *,
    stage: Path,
    dependencies: tuple[LockedPackage, ...],
) -> None:
    """Install the exact lock closure as Python 3.13 arm64 wheels with no resolver drift."""
    specifications = [f"{package.name}=={package.version}" for package in dependencies]
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python-platform",
            _PLATFORM,
            "--python-version",
            "3.13",
            "--target",
            str(stage),
            "--only-binary=:all:",
            "--no-deps",
            *specifications,
        ],
        check=True,
    )


def _remove_bytecode(stage: Path) -> None:
    """Remove build-machine bytecode that AgentCore documentation advises against shipping."""
    for cache_dir in sorted(stage.rglob("__pycache__"), reverse=True):
        shutil.rmtree(cache_dir)
    for suffix in ("*.pyc", "*.pyo"):
        for path in stage.rglob(suffix):
            path.unlink()


def _validate_stage(
    *,
    stage: Path,
    dependencies: tuple[LockedPackage, ...],
) -> tuple[str, ...]:
    """Fail closed on forbidden dependency families, native files, or import gaps."""
    names = frozenset(package.name for package in dependencies)
    forbidden = sorted(names & _FORBIDDEN_DISTRIBUTIONS)
    if forbidden:
        raise RuntimeError(f"forbidden runtime dependencies admitted: {', '.join(forbidden)}")

    native_files = tuple(
        sorted(
            path.relative_to(stage).as_posix()
            for path in stage.rglob("*")
            if path.is_file() and path.suffix.lower() in _NATIVE_SUFFIXES
        )
    )
    if native_files:
        raise RuntimeError(
            "Gate 14.2 initial direct-code package unexpectedly contains native files: "
            + ", ".join(native_files)
        )

    stage_literal = repr(str(stage))
    subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            (
                "import sys; "
                f"sys.path.insert(0, {stage_literal}); "
                "import opslens.agentcore_runtime.server; "
                "import botocore.session"
            ),
        ],
        check=True,
    )
    return native_files


def _write_deterministic_zip(*, stage: Path, zip_path: Path) -> tuple[int, int, str]:
    """Write one deterministic ZIP and return compressed bytes, source bytes, and SHA-256."""
    files = tuple(sorted(path for path in stage.rglob("*") if path.is_file()))
    uncompressed_bytes = sum(path.stat().st_size for path in files)
    if uncompressed_bytes > _MAX_UNCOMPRESSED_BYTES:
        raise RuntimeError("AgentCore package exceeds the uncompressed direct-code limit")

    with zipfile.ZipFile(
        zip_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            relative = path.relative_to(stage).as_posix()
            info = zipfile.ZipInfo(relative, date_time=_FIXED_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())

    compressed_bytes = zip_path.stat().st_size
    if compressed_bytes > _MAX_COMPRESSED_BYTES:
        raise RuntimeError("AgentCore package exceeds the compressed direct-code limit")
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    return compressed_bytes, uncompressed_bytes, digest


def main() -> int:
    """Build and describe one bounded reproducible AgentCore direct-code artifact."""
    args = _parse_args()
    output_dir = cast(Path, args.output_dir).resolve()
    repository_root = Path(__file__).resolve().parents[1]
    lock_path = repository_root / "uv.lock"
    packages = _load_locked_packages(lock_path)
    dependencies = _dependency_closure(packages, _ROOT_DEPENDENCY)

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / "opslens-agentcore-runtime.zip"
    manifest_path = output_dir / "opslens-agentcore-runtime-package.json"

    with tempfile.TemporaryDirectory(prefix="opslens-agentcore-") as temporary:
        stage = Path(temporary) / "package"
        stage.mkdir()
        _copy_runtime_sources(repository_root=repository_root, stage=stage)
        _install_locked_dependencies(stage=stage, dependencies=dependencies)
        _remove_bytecode(stage)
        native_files = _validate_stage(stage=stage, dependencies=dependencies)
        compressed_bytes, uncompressed_bytes, digest = _write_deterministic_zip(
            stage=stage,
            zip_path=zip_path,
        )

    manifest: dict[str, object] = {
        "artifact_version": _PACKAGE_ARTIFACT_VERSION,
        "architecture": "arm64",
        "compressed_bytes": compressed_bytes,
        "entry_point": list(_ENTRY_POINT),
        "forbidden_distributions_present": [],
        "locked_dependencies": [
            {"name": package.name, "version": package.version}
            for package in dependencies
        ],
        "native_files": list(native_files),
        "python_platform": _PLATFORM,
        "runtime": _RUNTIME,
        "sha256": digest,
        "source_files": list(_RUNTIME_SOURCE_FILES),
        "uncompressed_bytes": uncompressed_bytes,
        "zip_file": zip_path.name,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
