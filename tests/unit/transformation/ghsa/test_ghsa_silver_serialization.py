# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Tests for GHSA logical hashing and deterministic Parquet serialization."""

from copy import deepcopy
from typing import cast

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from opslens.transformation.ghsa.application.record_composer import (
    GhsaSilverRecordComposerV1,
)
from opslens.transformation.ghsa.domain.collections_transformer import (
    GhsaAdvisoryCollectionsTransformer,
)
from opslens.transformation.ghsa.domain.transformer import (
    GhsaAdvisoryCoreTransformer,
)
from opslens.transformation.ghsa.domain.vulnerabilities_transformer import (
    GhsaVulnerabilitiesTransformer,
)
from opslens.transformation.ghsa.serialization.logical_hash import (
    GhsaLogicalRecordSetHasherV1,
)
from opslens.transformation.ghsa.serialization.parquet import (
    GHSA_PARQUET_COMPRESSION,
    GHSA_PARQUET_DATA_PAGE_VERSION,
    GHSA_PARQUET_FORMAT_VERSION,
    GHSA_PARQUET_ROW_GROUP_SIZE,
    GHSA_PARQUET_WRITER_CONTRACT_VERSION,
    GhsaSilverParquetSerializerV1,
)
from opslens.transformation.ghsa.serialization.schema import (
    GHSA_ADVISORY_VERSIONS_SCHEMA_V1,
)


def _source_advisory(
    *,
    ghsa_id: str = "GHSA-2345-6789-cfgh",
    cve_id: str = "CVE-2026-12345",
) -> dict[str, object]:
    """Return one complete reviewed advisory accepted by all Silver transformers."""
    return {
        "ghsa_id": ghsa_id,
        "cve_id": cve_id,
        "url": f"https://api.github.com/advisories/{ghsa_id}",
        "html_url": f"https://github.com/advisories/{ghsa_id}",
        "repository_advisory_url": None,
        "summary": f"Example reviewed advisory {ghsa_id}",
        "description": "Example advisory description.",
        "type": "reviewed",
        "severity": "high",
        "source_code_location": None,
        "published_at": "2026-08-20T10:00:00Z",
        "updated_at": "2026-08-21T11:00:00Z",
        "github_reviewed_at": "2026-08-21T12:00:00Z",
        "nvd_published_at": None,
        "withdrawn_at": None,
        "identifiers": [
            {"type": "GHSA", "value": ghsa_id},
            {"type": "CVE", "value": cve_id},
        ],
        "references": [f"https://github.com/advisories/{ghsa_id}"],
        "cwes": [{"cwe_id": "CWE-79", "name": "Cross-site Scripting"}],
        "cvss_severities": {
            "cvss_v3": {
                "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                "score": 9.8,
            },
        },
        "vulnerabilities": [
            {
                "package": {"ecosystem": "pip", "name": "example-package"},
                "vulnerable_version_range": ">= 1.0.0, < 1.2.0",
                "first_patched_version": "1.2.0",
                "vulnerable_functions": ["unsafe_load"],
            },
        ],
    }


def _composer() -> GhsaSilverRecordComposerV1:
    """Build the deterministic GHSA logical-record composer."""
    return GhsaSilverRecordComposerV1(
        core_transformer=GhsaAdvisoryCoreTransformer(),
        collections_transformer=GhsaAdvisoryCollectionsTransformer(),
        vulnerabilities_transformer=GhsaVulnerabilitiesTransformer(),
    )


def _object_list(value: object) -> list[object]:
    """Narrow one mutable JSON-like list for test mutation."""
    assert isinstance(value, list)
    return cast(list[object], value)


def _object_dict(value: object) -> dict[str, object]:
    """Narrow one mutable JSON-like object for test mutation."""
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_logical_hash_is_independent_of_input_record_order() -> None:
    """Hash the logical advisory-version set rather than caller iteration order."""
    first = _composer().compose(_source_advisory())
    second = _composer().compose(
        _source_advisory(
            ghsa_id="GHSA-2345-6789-cfgj",
            cve_id="CVE-2026-54321",
        )
    )
    hasher = GhsaLogicalRecordSetHasherV1()

    assert hasher.digest((first, second)) == hasher.digest((second, first))


def test_logical_hash_changes_when_nested_package_evidence_changes() -> None:
    """Include exact nested package/range/fix evidence in the logical digest."""
    original_source = _source_advisory()
    changed_source = deepcopy(original_source)
    vulnerabilities = _object_list(changed_source["vulnerabilities"])
    first = _object_dict(vulnerabilities[0])
    first["first_patched_version"] = "1.2.1"

    original = _composer().compose(original_source)
    changed = _composer().compose(changed_source)
    hasher = GhsaLogicalRecordSetHasherV1()

    assert hasher.digest((original,)) != hasher.digest((changed,))


def test_logical_hash_rejects_duplicate_observed_versions() -> None:
    """Keep one logical row per exact observed advisory content version."""
    record = _composer().compose(_source_advisory())

    with pytest.raises(ValueError, match="duplicate observed_advisory_version_id"):
        GhsaLogicalRecordSetHasherV1().digest((record, record))


def test_parquet_writer_contract_is_frozen() -> None:
    """Freeze the physical writer knobs that participate in artifact identity."""
    assert GHSA_PARQUET_WRITER_CONTRACT_VERSION == 1
    assert GHSA_PARQUET_FORMAT_VERSION == "1.0"
    assert GHSA_PARQUET_DATA_PAGE_VERSION == "1.0"
    assert GHSA_PARQUET_COMPRESSION == "snappy"
    assert GHSA_PARQUET_ROW_GROUP_SIZE == 5_000


def test_parquet_bytes_are_independent_of_input_record_order() -> None:
    """Sort rows canonically before physical serialization."""
    first = _composer().compose(_source_advisory())
    second = _composer().compose(
        _source_advisory(
            ghsa_id="GHSA-2345-6789-cfgj",
            cve_id="CVE-2026-54321",
        )
    )
    serializer = GhsaSilverParquetSerializerV1()

    forward = serializer.serialize((first, second))
    reverse = serializer.serialize((second, first))

    assert forward.parquet_bytes == reverse.parquet_bytes
    assert forward.parquet_sha256 == reverse.parquet_sha256
    assert forward.row_count == 2


def test_parquet_round_trip_preserves_nested_package_evidence() -> None:
    """Prove the frozen nested Arrow shape survives Parquet serialization."""
    record = _composer().compose(_source_advisory())
    artifact = GhsaSilverParquetSerializerV1().serialize((record,))
    table = pq.read_table(pa.BufferReader(artifact.parquet_bytes))

    assert table.schema == GHSA_ADVISORY_VERSIONS_SCHEMA_V1
    rows = table.to_pylist()
    assert len(rows) == 1
    row = rows[0]
    assert row["ghsa_id"] == "GHSA-2345-6789-cfgh"
    assert row["vulnerability_entry_count"] == 1
    vulnerabilities = row["vulnerabilities"]
    assert len(vulnerabilities) == 1
    assert vulnerabilities[0]["ecosystem"] == "pip"
    assert vulnerabilities[0]["package_name"] == "example-package"
    assert vulnerabilities[0]["first_patched_version"] == "1.2.0"


def test_parquet_rejects_duplicate_observed_versions() -> None:
    """Reject duplicate logical content versions before writing physical bytes."""
    record = _composer().compose(_source_advisory())

    with pytest.raises(ValueError, match="duplicate observed_advisory_version_id"):
        GhsaSilverParquetSerializerV1().serialize((record, record))
