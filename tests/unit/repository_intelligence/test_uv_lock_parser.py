"""Tests for deterministic parsing of integrity-verified inert `uv.lock` evidence."""

from __future__ import annotations

from pathlib import Path

import pytest

from opslens.repository_intelligence.domain import (
    MAX_UV_LOCK_PACKAGE_RECORDS,
    PYPI_SIMPLE_REGISTRY_URL,
    GitHubRepositoryIdentity,
    ImmutableRepositoryFileEvidence,
    ImmutableRepositorySnapshot,
    InvalidUvLockError,
    UnsupportedUvLockSchemaError,
    UvUnsupportedPackageReason,
    compute_content_sha256,
    compute_git_blob_sha1,
)
from opslens.repository_intelligence.parsers.uv_lock import parse_uv_lock_evidence

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "eaf510b11db540bbe47ea19b888b7f9edf1259c0"
_TREE_SHA = "774b14953ef300d88c82e9abd38265fa0134c465"


def _snapshot() -> ImmutableRepositorySnapshot:
    """Build one exact public OpsLens snapshot for parser evidence fixtures."""
    return ImmutableRepositorySnapshot(
        repository=GitHubRepositoryIdentity(
            repository_id=_REPOSITORY_ID,
            owner="brunovicco",
            name="opslens",
            full_name="brunovicco/opslens",
            is_private=False,
        ),
        requested_ref="main",
        commit_sha=_COMMIT_SHA,
        tree_sha=_TREE_SHA,
    )


def _file_evidence(content: bytes) -> ImmutableRepositoryFileEvidence:
    """Wrap inert fixture bytes in the same integrity contract used by acquisition."""
    return ImmutableRepositoryFileEvidence(
        snapshot=_snapshot(),
        path="uv.lock",
        blob_sha=compute_git_blob_sha1(content),
        size_bytes=len(content),
        content_sha256=compute_content_sha256(content),
        content_bytes=content,
    )


def _lock_bytes(
    package_records: str,
    *,
    version: str = "1",
    revision_line: str = "revision = 3\n",
    extra_header: str = "",
) -> bytes:
    """Build a small deterministic uv.lock TOML fixture."""
    return (
        f"version = {version}\n"
        f"{revision_line}"
        'requires-python = ">=3.13, <3.15"\n'
        f"{extra_header}"
        f"{package_records}"
    ).encode()


def _pypi_package(
    name: str = "packaging",
    version: str = "26.3",
    *,
    registry: str = PYPI_SIMPLE_REGISTRY_URL,
    markers: str = "",
) -> str:
    """Build one registry-backed package record."""
    marker_line = f"resolution-markers = [{markers}]\n" if markers else ""
    return (
        "[[package]]\n"
        f'name = "{name}"\n'
        f'version = "{version}"\n'
        f'source = {{ registry = "{registry}" }}\n'
        f"{marker_line}"
    )


def test_parser_emits_pypi_and_explicit_unsupported_inventory() -> None:
    """Keep supported and unsupported source evidence visible in one bounded result."""
    content = _lock_bytes(
        _pypi_package()
        + "[[package]]\n"
        'name = "opslens"\n'
        'version = "0.1.0"\n'
        'source = { virtual = "." }\n'
        + "[[package]]\n"
        'name = "internal-lib"\n'
        'version = "2.0.0"\n'
        'source = { registry = "https://packages.example.com/simple" }\n'
        + "[[package]]\n"
        'name = "git-lib"\n'
        'version = "1.0.0"\n'
        'source = { git = "https://github.com/example/git-lib.git#abc" }\n'
    )

    parsed = parse_uv_lock_evidence(_file_evidence(content))

    assert parsed.schema_version == 1
    assert parsed.revision == 3
    assert parsed.requires_python == ">=3.13, <3.15"
    assert parsed.package_count == 4
    assert len(parsed.pypi_packages) == 1
    assert parsed.pypi_packages[0].record_index == 0
    assert parsed.pypi_packages[0].name_original == "packaging"
    assert parsed.pypi_packages[0].version_original == "26.3"

    assert [package.record_index for package in parsed.unsupported_packages] == [1, 2, 3]
    assert parsed.unsupported_packages[0].source_kind == "virtual"
    assert (
        parsed.unsupported_packages[0].reason_code
        == UvUnsupportedPackageReason.UNSUPPORTED_NON_REGISTRY_SOURCE
    )
    assert parsed.unsupported_packages[1].source_kind == "custom_registry"
    assert (
        parsed.unsupported_packages[1].reason_code
        == UvUnsupportedPackageReason.UNSUPPORTED_REGISTRY
    )
    assert parsed.unsupported_packages[2].source_kind == "git"


