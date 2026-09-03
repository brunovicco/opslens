"""Exact-snapshot EPSS evidence for affected repository findings."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import TypeAlias

from opslens.ingestion.epss.domain.errors import InvalidEpssSnapshotError
from opslens.ingestion.epss.domain.history import (
    HistoricalEpssSnapshot,
    HistoricalEpssSnapshotParser,
)
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.repository_intelligence.domain.errors import (
    InvalidRepositoryEpssEnrichmentError,
    RepositoryEpssEnrichmentLimitError,
)
from opslens.repository_intelligence.domain.kev_enrichment import (
    RepositoryKevEnrichedFinding,
    RepositoryKevEnrichmentEvidence,
)
from opslens.transformation.epss.domain.errors import InvalidEpssSilverSourceError
from opslens.transformation.epss.domain.models import SilverEpssRecord
from opslens.transformation.epss.domain.transformer import EpssSilverTransformer
from opslens.transformation.epss.history.preparation import (
    HistoricalEpssSilverRecordTransformer,
)

MAX_EPSS_ENRICHMENT_RECORDS = 1_000_000
MAX_EPSS_ENRICHMENT_BYTES = 64 * 1024 * 1024
_EPSS_ENRICHMENT_SCHEMA_VERSION = "1"
_EPSS_ENRICHMENT_ENGINE = "opslens.phase4.repository-epss.v1"

RepositoryEpssSourceSnapshot: TypeAlias = EpssSnapshot | HistoricalEpssSnapshot


class RepositoryEpssSnapshotKind(StrEnum):
    """Supported immutable EPSS source snapshot kinds."""

    CURRENT = "current"
    HISTORICAL = "historical"


class RepositoryEpssState(StrEnum):
    """Deterministic CVE score states against one complete EPSS snapshot."""

    SCORE_PRESENT = "score_present"
    SCORE_ABSENT = "score_absent"
    CVE_UNAVAILABLE = "cve_unavailable"


@dataclass(frozen=True, slots=True)
class RepositoryEpssSnapshotEvidence:
    """Revalidate and index one complete current or historical EPSS snapshot."""

    snapshot: RepositoryEpssSourceSnapshot
    kind: RepositoryEpssSnapshotKind = field(init=False)
    records: tuple[SilverEpssRecord, ...] = field(init=False)
    _records_by_cve: dict[str, SilverEpssRecord] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Verify bytes, bounds, parser identity, and complete Silver transformation."""
        if self.snapshot.row_count > MAX_EPSS_ENRICHMENT_RECORDS:
            raise RepositoryEpssEnrichmentLimitError(
                "Repository EPSS enrichment exceeds the EPSS record bound."
            )
        if len(self.snapshot.raw_bytes) > MAX_EPSS_ENRICHMENT_BYTES:
            raise RepositoryEpssEnrichmentLimitError(
                "Repository EPSS enrichment exceeds the EPSS source-byte bound."
            )

        calculated_sha256 = hashlib.sha256(self.snapshot.raw_bytes).hexdigest()
        if calculated_sha256 != self.snapshot.sha256:
            raise InvalidRepositoryEpssEnrichmentError(
                "EPSS snapshot SHA-256 does not match the supplied immutable source bytes."
            )

        try:
            kind, validated, records = _revalidate_and_transform(self.snapshot)
        except (InvalidEpssSnapshotError, InvalidEpssSilverSourceError, ValueError) as exc:
            raise InvalidRepositoryEpssEnrichmentError(
                "EPSS snapshot cannot produce complete deterministic Silver evidence."
            ) from exc

        if validated != self.snapshot:
            raise InvalidRepositoryEpssEnrichmentError(
                "EPSS snapshot metadata does not match reparsed immutable source bytes."
            )
        if len(records) != self.snapshot.row_count:
            raise InvalidRepositoryEpssEnrichmentError(
                "EPSS transformed row count does not match the complete snapshot."
            )

        records_by_cve = {record.cve: record for record in records}
        if len(records_by_cve) != len(records):
            raise InvalidRepositoryEpssEnrichmentError(
                "EPSS complete snapshot must contain unique CVE identities."
            )

        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "_records_by_cve", records_by_cve)

    def record_for_cve(self, cve_id: str) -> SilverEpssRecord | None:
        """Return exact score evidence from the fully validated selected snapshot."""
        return self._records_by_cve.get(cve_id)

    @property
    def snapshot_date(self) -> date:
        """Return the canonical selected EPSS observation date."""
        if isinstance(self.snapshot, EpssSnapshot):
            return date.fromisoformat(self.snapshot.snapshot_date)
        return self.snapshot.snapshot_date

    @property
    def model_version(self) -> str | None:
        """Return source-declared EPSS model version when present."""
        return self.snapshot.model_version

    @property
    def score_timestamp(self) -> datetime | None:
        """Return source-declared score timestamp when present."""
        return self.snapshot.score_timestamp


