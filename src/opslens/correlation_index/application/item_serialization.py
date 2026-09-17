"""Turn index rows into stored items, and set the only clock the index has.

Two things happen here, and the second is more dangerous than it looks.

**Keying.** Every item's partition key carries the build generation (ADR 0088), so a
build writes where nothing is reading. The keys are built by the contract's own
functions rather than formatted here, because a key assembled in two places is a key
that eventually disagrees with itself.

**Expiry.** Retired generations leave by TTL. The number is not a safety mechanism and
must not be mistaken for one.

A TTL set at write time expires the live generation too, on schedule, whether or not a
newer build ever succeeded. If builds fail for longer than the window, the live index
does not become stale — it becomes *empty*, and an empty index answers "no known
vulnerabilities" for every package with total confidence.

```text
stale index != empty index
expired index != answered honestly
```

So the window is long relative to the rebuild cadence, and it is deliberately not what
keeps a stale index from lying. That is the response contract's job: a response cites
the manifest that answered it and how old it is, and an index past its freshness bound
must produce a distinct outcome rather than a clean bill of health. The TTL only
reclaims space once a newer generation is live.
"""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Final

from opslens.correlation_index.domain.index_contract import (
    ProjectedGhsaIndexRow,
    ProjectedNvdIndexRow,
    ghsa_partition_key,
    index_generation,
    nvd_partition_key,
)

# Long relative to a daily rebuild, so a run of failed builds surfaces as a stale index
# the response contract can refuse to answer from, rather than as an empty one it
# cannot distinguish from a clean corpus.
RETIRED_GENERATION_RETENTION: Final = timedelta(days=14)


def expiry_epoch(built_at: datetime, retention: timedelta = RETIRED_GENERATION_RETENTION) -> int:
    """Return the DynamoDB TTL value for items written by one build.

    Args:
        built_at: When the build ran.
        retention: How long a generation is kept after it is written.

    Returns:
        Epoch seconds, which is the unit DynamoDB TTL reads.

    Raises:
        ValueError: If the instant carries no timezone, or the retention is not
            positive — a non-positive window would expire a generation as it is written.
    """
    if built_at.tzinfo is None:
        raise ValueError("a build instant must be timezone-aware")
    if retention <= timedelta(0):
        raise ValueError("retention must be positive; items would expire as written")
    return int((built_at.astimezone(UTC) + retention).timestamp())


def ghsa_item(
    row: ProjectedGhsaIndexRow, *, index_id: str, expires_at: int
) -> Mapping[str, object]:
    """Serialize one GHSA index row as a stored item.

    Args:
        row: The projected row.
        index_id: The manifest identity this build carries.
        expires_at: TTL value in epoch seconds.

    Returns:
        The item, using plain types the DynamoDB resource API accepts.

    Raises:
        CorrelationIndexContractError: If the identity or the row cannot be keyed.
    """
    generation = index_generation(index_id)
    return {
        "pk": ghsa_partition_key(generation, row.package_name_canonical),
        "sk": row.occurrence_key,
        "expires_at": expires_at,
        "index_id": index_id,
        "package_name_canonical": row.package_name_canonical,
        "observed_advisory_version_id": row.observed_advisory_version_id,
        "source_advisory_sha256": row.source_advisory_sha256,
        "source_entry_sha256": row.source_entry_sha256,
        "ghsa_id": row.ghsa_id,
        "github_cve_id": row.github_cve_id,
        "github_identifiers": [
            {"identifier_type": item.identifier_type, "value": item.value}
            for item in row.github_identifiers
        ],
        "vulnerability_entry_id": row.vulnerability_entry_id,
        "source_index": row.source_index,
        "ecosystem_original": row.ecosystem_original,
        "package_name_original": row.package_name_original,
        "vulnerable_range_original": row.vulnerable_range_original,
        "first_patched_version_original": row.first_patched_version_original,
    }


def nvd_item(
    row: ProjectedNvdIndexRow, *, index_id: str, expires_at: int
) -> Mapping[str, object]:
    """Serialize one NVD index row as a stored item.

    Args:
        row: The projected row.
        index_id: The manifest identity this build carries.
        expires_at: TTL value in epoch seconds.

    Returns:
        The item, using plain types the DynamoDB resource API accepts.

    Raises:
        CorrelationIndexContractError: If the identity or the row cannot be keyed.
    """
    generation = index_generation(index_id)
    return {
        "pk": nvd_partition_key(generation, row.cve_id),
        "expires_at": expires_at,
        "index_id": index_id,
        "cve_id": row.cve_id,
        "observed_cve_version_id": row.observed_cve_version_id,
        "source_cve_sha256": row.source_cve_sha256,
        "source_identifier": row.source_identifier,
        "published_at": row.published_at,
        "last_modified_at": row.last_modified_at,
        "vuln_status": row.vuln_status,
    }


def pointer_document(index_id: str, built_at: str) -> Mapping[str, object]:
    """Build the object that makes one generation live.

    Written last, after every row and the manifest. Until it lands, the new generation
    is unreachable; after it, the old one is.

    Args:
        index_id: The manifest identity of the finished build.
        built_at: When that build ran.

    Returns:
        The pointer document.

    Raises:
        CorrelationIndexContractError: If the identity is not content-addressed.
    """
    return {
        "built_at": built_at,
        "generation": index_generation(index_id),
        "index_id": index_id,
    }
