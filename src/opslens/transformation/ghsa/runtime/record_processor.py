"""Compose GHSA Silver records from verified Bronze advisory occurrences.

One malformed advisory used to abort the whole manifest, so a single upstream record
the V1 validators did not anticipate discarded every other advisory promoted with it.
Real GHSA data contains such records, and a discarded advisory becomes a silent
absence downstream — which becomes "no known vulnerability". Excessive strictness
reaches the same wrong answer as laxity.

So a page is composed with partial admission and exact accounting: every occurrence
ends up either admitted or rejected with a reason, never dropped. The invariant that
matters is preserved and in fact strengthened — admitted plus rejected must equal the
Bronze manifest's own item count. See ADR 0085.

```text
admitted + rejected == total_items
rejected advisory != absent advisory
excessive strictness != safety
```
"""

import json
from dataclasses import dataclass
from typing import cast

from opslens.transformation.ghsa.application.record_composer import (
    GhsaSilverRecordComposerV1,
)
from opslens.transformation.ghsa.runtime.page_processor import (
    GhsaVerifiedBronzePageV1,
)
from opslens.transformation.ghsa.runtime.provenance import (
    GhsaBronzeAdvisoryOccurrenceV1,
)
from opslens.transformation.ghsa.serialization.models import (
    GhsaSilverRecordV1,
)


@dataclass(frozen=True, slots=True)
class GhsaSilverRejectedAdvisoryV1:
    """One verified Bronze occurrence the Silver transformers could not normalize.

    Attributes:
        observed_advisory_version_id: The exact Bronze content identity.
        reason: The transformer's own message, preserved rather than reworded.
    """

    observed_advisory_version_id: str
    reason: str

    def __post_init__(self) -> None:
        """Require an identity and a stated reason.

        Raises:
            ValueError: If either field is blank, since a rejection with no reason is
                indistinguishable from a dropped record.
        """
        if not self.observed_advisory_version_id.strip():
            raise ValueError("a rejected GHSA advisory must carry its content identity")
        if not self.reason.strip():
            raise ValueError("a rejected GHSA advisory must carry a stated reason")


@dataclass(frozen=True, slots=True)
class GhsaSilverPageCompositionV1:
    """Complete accounting for one composed page: what was admitted, what was not.

    Attributes:
        records: Admitted occurrence/record bindings, in source order.
        rejected: Occurrences no transformer could normalize, in source order.
    """

    records: tuple["GhsaSilverOccurrenceRecordV1", ...]
    rejected: tuple[GhsaSilverRejectedAdvisoryV1, ...]

    @property
    def accounted_count(self) -> int:
        """Return how many source occurrences this page accounted for."""
        return len(self.records) + len(self.rejected)


@dataclass(frozen=True, slots=True)
class GhsaSilverOccurrenceRecordV1:
    """Bind one exact Bronze occurrence to its normalized Silver record."""

    occurrence: GhsaBronzeAdvisoryOccurrenceV1
    record: GhsaSilverRecordV1

    def __post_init__(self) -> None:
        """Require physical provenance and Silver content identity to agree."""
        if (
            self.record.core.observed_version
            != self.occurrence.observed_version
        ):
            raise ValueError(
                "GHSA Silver record does not match the exact "
                "Bronze advisory content version."
            )

    @property
    def observed_advisory_version_id(self) -> str:
        """Return the content identity shared by Bronze and Silver."""
        return self.occurrence.observed_advisory_version_id


class GhsaSilverRecordProcessorV1:
    """Normalize verified Bronze occurrences into bound Silver records."""

    def __init__(
        self,
        *,
        composer: GhsaSilverRecordComposerV1,
    ) -> None:
        """Initialize the deterministic Silver record composer."""
        self._composer = composer

    def process_page(
        self,
        verified_page: GhsaVerifiedBronzePageV1,
    ) -> GhsaSilverPageCompositionV1:
        """Compose Silver records from every verified occurrence, accounting for each.

        A record the transformers refuse is recorded with its reason rather than
        aborting the page, so one unanticipated upstream advisory cannot discard every
        advisory promoted alongside it.

        Args:
            verified_page: One verified Bronze page.

        Returns:
            The admitted bindings and the rejected occurrences, both in source order.
        """
        records: list[GhsaSilverOccurrenceRecordV1] = []
        rejected: list[GhsaSilverRejectedAdvisoryV1] = []

        for occurrence in verified_page.occurrences:
            try:
                records.append(self._compose_occurrence(occurrence))
            except ValueError as exc:
                # ValueError is the base of every transformer and domain rejection
                # here. An unexpected error type still propagates, because only a
                # stated domain refusal is safe to account for and continue past.
                rejected.append(
                    GhsaSilverRejectedAdvisoryV1(
                        observed_advisory_version_id=(
                            occurrence.observed_advisory_version_id
                        ),
                        reason=str(exc),
                    )
                )

        return GhsaSilverPageCompositionV1(
            records=tuple(records),
            rejected=tuple(rejected),
        )

    def _compose_occurrence(
        self,
        occurrence: GhsaBronzeAdvisoryOccurrenceV1,
    ) -> GhsaSilverOccurrenceRecordV1:
        """Compose one Silver record from canonical verified source content."""
        source_advisory = self._source_advisory(occurrence)
        record = self._composer.compose(source_advisory)

        return GhsaSilverOccurrenceRecordV1(
            occurrence=occurrence,
            record=record,
        )

    @staticmethod
    def _source_advisory(
        occurrence: GhsaBronzeAdvisoryOccurrenceV1,
    ) -> dict[str, object]:
        """Reconstruct source data only from validated canonical advisory bytes."""
        canonical_json = occurrence.observed_version.canonical_json

        try:
            parsed = cast(
                object,
                json.loads(canonical_json.decode("utf-8")),
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                "GHSA verified advisory canonical JSON cannot be decoded."
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                "GHSA verified advisory canonical JSON must contain an object."
            )

        return cast(dict[str, object], parsed)
