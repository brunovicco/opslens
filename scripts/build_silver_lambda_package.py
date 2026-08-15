"""Build the deterministic AWS Lambda deployment package for EPSS Silver."""

import hashlib
import shutil
import stat
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BUILD_DIR = PROJECT_ROOT / "build" / "lambda" / "epss-silver"
PACKAGE_DIR = BUILD_DIR / "package"
REQUIREMENTS_FILE = BUILD_DIR / "requirements.txt"

DIST_DIR = PROJECT_ROOT / "dist"
ARTIFACT_PATH = DIST_DIR / "opslens-epss-silver.zip"

PYTHON_VERSION = "3.13"
PYTHON_PLATFORM = "x86_64-manylinux_2_28"
RUNTIME_DEPENDENCY_GROUP = "epss-silver-runtime"

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
        PROJECT_ROOT / "src" / "opslens" / "ingestion" / "epss" / "__init__.py",
        Path("opslens/ingestion/epss/__init__.py"),
    ),
    (
        PROJECT_ROOT / "src" / "opslens" / "ingestion" / "epss" / "domain",
        Path("opslens/ingestion/epss/domain"),
    ),
    (
        PROJECT_ROOT / "src" / "opslens" / "transformation" / "__init__.py",
        Path("opslens/transformation/__init__.py"),
    ),
    (
        PROJECT_ROOT / "src" / "opslens" / "transformation" / "epss",
        Path("opslens/transformation/epss"),
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
    Path("opslens/transformation/epss/lambda_handler.py"),
    Path("opslens/transformation/epss/composition.py"),
    Path("opslens/transformation/epss/application/service.py"),
    Path("opslens/transformation/epss/adapters/outbound/parquet.py"),
    Path("opslens/ingestion/epss/domain/parser.py"),
    Path("opslens/shared/observability/powertools.py"),
    Path("pyarrow/__init__.py"),
)

FORBIDDEN_PACKAGE_FILES = (
    Path("opslens/ingestion/epss/lambda_handler.py"),
    Path("opslens/ingestion/epss/composition.py"),
)


def run_command(command: list[str]) -> None:
    """Run a build command and fail immediately on non-zero exit.

    Args:
        command: Command and arguments to execute.
    """
    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
    )


def prepare_directories() -> None:
    """Create clean build and distribution directories."""
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
    """Export locked Silver runtime dependencies from the uv lockfile."""
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
    """Install Linux-compatible Silver dependencies into staging."""
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
    """Copy only source required by the Silver Lambda runtime."""
    for source, relative_destination in SOURCE_MANIFEST:
        if not source.exists():
            raise FileNotFoundError(f"Silver Lambda source manifest entry does not exist: {source}")

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


def remove_generated_bytecode() -> None:
    """Remove generated Python bytecode from the staging directory."""
    for path in PACKAGE_DIR.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path)

    for pattern in ("*.pyc", "*.pyo"):
        for path in PACKAGE_DIR.rglob(pattern):
            path.unlink()


def validate_package_contents() -> None:
    """Validate required and forbidden Silver package contents."""
    missing = [path for path in REQUIRED_PACKAGE_FILES if not (PACKAGE_DIR / path).is_file()]

    if missing:
        formatted = ", ".join(path.as_posix() for path in missing)
        raise RuntimeError(f"Silver Lambda package is missing required files: {formatted}")

    forbidden = [path for path in FORBIDDEN_PACKAGE_FILES if (PACKAGE_DIR / path).exists()]

    if forbidden:
        formatted = ", ".join(path.as_posix() for path in forbidden)
        raise RuntimeError(f"Silver Lambda package contains forbidden files: {formatted}")


def normalized_permissions(path: Path) -> int:
    """Return deterministic POSIX permissions for a packaged file.

    Args:
        path: File whose executable bit should be inspected.

    Returns:
        Normalized POSIX file mode.
    """
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

            permissions = normalized_permissions(path)
            info.external_attr = permissions << 16

            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=ZIP_DEFLATED,
                compresslevel=9,
            )


def artifact_sha256() -> str:
    """Calculate the SHA-256 digest of the generated deployment artifact.

    Returns:
        Lowercase hexadecimal SHA-256 digest.
    """
    digest = hashlib.sha256()

    with ARTIFACT_PATH.open("rb") as artifact:
        for chunk in iter(
            lambda: artifact.read(MEBIBYTE),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def package_uncompressed_size() -> int:
    """Return the total uncompressed size of staged package files."""
    return sum(path.stat().st_size for path in PACKAGE_DIR.rglob("*") if path.is_file())


def package_file_count() -> int:
    """Return the number of files staged in the deployment package."""
    return sum(1 for path in PACKAGE_DIR.rglob("*") if path.is_file())


def validate_lambda_size_limit(
    uncompressed_size: int,
) -> None:
    """Reject packages exceeding the Lambda uncompressed ZIP limit.

    Args:
        uncompressed_size: Total staged package size in bytes.
    """
    if uncompressed_size > LAMBDA_UNZIPPED_LIMIT_BYTES:
        raise RuntimeError(
            "Silver Lambda package exceeds the 250 MiB "
            f"uncompressed limit: {uncompressed_size} bytes."
        )


def main() -> None:
    """Build and report the EPSS Silver Lambda deployment artifact."""
    prepare_directories()
    export_runtime_dependencies()
    install_runtime_dependencies()
    copy_application_source()
    remove_generated_bytecode()
    validate_package_contents()

    uncompressed_size = package_uncompressed_size()
    validate_lambda_size_limit(uncompressed_size)

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
