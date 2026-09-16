"""Tests for the derived correlation index contract.

The central property is not that the types validate. It is that they validate the
**same** things `PublicRepositoryThreatEvidence` validates, so a row the request path
would refuse cannot be written into the index in the first place. A row that only fails
at request time fails on the public path, for a repository that did nothing wrong.

```text
rejected at write != rejected at request
```

The identity tests exist because a manifest whose digest moves with incidental ordering
is not an identity. Watermarks arriving in a different order must produce the same
index id, and a real change must move it.
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from opslens.correlation_index.domain.index_contract import (
    CORRELATION_INDEX_CONTRACT_VERSION,
    CorrelationIndexContractError,
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
    SourceWatermark,
    build_manifest,
    index_timestamp,
)

_ADVISORY_DIGEST = "6872a46115d1775d1eac3f5ba734e73ec98a9f78487d178e38e13163c69d7dbf"
_ENTRY_DIGEST = "f086757888580ceef4a1f94c58aacb2c28ae445a18fecdac07c6561ff0519f6d"
_GHSA_ID = "GHSA-fq2j-3j99-rx65"
_CVE_DIGEST = "3e8f5bff0551f7533a34c40a9a944832e9a01d258049d908e179b24da872431c"


def _ghsa_row(**overrides: object) -> ProjectedGhsaIndexRow:
    """Build one valid GHSA index row, with fields overridden for the case at hand."""
    fields: dict[str, object] = {
        "package_name_canonical": "tensorflow",
        "observed_advisory_version_id": f"{_GHSA_ID}@sha256:{_ADVISORY_DIGEST}",
        "source_advisory_sha256": _ADVISORY_DIGEST,
        "source_entry_sha256": _ENTRY_DIGEST,
        "ghsa_id": _GHSA_ID,
        "github_cve_id": "CVE-2026-1234",
        "vulnerability_entry_id": "entry-0",
        "source_index": 0,
        "ecosystem_original": "PIP",
        "package_name_original": "TensorFlow",
        "vulnerable_range_original": ">= 2.0.0, < 2.11.1",
        "first_patched_version_original": "2.11.1",
    }
    fields.update(overrides)
    return ProjectedGhsaIndexRow(**fields)  # pyright: ignore[reportArgumentType]


def _nvd_row(**overrides: object) -> ProjectedNvdIndexRow:
    """Build one valid NVD index row."""
    fields: dict[str, object] = {
        "cve_id": "CVE-2026-1234",
        "observed_cve_version_id": f"CVE-2026-1234@sha256:{_CVE_DIGEST}",
        "source_cve_sha256": _CVE_DIGEST,
        "source_identifier": "cve@mitre.org",
        "published_at": "2026-01-02T03:04:05Z",
        "last_modified_at": "2026-02-03T04:05:06Z",
        "vuln_status": "Analyzed",
    }
    fields.update(overrides)
    return ProjectedNvdIndexRow(**fields)  # pyright: ignore[reportArgumentType]


def _watermark(source: str = "ghsa", count: int = 1) -> SourceWatermark:
    """Build one valid watermark."""
    return SourceWatermark(
        source=source, observed_through="2026-09-16T21:20:51Z", record_count=count
    )


class TestGhsaRowRefusesWhatTheRequestPathWouldRefuse:
    """The index cannot hold a row `PublicRepositoryThreatEvidence` would reject."""

    def test_a_valid_row_is_accepted(self) -> None:
        """The happy case exists so the refusals below mean something."""
        assert _ghsa_row().package_name_canonical == "tensorflow"

    def test_an_identity_contradicting_its_digest_is_refused(self) -> None:
        """The authority checks this exact equality; so does the index."""
        with pytest.raises(CorrelationIndexContractError):
            _ghsa_row(observed_advisory_version_id=f"{_GHSA_ID}@sha256:{_ENTRY_DIGEST}")

    @pytest.mark.parametrize(
        "digest", ["", _ADVISORY_DIGEST.upper(), _ADVISORY_DIGEST[:-1], "not-a-digest"]
    )
    def test_a_digest_that_is_not_lowercase_hex_is_refused(self, digest: str) -> None:
        """"Exact lowercase source hashes" is the authority's wording and its rule."""
        with pytest.raises(CorrelationIndexContractError):
            _ghsa_row(
                source_advisory_sha256=digest,
                observed_advisory_version_id=f"{_GHSA_ID}@sha256:{digest}",
            )

    def test_an_entry_digest_that_is_not_lowercase_hex_is_refused(self) -> None:
        """Both hashes are checked, not just the one that forms the identity."""
        with pytest.raises(CorrelationIndexContractError):
            _ghsa_row(source_entry_sha256="short")

    def test_a_malformed_advisory_id_is_refused(self) -> None:
        """GHSA identifiers use a restricted alphabet; l, o and u are not in it."""
        with pytest.raises(CorrelationIndexContractError):
            _ghsa_row(ghsa_id="GHSA-loop-loop-loop")

    def test_a_malformed_cve_is_refused(self) -> None:
        """A CVE that cannot be matched against NVD must not enter the index."""
        with pytest.raises(CorrelationIndexContractError):
            _ghsa_row(github_cve_id="CVE-26-1")

    def test_an_absent_cve_is_allowed(self) -> None:
        """Most GHSA advisories name no CVE, and that is not a defect."""
        assert _ghsa_row(github_cve_id=None).github_cve_id is None

    @pytest.mark.parametrize("value", [-1, 1_000_000])
    def test_a_source_index_outside_the_key_width_is_refused(self, value: int) -> None:
        """An index the sort key cannot render would collide with another occurrence."""
        with pytest.raises(CorrelationIndexContractError):
            _ghsa_row(source_index=value)

    @pytest.mark.parametrize(
        "field",
        [
            "package_name_canonical",
            "vulnerability_entry_id",
            "ecosystem_original",
            "package_name_original",
            "vulnerable_range_original",
        ],
    )
    def test_an_empty_required_field_is_refused(self, field: str) -> None:
        """An empty range or package name would make the row unusable downstream."""
        with pytest.raises(CorrelationIndexContractError):
            _ghsa_row(**{field: ""})


