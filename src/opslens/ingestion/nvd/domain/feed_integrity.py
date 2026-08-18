"""Integrity verification for NVD yearly gzip feeds."""

import gzip
import hashlib
import zlib
from io import BytesIO

from opslens.ingestion.nvd.domain.errors import InvalidNvdFeedArtifactError
from opslens.ingestion.nvd.domain.feed_artifact import NvdFeedArtifact
from opslens.ingestion.nvd.domain.models import NvdFeedMeta


class NvdFeedIntegrityVerifier:
    """Verify an NVD gzip artifact against its authoritative META evidence."""

    READ_CHUNK_SIZE_BYTES = 1024 * 1024

    def verify(
        self,
        payload: bytes,
        meta: NvdFeedMeta,
    ) -> NvdFeedArtifact:
        """Verify compressed and uncompressed NVD feed integrity.

        Verification includes:

        - exact gzip byte size against `gzSize`;
        - valid gzip decompression;
        - bounded decompression against declared uncompressed `size`;
        - exact uncompressed byte count;
        - SHA-256 of uncompressed JSON against the NVD META `sha256`;
        - SHA-256 of exact gzip bytes for OpsLens Bronze provenance.

        Args:
            payload: Exact gzip bytes received from NVD.
            meta: Previously validated NVD META evidence.

        Returns:
            Integrity-verified immutable NVD feed artifact.

        Raises:
            InvalidNvdFeedArtifactError: If the gzip artifact does not match
                the associated META evidence.
        """
        if not payload:
            raise InvalidNvdFeedArtifactError("NVD gzip feed payload is empty.")

        self._verify_compressed_size(
            actual_size=len(payload),
            expected_size=meta.gzip_size_bytes,
        )

        source_sha256, uncompressed_size = self._inspect_uncompressed(
            payload=payload,
            maximum_size=meta.uncompressed_size_bytes,
        )

        if uncompressed_size != meta.uncompressed_size_bytes:
            raise InvalidNvdFeedArtifactError(
                "NVD uncompressed feed size does not match META size: "
                f"expected={meta.uncompressed_size_bytes}, "
                f"actual={uncompressed_size}."
            )

        if source_sha256 != meta.source_sha256:
            raise InvalidNvdFeedArtifactError(
                "NVD uncompressed feed SHA-256 does not match META sha256."
            )

        bronze_object_sha256 = hashlib.sha256(payload).hexdigest()

        return NvdFeedArtifact(
            raw_gzip_bytes=payload,
            meta=meta,
            bronze_object_sha256=bronze_object_sha256,
        )

    @staticmethod
    def _verify_compressed_size(
        *,
        actual_size: int,
        expected_size: int,
    ) -> None:
        """Verify exact gzip byte size against META evidence."""
        if actual_size != expected_size:
            raise InvalidNvdFeedArtifactError(
                "NVD gzip feed size does not match META gzSize: "
                f"expected={expected_size}, actual={actual_size}."
            )

    def _inspect_uncompressed(
        self,
        *,
        payload: bytes,
        maximum_size: int,
    ) -> tuple[str, int]:
        """Stream decompressed bytes into a SHA-256 digest and byte counter."""
        digest = hashlib.sha256()
        total_size = 0

        try:
            with gzip.GzipFile(
                fileobj=BytesIO(payload),
                mode="rb",
            ) as source:
                while True:
                    chunk = source.read(self.READ_CHUNK_SIZE_BYTES)

                    if not chunk:
                        break

                    total_size += len(chunk)

                    if total_size > maximum_size:
                        raise InvalidNvdFeedArtifactError(
                            "NVD uncompressed feed exceeds META size: "
                            f"maximum={maximum_size}, "
                            f"observed={total_size}."
                        )

                    digest.update(chunk)

        except InvalidNvdFeedArtifactError:
            raise
        except (gzip.BadGzipFile, EOFError, zlib.error) as exc:
            raise InvalidNvdFeedArtifactError(
                "NVD feed payload is not a valid complete gzip artifact."
            ) from exc

        return digest.hexdigest(), total_size
