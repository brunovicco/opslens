"""Deterministic completion manifest for NVD Bootstrap Bronze."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

from opslens.ingestion.nvd.application.key_factory import (
    NvdBootstrapObjectKeys,
)
from opslens.ingestion.nvd.domain.feed_artifact import NvdFeedArtifact
from opslens.ingestion.nvd.domain.source_identity import (
    NvdBootstrapSourceIdentity,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class NvdBootstrapStoredObject:
    """Describe one exact S3 object referenced by the completion manifest.

    Attributes:
        key: Deterministic S3 object key.
        version_id: Exact S3 VersionId created or verified by OpsLens.
        size_bytes: Exact number of bytes stored in the object.
        sha256: SHA-256 of the exact stored object bytes.
    """

    key: str
    version_id: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        """Validate immutable stored-object provenance."""
        if not self.key:
            raise ValueError("NVD Bootstrap object key cannot be empty.")

        if not self.version_id:
            raise ValueError("NVD Bootstrap object VersionId cannot be empty.")

        if self.size_bytes <= 0:
            raise ValueError("NVD Bootstrap object size must be positive.")

        if not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ValueError(
                "NVD Bootstrap object SHA-256 must contain exactly "
                "64 lowercase hexadecimal characters."
            )


@dataclass(frozen=True, slots=True)
class NvdBootstrapManifest:
    """Represent COMPLETE evidence for one NVD bootstrap source revision.

    The manifest is valid only after both the original gzip feed and the
    original META artifact have been durably persisted and their exact S3
    VersionIds are known.
    """

    MANIFEST_VERSION: ClassVar[str] = "1"
    COMPLETION_STATUS: ClassVar[str] = "complete"
    SOURCE: ClassVar[str] = "nvd-cve"
    SOURCE_INTERFACE: ClassVar[str] = "json-2.0-yearly-feed"

    feed_year: int
    feed_revision: str
    source_last_modified_at: datetime
    source_sha256: str
    retrieved_at: datetime
    uncompressed_size_bytes: int
    zip_size_bytes: int
    gzip_size_bytes: int
    feed_object: NvdBootstrapStoredObject
    meta_object: NvdBootstrapStoredObject

    def __post_init__(self) -> None:
        """Validate invariants required by COMPLETE bootstrap evidence."""
        if type(self.feed_year) is not int:
            raise ValueError("NVD Bootstrap manifest feed year must be an integer.")

        if self.feed_year < 1000 or self.feed_year > 9999:
            raise ValueError("NVD Bootstrap manifest feed year must contain four digits.")

        if not self.feed_revision:
            raise ValueError("NVD Bootstrap manifest feed revision cannot be empty.")

        if self.source_last_modified_at.tzinfo is None:
            raise ValueError("NVD Bootstrap source timestamp must be timezone-aware.")

        if self.retrieved_at.tzinfo is None:
            raise ValueError("NVD Bootstrap retrieved_at must be timezone-aware.")

        if not _SHA256_PATTERN.fullmatch(self.source_sha256):
            raise ValueError(
                "NVD Bootstrap source SHA-256 must contain exactly "
                "64 lowercase hexadecimal characters."
            )

        if self.uncompressed_size_bytes <= 0:
            raise ValueError("NVD Bootstrap uncompressed size must be positive.")

        if self.zip_size_bytes <= 0:
            raise ValueError("NVD Bootstrap ZIP size must be positive.")

        if self.gzip_size_bytes <= 0:
            raise ValueError("NVD Bootstrap gzip size must be positive.")


class NvdBootstrapManifestFactory:
    """Build COMPLETE evidence from verified source and storage provenance."""

    def build(
        self,
        *,
        artifact: NvdFeedArtifact,
        identity: NvdBootstrapSourceIdentity,
        keys: NvdBootstrapObjectKeys,
        feed_version_id: str,
        meta_version_id: str,
        retrieved_at: datetime,
    ) -> NvdBootstrapManifest:
        """Build the completion manifest for one persisted source revision.

        Args:
            artifact: Integrity-verified NVD gzip source artifact.
            identity: Deterministic identity of the NVD source revision.
            keys: Deterministic Bronze keys for the revision.
            feed_version_id: Exact S3 VersionId of the gzip object.
            meta_version_id: Exact S3 VersionId of the META object.
            retrieved_at: Time OpsLens completed observing the source revision.

        Returns:
            Validated COMPLETE bootstrap manifest.

        Raises:
            ValueError: If source evidence is inconsistent.
        """
        if artifact.meta != identity.meta:
            raise ValueError("NVD Bootstrap artifact META does not match source identity.")

        if retrieved_at.tzinfo is None:
            raise ValueError("NVD Bootstrap retrieved_at must be timezone-aware.")

        meta_object_sha256 = hashlib.sha256(identity.meta.raw_bytes).hexdigest()

        feed_object = NvdBootstrapStoredObject(
            key=keys.feed_key,
            version_id=feed_version_id,
            size_bytes=artifact.gzip_size_bytes,
            sha256=artifact.bronze_object_sha256,
        )

        meta_object = NvdBootstrapStoredObject(
            key=keys.meta_key,
            version_id=meta_version_id,
            size_bytes=len(identity.meta.raw_bytes),
            sha256=meta_object_sha256,
        )

        return NvdBootstrapManifest(
            feed_year=identity.feed_year,
            feed_revision=identity.feed_revision,
            source_last_modified_at=identity.meta.last_modified_at,
            source_sha256=identity.meta.source_sha256,
            retrieved_at=retrieved_at,
            uncompressed_size_bytes=(identity.meta.uncompressed_size_bytes),
            zip_size_bytes=identity.meta.zip_size_bytes,
            gzip_size_bytes=identity.meta.gzip_size_bytes,
            feed_object=feed_object,
            meta_object=meta_object,
        )


class NvdBootstrapManifestSerializer:
    """Serialize a bootstrap completion manifest deterministically."""

    def serialize(
        self,
        manifest: NvdBootstrapManifest,
    ) -> bytes:
        """Return canonical UTF-8 JSON bytes for the completion manifest."""
        document: dict[str, object] = {
            "completion_status": manifest.COMPLETION_STATUS,
            "feed_object": {
                "key": manifest.feed_object.key,
                "sha256": manifest.feed_object.sha256,
                "size_bytes": manifest.feed_object.size_bytes,
                "version_id": manifest.feed_object.version_id,
            },
            "feed_revision": manifest.feed_revision,
            "feed_year": manifest.feed_year,
            "gzip_size_bytes": manifest.gzip_size_bytes,
            "manifest_version": manifest.MANIFEST_VERSION,
            "meta_object": {
                "key": manifest.meta_object.key,
                "sha256": manifest.meta_object.sha256,
                "size_bytes": manifest.meta_object.size_bytes,
                "version_id": manifest.meta_object.version_id,
            },
            "retrieved_at": self._format_utc(manifest.retrieved_at),
            "source": manifest.SOURCE,
            "source_interface": manifest.SOURCE_INTERFACE,
            "source_last_modified_at": self._format_utc(manifest.source_last_modified_at),
            "source_sha256": manifest.source_sha256,
            "uncompressed_size_bytes": (manifest.uncompressed_size_bytes),
            "zip_size_bytes": manifest.zip_size_bytes,
        }

        text = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

        return f"{text}\n".encode()

    @staticmethod
    def _format_utc(value: datetime) -> str:
        """Format one timezone-aware timestamp as canonical UTC."""
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