class TestOccurrenceKey:
    """The sort key must distinguish exactly what the authority refuses to see twice."""

    def test_two_entries_of_one_advisory_get_distinct_keys(self) -> None:
        """The authority rejects duplicate (version id, source index) pairs."""
        first = _ghsa_row(source_index=0)
        second = _ghsa_row(source_index=1)
        assert first.occurrence_key != second.occurrence_key

    def test_the_key_sorts_as_text_in_source_order(self) -> None:
        """A key-value store orders by text, so the padding is load-bearing."""
        keys = [_ghsa_row(source_index=value).occurrence_key for value in (2, 10, 1)]
        assert sorted(keys) == [
            _ghsa_row(source_index=value).occurrence_key for value in (1, 2, 10)
        ]


class TestNvdRow:
    """NVD rows carry no skew, but the same identity rule."""

    def test_a_valid_row_is_accepted(self) -> None:
        """The happy case."""
        assert _nvd_row().cve_id == "CVE-2026-1234"

    def test_an_identity_contradicting_its_digest_is_refused(self) -> None:
        """CVE identity and CVE content-version identity are deliberately different."""
        with pytest.raises(CorrelationIndexContractError):
            _nvd_row(observed_cve_version_id=f"CVE-2026-1234@sha256:{_ADVISORY_DIGEST}")

    def test_a_malformed_cve_is_refused(self) -> None:
        """A row nothing can look up by CVE has no place in a CVE-keyed index."""
        with pytest.raises(CorrelationIndexContractError):
            _nvd_row(cve_id="CVE-bad")


class TestWatermark:
    """A response cites freshness from these, so a malformed one overstates it."""

    def test_a_valid_watermark_is_accepted(self) -> None:
        """The happy case."""
        assert _watermark().record_count == 1

    def test_a_non_utc_rendering_is_refused(self) -> None:
        """One timestamp form, so two indexes are comparable."""
        with pytest.raises(CorrelationIndexContractError):
            SourceWatermark(
                source="ghsa", observed_through="2026-09-16T21:20:51+00:00", record_count=1
            )

    def test_a_negative_record_count_is_refused(self) -> None:
        """A count that cannot have happened cannot describe a build."""
        with pytest.raises(CorrelationIndexContractError):
            SourceWatermark(
                source="ghsa", observed_through="2026-09-16T21:20:51Z", record_count=-1
            )