def test_parser_preserves_global_and_package_resolution_markers() -> None:
    """Preserve universal-lock marker context without evaluating runtime applicability."""
    content = _lock_bytes(
        _pypi_package(
            markers='"python_full_version < \'3.14\'", "sys_platform == \'linux\'"',
        ),
        extra_header=(
            "resolution-markers = [\n"
            '    "python_full_version < \'3.14\'",\n'
            '    "python_full_version >= \'3.14\'",\n'
            "]\n"
        ),
    )

    parsed = parse_uv_lock_evidence(_file_evidence(content))

    assert parsed.resolution_markers == (
        "python_full_version < '3.14'",
        "python_full_version >= '3.14'",
    )
    assert parsed.pypi_packages[0].resolution_markers == (
        "python_full_version < '3.14'",
        "sys_platform == 'linux'",
    )


@pytest.mark.parametrize("revision", [1, 2, 3])
def test_parser_accepts_known_revision_window(revision: int) -> None:
    """Accept only the explicitly reviewed backwards-compatible revision window."""
    content = _lock_bytes(_pypi_package(), revision_line=f"revision = {revision}\n")

    parsed = parse_uv_lock_evidence(_file_evidence(content))

    assert parsed.revision == revision


def test_parser_preserves_missing_revision_as_none() -> None:
    """Support historical schema-v1 lockfiles without inventing a revision value."""
    content = _lock_bytes(_pypi_package(), revision_line="")

    parsed = parse_uv_lock_evidence(_file_evidence(content))

    assert parsed.revision is None


@pytest.mark.parametrize("version", ["2", "0", "-1"])
def test_unsupported_schema_version_fails_closed(version: str) -> None:
    """Require explicit review before accepting a different uv.lock schema version."""
    content = _lock_bytes(_pypi_package(), version=version)

    with pytest.raises(UnsupportedUvLockSchemaError) as exc_info:
        parse_uv_lock_evidence(_file_evidence(content))

    assert exc_info.value.reason_code == "unsupported_uv_lock_schema"


def test_future_revision_fails_closed() -> None:
    """Require review before consuming unseen revision semantics."""
    content = _lock_bytes(_pypi_package(), revision_line="revision = 4\n")

    with pytest.raises(UnsupportedUvLockSchemaError):
        parse_uv_lock_evidence(_file_evidence(content))


@pytest.mark.parametrize(
    "header",
    [
        "version = true\nrevision = 3\n",
        "version = 1\nrevision = true\n",
        'version = "1"\nrevision = 3\n',
    ],
)
def test_boolean_and_non_integer_schema_fields_are_invalid(header: str) -> None:
    """Keep TOML booleans/strings from being accepted as integer schema evidence."""
    content = (header + _pypi_package()).encode()

    with pytest.raises(InvalidUvLockError):
        parse_uv_lock_evidence(_file_evidence(content))


def test_invalid_toml_fails_closed() -> None:
    """Reject malformed TOML after immutable file integrity has already been verified."""
    content = b"version = 1\n[[package]\n"

    with pytest.raises(InvalidUvLockError) as exc_info:
        parse_uv_lock_evidence(_file_evidence(content))

    assert exc_info.value.reason_code == "invalid_uv_lock"


def test_invalid_utf8_fails_closed() -> None:
    """Require deterministic UTF-8 TOML before structural parsing."""
    content = b"version = 1\n[[package]]\nname = \"x\"\n\xff"

    with pytest.raises(InvalidUvLockError):
        parse_uv_lock_evidence(_file_evidence(content))


@pytest.mark.parametrize(
    "content",
    [
        b"version = 1\nrevision = 3\n",
        b"version = 1\nrevision = 3\npackage = []\n",
        b'version = 1\nrevision = 3\npackage = "not-an-array"\n',
    ],
)
def test_missing_empty_or_non_array_package_inventory_fails(content: bytes) -> None:
    """Require at least one explicitly structured package record."""
    with pytest.raises(InvalidUvLockError):
        parse_uv_lock_evidence(_file_evidence(content))


def test_package_count_bound_fails_before_record_processing() -> None:
    """Apply an explicit logical-work bound independent of the 1 MiB file cap."""
    package = (
        "[[package]]\n"
        'name = "x"\n'
        'version = "1"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
    )
    content = _lock_bytes(package * (MAX_UV_LOCK_PACKAGE_RECORDS + 1))

    with pytest.raises(InvalidUvLockError):
        parse_uv_lock_evidence(_file_evidence(content))


