"""Deterministic normalization of GitHub advisory scalar Silver fields."""

from datetime import UTC, datetime

from opslens.transformation.ghsa.domain.errors import (
    InvalidGhsaAdvisoryCoreRecordError,
)
from opslens.transformation.ghsa.domain.models import (
    GhsaAdvisoryCoreRecord,
    GhsaAdvisorySeverity,
    GhsaAdvisoryType,
    ObservedGhsaAdvisoryVersion,
)


class GhsaAdvisoryCoreTransformer:
    """Normalize scalar fields from one complete reviewed GitHub advisory."""

    REQUIRED_FIELDS = frozenset(
        {
            "ghsa_id",
            "cve_id",
            "url",
            "html_url",
            "repository_advisory_url",
            "summary",
            "description",
            "type",
            "severity",
            "source_code_location",
            "published_at",
            "updated_at",
            "github_reviewed_at",
            "nvd_published_at",
            "withdrawn_at",
        }
    )

    def transform(self, source_advisory: dict[str, object]) -> GhsaAdvisoryCoreRecord:
        """Normalize one GitHub REST advisory into its core Silver representation."""
        missing_fields = self.REQUIRED_FIELDS - source_advisory.keys()

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"GitHub advisory is missing required core fields: {missing}."
            )

        observed_version = ObservedGhsaAdvisoryVersion.from_source(source_advisory)

        try:
            advisory_type = GhsaAdvisoryType(self._required_text(source_advisory, "type"))
        except ValueError as exc:
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"Unsupported GitHub advisory type: {source_advisory['type']!r}."
            ) from exc

        if advisory_type is not GhsaAdvisoryType.REVIEWED:
            raise InvalidGhsaAdvisoryCoreRecordError(
                "Phase 2.4 GHSA Silver accepts reviewed advisories only."
            )

        try:
            severity = GhsaAdvisorySeverity(
                self._required_text(source_advisory, "severity")
            )
        except ValueError as exc:
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"Unsupported GitHub advisory severity: {source_advisory['severity']!r}."
            ) from exc

        try:
            return GhsaAdvisoryCoreRecord(
                observed_version=observed_version,
                cve_id=self._optional_text(source_advisory, "cve_id"),
                advisory_type=advisory_type,
                severity=severity,
                url=self._required_text(source_advisory, "url"),
                html_url=self._required_text(source_advisory, "html_url"),
                repository_advisory_url=self._optional_text(
                    source_advisory,
                    "repository_advisory_url",
                ),
                source_code_location=self._optional_text(
                    source_advisory,
                    "source_code_location",
                ),
                summary=self._required_text(source_advisory, "summary"),
                description=self._required_text(source_advisory, "description"),
                published_at=self._required_timestamp(source_advisory, "published_at"),
                updated_at=self._required_timestamp(source_advisory, "updated_at"),
                github_reviewed_at=self._optional_timestamp(
                    source_advisory,
                    "github_reviewed_at",
                ),
                nvd_published_at=self._optional_timestamp(
                    source_advisory,
                    "nvd_published_at",
                ),
                withdrawn_at=self._optional_timestamp(
                    source_advisory,
                    "withdrawn_at",
                ),
            )
        except ValueError as exc:
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"Invalid GitHub advisory core record {observed_version.ghsa_id!r}: {exc}"
            ) from exc

    @staticmethod
    def _required_text(
        source_advisory: dict[str, object],
        field_name: str,
    ) -> str:
        """Read one required non-empty source string without rewriting it."""
        value = source_advisory[field_name]

        if not isinstance(value, str):
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"GitHub advisory field {field_name!r} must be a string."
            )

        if not value.strip():
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"GitHub advisory field {field_name!r} cannot be empty."
            )

        return value

    @staticmethod
    def _optional_text(
        source_advisory: dict[str, object],
        field_name: str,
    ) -> str | None:
        """Read one nullable source string without rewriting it."""
        value = source_advisory[field_name]

        if value is None:
            return None

        if not isinstance(value, str):
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"GitHub advisory field {field_name!r} must be a string or null."
            )

        if not value.strip():
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"GitHub advisory field {field_name!r} cannot be empty when present."
            )

        return value

    @classmethod
    def _required_timestamp(
        cls,
        source_advisory: dict[str, object],
        field_name: str,
    ) -> datetime:
        """Parse one required GitHub ISO-8601 timestamp into UTC."""
        value = source_advisory[field_name]

        if not isinstance(value, str):
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"GitHub advisory field {field_name!r} must be a timestamp string."
            )

        return cls._parse_timestamp(value, field_name=field_name)

    @classmethod
    def _optional_timestamp(
        cls,
        source_advisory: dict[str, object],
        field_name: str,
    ) -> datetime | None:
        """Parse one nullable GitHub ISO-8601 timestamp into UTC."""
        value = source_advisory[field_name]

        if value is None:
            return None

        if not isinstance(value, str):
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"GitHub advisory field {field_name!r} must be a timestamp string or null."
            )

        return cls._parse_timestamp(value, field_name=field_name)

    @staticmethod
    def _parse_timestamp(value: str, *, field_name: str) -> datetime:
        """Parse a timezone-aware GitHub timestamp and normalize it to UTC."""
        normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"GitHub advisory field {field_name!r} contains an invalid "
                f"timestamp: {value!r}."
            ) from exc

        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"GitHub advisory field {field_name!r} must include a timezone offset."
            )

        return parsed.astimezone(UTC)
