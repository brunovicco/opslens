"""Deterministic S3 key generation for NVD incremental Bronze pages."""

import re

from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class NvdIncrementalKeyFactory:
    """Build deterministic Bronze keys for NVD CVE API update pages."""

    DEFAULT_PREFIX = "bronze/nvd/cve/updates"

    def __init__(
        self,
        prefix: str = DEFAULT_PREFIX,
    ) -> None:
        """Initialize the key factory with a configurable Bronze prefix."""
        normalized_prefix = prefix.strip("/")

        if not normalized_prefix:
            raise ValueError("NVD incremental Bronze prefix cannot be empty.")

        self._prefix = normalized_prefix

    def build_page_key(
        self,
        *,
        window: NvdIncrementalWindow,
        start_index: int,
    ) -> str:
        """Build the immutable key for one incremental API response page."""
        if type(start_index) is not int:
            raise ValueError("NVD incremental page start index must be an integer.")

        if start_index < 0:
            raise ValueError("NVD incremental page start index must not be negative.")

        return (
            f"{self._prefix}/"
            f"update_id={window.update_id}/"
            f"page_start={start_index:06d}/"
            "response.json"
        )

    def build_manifest_key(
        self,
        *,
        window: NvdIncrementalWindow,
    ) -> str:
        """Build the COMPLETE manifest key for one update window."""
        return f"{self._prefix}/update_id={window.update_id}/manifest.json"

    def build_attempt_page_key(
        self,
        *,
        window: NvdIncrementalWindow,
        attempt_id: str,
        start_index: int,
    ) -> str:
        """Build an immutable page key scoped to one physical source attempt."""
        if not _SHA256_PATTERN.fullmatch(attempt_id):
            raise ValueError(
                "NVD incremental attempt id must contain exactly "
                "64 lowercase hexadecimal characters."
            )

        if type(start_index) is not int:
            raise ValueError(
                "NVD incremental page start index must be an integer."
            )

        if start_index < 0:
            raise ValueError(
                "NVD incremental page start index must not be negative."
            )

        return (
            f"{self._prefix}/"
            f"update_id={window.update_id}/"
            f"attempt_id={attempt_id}/"
            f"page_start={start_index:06d}/"
            "response.json"
        )
