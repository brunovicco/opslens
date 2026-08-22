"""Build the deterministic AWS Lambda deployment package for NVD Silver."""

import hashlib
import shutil
import stat
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BUILD_DIR = PROJECT_ROOT / "build" / "lambda" / "nvd-silver"
PACKAGE_DIR = BUILD_DIR / "package"
REQUIREMENTS_FILE = BUILD_DIR / "requirements.txt"

DIST_DIR = PROJECT_ROOT / "dist"
ARTIFACT_PATH = DIST_DIR / "opslens-nvd-silver.zip"

PYTHON_VERSION = "3.13"
PYTHON_PLATFORM = "x86_64-manylinux_2_28"
RUNTIME_DEPENDENCY_GROUP = "nvd-silver-runtime"

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

MEBIBYTE = 1024 * 1024
LAMBDA_DIRECT_UPLOAD_LIMIT_BYTES = 50 * MEBIBYTE
LAMBDA_UNZIPPED_LIMIT_BYTES = 250 * MEBIBYTE

SOURCE_MANIFEST = (
    (
        PROJECT_ROOT / "src" / "opslens" / "__init__.py",
        Path("opslens/__init__.py"),
    ),
    (
        PROJECT_ROOT / "src" / "opslens" / "ingestion" / "__init__.py",
        Path("opslens/ingestion/__init__.py"),
    ),
    (
        PROJECT_ROOT / "src" / "opslens" / "ingestion" / "nvd" / "__init__.py",
        Path("opslens/ingestion/nvd/__init__.py"),
    ),
    (
        PROJECT_ROOT / "src" / "opslens" / "ingestion" / "nvd" / "domain",
        Path("opslens/ingestion/nvd/domain"),
    ),
    (
        PROJECT_ROOT / "src" / "opslens" / "transformation" / "__init__.py",
        Path("opslens/transformation/__init__.py"),
    ),
    (
        PROJECT_ROOT / "src" / "opslens" / "transformation" / "nvd",
        Path("opslens/transformation/nvd"),
    ),
    (
        PROJECT_ROOT / "src" / "opslens" / "shared" / "__init__.py",
        Path("opslens/shared/__init__.py"),
    ),
    (
        PROJECT_ROOT / "src" / "opslens" / "shared" / "observability",
        Path("opslens/shared/observability"),
    ),
)

REQUIRED_PACKAGE_FILES = (
    Path("opslens/ingestion/nvd/domain/incremental.py"),
    Path("opslens/transformation/nvd/lambda_handler.py"),
    Path("opslens/transformation/nvd/composition.py"),
    Path("opslens/transformation/nvd/adapters/inbound/invocation.py"),
    Path("opslens/transformation/nvd/application/service.py"),
    Path("opslens/transformation/nvd/application/persistence_service.py"),
    Path("opslens/transformation/nvd/application/completion_persistence_service.py"),
    Path("opslens/transformation/nvd/adapters/outbound/s3_exact_object.py"),
    Path("opslens/transformation/nvd/adapters/outbound/s3_silver_parquet.py"),
    Path("opslens/transformation/nvd/adapters/outbound/s3_silver_replay.py"),
    Path("opslens/transformation/nvd/adapters/outbound/s3_silver_completion.py"),
    Path("opslens/transformation/nvd/provenance/verifier.py"),
    Path("opslens/transformation/nvd/serialization/parquet.py"),
    Path("opslens/shared/observability/powertools.py"),
    Path("pyarrow/__init__.py"),
)

FORBIDDEN_PACKAGE_FILES = (
    Path("opslens/ingestion/nvd/lambda_handler.py"),
    Path("opslens/ingestion/nvd/composition.py"),
)


def run_command(command: list[str]) -> None:
    """Run one build command and fail on non-zero exit."""
    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
    )


def prepare_directories() -> None:
    """Create clean deterministic build directories."""
    shutil.rmtree(
        BUILD_DIR,
        ignore_errors=True,
    )

    BUILD_DIR.mkdir(parents=True)
    PACKAGE_DIR.mkdir()
    DIST_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ARTIFACT_PATH.unlink(
        missing_ok=True,
    )


def export_runtime_dependencies() -> None:
    """Export locked NVD Silver runtime dependencies."""
    run_command(
        [
            "uv",
            "export",
            "--locked",
            "--no-default-groups",
            "--group",
            RUNTIME_DEPENDENCY_GROUP,
            "--no-emit-project",
            "--format",
            "requirements.txt",
            "--output-file",
            str(REQUIREMENTS_FILE),
        ]
    )


def install_runtime_dependencies() -> None:
    """Install Linux x86_64 runtime dependencies into staging."""
    run_command(
        [
            "uv",
            "pip",
            "install",
            "--requirements",
            str(REQUIREMENTS_FILE),
            "--target",
            str(PACKAGE_DIR),
            "--python",
            PYTHON_VERSION,
            "--python-platform",
            PYTHON_PLATFORM,
            "--only-binary",
            ":all:",
        ]
    )


