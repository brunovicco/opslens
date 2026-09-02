"""Tests for bridging parsed `uv.lock` PyPI records to Phase 3 identity semantics."""

from __future__ import annotations

from pathlib import Path

import pytest

from opslens.repository_intelligence.application import (
    normalize_uv_lock_pypi_dependencies,
)
from opslens.repository_intelligence.domain import (
    GitHubRepositoryIdentity,
    ImmutableRepositoryFileEvidence,
    ImmutableRepositorySnapshot,
    InvalidUvLockError,
    NormalizedRepositoryPyPIDependencyEvidence,
    RepositoryPyPINormalizationInventory,
    UnsupportedRepositoryPyPINormalizationEvidence,
    compute_content_sha256,
    compute_git_blob_sha1,
)
from opslens.repository_intelligence.parsers.uv_lock import parse_uv_lock_evidence

_REPOSITORY_ID = 1_333_092_779
_COMMIT_SHA = "90e860e7231a327c3358867a9248f2c4678d1687"
_TREE_SHA = "a" * 40


def _snapshot() -> ImmutableRepositorySnapshot:
    """Build one exact repository snapshot for deterministic bridge fixtures."""
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
    """Wrap fixture bytes in the immutable file evidence contract."""
    return ImmutableRepositoryFileEvidence(
        snapshot=_snapshot(),
        path="uv.lock",
        blob_sha=compute_git_blob_sha1(content),
        size_bytes=len(content),
        content_sha256=compute_content_sha256(content),
        content_bytes=content,
    )


def _lock_bytes(package_records: str) -> bytes:
    """Build one supported schema-v1 lockfile fixture."""
    return (
        "version = 1\n"
        "revision = 3\n"
        'requires-python = ">=3.13"\n'
        f"{package_records}"
    ).encode()


def _pypi_package(
    name: str,
    version: str,
    *,
    markers: str = "",
) -> str:
    """Build one canonical-PyPI source package record."""
    marker_line = f"resolution-markers = [{markers}]\n" if markers else ""
    return (
        "[[package]]\n"
        f'name = "{name}"\n'
        f'version = "{version}"\n'
        'source = { registry = "https://pypi.org/simple" }\n'
        f"{marker_line}"
    )


def _normalize(content: bytes) -> RepositoryPyPINormalizationInventory:
    """Parse inert lock bytes then apply the Phase 3 normalization bridge."""
    parsed = parse_uv_lock_evidence(_file_evidence(content))
    return normalize_uv_lock_pypi_dependencies(parsed)


def test_bridge_uses_phase3_name_version_and_purl_semantics() -> None:
    """Apply PyPA name normalization and PEP 440 canonicalization exactly once."""
    inventory = _normalize(_lock_bytes(_pypi_package("Friendly_Bard", "1.0RC1")))

    assert inventory.pypi_source_record_count == 1
    assert inventory.unsupported_normalization == ()
    dependency = inventory.normalized_dependencies[0]
    assert dependency.record_index == 0
    assert dependency.source_record.name_original == "Friendly_Bard"
    assert dependency.package.canonical == "friendly-bard"
    assert dependency.source_record.version_original == "1.0RC1"
    assert dependency.version.canonical == "1.0rc1"
    assert dependency.purl == "pkg:pypi/friendly-bard@1.0rc1"


def test_bridge_preserves_phase3_purl_encoding_for_local_and_epoch_versions() -> None:
    """Keep canonical purl encoding under the Phase 3 implementation authority."""
    inventory = _normalize(
        _lock_bytes(
            _pypi_package("local_pkg", "1.0+cpu")
            + _pypi_package("epoch-pkg", "1!2.0")
        )
    )

    assert [item.purl for item in inventory.normalized_dependencies] == [
        "pkg:pypi/local-pkg@1.0%2Bcpu",
        "pkg:pypi/epoch-pkg@1%212.0",
    ]


@pytest.mark.parametrize(
    ("name", "version", "reason_code"),
    [
        ("bad/name", "1.0", "invalid_package_name"),
        ("valid-name", "not a version", "invalid_version"),
    ],
)
def test_phase3_identity_failures_become_record_level_unsupported_evidence(
    name: str,
    version: str,
    reason_code: str,
) -> None:
    """Never correlate a PyPI-source record whose canonical identity cannot be proven."""
    inventory = _normalize(_lock_bytes(_pypi_package(name, version)))

    assert inventory.normalized_dependencies == ()
    assert len(inventory.unsupported_normalization) == 1
    unsupported = inventory.unsupported_normalization[0]
    assert unsupported.record_index == 0
    assert unsupported.reason_code == reason_code
    assert unsupported.source_record.name_original == name
    assert unsupported.source_record.version_original == version


def test_one_invalid_pypi_record_does_not_hide_independent_valid_records() -> None:
    """Fail closed per record while retaining deterministic evidence for other records."""
    inventory = _normalize(
        _lock_bytes(
            _pypi_package("requests", "2.32.0")
            + _pypi_package("bad/name", "1.0")
            + _pypi_package("packaging", "26.3")
        )
    )

    assert [item.record_index for item in inventory.normalized_dependencies] == [0, 2]
    assert [item.record_index for item in inventory.unsupported_normalization] == [1]
    assert inventory.pypi_source_record_count == 3


