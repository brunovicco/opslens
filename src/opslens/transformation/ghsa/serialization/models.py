"""Serialization-boundary models for GHSA Silver schema v1."""

import re
from dataclasses import dataclass
from hashlib import sha256

from opslens.transformation.ghsa.domain.collections_models import (
    GhsaAdvisoryCollections,
)
from opslens.transformation.ghsa.domain.models import (
    GhsaAdvisoryCoreRecord,
)
from opslens.transformation.ghsa.domain.vulnerability_models import (
    GhsaVulnerabilitySet,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class GhsaSilverRecordV1:
    """Aggregate one normalized observed GHSA content version for serialization."""

    core: GhsaAdvisoryCoreRecord
    collections: GhsaAdvisoryCollections
    vulnerabilities: GhsaVulnerabilitySet

    def __post_init__(self) -> None:
        """Require all normalized components to describe the same advisory version."""
        observed = self.core.observed_version

        if self.collections.ghsa_id != observed.ghsa_id:
            raise ValueError("GHSA Silver collections must match the core ghsa_id.")

        if self.collections.cve_id != self.core.cve_id:
            raise ValueError("GHSA Silver collections must match the core cve_id.")

        if self.vulnerabilities.observed_version != observed:
            raise ValueError(
                "GHSA Silver vulnerabilities must bind to the exact core advisory version."
            )


@dataclass(frozen=True, slots=True)
class GhsaSilverParquetArtifactV1:
    """Represent one deterministic GHSA Silver Parquet artifact."""

    parquet_bytes: bytes
    parquet_sha256: str
    row_count: int
    size_bytes: int
    schema_version: int

    def __post_init__(self) -> None:
        """Validate serialized Parquet artifact invariants."""
        if not self.parquet_bytes:
            raise ValueError("GHSA Silver parquet_bytes cannot be empty.")

        if not self.parquet_bytes.startswith(b"PAR1") or not self.parquet_bytes.endswith(b"PAR1"):
            raise ValueError("GHSA Silver parquet_bytes must use Parquet framing.")

        if _SHA256_PATTERN.fullmatch(self.parquet_sha256) is None:
            raise ValueError("GHSA Silver parquet_sha256 must be a lowercase SHA-256 digest.")

        if type(self.row_count) is not int or self.row_count < 0:
            raise ValueError("GHSA Silver Parquet row_count must be non-negative.")

        if type(self.size_bytes) is not int:
            raise ValueError("GHSA Silver Parquet size_bytes must be an integer.")

        if self.size_bytes != len(self.parquet_bytes):
            raise ValueError("GHSA Silver Parquet size_bytes does not match payload.")

        if self.schema_version != 1:
            raise ValueError("GHSA Silver Parquet artifact requires schema version 1.")

        expected_sha256 = sha256(self.parquet_bytes).hexdigest()

        if self.parquet_sha256 != expected_sha256:
            raise ValueError("GHSA Silver Parquet SHA-256 does not match payload.")
