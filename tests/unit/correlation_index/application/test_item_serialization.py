"""Tests for serializing index rows, and for the clock that can empty the index.

The TTL is the dangerous part. Set at write time, it expires the live generation too,
on schedule, whether or not a newer build ever succeeded. If builds fail for longer than
the window the index does not go stale — it goes *empty*, and an empty index answers
"no known vulnerabilities" for every package with total confidence.

```text
stale index != empty index
expired index != answered honestly
```

The window is therefore long relative to the rebuild cadence, and these tests assert
that relationship rather than a magic number. What actually keeps a stale index from
lying is the response contract, not this value.
"""

from datetime import UTC, datetime, timedelta

import pytest

from opslens.correlation_index.application.item_serialization import (
    RETIRED_GENERATION_RETENTION,
    expiry_epoch,
    ghsa_item,
    nvd_item,
    pointer_document,
)
from opslens.correlation_index.domain.index_contract import (
    CorrelationIndexContractError,
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
    ProjectedSourceIdentifier,
    index_generation,
)

_ADVISORY_DIGEST = "6872a46115d1775d1eac3f5ba734e73ec98a9f78487d178e38e13163c69d7dbf"
_ENTRY_DIGEST = "f086757888580ceef4a1f94c58aacb2c28ae445a18fecdac07c6561ff0519f6d"
_CVE_DIGEST = "3e8f5bff0551f7533a34c40a9a944832e9a01d258049d908e179b24da872431c"
_GHSA_ID = "GHSA-fq2j-3j99-rx65"
_INDEX_ID = f"opslens-correlation-index:v2@sha256:{_CVE_DIGEST}"
_BUILT_AT = datetime(2026, 9, 16, 21, 20, 51, tzinfo=UTC)


def _ghsa_row() -> ProjectedGhsaIndexRow:
    """Build one projected GHSA row."""
    return ProjectedGhsaIndexRow(
        package_name_canonical="tensorflow",
        observed_advisory_version_id=f"{_GHSA_ID}@sha256:{_ADVISORY_DIGEST}",
        source_advisory_sha256=_ADVISORY_DIGEST,
        source_entry_sha256=_ENTRY_DIGEST,
        ghsa_id=_GHSA_ID,
        github_cve_id="CVE-2026-1234",
        github_identifiers=(
            ProjectedSourceIdentifier(identifier_type="GHSA", value=_GHSA_ID),
        ),
        vulnerability_entry_id="entry-0",
        source_index=3,
        ecosystem_original="pip",
        package_name_original="TensorFlow",
        vulnerable_range_original="< 2.11.1",
        first_patched_version_original="2.11.1",
    )


def _nvd_row() -> ProjectedNvdIndexRow:
    """Build one projected NVD row."""
    return ProjectedNvdIndexRow(
        cve_id="CVE-2026-1234",
        observed_cve_version_id=f"CVE-2026-1234@sha256:{_CVE_DIGEST}",
        source_cve_sha256=_CVE_DIGEST,
        source_identifier="cve@mitre.org",
        published_at="2026-01-02T03:04:05Z",
        last_modified_at="2026-02-03T04:05:06Z",
        vuln_status="Analyzed",
    )


class TestExpiry:
    """The TTL reclaims retired generations; it does not make staleness safe."""

    def test_the_window_outlasts_a_daily_rebuild_by_a_wide_margin(self) -> None:
        """A window near the cadence would empty the index after a few failed builds."""
        assert timedelta(days=7) <= RETIRED_GENERATION_RETENTION

    def test_the_value_is_epoch_seconds_after_the_build(self) -> None:
        """DynamoDB reads TTL as epoch seconds, not as a timestamp string."""
        assert expiry_epoch(_BUILT_AT) == int(
            (_BUILT_AT + RETIRED_GENERATION_RETENTION).timestamp()
        )

    def test_a_naive_instant_is_refused(self) -> None:
        """An expiry computed from an ambiguous instant is off by the operator's offset."""
        with pytest.raises(ValueError, match="timezone-aware"):
            expiry_epoch(datetime(2026, 9, 16, 21, 20, 51))  # noqa: DTZ001

    @pytest.mark.parametrize("retention", [timedelta(0), timedelta(seconds=-1)])
    def test_a_non_positive_window_is_refused(self, retention: timedelta) -> None:
        """Items would expire as they are written, emptying the index during the build."""
        with pytest.raises(ValueError, match="positive"):
            expiry_epoch(_BUILT_AT, retention)