@dataclass(frozen=True, slots=True)
class RepositoryEpssEnrichedFinding:
    """Attach one exact EPSS score observation to a KEV-enriched finding."""

    previous: RepositoryKevEnrichedFinding
    epss_snapshot: RepositoryEpssSnapshotEvidence
    state: RepositoryEpssState
    epss_record: SilverEpssRecord | None

    def __post_init__(self) -> None:
        """Require the state and optional score row to equal exact snapshot evidence."""
        cve_id = self.previous.evaluated_cve_id
        expected_record = (
            self.epss_snapshot.record_for_cve(cve_id)
            if cve_id is not None
            else None
        )
        if cve_id is None:
            expected_state = RepositoryEpssState.CVE_UNAVAILABLE
        elif expected_record is None:
            expected_state = RepositoryEpssState.SCORE_ABSENT
        else:
            expected_state = RepositoryEpssState.SCORE_PRESENT

        if self.state is not expected_state:
            raise InvalidRepositoryEpssEnrichmentError(
                "Repository EPSS state does not match the complete supplied snapshot."
            )
        if self.epss_record != expected_record:
            raise InvalidRepositoryEpssEnrichmentError(
                "Repository EPSS record does not match exact complete-snapshot evidence."
            )

    @property
    def evaluated_cve_id(self) -> str | None:
        """Return the GitHub-asserted CVE used for EPSS lookup when available."""
        return self.previous.evaluated_cve_id

    @property
    def canonical_json(self) -> bytes:
        """Return stable canonical JSON for immutable EPSS enrichment evidence."""
        payload: dict[str, object] = {
            "schema_version": _EPSS_ENRICHMENT_SCHEMA_VERSION,
            "engine": _EPSS_ENRICHMENT_ENGINE,
            "previous_enrichment": {
                "enrichment_id": self.previous.enrichment_id,
                "evidence_sha256": self.previous.evidence_sha256,
            },
            "cve_id": self.evaluated_cve_id,
            "epss_state": self.state.value,
            "epss_snapshot": _snapshot_payload(self.epss_snapshot),
            "epss_record": (
                _epss_record_payload(self.epss_record)
                if self.epss_record is not None
                else None
            ),
        }
        return _canonical_json(payload)

    @property
    def evidence_sha256(self) -> str:
        """Return SHA-256 of canonical exact-snapshot EPSS enrichment evidence."""
        return hashlib.sha256(self.canonical_json).hexdigest()

    @property
    def enrichment_id(self) -> str:
        """Return content-addressed EPSS enrichment identity."""
        return f"repository-epss-enrichment:v1@sha256:{self.evidence_sha256}"