def test_source_unsupported_records_never_enter_phase3_pypi_bridge() -> None:
    """Keep local/private source classification distinct from PyPI identity failures."""
    content = _lock_bytes(
        _pypi_package("packaging", "26.3")
        + "[[package]]\n"
        'name = "opslens"\n'
        'version = "0.1.0"\n'
        'source = { virtual = "." }\n'
        + "[[package]]\n"
        'name = "private-lib"\n'
        'version = "1.0"\n'
        'source = { registry = "https://packages.example.com/simple" }\n'
    )
    parsed = parse_uv_lock_evidence(_file_evidence(content))

    inventory = normalize_uv_lock_pypi_dependencies(parsed)

    assert inventory.pypi_source_record_count == 1
    assert [item.record_index for item in inventory.normalized_dependencies] == [0]
    assert inventory.unsupported_normalization == ()
    assert [item.record_index for item in parsed.unsupported_packages] == [1, 2]


def test_duplicate_canonical_identity_records_preserve_index_and_markers() -> None:
    """Do not collapse universal-lock marker forks after canonical normalization."""
    inventory = _normalize(
        _lock_bytes(
            _pypi_package("Example_Pkg", "1.0", markers='"sys_platform == \'linux\'"')
            + _pypi_package(
                "example-pkg",
                "1.0.0",
                markers='"sys_platform == \'darwin\'"',
            )
        )
    )

    first, second = inventory.normalized_dependencies
    assert first.package.canonical == second.package.canonical == "example-pkg"
    assert first.version.canonical == second.version.canonical == "1.0"
    assert first.record_index == 0
    assert second.record_index == 1
    assert first.resolution_markers != second.resolution_markers


def test_normalized_dependency_retains_snapshot_and_file_provenance() -> None:
    """Carry exact repository and file evidence identity into canonical dependency evidence."""
    inventory = _normalize(_lock_bytes(_pypi_package("packaging", "26.3")))

    dependency = inventory.normalized_dependencies[0]
    file_evidence = inventory.parsed_lock.file_evidence
    assert dependency.snapshot_id == file_evidence.snapshot.snapshot_id
    assert dependency.file_evidence_id == file_evidence.evidence_id


def test_inventory_rejects_duplicate_accounting_of_one_pypi_source_record() -> None:
    """Enforce exactly-once bridge accounting rather than silently double counting."""
    inventory = _normalize(_lock_bytes(_pypi_package("packaging", "26.3")))
    dependency = inventory.normalized_dependencies[0]

    with pytest.raises(InvalidUvLockError):
        RepositoryPyPINormalizationInventory(
            parsed_lock=inventory.parsed_lock,
            normalized_dependencies=(dependency, dependency),
            unsupported_normalization=(),
        )


def test_inventory_rejects_missing_pypi_source_record() -> None:
    """Prevent silent coverage loss when a source record disappears from bridge output."""
    inventory = _normalize(_lock_bytes(_pypi_package("packaging", "26.3")))

    with pytest.raises(InvalidUvLockError):
        RepositoryPyPINormalizationInventory(
            parsed_lock=inventory.parsed_lock,
            normalized_dependencies=(),
            unsupported_normalization=(),
        )


def test_normalized_model_rejects_purl_not_built_from_phase3_identity() -> None:
    """Keep the canonical purl linked to the exact Phase 3 package/version objects."""
    inventory = _normalize(_lock_bytes(_pypi_package("packaging", "26.3")))
    dependency = inventory.normalized_dependencies[0]

    with pytest.raises(InvalidUvLockError):
        NormalizedRepositoryPyPIDependencyEvidence(
            source_record=dependency.source_record,
            package=dependency.package,
            version=dependency.version,
            purl="pkg:pypi/other@1.0",
            snapshot_id=dependency.snapshot_id,
            file_evidence_id=dependency.file_evidence_id,
        )


def test_unsupported_model_requires_explicit_reason_code() -> None:
    """Do not allow fail-closed records to lose their normalization failure reason."""
    inventory = _normalize(_lock_bytes(_pypi_package("bad/name", "1.0")))
    source_record = inventory.unsupported_normalization[0].source_record

    with pytest.raises(InvalidUvLockError):
        UnsupportedRepositoryPyPINormalizationEvidence(
            source_record=source_record,
            reason_code="",
        )


def test_current_repository_lock_normalizes_pypi_records_without_uv_execution() -> None:
    """Normalize the checked-in lockfile as inert evidence using existing Phase 3 rules."""
    parsed = parse_uv_lock_evidence(_file_evidence(Path("uv.lock").read_bytes()))

    inventory = normalize_uv_lock_pypi_dependencies(parsed)

    assert inventory.pypi_source_record_count > 1
    assert inventory.unsupported_normalization == ()
    packaging_records = [
        item for item in inventory.normalized_dependencies if item.package.canonical == "packaging"
    ]
    assert packaging_records
    assert all(item.purl.startswith("pkg:pypi/packaging@") for item in packaging_records)
    assert any(item.name_original == "opslens" for item in parsed.unsupported_packages)