class TestGhsaItem:
    """The stored item must be addressable by the generation that owns it."""

    def test_the_partition_key_carries_the_generation(self) -> None:
        """This is what keeps a build writing where nothing is reading."""
        item = ghsa_item(_ghsa_row(), index_id=_INDEX_ID, expires_at=1)
        assert item["pk"] == f"{index_generation(_INDEX_ID)}#tensorflow"

    def test_the_sort_key_is_the_occurrence(self) -> None:
        """Two entries of one advisory must not overwrite each other."""
        item = ghsa_item(_ghsa_row(), index_id=_INDEX_ID, expires_at=1)
        assert item["sk"] == _ghsa_row().occurrence_key

    def test_the_item_carries_its_own_index_identity(self) -> None:
        """A row whose generation and manifest disagree becomes detectable."""
        item = ghsa_item(_ghsa_row(), index_id=_INDEX_ID, expires_at=1)
        assert item["index_id"] == _INDEX_ID

    def test_identifiers_are_stored_as_readable_structures(self) -> None:
        """They rebuild into typed evidence, so they cannot be flattened to strings."""
        item = ghsa_item(_ghsa_row(), index_id=_INDEX_ID, expires_at=1)
        assert item["github_identifiers"] == [
            {"identifier_type": "GHSA", "value": _GHSA_ID}
        ]

    def test_absent_optional_fields_stay_absent_rather_than_becoming_empty(self) -> None:
        """An empty string is a value; None is the source saying nothing."""
        row = ProjectedGhsaIndexRow(
            package_name_canonical="django",
            observed_advisory_version_id=f"{_GHSA_ID}@sha256:{_ADVISORY_DIGEST}",
            source_advisory_sha256=_ADVISORY_DIGEST,
            source_entry_sha256=_ENTRY_DIGEST,
            ghsa_id=_GHSA_ID,
            github_cve_id=None,
            github_identifiers=(),
            vulnerability_entry_id="entry-0",
            source_index=0,
            ecosystem_original="pip",
            package_name_original="django",
            vulnerable_range_original="< 1.0",
            first_patched_version_original=None,
        )
        item = ghsa_item(row, index_id=_INDEX_ID, expires_at=1)
        assert item["github_cve_id"] is None
        assert item["first_patched_version_original"] is None

    def test_an_identity_without_a_digest_cannot_key_an_item(self) -> None:
        """A generation invented from a non-content identity addresses nothing."""
        with pytest.raises(CorrelationIndexContractError):
            ghsa_item(_ghsa_row(), index_id="opslens-correlation-index:v1", expires_at=1)


class TestNvdItem:
    """NVD items are keyed by CVE within the same generation."""

    def test_the_partition_key_carries_the_generation(self) -> None:
        """The swap has to move both indexes together."""
        item = nvd_item(_nvd_row(), index_id=_INDEX_ID, expires_at=1)
        assert item["pk"] == f"{index_generation(_INDEX_ID)}#CVE-2026-1234"

    def test_the_item_carries_no_sort_key(self) -> None:
        """One observed version per CVE; a sort key would invite a second."""
        assert "sk" not in nvd_item(_nvd_row(), index_id=_INDEX_ID, expires_at=1)


class TestPointer:
    """The pointer is the whole swap, so what it names has to be unambiguous."""

    def test_it_names_the_generation_and_the_manifest(self) -> None:
        """A reader keys on the generation and cites the manifest; it needs both."""
        document = pointer_document(_INDEX_ID, "2026-09-16T21:20:51Z")
        assert document["generation"] == index_generation(_INDEX_ID)
        assert document["index_id"] == _INDEX_ID

    def test_it_records_when_the_build_ran(self) -> None:
        """Freshness is what stops a stale index from answering as a current one."""
        document = pointer_document(_INDEX_ID, "2026-09-16T21:20:51Z")
        assert document["built_at"] == "2026-09-16T21:20:51Z"

    def test_a_pointer_cannot_name_a_non_content_identity(self) -> None:
        """Otherwise the live generation would not be derivable from what it names."""
        with pytest.raises(CorrelationIndexContractError):
            pointer_document("not-an-identity", "2026-09-16T21:20:51Z")