@dataclass(frozen=True, slots=True)
class RepositoryEpssEnrichmentEvidence:
    """Complete EPSS accounting for every KEV-enriched affected finding."""

    previous: RepositoryKevEnrichmentEvidence
    epss_snapshot: RepositoryEpssSnapshotEvidence
    enriched_findings: tuple[RepositoryEpssEnrichedFinding, ...]

    def __post_init__(self) -> None:
        """Require one EPSS enrichment per previous finding in stable order."""
        observed_previous = tuple(
            enriched.previous for enriched in self.enriched_findings
        )
        if observed_previous != self.previous.enriched_findings:
            raise InvalidRepositoryEpssEnrichmentError(
                "Repository EPSS enrichment must preserve every previous finding "
                "exactly once and in order."
            )
        if any(
            enriched.epss_snapshot != self.epss_snapshot
            for enriched in self.enriched_findings
        ):
            raise InvalidRepositoryEpssEnrichmentError(
                "Every repository EPSS enrichment must use the same exact snapshot."
            )

        enrichment_ids = [
            enriched.enrichment_id for enriched in self.enriched_findings
        ]
        if len(set(enrichment_ids)) != len(enrichment_ids):
            raise InvalidRepositoryEpssEnrichmentError(
                "Repository EPSS enrichment records must have unique identities."
            )

    @property
    def score_present_count(self) -> int:
        """Return findings with a score in the selected complete EPSS snapshot."""
        return sum(
            enriched.state is RepositoryEpssState.SCORE_PRESENT
            for enriched in self.enriched_findings
        )

    @property
    def score_absent_count(self) -> int:
        """Return findings proven absent from the selected complete EPSS snapshot."""
        return sum(
            enriched.state is RepositoryEpssState.SCORE_ABSENT
            for enriched in self.enriched_findings
        )

    @property
    def cve_unavailable_count(self) -> int:
        """Return findings whose GHSA evidence did not provide a CVE for EPSS lookup."""
        return sum(
            enriched.state is RepositoryEpssState.CVE_UNAVAILABLE
            for enriched in self.enriched_findings
        )


def _revalidate_and_transform(
    snapshot: RepositoryEpssSourceSnapshot,
) -> tuple[
    RepositoryEpssSnapshotKind,
    RepositoryEpssSourceSnapshot,
    tuple[SilverEpssRecord, ...],
]:
    """Reparse exact bytes and fully transform the selected EPSS snapshot kind."""
    if isinstance(snapshot, EpssSnapshot):
        validated = EpssSnapshotParser().parse(snapshot.raw_bytes)
        records = tuple(EpssSilverTransformer().iter_records(validated))
        return RepositoryEpssSnapshotKind.CURRENT, validated, records

    validated_historical = HistoricalEpssSnapshotParser().parse(
        snapshot.raw_bytes,
        snapshot_date=snapshot.snapshot_date,
    )
    historical_records = tuple(
        HistoricalEpssSilverRecordTransformer().iter_records(validated_historical)
    )
    return (
        RepositoryEpssSnapshotKind.HISTORICAL,
        validated_historical,
        historical_records,
    )


def _snapshot_payload(evidence: RepositoryEpssSnapshotEvidence) -> dict[str, object]:
    """Serialize exact current or historical EPSS snapshot coordinates."""
    snapshot = evidence.snapshot
    payload: dict[str, object] = {
        "kind": evidence.kind.value,
        "snapshot_date": evidence.snapshot_date.isoformat(),
        "model_version": evidence.model_version,
        "score_timestamp": (
            evidence.score_timestamp.isoformat()
            if evidence.score_timestamp is not None
            else None
        ),
        "source_sha256": snapshot.sha256,
        "row_count": snapshot.row_count,
        "payload_size_bytes": len(snapshot.raw_bytes),
    }
    if isinstance(snapshot, HistoricalEpssSnapshot):
        payload.update(
            {
                "model_era": snapshot.model_era.value,
                "source_shape": snapshot.source_shape.value,
                "source_metadata_present": snapshot.source_metadata_present,
                "percentile_available": snapshot.percentile_available,
            }
        )
    else:
        payload.update(
            {
                "model_era": None,
                "source_shape": "modern_metadata",
                "source_metadata_present": True,
                "percentile_available": True,
            }
        )
    return payload


def _epss_record_payload(record: SilverEpssRecord) -> dict[str, object]:
    """Serialize normalized EPSS row evidence without applying risk policy."""
    return {
        "cve": record.cve,
        "epss": record.epss,
        "percentile": record.percentile,
        "model_version": record.model_version,
        "score_timestamp": (
            record.score_timestamp.isoformat()
            if record.score_timestamp is not None
            else None
        ),
        "source": record.source,
        "source_sha256": record.source_sha256,
        "snapshot_date": record.snapshot_date.isoformat(),
    }


def _canonical_json(payload: dict[str, object]) -> bytes:
    """Encode EPSS enrichment evidence using deterministic Canonical JSON v1."""
    try:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise InvalidRepositoryEpssEnrichmentError(
            "Repository EPSS enrichment contains a non-canonicalizable value."
        ) from exc
    return text.encode("utf-8")
