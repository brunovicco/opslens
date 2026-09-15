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
                # GitHub returns "" for these two when it has none, so empty and
                # absent mean the same thing upstream. They are pure passthrough
                # links carrying no identity, applicability or severity, so
                # rejecting a whole advisory over one would discard the package and
                # range that correlation needs. See ADR 0085.
                repository_advisory_url=self._optional_text(
                    source_advisory,
                    "repository_advisory_url",
                    empty_means_absent=True,
                ),
                source_code_location=self._optional_text(
                    source_advisory,
                    "source_code_location",
                    empty_means_absent=True,
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
        *,
        empty_means_absent: bool = False,
    ) -> str | None:
        """Read one nullable source string without rewriting it.

        Args:
            source_advisory: The verified canonical advisory object.
            field_name: Field to read.
            empty_means_absent: Whether upstream's empty string means "not supplied"
                for this field. True only for pure passthrough links, never for a
                field carrying identity: reading `""` as absent is safe when nothing
                depends on the value, and a silent loss of meaning when something does.

        Returns:
            The string, or None when upstream supplied nothing.

        Raises:
            InvalidGhsaAdvisoryCoreRecordError: If the value is neither a string nor
                null, or is empty for a field where empty is not a legitimate absence.
        """
        value = source_advisory[field_name]

        if value is None:
            return None

        if not isinstance(value, str):
            raise InvalidGhsaAdvisoryCoreRecordError(
                f"GitHub advisory field {field_name!r} must be a string or null."
            )

        if not value.strip():
            if empty_means_absent:
                return None
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
