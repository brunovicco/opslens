"""Exact-key S3 reader for NVD incremental Bronze COMPLETE manifests."""

import hashlib
from collections.abc import Mapping
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.ingestion.nvd.application.incremental_complete import (
    NvdIncrementalManifestParser,
    NvdPersistedIncrementalManifest,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)
from opslens.shared.observability.ports import OperationalTelemetry


class NvdIncrementalCompleteManifestEvidenceError(RuntimeError):
    """Raised when persisted incremental COMPLETE evidence is invalid."""


class NvdIncrementalCompleteManifestReadError(RuntimeError):
    """Raised when canonical incremental COMPLETE evidence cannot be read."""


class _ReadableBody(Protocol):
    """Define the S3 response-body capability required by this adapter."""

    def read(
        self,
        amt: int | None = None,
    ) -> bytes:
        """Read response bytes."""
        ...


class S3NvdIncrementalCompleteManifestClient(Protocol):
    """Define minimal S3 capability for canonical COMPLETE lookup."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Read one current exact-key object."""
        ...


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent HTTP metadata returned by Botocore errors."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent Botocore error fields inspected by this adapter."""

    ResponseMetadata: _S3ResponseMetadata


class S3NvdIncrementalCompleteManifestReader:
    """Load and verify known-existing NVD incremental COMPLETE evidence."""

    CONTENT_TYPE = "application/json"
    MAX_PAYLOAD_BYTES = 64 * 1024

    def __init__(
        self,
        *,
        client: S3NvdIncrementalCompleteManifestClient,
        bucket_name: str,
        parser: NvdIncrementalManifestParser,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the exact-key COMPLETE reader."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError(
                "NVD incremental COMPLETE bucket name cannot be empty."
            )

        self._client = client
        self._bucket_name = normalized_bucket
        self._parser = parser
        self._telemetry = telemetry

    def load_existing(
        self,
        *,
        window: NvdIncrementalWindow,
        object_key: str,
    ) -> NvdPersistedIncrementalManifest:
        """Load and verify one known-existing canonical COMPLETE manifest.

        Existence must already have been established by the caller's control
        flow. Any S3 GetObject failure is therefore treated as a read failure
        rather than as evidence that the manifest is absent.

        Args:
            window: Logical incremental window expected by the manifest.
            object_key: Exact canonical COMPLETE manifest key.

        Returns:
            Exact persisted and verified COMPLETE evidence.

        Raises:
            ValueError: If the object key is empty.
            NvdIncrementalCompleteManifestReadError: If S3 cannot read the
                known-existing object.
            NvdIncrementalCompleteManifestEvidenceError: If persisted S3
                evidence does not satisfy the expected contract.
        """
        if not object_key:
            raise ValueError(
                "NVD incremental COMPLETE object key cannot be empty."
            )

        self._telemetry.info(
            "Reading known-existing canonical NVD incremental COMPLETE manifest",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "update_id": window.update_id,
            },
        )

        try:
            with self._telemetry.span(
                "nvd.incremental.s3.get_complete_manifest"
            ):
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=object_key,
                )
        except ClientError as exc:
            status_code = self._extract_http_status(
                exc
            )

            self._telemetry.metric(
                name="NvdIncrementalCompleteManifestReadFailure",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Failed to read known-existing canonical "
                "NVD incremental COMPLETE manifest",
                fields={
                    "bucket": self._bucket_name,
                    "object_key": object_key,
                    "http_status": status_code,
                },
            )

            raise NvdIncrementalCompleteManifestReadError(
                "Failed to read known-existing canonical "
                "NVD incremental COMPLETE manifest."
            ) from exc

        payload = self._read_payload(
            response
        )

        version_id = self._require_string(
            response.get("VersionId"),
            field_name="VersionId",
        )

        content_length = response.get(
            "ContentLength"
        )

        if (
            type(content_length) is not int
            or content_length != len(payload)
        ):
            raise NvdIncrementalCompleteManifestEvidenceError(
                "NVD incremental COMPLETE ContentLength does not "
                "match exact payload bytes."
            )

        if response.get("ContentType") != self.CONTENT_TYPE:
            raise NvdIncrementalCompleteManifestEvidenceError(
                "NVD incremental COMPLETE ContentType is invalid."
            )

        manifest = self._parser.parse(
            payload
        )

        self._verify_logical_window(
            manifest_update_id=manifest.update_id,
            manifest_window_start_at=manifest.canonical_window_start_at,
            manifest_window_end_at=manifest.canonical_window_end_at,
            window=window,
        )

        sha256 = hashlib.sha256(
            payload
        ).hexdigest()

        expected_metadata = {
            "source": manifest.SOURCE,
            "source_interface": manifest.SOURCE_INTERFACE,
            "artifact_kind": "manifest",
            "update_id": manifest.update_id,
            "window_start_at": manifest.canonical_window_start_at,
            "window_end_at": manifest.canonical_window_end_at,
            "total_results": str(
                manifest.total_results
            ),
            "page_count": str(
                manifest.page_count
            ),
            "manifest_version": manifest.MANIFEST_VERSION,
            "completion_status": manifest.COMPLETION_STATUS,
            "object_sha256": sha256,
        }

        self._verify_metadata(
            response=response,
            expected=expected_metadata,
        )

        etag_value = response.get(
            "ETag"
        )
        etag = (
            etag_value
            if isinstance(
                etag_value,
                str,
            )
            else None
        )

        persisted = NvdPersistedIncrementalManifest(
            manifest=manifest,
            payload=payload,
            version_id=version_id,
            etag=etag,
            sha256=sha256,
            size_bytes=len(payload),
        )

        self._telemetry.metric(
            name="NvdIncrementalCompleteManifestRead",
            value=1.0,
            unit="Count",
        )
        self._telemetry.info(
            "Known-existing canonical NVD incremental "
            "COMPLETE manifest verified",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "version_id": version_id,
                "update_id": manifest.update_id,
                "total_results": manifest.total_results,
                "page_count": manifest.page_count,
                "object_sha256": sha256,
            },
        )

        return persisted

    def _read_payload(
        self,
        response: Mapping[str, object],
    ) -> bytes:
        """Read one bounded S3 response body."""
        body_value = response.get(
            "Body"
        )

        if not hasattr(
            body_value,
            "read",
        ):
            raise NvdIncrementalCompleteManifestEvidenceError(
                "NVD incremental COMPLETE S3 response has no readable body."
            )

        body = cast(
            _ReadableBody,
            body_value,
        )

        payload = body.read(
            self.MAX_PAYLOAD_BYTES + 1
        )

        if len(payload) > self.MAX_PAYLOAD_BYTES:
            raise NvdIncrementalCompleteManifestEvidenceError(
                "NVD incremental COMPLETE manifest exceeds maximum size."
            )

        if not payload:
            raise NvdIncrementalCompleteManifestEvidenceError(
                "NVD incremental COMPLETE manifest payload is empty."
            )

        return payload

    @staticmethod
    def _verify_logical_window(
        *,
        manifest_update_id: str,
        manifest_window_start_at: str,
        manifest_window_end_at: str,
        window: NvdIncrementalWindow,
    ) -> None:
        """Require persisted COMPLETE evidence for the expected logical window."""
        if manifest_update_id != window.update_id:
            raise NvdIncrementalCompleteManifestEvidenceError(
                "NVD incremental COMPLETE update_id does not match "
                "the requested logical window."
            )

        if manifest_window_start_at != window.canonical_start_at:
            raise NvdIncrementalCompleteManifestEvidenceError(
                "NVD incremental COMPLETE lower boundary does not "
                "match the requested logical window."
            )

        if manifest_window_end_at != window.canonical_end_at:
            raise NvdIncrementalCompleteManifestEvidenceError(
                "NVD incremental COMPLETE upper boundary does not "
                "match the requested logical window."
            )

    @staticmethod
    def _verify_metadata(
        *,
        response: Mapping[str, object],
        expected: Mapping[str, str],
    ) -> None:
        """Require exact S3 metadata for persisted COMPLETE evidence."""
        metadata_value = response.get(
            "Metadata"
        )

        if not isinstance(
            metadata_value,
            Mapping,
        ):
            raise NvdIncrementalCompleteManifestEvidenceError(
                "NVD incremental COMPLETE object has no valid metadata."
            )

        stored_metadata = cast(
            Mapping[object, object],
            metadata_value,
        )

        if set(stored_metadata.keys()) != set(expected.keys()):
            raise NvdIncrementalCompleteManifestEvidenceError(
                "NVD incremental COMPLETE metadata fields are not exact."
            )

        for key, expected_value in expected.items():
            if stored_metadata.get(key) != expected_value:
                raise NvdIncrementalCompleteManifestEvidenceError(
                    "NVD incremental COMPLETE metadata does not match "
                    f"expected evidence for '{key}'."
                )

    @staticmethod
    def _require_string(
        value: object,
        *,
        field_name: str,
    ) -> str:
        """Require one non-empty S3 response string."""
        if not isinstance(
            value,
            str,
        ) or not value:
            raise NvdIncrementalCompleteManifestEvidenceError(
                "NVD incremental COMPLETE object has no valid "
                f"{field_name}."
            )

        return value

    @staticmethod
    def _extract_http_status(
        error: ClientError,
    ) -> int | None:
        """Extract HTTP status from one Botocore client error."""
        response = cast(
            _S3ClientErrorResponse,
            error.response,
        )

        metadata = response.get(
            "ResponseMetadata",
            {},
        )

        status_code = metadata.get(
            "HTTPStatusCode"
        )

        return (
            status_code
            if isinstance(
                status_code,
                int,
            )
            else None
        )
