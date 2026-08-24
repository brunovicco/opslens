"""Physical attempt identity for NVD incremental source observations."""

import hashlib
import json

from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPagination,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


class NvdIncrementalAttemptIdFactory:
    """Build content-bound identities for complete NVD source observations."""

    ATTEMPT_VERSION = "1"

    def build(
        self,
        *,
        window: NvdIncrementalWindow,
        pagination: NvdCveApiPagination,
    ) -> str:
        """Build one deterministic physical-attempt identifier.

        The logical update id identifies the requested time window. The
        attempt id additionally binds the exact source-response bytes fetched
        for that window, so repeated observations with different NVD response
        timestamps cannot alias the same immutable Bronze page objects.
        """
        pages: list[dict[str, object]] = [
            {
                "sha256": page.sha256,
                "size_bytes": len(page.raw_bytes),
                "start_index": page.start_index,
            }
            for page in pagination.pages
        ]

        document: dict[str, object] = {
            "attempt_version": self.ATTEMPT_VERSION,
            "page_count": len(pagination.pages),
            "pages": pages,
            "total_results": pagination.total_results,
            "update_id": window.update_id,
        }

        payload = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()

        return hashlib.sha256(payload).hexdigest()
