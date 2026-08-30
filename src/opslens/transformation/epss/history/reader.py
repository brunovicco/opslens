"""Application service for exact historical EPSS Bronze evidence reads."""

import hashlib

from opslens.transformation.epss.adapters.outbound.s3_history_exact_object import (
    EPSS_HISTORY_MAX_MANIFEST_BYTES,
    EPSS_HISTORY_MAX_SOURCE_BYTES,
    S3VersionedHistoricalEpssBronzeObjectReader,
)
from opslens.transformation.epss.history.manifest import (
    HistoricalEpssBronzeManifestParserV1,
)
from opslens.transformation.epss.history.models import (
    HistoricalEpssBronzeEvidenceV1,
)


class HistoricalEpssBronzeSourceEvidenceMismatchError(ValueError):
    """Raised when exact source bytes disagree with their Bronze manifest."""


class ReadHistoricalEpssBronzeEvidence:
    """Read one exact manifest and the exact source version it authorizes."""

    def __init__(
        self,
        *,
        object_reader: S3VersionedHistoricalEpssBronzeObjectReader,
        manifest_parser: HistoricalEpssBronzeManifestParserV1 | None = None,
    ) -> None:
        self._object_reader = object_reader
        self._manifest_parser = manifest_parser or HistoricalEpssBronzeManifestParserV1()

    def execute(
        self,
        *,
        manifest_key: str,
        manifest_version_id: str,
    ) -> HistoricalEpssBronzeEvidenceV1:
        """Read and verify the complete exact historical Bronze evidence pair."""
        manifest_payload = self._object_reader.get(
            key=manifest_key,
            version_id=manifest_version_id,
            max_bytes=EPSS_HISTORY_MAX_MANIFEST_BYTES,
        )
        manifest = self._manifest_parser.parse(manifest_payload)

        source = self._object_reader.get(
            key=manifest.source_object_key,
            version_id=manifest.source_object_version_id,
            max_bytes=EPSS_HISTORY_MAX_SOURCE_BYTES,
        )

        if len(source.raw_bytes) != manifest.compressed_size_bytes:
            raise HistoricalEpssBronzeSourceEvidenceMismatchError(
                "Historical EPSS source size does not match Bronze manifest evidence."
            )

        source_sha256 = hashlib.sha256(source.raw_bytes).hexdigest()
        if source_sha256 != manifest.source_sha256:
            raise HistoricalEpssBronzeSourceEvidenceMismatchError(
                "Historical EPSS source SHA-256 does not match Bronze manifest evidence."
            )

        git_blob_prefix = f"blob {len(source.raw_bytes)}\0".encode()
        git_blob_sha1 = hashlib.sha1(  # noqa: S324
            git_blob_prefix + source.raw_bytes,
            usedforsecurity=False,
        ).hexdigest()
        if git_blob_sha1 != manifest.archive_git_blob_sha1:
            raise HistoricalEpssBronzeSourceEvidenceMismatchError(
                "Historical EPSS source Git blob identity does not match Bronze manifest evidence."
            )

        return HistoricalEpssBronzeEvidenceV1(
            manifest=manifest,
            source=source,
        )
