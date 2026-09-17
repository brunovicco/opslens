"""Tests that the index preserves enough to rebuild what the request path consumes.

The projected row was first contracted without `github_identifiers`, which
`GhsaPyPIVulnerabilityEvidence` requires. Nothing caught it: every type validated, every
test passed, and the index simply could not have fed the authority it exists to feed.

The failure mode is specific. An index missing a field is not detectably wrong until
something tries to build the evidence — which happens on the public request path, at
request time, for a repository that did nothing wrong.

```text
a claim about coverage != a check of coverage
```

So coverage is asserted from `dataclasses.fields` rather than from a list someone
maintains. Adding a field to the evidence type fails this test until the index carries
it.
"""

from dataclasses import fields

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.correlation_index.application.evidence_rebuild import rebuild_ghsa_evidence
from opslens.correlation_index.domain.index_contract import (
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
    ProjectedSourceIdentifier,
)
from opslens.transformation.nvd.domain.models import (
    NvdCveCoreRecord,
    ObservedCveVersion,
)

_ADVISORY_DIGEST = "6872a46115d1775d1eac3f5ba734e73ec98a9f78487d178e38e13163c69d7dbf"
_ENTRY_DIGEST = "f086757888580ceef4a1f94c58aacb2c28ae445a18fecdac07c6561ff0519f6d"
_GHSA_ID = "GHSA-fq2j-3j99-rx65"


def _row() -> ProjectedGhsaIndexRow:
    """Build one fully populated index row."""
    return ProjectedGhsaIndexRow(
        package_name_canonical="tensorflow",
        observed_advisory_version_id=f"{_GHSA_ID}@sha256:{_ADVISORY_DIGEST}",
        source_advisory_sha256=_ADVISORY_DIGEST,
        source_entry_sha256=_ENTRY_DIGEST,
        ghsa_id=_GHSA_ID,
        github_cve_id="CVE-2026-1234",
        github_identifiers=(
            ProjectedSourceIdentifier(identifier_type="GHSA", value=_GHSA_ID),
            ProjectedSourceIdentifier(identifier_type="CVE", value="CVE-2026-1234"),
        ),
        vulnerability_entry_id="entry-0",
        source_index=0,
        ecosystem_original="PIP",
        package_name_original="TensorFlow",
        vulnerable_range_original=">= 2.0.0, < 2.11.1",
        first_patched_version_original="2.11.1",
    )


def test_every_evidence_field_is_reachable_from_the_index() -> None:
    """The index must carry everything the consumer's type requires.

    Driven by the evidence dataclass itself, so a field added there fails here rather
    than at request time.
    """
    rebuilt = rebuild_ghsa_evidence(_row())
    for field in fields(GhsaPyPIVulnerabilityEvidence):
        value = getattr(rebuilt, field.name)
        assert value is not None or field.name in {
            "github_cve_id",
            "first_patched_version_original",
        }, f"{field.name} is not reachable from a projected index row"


def test_the_rebuild_invents_nothing() -> None:
    """Every rebuilt value equals the stored one; a projection that edits is not a projection."""
    row = _row()
    rebuilt = rebuild_ghsa_evidence(row)

    assert rebuilt.observed_advisory_version_id == row.observed_advisory_version_id
    assert rebuilt.source_advisory_sha256 == row.source_advisory_sha256
    assert rebuilt.source_entry_sha256 == row.source_entry_sha256
    assert rebuilt.ghsa_id == row.ghsa_id
    assert rebuilt.github_cve_id == row.github_cve_id
    assert rebuilt.vulnerability_entry_id == row.vulnerability_entry_id
    assert rebuilt.source_index == row.source_index
    assert rebuilt.ecosystem_original == row.ecosystem_original
    assert rebuilt.package_name_original == row.package_name_original
    assert rebuilt.vulnerable_range_original == row.vulnerable_range_original
    assert rebuilt.first_patched_version_original == row.first_patched_version_original


def test_the_identifiers_survive_in_source_order() -> None:
    """GitHub emits identifiers in an order, and reordering them rewrites the source."""
    rebuilt = rebuild_ghsa_evidence(_row())
    assert [(item.identifier_type, item.value) for item in rebuilt.github_identifiers] == [
        ("GHSA", _GHSA_ID),
        ("CVE", "CVE-2026-1234"),
    ]


def test_an_advisory_with_no_identifiers_still_rebuilds() -> None:
    """An advisory carrying none is sparse, not invalid — the same reading as ADR 0085."""
    row = ProjectedGhsaIndexRow(
        package_name_canonical="tensorflow",
        observed_advisory_version_id=f"{_GHSA_ID}@sha256:{_ADVISORY_DIGEST}",
        source_advisory_sha256=_ADVISORY_DIGEST,
        source_entry_sha256=_ENTRY_DIGEST,
        ghsa_id=_GHSA_ID,
        github_cve_id=None,
        github_identifiers=(),
        vulnerability_entry_id="entry-0",
        source_index=0,
        ecosystem_original="pip",
        package_name_original="tensorflow",
        vulnerable_range_original="< 1.0.0",
        first_patched_version_original=None,
    )
    assert rebuild_ghsa_evidence(row).github_identifiers == ()


class TestNvdRowCannotRebuildTheRecord:
    """The other half, named by a check instead of by a document.

    There is deliberately no `rebuild_nvd_evidence`. `NvdCveCoreRecord` carries an
    `ObservedCveVersion`, whose validation requires the complete canonical JSON of the
    source CVE — it verifies the digest against it and re-canonicalizes it — and
    `derive_repository_nvd_cvss_evidence` re-runs the CVSS transformer over those same
    bytes on every request. The index stores the digest and seven scalars.

    ```text
    the digest of the content != the content
    ```

    ADR 0089 records why that is deferred rather than solved. These tests exist so the
    deferral is enforced: adding a rebuild without also giving the index the CVE body
    fails here rather than producing a record that cannot be validated.
    """

    def test_no_nvd_rebuild_is_exported(self) -> None:
        """A rebuild that cannot produce a valid record must not exist to be called."""
        import opslens.correlation_index.application.evidence_rebuild as module

        assert not hasattr(module, "rebuild_nvd_evidence"), (
            "an NVD rebuild exists; ADR 0089 requires the CVE body in the index first"
        )

    def test_the_row_covers_every_scalar_the_record_needs(self) -> None:
        """What the index does carry is exactly the record's scalar surface."""
        record_fields = {item.name for item in fields(NvdCveCoreRecord)}
        row_fields = {item.name for item in fields(ProjectedNvdIndexRow)}
        assert record_fields - {"observed_version"} <= row_fields

    def test_the_row_does_not_carry_the_canonical_content(self) -> None:
        """The one field that blocks the rebuild, asserted rather than assumed.

        If a future change adds the CVE body to the index row, this test fails and the
        next reader is sent to ADR 0089 to decide whether the deferral is over.
        """
        row_fields = {item.name for item in fields(ProjectedNvdIndexRow)}
        assert "canonical_json" not in row_fields
        assert "observed_version" not in row_fields

    def test_the_record_still_demands_that_content(self) -> None:
        """The blocker is in the consumer's type, so the consumer is what is checked."""
        observed_fields = {item.name for item in fields(ObservedCveVersion)}
        assert "canonical_json" in observed_fields
