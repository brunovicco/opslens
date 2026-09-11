# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Tests for exact GHSA Silver authority decoding."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from opslens.public_analysis.adapters.exact_s3_authority_object import (
    ExactS3AuthorityObject,
)
from opslens.public_analysis.adapters.ghsa_authority import (
    ExactGhsaSilverAuthorityReader,
    GhsaAuthorityDecodeError,
)
from opslens.transformation.ghsa.serialization.schema import (
    GHSA_ADVISORY_VERSIONS_SCHEMA_V1,
)

_GHSA_ID = "GHSA-6hx8-3wjj-gr8g"
_CVE_ID = "CVE-2026-54770"
_SOURCE_SHA = "a" * 64
_ENTRY_SHA = "b" * 64
_OBSERVED_ID = f"{_GHSA_ID}@sha256:{_SOURCE_SHA}"


def _row(*, ecosystem: str = "pip", cve_id: str = _CVE_ID) -> dict[str, object]:
    timestamp = datetime(2026, 9, 10, tzinfo=UTC)
    return {
        "schema_version": 1,
        "ghsa_id": _GHSA_ID,
        "observed_advisory_version_id": _OBSERVED_ID,
        "source_advisory_sha256": _SOURCE_SHA,
        "cve_id": cve_id,
        "advisory_type": "reviewed",
        "severity": "high",
        "url": "https://api.github.com/advisories/GHSA-6hx8-3wjj-gr8g",
        "html_url": "https://github.com/advisories/GHSA-6hx8-3wjj-gr8g",
        "repository_advisory_url": None,
        "source_code_location": None,
        "summary": "Representative WebOb advisory",
        "description": "First-party deterministic test fixture.",
        "published_at": timestamp,
        "updated_at": timestamp,
        "github_reviewed_at": timestamp,
        "nvd_published_at": timestamp,
        "withdrawn_at": None,
        "is_withdrawn": False,
        "identifiers": [
            {"type": "GHSA", "value": _GHSA_ID},
            {"type": "CVE", "value": _CVE_ID},
        ],
        "references": [],
        "cwes": [],
        "cvss_metrics": [],
        "cvss_severities_json": "{}",
        "vulnerability_entry_count": 1,
        "vulnerabilities": [
            {
                "source_index": 0,
                "vulnerability_entry_id": "ghsa-entry-0",
                "source_entry_sha256": _ENTRY_SHA,
                "ecosystem": ecosystem,
                "package_name": "webob",
                "vulnerable_version_range": "< 1.8.11",
                "first_patched_version": "1.8.11",
                "vulnerable_functions": [],
                "source_entry_json": "{}",
            }
        ],
    }


def _parquet(*rows: dict[str, object], schema: pa.Schema = GHSA_ADVISORY_VERSIONS_SCHEMA_V1) -> bytes:
    table = pa.Table.from_pylist(list(rows), schema=schema)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink)
    return sink.getvalue().to_pybytes()


@dataclass
class _FakeObjectReader:
    payload: bytes
    calls: int = 0

    def read(self, *, object_key: str, version_id: str) -> ExactS3AuthorityObject:
        self.calls += 1
        return ExactS3AuthorityObject(
            object_key=object_key,
            version_id=version_id,
            payload=self.payload,
        )


def _read(payload: bytes):
    object_reader = _FakeObjectReader(payload)
    reader = ExactGhsaSilverAuthorityReader(object_reader)
    result = reader.read(
        object_key="analytics/ghsa/advisory.parquet",
        version_id="version-1",
        cve_id=_CVE_ID,
        observed_advisory_version_id=_OBSERVED_ID,
        source_index=0,
    )
    return result, object_reader


def test_exact_ghsa_reader_projects_one_pypi_occurrence() -> None:
    result, object_reader = _read(_parquet(_row()))

    assert object_reader.calls == 1
    assert result.ghsa_id == _GHSA_ID
    assert result.github_cve_id == _CVE_ID
    assert result.observed_advisory_version_id == _OBSERVED_ID
    assert result.source_advisory_sha256 == _SOURCE_SHA
    assert result.source_index == 0
    assert result.source_entry_sha256 == _ENTRY_SHA
    assert result.ecosystem_original == "pip"
    assert result.package_name_original == "webob"
    assert result.vulnerable_range_original == "< 1.8.11"
    assert result.first_patched_version_original == "1.8.11"
    assert tuple((item.identifier_type, item.value) for item in result.github_identifiers) == (
        ("GHSA", _GHSA_ID),
        ("CVE", _CVE_ID),
    )


def test_exact_ghsa_reader_rejects_duplicate_observed_rows() -> None:
    with pytest.raises(GhsaAuthorityDecodeError, match="exactly one Silver row"):
        _read(_parquet(_row(), _row()))


def test_exact_ghsa_reader_rejects_cve_drift() -> None:
    with pytest.raises(GhsaAuthorityDecodeError, match="CVE identity mismatch"):
        _read(_parquet(_row(cve_id="CVE-2026-55558")))


def test_exact_ghsa_reader_rejects_non_pip_occurrence() -> None:
    with pytest.raises(GhsaAuthorityDecodeError, match="requires pip ecosystem"):
        _read(_parquet(_row(ecosystem="npm")))


def test_exact_ghsa_reader_rejects_missing_source_index() -> None:
    object_reader = _FakeObjectReader(_parquet(_row()))
    reader = ExactGhsaSilverAuthorityReader(object_reader)

    with pytest.raises(GhsaAuthorityDecodeError, match="source_index"):
        reader.read(
            object_key="analytics/ghsa/advisory.parquet",
            version_id="version-1",
            cve_id=_CVE_ID,
            observed_advisory_version_id=_OBSERVED_ID,
            source_index=1,
        )


def test_exact_ghsa_reader_rejects_wrong_schema() -> None:
    wrong_schema = pa.schema([pa.field("value", pa.string(), nullable=False)])
    payload = _parquet({"value": "not-ghsa"}, schema=wrong_schema)

    with pytest.raises(GhsaAuthorityDecodeError, match="schema is not Silver v1"):
        _read(payload)
