"""Semantic provenance verification for CISA KEV Bronze evidence."""

import re
from datetime import datetime

from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.ingestion.kev.domain.parser import KevCatalogParser
from opslens.transformation.kev.adapters.outbound.s3_bronze import (
    KevBronzeObject,
)


class KevBronzeProvenanceError(ValueError):
    """Raised when KEV Bronze metadata disagrees with source evidence."""


class KevBronzeProvenanceVerifier:
    """Reconstruct and verify a KEV catalog snapshot from Bronze evidence."""

    SOURCE_NAME = "cisa-kev"

    REQUIRED_METADATA = frozenset(
        {
            "source",
            "catalog_version",
            "date_released",
            "retrieved_at",
            "sha256",
            "record_count",
        }
    )

    _SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

    def __init__(
        self,
        *,
        parser: KevCatalogParser,
    ) -> None:
        """Initialize the verifier with the canonical KEV source parser.

        Args:
            parser: Parser responsible for validating raw CISA KEV bytes.
        """
        self._parser = parser

    def verify(
        self,
        bronze: KevBronzeObject,
    ) -> KevCatalogSnapshot:
        """Verify Bronze metadata against the immutable source bytes.

        Args:
            bronze: Transport-verified KEV Bronze evidence.

        Returns:
            Reconstructed and semantically verified KEV catalog snapshot.

        Raises:
            KevBronzeProvenanceError: If metadata, partition identity, or
                parsed source evidence disagree.
        """
        metadata = bronze.metadata

        missing = self.REQUIRED_METADATA - metadata.keys()

        if missing:
            missing_fields = ", ".join(sorted(missing))
            raise KevBronzeProvenanceError(
                f"KEV Bronze metadata is missing required fields: {missing_fields}."
            )

        source = self._require_metadata_text(
            metadata["source"],
            field_name="source",
        )

        if source != self.SOURCE_NAME:
            raise KevBronzeProvenanceError(
                f"KEV Bronze metadata source must be {self.SOURCE_NAME!r}, received {source!r}."
            )

        catalog_version = self._require_metadata_text(
            metadata["catalog_version"],
            field_name="catalog_version",
        )

        date_released = self._parse_timestamp(
            metadata["date_released"],
            field_name="date_released",
        )

        retrieved_at = self._parse_timestamp(
            metadata["retrieved_at"],
            field_name="retrieved_at",
        )

        source_sha256 = self._require_metadata_text(
            metadata["sha256"],
            field_name="sha256",
        )

        if self._SHA256_PATTERN.fullmatch(source_sha256) is None:
            raise KevBronzeProvenanceError(
                "KEV Bronze metadata sha256 must contain 64 lowercase hexadecimal characters."
            )

        record_count = self._parse_positive_integer(
            metadata["record_count"],
            field_name="record_count",
        )

        snapshot = self._parser.parse(
            payload=bronze.raw_bytes,
            retrieved_at=retrieved_at,
        )

        self._verify_snapshot(
            bronze=bronze,
            snapshot=snapshot,
            catalog_version=catalog_version,
            date_released=date_released,
            source_sha256=source_sha256,
            record_count=record_count,
        )

        return snapshot

    @staticmethod
    def _require_metadata_text(
        value: str,
        *,
        field_name: str,
    ) -> str:
        """Require one normalized non-empty metadata value."""
        if not value:
            raise KevBronzeProvenanceError(f"KEV Bronze metadata {field_name} cannot be empty.")

        if value != value.strip():
            raise KevBronzeProvenanceError(
                f"KEV Bronze metadata {field_name} must not contain outer whitespace."
            )

        return value

    @staticmethod
    def _parse_timestamp(
        value: str,
        *,
        field_name: str,
    ) -> datetime:
        """Parse one timezone-aware ISO-8601 metadata timestamp."""
        if not value or value != value.strip():
            raise KevBronzeProvenanceError(
                f"KEV Bronze metadata {field_name} must be a normalized ISO-8601 timestamp."
            )

        normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise KevBronzeProvenanceError(
                f"KEV Bronze metadata {field_name} is not a valid ISO-8601 timestamp."
            ) from exc

        if parsed.tzinfo is None:
            raise KevBronzeProvenanceError(
                f"KEV Bronze metadata {field_name} must include timezone information."
            )

        return parsed

    @staticmethod
    def _parse_positive_integer(
        value: str,
        *,
        field_name: str,
    ) -> int:
        """Parse one canonical positive decimal metadata integer."""
        if not value.isdigit():
            raise KevBronzeProvenanceError(
                f"KEV Bronze metadata {field_name} must be a positive decimal integer."
            )

        parsed = int(value)

        if parsed <= 0 or str(parsed) != value:
            raise KevBronzeProvenanceError(
                f"KEV Bronze metadata {field_name} must be a canonical positive decimal integer."
            )

        return parsed

    @staticmethod
    def _verify_snapshot(
        *,
        bronze: KevBronzeObject,
        snapshot: KevCatalogSnapshot,
        catalog_version: str,
        date_released: datetime,
        source_sha256: str,
        record_count: int,
    ) -> None:
        """Cross-check parsed source evidence against Bronze metadata."""
        if snapshot.sha256 != source_sha256:
            raise KevBronzeProvenanceError(
                "KEV Bronze metadata sha256 does not match the source bytes."
            )

        if snapshot.catalog_version != catalog_version:
            raise KevBronzeProvenanceError(
                "KEV Bronze metadata catalog_version does not match the source catalog."
            )

        if snapshot.date_released != date_released:
            raise KevBronzeProvenanceError(
                "KEV Bronze metadata date_released does not match the source catalog."
            )

        if snapshot.record_count != record_count:
            raise KevBronzeProvenanceError(
                "KEV Bronze metadata record_count does not match the source catalog."
            )

        if snapshot.payload_size_bytes != bronze.content_length:
            raise KevBronzeProvenanceError(
                "KEV Bronze payload size does not match verified S3 ContentLength."
            )

        if snapshot.snapshot_date != bronze.reference.snapshot_date.isoformat():
            raise KevBronzeProvenanceError(
                "KEV Bronze snapshot_date partition does not match the UTC retrieved_at date."
            )
