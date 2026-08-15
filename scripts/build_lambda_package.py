"""Build the deterministic AWS Lambda deployment package for EPSS ingestion."""

import hashlib
import shutil
import stat
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BUILD_DIR = PROJECT_ROOT / "build" / "lambda" / "epss-ingestion"
PACKAGE_DIR = BUILD_DIR / "package"
REQUIREMENTS_FILE = BUILD_DIR / "requirements.txt"

DIST_DIR = PROJECT_ROOT / "dist"
ARTIFACT_PATH = DIST_DIR / "opslens-epss-ingestion.zip"

SOURCE_PACKAGE = PROJECT_ROOT / "src" / "opslens"

PYTHON_VERSION = "3.13"
PYTHON_PLATFORM = "x86_64-manylinux2014"

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


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
    shutil.rmtree(BUILD_DIR, ignore_errors=True)

    BUILD_DIR.mkdir(parents=True)
    PACKAGE_DIR.mkdir()
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    ARTIFACT_PATH.unlink(missing_ok=True)


def export_runtime_dependencies() -> None:
    """Export locked production dependencies from the uv lockfile."""
    run_command(
        [
            "uv",
            "export",
            "--locked",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements.txt",
            "--output-file",
            str(REQUIREMENTS_FILE),
        ]
    )


def install_runtime_dependencies() -> None:
    """Install Linux-compatible runtime dependencies into the staging directory."""
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
    """Copy the OpsLens application package into the Lambda staging directory."""
    destination = PACKAGE_DIR / "opslens"

    shutil.copytree(
        SOURCE_PACKAGE,
        destination,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            "*.pyo",
        ),
    )


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
    """Create the Lambda ZIP with stable ordering, timestamps, and permissions."""
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
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main() -> None:
    """Build and report the EPSS ingestion Lambda deployment artifact."""
    prepare_directories()
    export_runtime_dependencies()
    install_runtime_dependencies()
    copy_application_source()
    write_deterministic_zip()

    print(f"artifact={ARTIFACT_PATH}")
    print(f"sha256={artifact_sha256()}")
    print(f"bytes={ARTIFACT_PATH.stat().st_size}")


if __name__ == "__main__":
    main()
