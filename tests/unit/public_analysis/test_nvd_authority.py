# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false
"""Tests for exact NVD Silver-to-Bronze authority resolution."""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from opslens.public_analysis.adapters.exact_s3_authority_object import ExactS3AuthorityObject
from opslens.public_analysis.adapters.nvd_authority import (
    ExactNvdBronzeAuthorityReader,
    NvdAuthorityDecodeError,
)
from opslens.transformation.nvd.domain.models import ObservedCveVersion
from opslens.transformation.nvd.serialization.schema import NVD_CVE_VERSIONS_SCHEMA_V1

_CVE_ID = "CVE-2026-54770"
_SILVER_KEY = "analytics/nvd/cve.parquet"
_SILVER_VERSION = "silver-version-1"
_BRONZE_KEY = "bronze/nvd/cve/page.json"
_BRONZE_VERSION = "bronze-version-1"


def _source_cve(*, cve_id: str = _CVE_ID) -> dict[str, object]:
    """Build one deterministic original NVD CVE source object."""
    return {
        "id": cve_id,
        "sourceIdentifier": "security@example.test",
        "published": "2026-09-10T00:00:00.000Z",
        "lastModified": "2026-09-10T01:00:00.000Z",
        "vulnStatus": "Analyzed",
        "descriptions": [{"lang": "en", "value": "Deterministic test CVE."}],
    }


def _bronze_payload(source_cve: dict[str, object], *, bootstrap: bool = False) -> bytes:
    """Serialize one original Bronze wrapper using an optional bootstrap gzip envelope."""
    raw = json.dumps(
        {"vulnerabilities": [{"cve": source_cve}]},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return gzip.compress(raw, mtime=0) if bootstrap else raw


def _silver_row(
    source_cve: dict[str, object],
    bronze_payload: bytes,
    *,
    source_kind: str = "incremental",
    bronze_record_index: int = 0,
    bronze_sha256: str | None = None,
) -> dict[str, object]:
    """Build a complete NVD Silver v1 row carrying immutable Bronze lineage."""
    observed = ObservedCveVersion.from_source(source_cve)
    timestamp = datetime(2026, 9, 10, tzinfo=UTC)
    return {
        "schema_version": 1,
        "cve_id": observed.cve_id,
        "observed_cve_version_id": observed.observed_cve_version_id,
        "source_cve_sha256": observed.source_cve_sha256,
        "observation_id": "observation-1",
        "source_kind": source_kind,
        "source_batch_id": "batch-1",
        "source_observed_at": timestamp,
        "bronze_manifest_key": "bronze/nvd/manifest.json",
        "bronze_manifest_version_id": "manifest-version-1",
        "bronze_manifest_sha256": "c" * 64,
        "bronze_object_key": _BRONZE_KEY,
        "bronze_object_version_id": _BRONZE_VERSION,
        "bronze_object_sha256": bronze_sha256 or sha256(bronze_payload).hexdigest(),
        "bronze_record_index": bronze_record_index,
        "bootstrap_feed_year": 2026 if source_kind == "bootstrap" else None,
        "bootstrap_feed_revision": "1.1" if source_kind == "bootstrap" else None,
        "incremental_update_id": "update-1" if source_kind == "incremental" else None,
        "incremental_page_start": 0 if source_kind == "incremental" else None,
        "source_identifier": "security@example.test",
        "published_at": timestamp,
        "last_modified_at": timestamp,
        "vuln_status": "Analyzed",
        "is_rejected": False,
        "descriptions": [{"lang": "en", "value": "Deterministic test CVE."}],
        "cve_tags": [],
        "weaknesses": [],
        "cwe_ids": [],
        "references": [],
        "cvss_metrics": [],
        "configurations_json": "[]",
        "configuration_count": 0,
    }


def _parquet(*rows: dict[str, object]) -> bytes:
    """Serialize deterministic NVD Silver v1 rows for authority tests."""
    table = pa.Table.from_pylist(list(rows), schema=NVD_CVE_VERSIONS_SCHEMA_V1)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink)
    return sink.getvalue().to_pybytes()


def _call_log() -> list[tuple[str, str]]:
    """Create a typed exact-object call log."""
    return []


@dataclass
class _FakeObjectReader:
    """Return one exact object payload while recording immutable coordinates."""

    payload: bytes
    calls: list[tuple[str, str]] = field(default_factory=_call_log)

    def read(self, *, object_key: str, version_id: str) -> ExactS3AuthorityObject:
        """Return the configured payload under exactly the requested coordinates."""
        self.calls.append((object_key, version_id))
        return ExactS3AuthorityObject(
            object_key=object_key,
            version_id=version_id,
            payload=self.payload,
        )


