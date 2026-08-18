"""Application models for CISA KEV Silver serialization."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KevSilverWriteResult:
    """Describe one successful KEV Silver serialization.

    Attributes:
        row_count: Number of records serialized.
        size_bytes: Serialized Parquet artifact size in bytes.
        schema_version: Physical KEV Silver schema version.
    """

    row_count: int
    size_bytes: int
    schema_version: int

    def __post_init__(self) -> None:
        """Validate invariants of a successful KEV Silver serialization."""
        if self.row_count <= 0:
            raise ValueError("KEV Silver write result must contain at least one row.")

        if self.size_bytes <= 0:
            raise ValueError("KEV Silver write result size must be greater than zero.")

        if self.schema_version <= 0:
            raise ValueError("KEV Silver schema version must be greater than zero.")
