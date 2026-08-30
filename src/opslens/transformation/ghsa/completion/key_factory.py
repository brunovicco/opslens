"""Deterministic object-key construction for GHSA Silver persistence."""

from dataclasses import dataclass

from opslens.transformation.ghsa.domain.models import (
    ObservedGhsaAdvisoryVersion,
)
from opslens.transformation.ghsa.runtime.materializer import (
    GhsaSilverAttemptContextV1,
)
from opslens.transformation.ghsa.serialization.schema import (
    GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION,
)


@dataclass(frozen=True, slots=True)
class GhsaSilverObjectKeysV1:
    """Represent deterministic Silver keys for one advisory content version."""

    content_object_key: str


class GhsaSilverKeyFactoryV1:
    """Build immutable GHSA Silver keys without runtime timestamps."""

    DEFAULT_CONTENT_PREFIX = "silver/ghsa/advisory_versions"
    DEFAULT_COMPLETION_PREFIX = "silver/ghsa/completions"

    def __init__(
        self,
        *,
        content_prefix: str = DEFAULT_CONTENT_PREFIX,
        completion_prefix: str = DEFAULT_COMPLETION_PREFIX,
    ) -> None:
        """Initialize normalized Silver object prefixes."""
        normalized_content = content_prefix.strip("/")
        normalized_completion = completion_prefix.strip("/")

        if not normalized_content:
            raise ValueError(
                "GHSA Silver content prefix cannot be empty."
            )

        if not normalized_completion:
            raise ValueError(
                "GHSA Silver completion prefix cannot be empty."
            )

        self._content_prefix = normalized_content
        self._completion_prefix = normalized_completion

    def build_content_object_key(
        self,
        observed_version: ObservedGhsaAdvisoryVersion,
    ) -> str:
        """Build one immutable key from advisory content identity."""
        return (
            f"{self._content_prefix}/"
            f"schema_version={GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION}/"
            f"ghsa_id={observed_version.ghsa_id}/"
            f"source_advisory_sha256="
            f"{observed_version.source_advisory_sha256}/"
            "record.parquet"
        )

    def build_completion_manifest_key(
        self,
        context: GhsaSilverAttemptContextV1,
    ) -> str:
        """Build one deterministic COMPLETE manifest key per Bronze attempt."""
        return (
            f"{self._completion_prefix}/"
            f"schema_version={GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION}/"
            f"sync_id={context.sync_id}/"
            f"attempt_id={context.attempt_id}/"
            "manifest.json"
        )
