"""Deterministic S3 key generation for NVD incremental Bronze pages."""

from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


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
