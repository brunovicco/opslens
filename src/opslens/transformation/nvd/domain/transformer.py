"""Deterministic normalization of NVD CVE scalar Silver fields."""

from datetime import UTC, datetime

from opslens.transformation.nvd.domain.errors import (
    InvalidNvdCveCoreRecordError,
)
from opslens.transformation.nvd.domain.models import (
    NvdCveCoreRecord,
    NvdVulnerabilityStatus,
    ObservedCveVersion,
)


class NvdCveCoreTransformer:
    """Normalize scalar fields from one complete observed NVD CVE object."""

    REQUIRED_FIELDS = frozenset(
        {
            "id",
            "sourceIdentifier",
            "published",
            "lastModified",
            "vulnStatus",
        }
    )

    def transform(self, source_cve: dict[str, object]) -> NvdCveCoreRecord:
        """Normalize one NVD CVE object into its core Silver representation."""
        missing_fields = self.REQUIRED_FIELDS - source_cve.keys()

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise InvalidNvdCveCoreRecordError(
                f"NVD CVE is missing required core fields: {missing}."
            )

        observed_version = ObservedCveVersion.from_source(source_cve)

        try:
            vuln_status = NvdVulnerabilityStatus(self._required_text(source_cve, "vulnStatus"))
        except ValueError as exc:
            raise InvalidNvdCveCoreRecordError(
                f"Unsupported NVD vulnStatus: {source_cve['vulnStatus']!r}."
            ) from exc

        try:
            return NvdCveCoreRecord(
                observed_version=observed_version,
                source_identifier=self._required_text(
                    source_cve,
                    "sourceIdentifier",
                ),
                published_at=self._timestamp(
                    source_cve,
                    "published",
                ),
                last_modified_at=self._timestamp(
                    source_cve,
                    "lastModified",
                ),
                vuln_status=vuln_status,
            )
        except ValueError as exc:
            raise InvalidNvdCveCoreRecordError(
                f"Invalid NVD CVE core record {observed_version.cve_id!r}: {exc}"
            ) from exc

    @staticmethod
    def _required_text(
        source_cve: dict[str, object],
        field_name: str,
    ) -> str:
        """Read one required non-empty source string without rewriting it."""
        value = source_cve[field_name]

        if not isinstance(value, str):
            raise InvalidNvdCveCoreRecordError(f"NVD field {field_name!r} must be a string.")

        if not value.strip():
            raise InvalidNvdCveCoreRecordError(f"NVD field {field_name!r} cannot be empty.")

        return value

    @staticmethod
    def _timestamp(
        source_cve: dict[str, object],
        field_name: str,
    ) -> datetime:
        """Parse an NVD ISO-8601 timestamp and normalize it to UTC."""
        value = source_cve[field_name]

        if not isinstance(value, str):
            raise InvalidNvdCveCoreRecordError(
                f"NVD field {field_name!r} must be a timestamp string."
            )

        normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise InvalidNvdCveCoreRecordError(
                f"NVD field {field_name!r} contains an invalid timestamp: {value!r}."
            ) from exc

        # NVD API 2.0 response timestamps are UTC even when their serialized
        # representation omits an explicit offset.
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)

        return parsed.astimezone(UTC)
