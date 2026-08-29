"""Runtime boundary models for GHSA Silver transformation."""

import re
from dataclasses import dataclass

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class GhsaSilverRuntimeRequestV1:
    """Identify one exact GHSA Bronze COMPLETE manifest to process."""

    manifest_key: str
    manifest_version_id: str

    def __post_init__(self) -> None:
        """Validate one untrusted exact-object coordinate envelope."""
        if not self.manifest_key.strip():
            raise ValueError("GHSA Silver runtime manifest key cannot be empty.")

        if not self.manifest_version_id.strip():
            raise ValueError(
                "GHSA Silver runtime manifest VersionId cannot be empty."
            )


@dataclass(frozen=True, slots=True)
class GhsaSilverRuntimeResultV1:
    """Describe one successfully persisted GHSA Silver Bronze attempt."""

    sync_id: str
    attempt_id: str

    bronze_manifest_key: str
    bronze_manifest_version_id: str

    logical_record_set_sha256: str

    silver_complete_key: str
    silver_complete_version_id: str
    silver_complete_sha256: str

    row_count: int
    content_object_count: int

    def __post_init__(self) -> None:
        """Validate exact runtime completion evidence."""
        for field_name, value in (
            ("sync_id", self.sync_id),
            ("attempt_id", self.attempt_id),
            (
                "logical_record_set_sha256",
                self.logical_record_set_sha256,
            ),
            (
                "silver_complete_sha256",
                self.silver_complete_sha256,
            ),
        ):
            if _SHA256_PATTERN.fullmatch(value) is None:
                raise ValueError(
                    f"GHSA Silver runtime {field_name} must be a "
                    "lowercase SHA-256 digest."
                )

        for field_name, value in (
            ("bronze_manifest_key", self.bronze_manifest_key),
            (
                "bronze_manifest_version_id",
                self.bronze_manifest_version_id,
            ),
            ("silver_complete_key", self.silver_complete_key),
            (
                "silver_complete_version_id",
                self.silver_complete_version_id,
            ),
        ):
            if not value.strip():
                raise ValueError(
                    f"GHSA Silver runtime {field_name} cannot be empty."
                )

        if type(self.row_count) is not int or self.row_count < 0:
            raise ValueError(
                "GHSA Silver runtime row_count must be non-negative."
            )

        if (
            type(self.content_object_count) is not int
            or self.content_object_count < 0
        ):
            raise ValueError(
                "GHSA Silver runtime content_object_count must be non-negative."
            )

        if self.content_object_count != self.row_count:
            raise ValueError(
                "GHSA Silver runtime content_object_count must match row_count."
            )
