"""Build deterministic deployment package for the historical EPSS transformer Lambda."""

import hashlib
import shutil
import stat
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = PROJECT_ROOT / "build" / "lambda" / "epss-history-transformer"
PACKAGE_DIR = BUILD_DIR / "package"
REQUIREMENTS_FILE = BUILD_DIR / "requirements.txt"
DIST_DIR = PROJECT_ROOT / "dist"
ARTIFACT_PATH = DIST_DIR / "opslens-epss-history-transformer.zip"
PYTHON_VERSION = "3.13"
PYTHON_PLATFORM = "x86_64-manylinux_2_28"
RUNTIME_DEPENDENCY_GROUP = "epss-silver-runtime"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
MEBIBYTE = 1024 * 1024
LAMBDA_UNZIPPED_LIMIT_BYTES = 250 * MEBIBYTE

SOURCE_MANIFEST = (
    (PROJECT_ROOT / "src" / "opslens" / "__init__.py", Path("opslens/__init__.py")),
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
    Path("opslens/transformation/epss/history/lambda_handler.py"),
    Path("opslens/transformation/epss/history/composition.py"),
    Path("opslens/transformation/epss/history/invocation.py"),
    Path("opslens/transformation/epss/history/reader.py"),
    Path("opslens/transformation/epss/history/preparation.py"),
    Path("opslens/transformation/epss/history/persistence.py"),
    Path("opslens/transformation/epss/history/completion.py"),
    Path("opslens/transformation/epss/adapters/outbound/parquet.py"),
    Path("opslens/transformation/epss/adapters/outbound/s3_history_exact_object.py"),
    Path("opslens/ingestion/epss/domain/history.py"),
    Path("opslens/shared/observability/powertools.py"),
    Path("pyarrow/__init__.py"),
)


def run_command(command: list[str]) -> None:
    """Run one build command and fail on non-zero exit."""
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def prepare_directories() -> None:
    """Create clean deterministic staging directories."""
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    BUILD_DIR.mkdir(parents=True)
    PACKAGE_DIR.mkdir()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.unlink(missing_ok=True)


def export_runtime_dependencies() -> None:
    """Export locked PyArrow runtime dependencies."""
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
    """Install Linux-compatible dependencies into staging."""
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
    """Copy only source required by the historical transformer runtime."""
    for source, relative_destination in SOURCE_MANIFEST:
        if not source.exists():
            raise FileNotFoundError(f"Historical transformer source entry is missing: {source}")
        destination = PACKAGE_DIR / relative_destination
        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def remove_generated_bytecode() -> None:
    """Remove generated Python bytecode from deterministic staging."""
    for path in PACKAGE_DIR.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path)
    for pattern in ("*.pyc", "*.pyo"):
        for path in PACKAGE_DIR.rglob(pattern):
            path.unlink()


def validate_package_contents() -> None:
    """Require the dedicated historical runtime surface to be packaged."""
    missing = [path for path in REQUIRED_PACKAGE_FILES if not (PACKAGE_DIR / path).is_file()]
    if missing:
        formatted = ", ".join(path.as_posix() for path in missing)
        raise RuntimeError(f"Historical transformer package is missing required files: {formatted}")


def normalized_permissions(path: Path) -> int:
    """Return deterministic POSIX permissions for one packaged file."""
    return 0o755 if path.stat().st_mode & stat.S_IXUSR else 0o644


def write_deterministic_zip() -> None:
    """Create ZIP bytes with stable ordering, timestamps, and permissions."""
    files = sorted(path for path in PACKAGE_DIR.rglob("*") if path.is_file())
    with ZipFile(
        ARTIFACT_PATH,
        mode="w",
        compression=ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            info = ZipInfo(
                filename=path.relative_to(PACKAGE_DIR).as_posix(),
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
    """Return exact SHA-256 of the generated deployment ZIP."""
    digest = hashlib.sha256()
    with ARTIFACT_PATH.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(MEBIBYTE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_uncompressed_size() -> int:
    """Return total staged uncompressed bytes."""
    return sum(path.stat().st_size for path in PACKAGE_DIR.rglob("*") if path.is_file())


def package_file_count() -> int:
    """Return number of staged files."""
    return sum(1 for path in PACKAGE_DIR.rglob("*") if path.is_file())


def main() -> None:
    """Build and report the deterministic historical transformer artifact."""
    prepare_directories()
    export_runtime_dependencies()
    install_runtime_dependencies()
    copy_application_source()
    remove_generated_bytecode()
    validate_package_contents()

    uncompressed_size = package_uncompressed_size()
    if uncompressed_size > LAMBDA_UNZIPPED_LIMIT_BYTES:
        raise RuntimeError(
            "Historical transformer package exceeds Lambda 250 MiB uncompressed limit: "
            f"{uncompressed_size} bytes."
        )

    write_deterministic_zip()
    print(f"artifact={ARTIFACT_PATH}")
    print(f"sha256={artifact_sha256()}")
    print(f"files={package_file_count()}")
    print(f"compressed_bytes={ARTIFACT_PATH.stat().st_size}")
    print(f"uncompressed_bytes={uncompressed_size}")


if __name__ == "__main__":
    main()