@pytest.mark.parametrize(
    "package_records",
    [
        'package = ["not-a-table"]\n',
        '[[package]]\nversion = "1.0"\nsource = { registry = "https://pypi.org/simple" }\n',
        '[[package]]\nname = "x"\nsource = { registry = "https://pypi.org/simple" }\n',
        '[[package]]\nname = "x"\nversion = "1.0"\n',
        (
            '[[package]]\n'
            'name = " x"\n'
            'version = "1.0"\n'
            'source = { registry = "https://pypi.org/simple" }\n'
        ),
    ],
)
def test_malformed_package_records_fail_closed(package_records: str) -> None:
    """Reject incomplete or dirty package identities instead of guessing."""
    content = _lock_bytes(package_records)

    with pytest.raises(InvalidUvLockError):
        parse_uv_lock_evidence(_file_evidence(content))


def test_source_with_multiple_kinds_is_ambiguous_and_fails_closed() -> None:
    """Never guess authority when a source table carries competing source kinds."""
    content = _lock_bytes(
        "[[package]]\n"
        'name = "x"\n'
        'version = "1.0"\n'
        'source = { registry = "https://pypi.org/simple", git = "https://example/x" }\n'
    )

    with pytest.raises(InvalidUvLockError):
        parse_uv_lock_evidence(_file_evidence(content))


def test_pypi_url_with_different_spelling_is_not_silently_canonicalized() -> None:
    """Treat non-exact registry authority as unsupported."""
    content = _lock_bytes(_pypi_package(registry="https://pypi.org/simple/"))

    parsed = parse_uv_lock_evidence(_file_evidence(content))

    assert parsed.pypi_packages == ()
    assert parsed.unsupported_packages[0].source_kind == "custom_registry"
    assert (
        parsed.unsupported_packages[0].reason_code
        == UvUnsupportedPackageReason.UNSUPPORTED_REGISTRY
    )


@pytest.mark.parametrize(
    ("source", "expected_kind", "expected_reason"),
    [
        ('{ virtual = "." }', "virtual", "unsupported_non_registry_source"),
        ('{ editable = "." }', "editable", "unsupported_non_registry_source"),
        ('{ directory = "../lib" }', "path", "unsupported_non_registry_source"),
        (
            '{ git = "https://github.com/example/lib.git#abc" }',
            "git",
            "unsupported_non_registry_source",
        ),
        ('{ url = "https://example.com/lib.whl" }', "url", "unsupported_source_kind"),
    ],
)
def test_non_pypi_sources_remain_explicit_unsupported_evidence(
    source: str,
    expected_kind: str,
    expected_reason: str,
) -> None:
    """Keep valid non-PyPI source evidence visible without false package attribution."""
    content = _lock_bytes(
        "[[package]]\n"
        'name = "example"\n'
        'version = "1.0"\n'
        f"source = {source}\n"
    )

    parsed = parse_uv_lock_evidence(_file_evidence(content))

    assert parsed.pypi_packages == ()
    unsupported = parsed.unsupported_packages[0]
    assert unsupported.source_kind == expected_kind
    assert unsupported.reason_code.value == expected_reason


def test_duplicate_package_identity_records_are_preserved_by_index() -> None:
    """Do not collapse marker forks that happen to share package name and version."""
    content = _lock_bytes(
        _pypi_package("example", "1.0", markers='"sys_platform == \'linux\'"')
        + _pypi_package("example", "1.0", markers='"sys_platform == \'darwin\'"')
    )

    parsed = parse_uv_lock_evidence(_file_evidence(content))

    assert [package.record_index for package in parsed.pypi_packages] == [0, 1]
    assert [package.name_original for package in parsed.pypi_packages] == [
        "example",
        "example",
    ]
    assert parsed.pypi_packages[0].resolution_markers != parsed.pypi_packages[1].resolution_markers


def test_malformed_resolution_markers_fail_closed() -> None:
    """Preserve markers only when every marker is an explicit non-empty string."""
    content = _lock_bytes(
        _pypi_package(),
        extra_header='resolution-markers = ["", "python_version >= \'3.13\'"]\n',
    )

    with pytest.raises(InvalidUvLockError):
        parse_uv_lock_evidence(_file_evidence(content))


def test_current_repository_uv_lock_is_supported_without_executing_uv() -> None:
    """Parse the repository's checked-in lockfile as inert bytes using the frozen contract."""
    content = Path("uv.lock").read_bytes()

    parsed = parse_uv_lock_evidence(_file_evidence(content))

    assert parsed.schema_version == 1
    assert parsed.package_count > 1
    assert any(package.name_original == "packaging" for package in parsed.pypi_packages)
    assert any(package.name_original == "opslens" for package in parsed.unsupported_packages)
