"""Tests for the generation that keeps a half-built index unreadable.

A rebuild that overwrites in place has a window where a package's rows are gone and its
replacements are not written yet. That package looks exactly like a package with no
advisories, and the endpoint answers "no known vulnerabilities" — the one failure this
project cannot afford, produced by a maintenance window rather than a defect.

ADR 0088 puts the build generation in the partition key, so a build writes where nothing
reads and a pointer makes it live atomically.

```text
partially built index != index
missing rows != no advisories
written != readable
```
"""

from datetime import UTC, datetime

import pytest

from opslens.correlation_index.domain.index_contract import (
    CorrelationIndexContractError,
    CorrelationIndexManifest,
    ProjectedNvdIndexRow,
    SourceWatermark,
    build_manifest,
    ghsa_partition_key,
    index_generation,
    nvd_partition_key,
)

_DIGEST = "3e8f5bff0551f7533a34c40a9a944832e9a01d258049d908e179b24da872431c"
_GENERATION = _DIGEST[:16]


def _manifest(built_at: datetime) -> CorrelationIndexManifest:
    """Build one manifest at a given instant."""
    return build_manifest(
        built_at=built_at,
        ghsa_rows=[],
        nvd_rows=[
            ProjectedNvdIndexRow(
                cve_id="CVE-2026-1234",
                observed_cve_version_id=f"CVE-2026-1234@sha256:{_DIGEST}",
                source_cve_sha256=_DIGEST,
                source_identifier="cve@mitre.org",
                published_at="2026-01-02T03:04:05Z",
                last_modified_at="2026-02-03T04:05:06Z",
                vuln_status="Analyzed",
            )
        ],
        watermarks=[
            SourceWatermark(
                source="nvd", observed_through="2026-09-16T21:20:51Z", record_count=1
            )
        ],
    )


class TestGeneration:
    """The generation derives from content, so a re-run is idempotent."""

    def test_it_is_the_manifest_digest_prefix(self) -> None:
        """Tying the key space to the digest lets a row prove which manifest made it."""
        assert index_generation(f"opslens-correlation-index:v2@sha256:{_DIGEST}") == (
            _GENERATION
        )

    def test_identical_builds_share_a_generation(self) -> None:
        """A counter would make a re-run a second generation of the same content."""
        moment = datetime(2026, 9, 16, 21, 20, 51, tzinfo=UTC)
        first = _manifest(moment)
        second = _manifest(moment)
        assert index_generation(first.index_id) == index_generation(second.index_id)

    def test_a_later_build_of_the_same_content_keeps_the_generation(self) -> None:
        """A re-run writes the rows it already wrote, into the space they are already in.

        This reads backwards until the alternative is spelled out: a clock-dependent
        generation would send an unchanged corpus to a fresh key space every night,
        leaving the previous generation live until the pointer flipped and doubling the
        stored rows for nothing.

        ```text
        when it was built != what was built
        ```
        """
        first = _manifest(datetime(2026, 9, 16, 21, 20, 51, tzinfo=UTC))
        second = _manifest(datetime(2026, 9, 17, 21, 20, 51, tzinfo=UTC))
        assert index_generation(first.index_id) == index_generation(second.index_id)

    def test_a_build_of_different_content_gets_a_different_generation(self) -> None:
        """What a new generation is actually for: not overwriting what is answering."""
        moment = datetime(2026, 9, 16, 21, 20, 51, tzinfo=UTC)
        first = _manifest(moment)
        second = build_manifest(
            built_at=moment,
            ghsa_rows=[],
            nvd_rows=[
                ProjectedNvdIndexRow(
                    cve_id="CVE-2026-9999",
                    observed_cve_version_id=f"CVE-2026-9999@sha256:{_DIGEST}",
                    source_cve_sha256=_DIGEST,
                    source_identifier="cve@mitre.org",
                    published_at="2026-01-02T03:04:05Z",
                    last_modified_at="2026-02-03T04:05:06Z",
                    vuln_status="Analyzed",
                )
            ],
            watermarks=[
                SourceWatermark(
                    source="nvd", observed_through="2026-09-16T21:20:51Z", record_count=1
                )
            ],
        )
        assert index_generation(first.index_id) != index_generation(second.index_id)

    def test_fresher_sources_over_the_same_rows_get_a_different_generation(self) -> None:
        """Freshness is part of the identity, because a response cites it as its own."""
        moment = datetime(2026, 9, 16, 21, 20, 51, tzinfo=UTC)
        first = _manifest(moment)
        second = build_manifest(
            built_at=moment,
            ghsa_rows=[],
            nvd_rows=[
                ProjectedNvdIndexRow(
                    cve_id="CVE-2026-1234",
                    observed_cve_version_id=f"CVE-2026-1234@sha256:{_DIGEST}",
                    source_cve_sha256=_DIGEST,
                    source_identifier="cve@mitre.org",
                    published_at="2026-01-02T03:04:05Z",
                    last_modified_at="2026-02-03T04:05:06Z",
                    vuln_status="Analyzed",
                )
            ],
            watermarks=[
                SourceWatermark(
                    source="nvd", observed_through="2026-09-17T09:00:00Z", record_count=2
                )
            ],
        )
        assert first.content_digest == second.content_digest
        assert index_generation(first.index_id) != index_generation(second.index_id)

    @pytest.mark.parametrize(
        "identity",
        ["", "opslens-correlation-index:v1", f"opslens-correlation-index:v1@md5:{_DIGEST}"],
    )
    def test_an_identity_without_a_digest_is_refused(self, identity: str) -> None:
        """A generation invented from a non-content identity addresses nothing."""
        with pytest.raises(CorrelationIndexContractError):
            index_generation(identity)


class TestPartitionKeys:
    """A key that can address another generation's space defeats the swap."""

    def test_a_ghsa_key_carries_generation_and_package(self) -> None:
        """The happy case."""
        assert ghsa_partition_key(_GENERATION, "tensorflow") == (
            f"{_GENERATION}#tensorflow"
        )

    def test_an_nvd_key_carries_generation_and_cve(self) -> None:
        """The happy case."""
        assert nvd_partition_key(_GENERATION, "CVE-2026-1234") == (
            f"{_GENERATION}#CVE-2026-1234"
        )

    def test_two_generations_of_one_package_do_not_collide(self) -> None:
        """This is the whole property: a build writes where nothing is reading."""
        other = "0" * 16
        assert ghsa_partition_key(_GENERATION, "tensorflow") != ghsa_partition_key(
            other, "tensorflow"
        )

    @pytest.mark.parametrize(
        "generation", ["", "short", _DIGEST, _GENERATION.upper(), "zzzzzzzzzzzzzzzz"]
    )
    def test_a_malformed_generation_is_refused(self, generation: str) -> None:
        """A key built from a wrong-width generation would land in no live space."""
        with pytest.raises(CorrelationIndexContractError):
            ghsa_partition_key(generation, "tensorflow")

    def test_a_package_name_cannot_smuggle_a_separator(self) -> None:
        """A canonical PyPI name cannot contain the separator, and is checked anyway."""
        assert "#" not in ghsa_partition_key(_GENERATION, "tensorflow").split("#", 1)[1]

    def test_an_empty_package_name_is_refused(self) -> None:
        """A key with no package addresses every package or none."""
        with pytest.raises(CorrelationIndexContractError):
            ghsa_partition_key(_GENERATION, "")

    def test_a_malformed_cve_is_refused(self) -> None:
        """A CVE key nothing can look up has no place in a CVE-keyed index."""
        with pytest.raises(CorrelationIndexContractError):
            nvd_partition_key(_GENERATION, "CVE-bad")
