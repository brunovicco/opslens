"""Application models for EPSS Silver serialization."""

from dataclasses import dataclass


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
