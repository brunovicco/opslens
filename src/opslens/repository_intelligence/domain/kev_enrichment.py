"""Complete-snapshot CISA KEV evidence for affected repository findings."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum

from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.repository_intelligence.domain.errors import (
    InvalidRepositoryKevEnrichmentError,
    RepositoryKevEnrichmentLimitError,
)
from opslens.repository_intelligence.domain.nvd_enrichment import (
    RepositoryNvdEnrichedFinding,
    RepositoryNvdEnrichmentEvidence,
)
from opslens.transformation.kev.domain.errors import InvalidKevSilverSourceError
from opslens.transformation.kev.domain.models import SilverKevRecord
from opslens.transformation.kev.domain.transformer import KevSilverTransformer

MAX_KEV_ENRICHMENT_RECORDS = 50_000
MAX_KEV_ENRICHMENT_BYTES = 32 * 1024 * 1024
_KEV_ENRICHMENT_SCHEMA_VERSION = "1"
_KEV_ENRICHMENT_ENGINE = "opslens.phase4.repository-kev.v1"


class RepositoryKevState(StrEnum):
    """Deterministic membership states against one complete CISA KEV snapshot."""

    PRESENT = "present"
    ABSENT = "absent"
    CVE_UNAVAILABLE = "cve_unavailable"


@dataclass(frozen=True, slots=True)
class RepositoryKevSnapshotEvidence:
    """Validate and index one complete immutable CISA KEV catalog snapshot."""

    snapshot: KevCatalogSnapshot
    records: tuple[SilverKevRecord, ...] = field(init=False)
    _records_by_cve: dict[str, SilverKevRecord] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Verify bytes, bounds, and complete Silver transformation before membership use."""
        if self.snapshot.record_count > MAX_KEV_ENRICHMENT_RECORDS:
            raise RepositoryKevEnrichmentLimitError(
                "Repository KEV enrichment exceeds the KEV record bound."
            )
        if self.snapshot.payload_size_bytes > MAX_KEV_ENRICHMENT_BYTES:
            raise RepositoryKevEnrichmentLimitError(
                "Repository KEV enrichment exceeds the KEV source-byte bound."
            )

        calculated_sha256 = hashlib.sha256(self.snapshot.raw_bytes).hexdigest()
        if calculated_sha256 != self.snapshot.sha256:
            raise InvalidRepositoryKevEnrichmentError(
                "KEV snapshot SHA-256 does not match the supplied immutable source bytes."
            )

        try:
            records = tuple(KevSilverTransformer().iter_records(self.snapshot))
        except (InvalidKevSilverSourceError, ValueError) as exc:
            raise InvalidRepositoryKevEnrichmentError(
                "KEV snapshot cannot produce complete deterministic Silver evidence."
            ) from exc

        if len(records) != self.snapshot.record_count:
            raise InvalidRepositoryKevEnrichmentError(
                "KEV transformed record count does not match the complete snapshot."
            )

        records_by_cve = {record.cve: record for record in records}
        if len(records_by_cve) != len(records):
            raise InvalidRepositoryKevEnrichmentError(
                "KEV complete snapshot must contain unique CVE identities."
            )

        object.__setattr__(self, "records", records)
        object.__setattr__(self, "_records_by_cve", records_by_cve)

    def record_for_cve(self, cve_id: str) -> SilverKevRecord | None:
        """Return exact KEV membership evidence from the validated complete snapshot."""
        return self._records_by_cve.get(cve_id)

    @property
    def snapshot_sha256(self) -> str:
        """Return the immutable Bronze source digest used for all membership decisions."""
        return self.snapshot.sha256


