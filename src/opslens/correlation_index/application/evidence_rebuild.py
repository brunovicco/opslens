"""Rebuild the evidence the request path consumes, from the index that answers it.

Gate 20.1 asks the projection to preserve "enough of each source record to rebuild the
typed evidence the port demands". That sentence is a claim about field coverage, and a
claim about field coverage is exactly the kind that rots silently: the projection was
first contracted without `github_identifiers`, which `GhsaPyPIVulnerabilityEvidence`
requires, and nothing in the types said so.

So the claim is made executable here. `rebuild_ghsa_evidence` is the only place that
maps a stored row onto the consumer's type, and its test asserts field coverage from
`dataclasses.fields` rather than from a list someone maintains. Adding a field to the
evidence type now fails a test instead of producing an index that cannot feed it.

```text
preserved enough != preserved everything
a claim about coverage != a check of coverage
```
"""

from opslens.correlation.adapters.ghsa import (
    GhsaPyPIVulnerabilityEvidence,
    GhsaSourceIdentifierEvidence,
)
from opslens.correlation_index.domain.index_contract import ProjectedGhsaIndexRow


def rebuild_ghsa_evidence(row: ProjectedGhsaIndexRow) -> GhsaPyPIVulnerabilityEvidence:
    """Rebuild one typed GHSA occurrence from its stored index row.

    The row's own validation already enforces what the request path checks, so this
    reconstructs rather than re-validates. It invents nothing: every field comes from
    the row, which is the property that makes the index sufficient.

    Args:
        row: One stored index row.

    Returns:
        The evidence the public threat authority returns for that occurrence.
    """
    return GhsaPyPIVulnerabilityEvidence(
        observed_advisory_version_id=row.observed_advisory_version_id,
        source_advisory_sha256=row.source_advisory_sha256,
        ghsa_id=row.ghsa_id,
        github_cve_id=row.github_cve_id,
        github_identifiers=tuple(
            GhsaSourceIdentifierEvidence(
                identifier_type=item.identifier_type, value=item.value
            )
            for item in row.github_identifiers
        ),
        vulnerability_entry_id=row.vulnerability_entry_id,
        source_index=row.source_index,
        source_entry_sha256=row.source_entry_sha256,
        ecosystem_original=row.ecosystem_original,
        package_name_original=row.package_name_original,
        vulnerable_range_original=row.vulnerable_range_original,
        first_patched_version_original=row.first_patched_version_original,
    )
