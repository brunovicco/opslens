"""Deterministic S3 key generation for GHSA Bronze source observations."""

import re

from opslens.ingestion.ghsa.domain.sync import (
    GhsaSyncWindow,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class GhsaBronzeKeyFactory:
    """Build immutable Bronze keys for one exact GHSA source attempt."""

    DEFAULT_PREFIX = "bronze/ghsa/advisories"

    def __init__(self, prefix: str = DEFAULT_PREFIX) -> None:
        """Initialize the key factory with a normalized Bronze prefix."""
        normalized_prefix = prefix.strip("/")

        if not normalized_prefix:
            raise ValueError("GHSA Bronze prefix cannot be empty.")

        self._prefix = normalized_prefix

    def build_page_key(
        self,
        *,
        window: GhsaSyncWindow,
        attempt_id: str,
        page_ordinal: int,
    ) -> str:
        """Build the immutable key for one ordered response page."""
        self._validate_attempt_id(attempt_id)

        if type(page_ordinal) is not int or page_ordinal < 1:
            raise ValueError("GHSA Bronze page_ordinal must be a positive integer.")

        return (
            f"{self._prefix}/"
            f"mode={window.mode.value}/"
            f"sync_id={window.sync_id}/"
            f"attempt_id={attempt_id}/"
            f"page={page_ordinal:06d}/"
            "response.json"
        )

    def build_manifest_key(
        self,
        *,
        window: GhsaSyncWindow,
        attempt_id: str,
    ) -> str:
        """Build the COMPLETE manifest key for one exact source attempt."""
        self._validate_attempt_id(attempt_id)

        return (
            f"{self._prefix}/"
            f"mode={window.mode.value}/"
            f"sync_id={window.sync_id}/"
            f"attempt_id={attempt_id}/"
            "manifest.json"
        )

    @staticmethod
    def _validate_attempt_id(attempt_id: str) -> None:
        """Require one lowercase SHA-256 physical-attempt identity."""
        if _SHA256_PATTERN.fullmatch(attempt_id) is None:
            raise ValueError(
                "GHSA Bronze attempt_id must contain exactly 64 lowercase hexadecimal characters."
            )
