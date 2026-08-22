"""Runtime boundary models for NVD Silver transformation."""

from dataclasses import dataclass

from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)


@dataclass(frozen=True, slots=True)
class NvdSilverRuntimeRequestV1:
    """Identify one exact Bronze COMPLETE manifest to process."""

    source_kind: NvdSilverSourceKind
    manifest_key: str
    manifest_version_id: str

    def __post_init__(self) -> None:
        """Validate the untrusted runtime coordinate envelope."""
        if not self.manifest_key.strip():
            raise ValueError("NVD Silver runtime manifest key cannot be empty.")

        if not self.manifest_version_id.strip():
            raise ValueError("NVD Silver runtime manifest VersionId cannot be empty.")


@dataclass(frozen=True, slots=True)
class NvdSilverRuntimeResultV1:
    """Describe one successfully persisted NVD Silver batch."""

    source_kind: NvdSilverSourceKind
    source_batch_id: str

    bronze_manifest_key: str
    bronze_manifest_version_id: str
    bronze_manifest_sha256: str

    silver_parquet_key: str
    silver_parquet_version_id: str
    silver_parquet_sha256: str

    silver_complete_key: str
    silver_complete_version_id: str
    silver_complete_sha256: str

    row_count: int

    def __post_init__(self) -> None:
        """Validate runtime completion evidence."""
        coordinates = (
            self.source_batch_id,
            self.bronze_manifest_key,
            self.bronze_manifest_version_id,
            self.silver_parquet_key,
            self.silver_parquet_version_id,
            self.silver_complete_key,
            self.silver_complete_version_id,
        )

        if any(not value.strip() for value in coordinates):
            raise ValueError("NVD Silver runtime result coordinates cannot be empty.")

        for name, value in (
            (
                "Bronze manifest",
                self.bronze_manifest_sha256,
            ),
            (
                "Silver Parquet",
                self.silver_parquet_sha256,
            ),
            (
                "Silver COMPLETE",
                self.silver_complete_sha256,
            ),
        ):
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise ValueError(f"NVD Silver runtime {name} SHA-256 is invalid.")

        if type(self.row_count) is not int or self.row_count < 0:
            raise ValueError("NVD Silver runtime row_count must be non-negative.")
