"""Physical attempt identity for complete GHSA source observations."""

import hashlib
import json

from opslens.ingestion.ghsa.domain.api_page import (
    GhsaAdvisoryPagination,
)
from opslens.ingestion.ghsa.domain.sync import (
    GhsaSyncWindow,
)


class GhsaAttemptIdFactory:
    """Build content-bound identities for complete GHSA source observations."""

    ATTEMPT_VERSION = "1"

    def build(
        self,
        *,
        window: GhsaSyncWindow,
        pagination: GhsaAdvisoryPagination,
    ) -> str:
        """Hash the exact ordered page inventory and cursor-navigation evidence."""
        if pagination.window.sync_id != window.sync_id:
            raise ValueError("GHSA attempt pagination does not match the requested sync window.")

        pages: list[dict[str, object]] = [
            {
                "item_count": page.item_count,
                "next_url": page.next_url,
                "request_url": page.request_url,
                "sha256": page.sha256,
                "size_bytes": page.size_bytes,
            }
            for page in pagination.pages
        ]

        document: dict[str, object] = {
            "attempt_version": self.ATTEMPT_VERSION,
            "page_count": len(pagination.pages),
            "pages": pages,
            "sync_id": window.sync_id,
            "total_bytes": pagination.total_bytes,
            "total_items": pagination.total_items,
        }

        payload = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")

        return hashlib.sha256(payload).hexdigest()
