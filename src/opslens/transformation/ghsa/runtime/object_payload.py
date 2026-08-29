"""Exact GHSA Bronze object payloads consumed by Silver runtime."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GhsaBronzeObjectPayloadV1:
    """Represent exact bytes fetched from one explicit S3 object version."""

    key: str
    version_id: str
    raw_bytes: bytes

    def __post_init__(self) -> None:
        """Validate exact immutable object coordinates and payload."""
        if not self.key.strip():
            raise ValueError(
                "GHSA Bronze payload key cannot be empty."
            )

        if not self.version_id.strip():
            raise ValueError(
                "GHSA Bronze payload VersionId cannot be empty."
            )

        if not self.raw_bytes:
            raise ValueError(
                "GHSA Bronze payload bytes cannot be empty."
            )