def copy_application_source() -> None:
    """Copy only source required by NVD Silver."""
    for source, relative_destination in SOURCE_MANIFEST:
        if not source.exists():
            raise FileNotFoundError(
                f"NVD Silver Lambda source manifest entry does not exist: {source}"
            )

        destination = PACKAGE_DIR / relative_destination

        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                ignore=shutil.ignore_patterns(
                    "__pycache__",
                    "*.pyc",
                    "*.pyo",
                ),
            )
            continue

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            destination,
        )


def remove_unneeded_runtime_files() -> None:
    """Remove files that cannot contribute to Lambda execution."""
    bin_dir = PACKAGE_DIR / "bin"

    if bin_dir.exists():
        shutil.rmtree(bin_dir)

    for path in PACKAGE_DIR.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path)

    for pattern in ("*.pyc", "*.pyo"):
        for path in PACKAGE_DIR.rglob(pattern):
            path.unlink()


def validate_package_contents() -> None:
    """Require expected runtime files and reject ingestion entrypoints."""
    missing = [path for path in REQUIRED_PACKAGE_FILES if not (PACKAGE_DIR / path).is_file()]

    if missing:
        formatted = ", ".join(path.as_posix() for path in missing)
        raise RuntimeError(f"NVD Silver Lambda package is missing required files: {formatted}")

    forbidden = [path for path in FORBIDDEN_PACKAGE_FILES if (PACKAGE_DIR / path).exists()]

    if forbidden:
        formatted = ", ".join(path.as_posix() for path in forbidden)
        raise RuntimeError(f"NVD Silver Lambda package contains forbidden files: {formatted}")


def normalized_permissions(path: Path) -> int:
    """Return deterministic POSIX permissions for one packaged file."""
    mode = path.stat().st_mode

    return 0o755 if mode & stat.S_IXUSR else 0o644


def write_deterministic_zip() -> None:
    """Create a ZIP with stable ordering, timestamps, and permissions."""
    files = sorted(path for path in PACKAGE_DIR.rglob("*") if path.is_file())

    with ZipFile(
        ARTIFACT_PATH,
        mode="w",
        compression=ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            relative_path = path.relative_to(PACKAGE_DIR).as_posix()

            info = ZipInfo(
                filename=relative_path,
                date_time=ZIP_TIMESTAMP,
            )
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = normalized_permissions(path) << 16

            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=ZIP_DEFLATED,
                compresslevel=9,
            )


def artifact_sha256() -> str:
    """Return SHA-256 for the generated deployment package."""
    digest = hashlib.sha256()

    with ARTIFACT_PATH.open("rb") as artifact:
        for chunk in iter(
            lambda: artifact.read(MEBIBYTE),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def package_uncompressed_size() -> int:
    """Return total uncompressed staged-package size."""
    return sum(path.stat().st_size for path in PACKAGE_DIR.rglob("*") if path.is_file())


def package_file_count() -> int:
    """Return total staged-package file count."""
    return sum(1 for path in PACKAGE_DIR.rglob("*") if path.is_file())


def validate_lambda_size_limit(
    uncompressed_size: int,
) -> None:
    """Reject packages exceeding Lambda's uncompressed ZIP limit."""
    if uncompressed_size > LAMBDA_UNZIPPED_LIMIT_BYTES:
        raise RuntimeError(
            "NVD Silver Lambda package exceeds the 250 MiB "
            f"uncompressed limit: {uncompressed_size} bytes."
        )


def main() -> None:
    """Build and report the deterministic NVD Silver Lambda package."""
    prepare_directories()
    export_runtime_dependencies()
    install_runtime_dependencies()
    copy_application_source()
    remove_unneeded_runtime_files()
    validate_package_contents()

    uncompressed_size = package_uncompressed_size()

    validate_lambda_size_limit(
        uncompressed_size,
    )

    write_deterministic_zip()

    compressed_size = ARTIFACT_PATH.stat().st_size
    requires_s3_upload = compressed_size > LAMBDA_DIRECT_UPLOAD_LIMIT_BYTES

    print(f"artifact={ARTIFACT_PATH}")
    print(f"sha256={artifact_sha256()}")
    print(f"files={package_file_count()}")
    print(f"compressed_bytes={compressed_size}")
    print(f"uncompressed_bytes={uncompressed_size}")
    print(f"compressed_mib={compressed_size / MEBIBYTE:.2f}")
    print(f"uncompressed_mib={uncompressed_size / MEBIBYTE:.2f}")
    print(f"unzipped_limit_percent={uncompressed_size / LAMBDA_UNZIPPED_LIMIT_BYTES * 100:.2f}")
    print(f"requires_s3_upload={str(requires_s3_upload).lower()}")


if __name__ == "__main__":
    main()
