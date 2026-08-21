"""Amazon S3 adapter for immutable NVD incremental Bronze pages."""

import hashlib
from collections.abc import Mapping
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifest,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
    NvdBronzeWriteStatus,
)
from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPage,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)
from opslens.shared.observability.ports import OperationalTelemetry


class NvdIncrementalBronzeEvidenceError(RuntimeError):
    """Raised when incremental Bronze evidence cannot be verified."""


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent HTTP metadata returned by Botocore errors."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent Botocore error fields inspected by this adapter."""

    ResponseMetadata: _S3ResponseMetadata


class S3NvdIncrementalBronzeClient(Protocol):
    """Define the minimal S3 capabilities required by incremental Bronze."""

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> Mapping[str, object]:
        """Conditionally create one immutable S3 object."""
        ...

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Read metadata for the current exact-key S3 object."""
        ...


class S3NvdIncrementalBronzeRepository:
    """Persist and verify immutable NVD CVE API response pages."""

    SOURCE = "nvd-cve"
    SOURCE_INTERFACE = "cve-api-2.0"
    PAGE_CONTENT_TYPE = "application/json"

    def __init__(
        self,
        *,
        client: S3NvdIncrementalBronzeClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the repository with explicit dependencies."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("NVD incremental Bronze bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def create_page(
        self,
        *,
        page: NvdCveApiPage,
        window: NvdIncrementalWindow,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create or verify one exact NVD CVE API response page."""
        metadata = self._page_metadata(
            page=page,
            window=window,
        )

        return self._create_if_absent(
            object_key=object_key,
            body=page.raw_bytes,
            content_type=self.PAGE_CONTENT_TYPE,
            metadata=metadata,
        )

    def _create_if_absent(
        self,
        *,
        object_key: str,
        body: bytes,
        content_type: str,
        metadata: Mapping[str, str],
    ) -> NvdBronzeWriteResult:
        """Conditionally create one page or verify existing evidence."""
        if not object_key:
            raise ValueError("NVD incremental Bronze object key cannot be empty.")

        if not body:
            raise NvdIncrementalBronzeEvidenceError(
                "NVD incremental Bronze object body cannot be empty."
            )

        self._telemetry.info(
            "Persisting NVD incremental Bronze page",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "payload_size_bytes": len(body),
            },
        )

        try:
            with self._telemetry.span("nvd.incremental.s3.put_object"):
                response = self._client.put_object(
                    Bucket=self._bucket_name,
                    Key=object_key,
                    Body=body,
                    ContentType=content_type,
                    Metadata=metadata,
                    IfNoneMatch="*",
                )

        except ClientError as exc:
            status_code = self._extract_http_status(exc)

            if status_code == 412:
                return self._verify_existing(
                    object_key=object_key,
                    expected_size=len(body),
                    expected_content_type=content_type,
                    expected_metadata=metadata,
                )

            self._record_failure(
                object_key=object_key,
                http_status=status_code,
            )
            raise

        version_id = self._require_version_id(response.get("VersionId"))
        etag = self._optional_string(response.get("ETag"))

        self._telemetry.metric(
            name="NvdIncrementalBronzeCreated",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="NvdIncrementalBronzePayloadBytes",
            value=float(len(body)),
            unit="Bytes",
        )
        self._telemetry.info(
            "NVD incremental Bronze page created",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "version_id": version_id,
                "etag": etag,
            },
        )

        return NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.CREATED,
            version_id=version_id,
            etag=etag,
        )

    def _verify_existing(
        self,
        *,
        object_key: str,
        expected_size: int,
        expected_content_type: str,
        expected_metadata: Mapping[str, str],
    ) -> NvdBronzeWriteResult:
        """Resolve a 412 by verifying the immutable existing object."""
        try:
            with self._telemetry.span("nvd.incremental.s3.head_object"):
                response = self._client.head_object(
                    Bucket=self._bucket_name,
                    Key=object_key,
                )
        except ClientError:
            self._record_failure(
                object_key=object_key,
                http_status=None,
            )
            raise

        version_id = self._require_version_id(response.get("VersionId"))

        content_length = response.get("ContentLength")

        if type(content_length) is not int:
            raise NvdIncrementalBronzeEvidenceError(
                "Existing NVD incremental Bronze object has no valid ContentLength."
            )

        if content_length != expected_size:
            raise NvdIncrementalBronzeEvidenceError(
                "Existing NVD incremental Bronze object size "
                "does not match expected immutable evidence."
            )

        if response.get("ContentType") != expected_content_type:
            raise NvdIncrementalBronzeEvidenceError(
                "Existing NVD incremental Bronze object ContentType "
                "does not match expected immutable evidence."
            )

        metadata_value = response.get("Metadata")

        if not isinstance(
            metadata_value,
            Mapping,
        ):
            raise NvdIncrementalBronzeEvidenceError(
                "Existing NVD incremental Bronze object has no valid metadata."
            )

        stored_metadata = cast(
            Mapping[object, object],
            metadata_value,
        )

        for key, expected_value in expected_metadata.items():
            if stored_metadata.get(key) != expected_value:
                raise NvdIncrementalBronzeEvidenceError(
                    "Existing NVD incremental Bronze object metadata "
                    f"does not match expected evidence for '{key}'."
                )

        etag = self._optional_string(response.get("ETag"))

        self._telemetry.metric(
            name="NvdIncrementalBronzeAlreadyExists",
            value=1.0,
            unit="Count",
        )
        self._telemetry.info(
            "NVD incremental Bronze page already exists and was verified",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "version_id": version_id,
                "etag": etag,
            },
        )

        return NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.ALREADY_EXISTS,
            version_id=version_id,
            etag=etag,
        )

    def _page_metadata(
        self,
        *,
        page: NvdCveApiPage,
        window: NvdIncrementalWindow,
    ) -> dict[str, str]:
        """Build deterministic source provenance for one API page."""
        return {
            "source": self.SOURCE,
            "source_interface": self.SOURCE_INTERFACE,
            "artifact_kind": "page",
            "update_id": window.update_id,
            "window_start_at": window.canonical_start_at,
            "window_end_at": window.canonical_end_at,
            "page_start": str(page.start_index),
            "results_per_page": str(page.results_per_page),
            "total_results": str(page.total_results),
            "source_format": page.source_format,
            "source_version": page.source_version,
            "source_timestamp": page.source_timestamp,
            "object_sha256": page.sha256,
        }

    def _record_failure(
        self,
        *,
        object_key: str,
        http_status: int | None,
    ) -> None:
        """Record failed incremental Bronze persistence."""
        self._telemetry.metric(
            name="NvdIncrementalBronzeWriteFailure",
            value=1.0,
            unit="Count",
        )
        self._telemetry.exception(
            "Failed to persist NVD incremental Bronze page",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "http_status": http_status,
            },
        )

    @staticmethod
    def _require_version_id(
        value: object,
    ) -> str:
        """Require an exact non-empty S3 VersionId."""
        if (
            not isinstance(
                value,
                str,
            )
            or not value
        ):
            raise NvdIncrementalBronzeEvidenceError(
                "NVD incremental Bronze object does not expose an S3 VersionId."
            )

        return value

    @staticmethod
    def _optional_string(
        value: object,
    ) -> str | None:
        """Return an optional string response field."""
        return value if isinstance(value, str) else None

    @staticmethod
    def _extract_http_status(
        error: ClientError,
    ) -> int | None:
        """Extract HTTP status from a Botocore client error."""
        response = cast(
            _S3ClientErrorResponse,
            error.response,
        )
        metadata = response.get(
            "ResponseMetadata",
            {},
        )
        status_code = metadata.get("HTTPStatusCode")

        return status_code if isinstance(status_code, int) else None

    def create_manifest(
        self,
        *,
        manifest: NvdIncrementalManifest,
        payload: bytes,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create or verify one deterministic COMPLETE manifest."""
        if not payload:
            raise NvdIncrementalBronzeEvidenceError(
                "NVD incremental manifest payload cannot be empty."
            )

        object_sha256 = hashlib.sha256(payload).hexdigest()

        metadata = {
            "source": manifest.SOURCE,
            "source_interface": (manifest.SOURCE_INTERFACE),
            "artifact_kind": "manifest",
            "update_id": manifest.update_id,
            "window_start_at": (manifest.canonical_window_start_at),
            "window_end_at": (manifest.canonical_window_end_at),
            "total_results": str(manifest.total_results),
            "page_count": str(manifest.page_count),
            "manifest_version": (manifest.MANIFEST_VERSION),
            "completion_status": (manifest.COMPLETION_STATUS),
            "object_sha256": object_sha256,
        }

        return self._create_if_absent(
            object_key=object_key,
            body=payload,
            content_type=self.PAGE_CONTENT_TYPE,
            metadata=metadata,
        )
