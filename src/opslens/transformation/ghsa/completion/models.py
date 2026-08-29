"""Exact persisted-object evidence for GHSA Silver v1."""

import re
from dataclasses import dataclass

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class GhsaSilverStoredContentObjectV1:
    """Describe one exact persisted authoritative Silver content row."""

    key: str
    version_id: str

    observed_advisory_version_id: str
    ghsa_id: str
    source_advisory_sha256: str

    parquet_sha256: str
    size_bytes: int
    row_count: int

    def __post_init__(self) -> None:
        """Validate exact persisted content-object evidence."""
        for field_name, value in (
            ("key", self.key),
            ("version_id", self.version_id),
            (
                "observed_advisory_version_id",
                self.observed_advisory_version_id,
            ),
            ("ghsa_id", self.ghsa_id),
        ):
            if not value.strip():
                raise ValueError(
                    f"GHSA Silver stored content {field_name} cannot be empty."
                )

        self._require_sha256(
            self.source_advisory_sha256,
            "source_advisory_sha256",
        )
        self._require_sha256(
            self.parquet_sha256,
            "parquet_sha256",
        )

        expected_observed_id = (
            f"{self.ghsa_id}@sha256:"
            f"{self.source_advisory_sha256}"
        )

        if self.observed_advisory_version_id != expected_observed_id:
            raise ValueError(
                "GHSA Silver stored content observed_advisory_version_id "
                "does not match its advisory content identity."
            )

        if type(self.size_bytes) is not int or self.size_bytes <= 0:
            raise ValueError(
                "GHSA Silver stored content size_bytes must be positive."
            )

        if type(self.row_count) is not int or self.row_count != 1:
            raise ValueError(
                "GHSA Silver authoritative content object "
                "must contain exactly one row."
            )

    @staticmethod
    def _require_sha256(
        value: str,
        field_name: str,
    ) -> None:
        """Require one lowercase hexadecimal SHA-256 digest."""
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError(
                f"GHSA Silver stored content {field_name} must be "
                "a lowercase SHA-256 digest."
            )


@dataclass(frozen=True, slots=True)
class GhsaSilverStoredCompletionV1:
    """Describe one exact persisted GHSA Silver COMPLETE manifest."""

    key: str
    version_id: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        """Validate exact persisted COMPLETE evidence."""
        if not self.key.strip():
            raise ValueError("GHSA Silver completion key cannot be empty.")

        if not self.version_id.strip():
            raise ValueError("GHSA Silver completion VersionId cannot be empty.")

        if _SHA256_PATTERN.fullmatch(self.sha256) is None:
            raise ValueError("GHSA Silver completion SHA-256 is invalid.")

        if type(self.size_bytes) is not int or self.size_bytes <= 0:
            raise ValueError(
                "GHSA Silver completion size_bytes must be positive."
            )