class TestManifest:
    """The manifest is what a response names, so its identity has to be stable."""

    def test_counts_come_from_the_rows_rather_than_being_asserted(self) -> None:
        """A manifest that can disagree with its index is worse than none."""
        rows = [_ghsa_row(source_index=0), _ghsa_row(source_index=1)]
        manifest = build_manifest(
            built_at=datetime(2026, 9, 16, 21, 20, 51, tzinfo=UTC),
            ghsa_rows=rows,
            nvd_rows=[_nvd_row()],
            watermarks=[_watermark("ghsa", 2), _watermark("nvd", 1)],
        )
        assert manifest.ghsa_row_count == 2
        assert manifest.nvd_row_count == 1
        assert manifest.distinct_package_count == 1

    def test_watermark_order_does_not_move_the_identity(self) -> None:
        """An identity that depends on argument order is not an identity."""
        moment = datetime(2026, 9, 16, 21, 20, 51, tzinfo=UTC)
        first = build_manifest(
            built_at=moment,
            ghsa_rows=[_ghsa_row()],
            nvd_rows=[_nvd_row()],
            watermarks=[_watermark("ghsa"), _watermark("nvd")],
        )
        second = build_manifest(
            built_at=moment,
            ghsa_rows=[_ghsa_row()],
            nvd_rows=[_nvd_row()],
            watermarks=[_watermark("nvd"), _watermark("ghsa")],
        )
        assert first.index_id == second.index_id

    def test_a_later_build_has_a_different_identity(self) -> None:
        """Two builds of the same corpus at different times are different answers."""
        moment = datetime(2026, 9, 16, 21, 20, 51, tzinfo=UTC)
        first = build_manifest(
            built_at=moment,
            ghsa_rows=[_ghsa_row()],
            nvd_rows=[_nvd_row()],
            watermarks=[_watermark()],
        )
        second = build_manifest(
            built_at=moment + timedelta(seconds=1),
            ghsa_rows=[_ghsa_row()],
            nvd_rows=[_nvd_row()],
            watermarks=[_watermark()],
        )
        assert first.index_id != second.index_id

    def test_the_identity_names_the_contract(self) -> None:
        """A response cites the contract, not only the digest."""
        manifest = build_manifest(
            built_at=datetime(2026, 9, 16, 21, 20, 51, tzinfo=UTC),
            ghsa_rows=[_ghsa_row()],
            nvd_rows=[_nvd_row()],
            watermarks=[_watermark()],
        )
        assert manifest.index_id.startswith(f"{CORRELATION_INDEX_CONTRACT_VERSION}@sha256:")

    def test_an_index_built_from_no_source_is_refused(self) -> None:
        """Without a watermark, freshness cannot be stated at all."""
        with pytest.raises(CorrelationIndexContractError):
            build_manifest(
                built_at=datetime(2026, 9, 16, tzinfo=UTC),
                ghsa_rows=[_ghsa_row()],
                nvd_rows=[],
                watermarks=[],
            )

    def test_one_source_cannot_carry_two_watermarks(self) -> None:
        """Two freshness claims for one source leave a response free to pick."""
        with pytest.raises(CorrelationIndexContractError):
            build_manifest(
                built_at=datetime(2026, 9, 16, tzinfo=UTC),
                ghsa_rows=[_ghsa_row()],
                nvd_rows=[],
                watermarks=[_watermark("ghsa", 1), _watermark("ghsa", 2)],
            )


class TestIndexTimestamp:
    """One rendering, so an identity does not depend on the operator's clock offset."""

    def test_a_naive_instant_is_refused(self) -> None:
        """An instant without a zone cannot be rendered in UTC honestly."""
        with pytest.raises(CorrelationIndexContractError):
            index_timestamp(datetime(2026, 9, 16, 21, 20, 51))  # noqa: DTZ001

    def test_an_offset_instant_is_rendered_in_utc(self) -> None:
        """The same instant renders identically whatever zone it arrives in."""
        offset = timezone(timedelta(hours=-3))
        assert index_timestamp(datetime(2026, 9, 16, 18, 20, 51, tzinfo=offset)) == (
            "2026-09-16T21:20:51Z"
        )
