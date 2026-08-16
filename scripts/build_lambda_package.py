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

SOURCE_ROOT = PROJECT_ROOT / "src" / "opslens"

RUNTIME_SOURCE_PATHS = (
    Path("__init__.py"),
    Path("ingestion/__init__.py"),
    Path("ingestion/epss"),
    Path("shared/__init__.py"),
    Path("shared/observability"),
)

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
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    BUILD_DIR.mkdir(parents=True)


def remove_unneeded_runtime_scripts() -> None:
    """Remove dependency CLI scripts that are not required by Lambda."""
    scripts_dir = PACKAGE_DIR / "bin"

    if scripts_dir.exists():
        shutil.rmtree(scripts_dir)


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
    """Copy only EPSS ingestion runtime source into the Lambda package."""
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
    remove_unneeded_runtime_scripts()
    copy_application_source()
    write_deterministic_zip()

    print(f"artifact={ARTIFACT_PATH}")
    print(f"sha256={artifact_sha256()}")
    print(f"bytes={ARTIFACT_PATH.stat().st_size}")


if __name__ == "__main__":
    main()
