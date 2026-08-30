"""Compose GHSA Silver records from verified Bronze advisory occurrences."""

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
    ) -> tuple[GhsaSilverOccurrenceRecordV1, ...]:
        """Compose Silver records from every verified occurrence in source order."""
        return tuple(
            self._compose_occurrence(occurrence)
            for occurrence in verified_page.occurrences
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