def _reader(
    *,
    silver_payload: bytes,
    bronze_payload: bytes,
) -> tuple[ExactNvdBronzeAuthorityReader, _FakeObjectReader, _FakeObjectReader]:
    """Compose the concrete NVD reader from two offline exact-object readers."""
    silver_reader = _FakeObjectReader(silver_payload)
    bronze_reader = _FakeObjectReader(bronze_payload)
    return (
        ExactNvdBronzeAuthorityReader(
            silver_object_reader=silver_reader,
            bronze_object_reader=bronze_reader,
        ),
        silver_reader,
        bronze_reader,
    )


def _read(
    reader: ExactNvdBronzeAuthorityReader,
    *,
    source_cve: dict[str, object],
):
    """Read one requested observed version from the test authority reader."""
    observed = ObservedCveVersion.from_source(source_cve)
    return reader.read(
        object_key=_SILVER_KEY,
        version_id=_SILVER_VERSION,
        cve_id=observed.cve_id,
        observed_cve_version_id=observed.observed_cve_version_id,
    )


def test_exact_nvd_reader_derives_core_from_incremental_bronze() -> None:
    """Prove exact Silver lineage resolves the original incremental source CVE."""
    source_cve = _source_cve()
    bronze = _bronze_payload(source_cve)
    silver = _parquet(_silver_row(source_cve, bronze))
    reader, silver_reader, bronze_reader = _reader(
        silver_payload=silver,
        bronze_payload=bronze,
    )

    result = _read(reader, source_cve=source_cve)
    observed = ObservedCveVersion.from_source(source_cve)

    assert silver_reader.calls == [(_SILVER_KEY, _SILVER_VERSION)]
    assert bronze_reader.calls == [(_BRONZE_KEY, _BRONZE_VERSION)]
    assert result.observed_version == observed
    assert result.source_identifier == "security@example.test"
    assert result.vuln_status.value == "Analyzed"


def test_exact_nvd_reader_supports_bootstrap_gzip_authority() -> None:
    """Prove bootstrap source authority is derived after exact gzip Bronze retrieval."""
    source_cve = _source_cve()
    bronze = _bronze_payload(source_cve, bootstrap=True)
    silver = _parquet(
        _silver_row(source_cve, bronze, source_kind="bootstrap")
    )
    reader, _, _ = _reader(silver_payload=silver, bronze_payload=bronze)

    result = _read(reader, source_cve=source_cve)

    assert result.observed_version.cve_id == _CVE_ID


def test_exact_nvd_reader_rejects_bronze_sha_drift() -> None:
    """Reject exact Bronze bytes that contradict the Silver lineage digest."""
    source_cve = _source_cve()
    bronze = _bronze_payload(source_cve)
    silver = _parquet(
        _silver_row(source_cve, bronze, bronze_sha256="f" * 64)
    )
    reader, _, _ = _reader(silver_payload=silver, bronze_payload=bronze)

    with pytest.raises(NvdAuthorityDecodeError, match="Bronze bytes"):
        _read(reader, source_cve=source_cve)


def test_exact_nvd_reader_rejects_duplicate_silver_observation() -> None:
    """Reject ambiguous duplicate Silver rows for one observed NVD version."""
    source_cve = _source_cve()
    bronze = _bronze_payload(source_cve)
    row = _silver_row(source_cve, bronze)
    reader, _, _ = _reader(
        silver_payload=_parquet(row, row),
        bronze_payload=bronze,
    )

    with pytest.raises(NvdAuthorityDecodeError, match="exactly one Silver row"):
        _read(reader, source_cve=source_cve)


def test_exact_nvd_reader_rejects_out_of_bounds_record_index() -> None:
    """Reject a Silver lineage record index not present in exact Bronze bytes."""
    source_cve = _source_cve()
    bronze = _bronze_payload(source_cve)
    silver = _parquet(
        _silver_row(source_cve, bronze, bronze_record_index=1)
    )
    reader, _, _ = _reader(silver_payload=silver, bronze_payload=bronze)

    with pytest.raises(NvdAuthorityDecodeError, match="out of bounds"):
        _read(reader, source_cve=source_cve)


def test_exact_nvd_reader_rejects_unsupported_source_kind_before_bronze_read() -> None:
    """Reject unknown NVD encodings before any Bronze provider I/O can occur."""
    source_cve = _source_cve()
    bronze = _bronze_payload(source_cve)
    silver = _parquet(
        _silver_row(source_cve, bronze, source_kind="future-source")
    )
    reader, _, bronze_reader = _reader(
        silver_payload=silver,
        bronze_payload=bronze,
    )

    with pytest.raises(NvdAuthorityDecodeError, match="source_kind"):
        _read(reader, source_cve=source_cve)

    assert bronze_reader.calls == []
