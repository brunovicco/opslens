"""Application models for EPSS Silver serialization."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class SilverRepositoryWriteStatus(StrEnum):
    """Represent the outcome of an idempotent Silver artifact write."""

    CREATED = "created"
    ALREADY_EXISTS = "already_exists"


@dataclass(frozen=True, slots=True)
class SilverWriteResult:
    """Describe the result of serializing normalized EPSS records.

    Attributes:
        row_count: Number of records successfully serialized.
        size_bytes: Total serialized artifact size in bytes.
        schema_version: Physical Silver schema version used by the writer.
    """

    row_count: int
    size_bytes: int
    schema_version: int

    def __post_init__(self) -> None:
        """Validate invariants of a successful Silver serialization."""
        if self.row_count <= 0:
            raise ValueError("Silver write result must contain at least one row.")

        if self.size_bytes <= 0:
            raise ValueError("Silver write result size must be greater than zero.")

        if self.schema_version <= 0:
            raise ValueError("Silver schema version must be greater than zero.")


@dataclass(frozen=True, slots=True)
class EpssSilverTransformationResult:
    """Describe the outcome of one Bronze-to-Silver transformation."""

    bronze_key: str
    silver_key: str
    snapshot_date: date
    row_count: int
    size_bytes: int
    schema_version: int
    source_sha256: str
    write_status: SilverRepositoryWriteStatus

    def __post_init__(self) -> None:
        """Validate the completed transformation result."""
        if not self.bronze_key.strip():
            raise ValueError("Bronze object key cannot be empty.")

        if not self.silver_key.strip():
            raise ValueError("Silver object key cannot be empty.")

        if self.row_count <= 0:
            raise ValueError("Silver transformation row count must be positive.")

        if self.size_bytes <= 0:
            raise ValueError("Silver transformation size must be positive.")

        if self.schema_version <= 0:
            raise ValueError("Silver schema version must be positive.")

        if len(self.source_sha256) != 64:
            raise ValueError("Silver source SHA-256 must contain 64 hexadecimal characters.")
