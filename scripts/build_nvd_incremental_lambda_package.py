"""Build the deterministic AWS Lambda package for NVD incremental ingestion."""

import hashlib
import shutil
import stat
import subprocess
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BUILD_DIR = PROJECT_ROOT / "build" / "lambda" / "nvd-incremental"
PACKAGE_DIR = BUILD_DIR / "package"
REQUIREMENTS_FILE = BUILD_DIR / "requirements.txt"

DIST_DIR = PROJECT_ROOT / "dist"
ARTIFACT_PATH = DIST_DIR / "opslens-nvd-incremental.zip"

SOURCE_ROOT = PROJECT_ROOT / "src" / "opslens"

RUNTIME_SOURCE_PATHS = (
    Path("__init__.py"),
    Path("ingestion/__init__.py"),
    Path("ingestion/nvd"),
    Path("shared/__init__.py"),
    Path("shared/observability"),
)

REQUIRED_PACKAGE_FILES = (
    Path("opslens/ingestion/nvd/incremental_lambda_handler.py"),
    Path("opslens/ingestion/nvd/incremental_runtime_config.py"),
    Path("opslens/ingestion/nvd/incremental_runtime_composition.py"),
    Path(
        "opslens/ingestion/nvd/adapters/inbound/"
        "incremental_invocation.py"
    ),
    Path(
        "opslens/ingestion/nvd/adapters/outbound/"
        "s3_authoritative_watermark.py"
    ),
    Path(
        "opslens/ingestion/nvd/adapters/outbound/"
        "s3_incremental_bronze.py"
    ),
    Path("opslens/ingestion/nvd/adapters/outbound/nvd_cve_api.py"),
    Path(
        "opslens/ingestion/nvd/application/"
        "authoritative_watermark_store.py"
    ),
    Path(
        "opslens/ingestion/nvd/application/"
        "incremental_runtime_plan.py"
    ),
    Path(
        "opslens/ingestion/nvd/application/"
        "incremental_runtime_service.py"
    ),
    Path(
        "opslens/ingestion/nvd/application/"
        "incremental_service.py"
    ),
    Path("opslens/shared/observability/powertools.py"),
)

PYTHON_VERSION = "3.13"
PYTHON_PLATFORM = "x86_64-manylinux2014"

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

MEBIBYTE = 1024 * 1024
LAMBDA_DIRECT_UPLOAD_LIMIT_BYTES = 50 * MEBIBYTE


def run_command(command: list[str]) -> None:
    """Run one build command and fail immediately on non-zero exit."""
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
    """Export locked production dependencies from the uv lockfile."""
    run_command(
        [
            "uv",
            "export",
            "--locked",
            "--no-default-groups",
            "--no-emit-project",
            "--format",
            "requirements.txt",
            "--output-file",
            str(REQUIREMENTS_FILE),
        ]
    )


def install_runtime_dependencies() -> None:
    """Install Linux-compatible runtime dependencies into staging."""
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


def remove_unneeded_runtime_files() -> None:
    """Remove dependency files that cannot contribute to Lambda execution."""
    bin_dir = PACKAGE_DIR / "bin"

    if bin_dir.exists():
        shutil.rmtree(bin_dir)

    for path in PACKAGE_DIR.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path)

    for pattern in ("*.pyc", "*.pyo"):
        for path in PACKAGE_DIR.rglob(pattern):
            path.unlink()


def copy_application_source() -> None:
    """Copy NVD ingestion and observability runtime source."""
    destination_root = PACKAGE_DIR / "opslens"

    for relative_path in RUNTIME_SOURCE_PATHS:
        source = SOURCE_ROOT / relative_path
        destination = destination_root / relative_path

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

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

        shutil.copy2(
            source,
            destination,
        )


def validate_package_contents() -> None:
    """Require the files needed by incremental Lambda execution."""
    missing = [
        path
        for path in REQUIRED_PACKAGE_FILES
        if not (PACKAGE_DIR / path).is_file()
    ]

    if missing:
        formatted = ", ".join(
            path.as_posix()
            for path in missing
        )
        raise RuntimeError(
            "NVD incremental Lambda package is missing required files: "
            f"{formatted}"
        )


def normalized_permissions(path: Path) -> int:
    """Return deterministic POSIX permissions for one packaged file."""
    mode = path.stat().st_mode

    return 0o755 if mode & stat.S_IXUSR else 0o644


def write_deterministic_zip() -> None:
    """Create the Lambda ZIP with deterministic metadata."""
    files = sorted(
        path
        for path in PACKAGE_DIR.rglob("*")
        if path.is_file()
    )

    with ZipFile(
        ARTIFACT_PATH,
        mode="w",
        # DEFLATE output varies across zlib versions even when filenames,
        # contents, and ZIP metadata are identical. The uncompressed package
        # remains below Lambda's direct-upload limit, so storing entries makes
        # the deployment hash reproducible across local and CI environments.
        compression=ZIP_STORED,
    ) as archive:
        for path in files:
            relative_path = path.relative_to(
                PACKAGE_DIR
            ).as_posix()

            info = ZipInfo(
                filename=relative_path,
                date_time=ZIP_TIMESTAMP,
            )
            info.compress_type = ZIP_STORED
            info.create_system = 3
            info.external_attr = (
                normalized_permissions(path) << 16
            )

            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=ZIP_STORED,
            )


def artifact_sha256() -> str:
    """Return SHA-256 for the generated deployment artifact."""
    digest = hashlib.sha256()

    with ARTIFACT_PATH.open("rb") as artifact:
        for chunk in iter(
            lambda: artifact.read(MEBIBYTE),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def package_file_count() -> int:
    """Return the number of files in the staged runtime package."""
    return sum(
        1
        for path in PACKAGE_DIR.rglob("*")
        if path.is_file()
    )


def main() -> None:
    """Build and report the deterministic incremental Lambda package."""
    prepare_directories()
    export_runtime_dependencies()
    install_runtime_dependencies()
    remove_unneeded_runtime_files()
    copy_application_source()
    validate_package_contents()
    write_deterministic_zip()

    compressed_size = ARTIFACT_PATH.stat().st_size

    if compressed_size > LAMBDA_DIRECT_UPLOAD_LIMIT_BYTES:
        raise RuntimeError(
            "NVD incremental Lambda package exceeds the direct "
            f"50 MiB upload limit: {compressed_size} bytes."
        )

    print(f"artifact={ARTIFACT_PATH}")
    print(f"sha256={artifact_sha256()}")
    print(f"files={package_file_count()}")
    print(f"compressed_bytes={compressed_size}")
    print(f"compressed_mib={compressed_size / MEBIBYTE:.2f}")
    print("requires_s3_upload=false")


if __name__ == "__main__":
    main()