@dataclass(frozen=True, slots=True)
class RepositoryKevEnrichedFinding:
    """Attach complete-snapshot KEV membership evidence to one NVD-enriched finding."""

    previous: RepositoryNvdEnrichedFinding
    kev_snapshot: RepositoryKevSnapshotEvidence
    state: RepositoryKevState
    kev_record: SilverKevRecord | None

    def __post_init__(self) -> None:
        """Require state and optional KEV row to equal deterministic snapshot membership."""
        cve_id = self.previous.alias.github_cve_id
        expected_record = (
            self.kev_snapshot.record_for_cve(cve_id)
            if cve_id is not None
            else None
        )
        if cve_id is None:
            expected_state = RepositoryKevState.CVE_UNAVAILABLE
        elif expected_record is None:
            expected_state = RepositoryKevState.ABSENT
        else:
            expected_state = RepositoryKevState.PRESENT

        if self.state is not expected_state:
            raise InvalidRepositoryKevEnrichmentError(
                "Repository KEV state does not match the complete supplied snapshot."
            )
        if self.kev_record != expected_record:
            raise InvalidRepositoryKevEnrichmentError(
                "Repository KEV record does not match exact complete-snapshot membership."
            )

    @property
    def evaluated_cve_id(self) -> str | None:
        """Return the GitHub-asserted CVE used for KEV membership when available."""
        return self.previous.alias.github_cve_id

    @property
    def canonical_json(self) -> bytes:
        """Return stable canonical JSON for immutable KEV enrichment evidence."""
        snapshot = self.kev_snapshot.snapshot
        payload: dict[str, object] = {
            "schema_version": _KEV_ENRICHMENT_SCHEMA_VERSION,
            "engine": _KEV_ENRICHMENT_ENGINE,
            "previous_enrichment": {
                "enrichment_id": self.previous.enrichment_id,
                "evidence_sha256": self.previous.evidence_sha256,
            },
            "cve_id": self.evaluated_cve_id,
            "kev_state": self.state.value,
            "kev_snapshot": {
                "catalog_version": snapshot.catalog_version,
                "date_released": snapshot.date_released.isoformat(),
                "retrieved_at": snapshot.retrieved_at.isoformat(),
                "snapshot_date": snapshot.snapshot_date,
                "source_sha256": snapshot.sha256,
                "record_count": snapshot.record_count,
                "payload_size_bytes": snapshot.payload_size_bytes,
            },
            "kev_record": (
                _kev_record_payload(self.kev_record)
                if self.kev_record is not None
                else None
            ),
        }
        return _canonical_json(payload)

    @property
    def evidence_sha256(self) -> str:
        """Return SHA-256 of canonical complete-snapshot KEV enrichment evidence."""
        return hashlib.sha256(self.canonical_json).hexdigest()

    @property
    def enrichment_id(self) -> str:
        """Return content-addressed KEV enrichment identity."""
        return f"repository-kev-enrichment:v1@sha256:{self.evidence_sha256}"


@dataclass(frozen=True, slots=True)
class RepositoryKevEnrichmentEvidence:
    """Complete KEV membership accounting for every affected repository finding."""

    previous: RepositoryNvdEnrichmentEvidence
    kev_snapshot: RepositoryKevSnapshotEvidence
    enriched_findings: tuple[RepositoryKevEnrichedFinding, ...]

    def __post_init__(self) -> None:
        """Require exactly one KEV enrichment for every previous finding in stable order."""
        observed_previous = tuple(
            enriched.previous for enriched in self.enriched_findings
        )
        if observed_previous != self.previous.enriched_findings:
            raise InvalidRepositoryKevEnrichmentError(
                "Repository KEV enrichment must preserve every previous finding "
                "exactly once and in order."
            )
        if any(
            enriched.kev_snapshot != self.kev_snapshot
            for enriched in self.enriched_findings
        ):
            raise InvalidRepositoryKevEnrichmentError(
                "Every repository KEV enrichment must use the same complete snapshot."
            )

        enrichment_ids = [
            enriched.enrichment_id for enriched in self.enriched_findings
        ]
        if len(set(enrichment_ids)) != len(enrichment_ids):
            raise InvalidRepositoryKevEnrichmentError(
                "Repository KEV enrichment records must have unique identities."
            )

    @property
    def present_count(self) -> int:
        """Return affected findings present in the complete supplied KEV snapshot."""
        return sum(
            enriched.state is RepositoryKevState.PRESENT
            for enriched in self.enriched_findings
        )

    @property
    def absent_count(self) -> int:
        """Return affected findings proven absent from the complete supplied snapshot."""
        return sum(
            enriched.state is RepositoryKevState.ABSENT
            for enriched in self.enriched_findings
        )

    @property
    def cve_unavailable_count(self) -> int:
        """Return findings whose GHSA evidence did not provide a CVE for KEV lookup."""
        return sum(
            enriched.state is RepositoryKevState.CVE_UNAVAILABLE
            for enriched in self.enriched_findings
        )


def _kev_record_payload(record: SilverKevRecord) -> dict[str, object]:
    """Serialize complete normalized KEV row evidence without applying risk policy."""
    return {
        "cve": record.cve,
        "vendor_project": record.vendor_project,
        "product": record.product,
        "vulnerability_name": record.vulnerability_name,
        "date_added": record.date_added.isoformat(),
        "short_description": record.short_description,
        "required_action": record.required_action,
        "due_date": record.due_date.isoformat(),
        "known_ransomware_campaign_use": record.known_ransomware_campaign_use.value,
        "notes": record.notes,
        "cwes": list(record.cwes),
        "catalog_version": record.catalog_version,
        "catalog_date_released": record.catalog_date_released.isoformat(),
        "source": record.source,
        "source_sha256": record.source_sha256,
        "retrieved_at": record.retrieved_at.isoformat(),
        "snapshot_date": record.snapshot_date.isoformat(),
    }


def _canonical_json(payload: dict[str, object]) -> bytes:
    """Encode KEV enrichment evidence using deterministic Canonical JSON v1."""
    try:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise InvalidRepositoryKevEnrichmentError(
            "Repository KEV enrichment contains a non-canonicalizable value."
        ) from exc
    return text.encode("utf-8")
