"""Amazon S3 adapter for immutable GHSA Bronze evidence."""

import hashlib
from collections.abc import Mapping
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.ingestion.ghsa.application.manifest import GhsaCompleteManifest
from opslens.ingestion.ghsa.application.models import GhsaBronzeWriteResult
from opslens.ingestion.ghsa.domain.api_page import GhsaAdvisoryApiPage
from opslens.ingestion.ghsa.domain.sync import GhsaSyncWindow
from opslens.shared.observability.ports import OperationalTelemetry


class GhsaBronzeEvidenceError(RuntimeError):
    """Raised when immutable GHSA Bronze evidence cannot be verified."""


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent HTTP metadata returned by Botocore errors."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent Botocore error fields inspected by this adapter."""

    ResponseMetadata: _S3ResponseMetadata


class S3GhsaBronzeClient(Protocol):
    """Define the minimum S3 capabilities required by GHSA Bronze."""

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
        """Read metadata for one exact S3 object key."""
        ...


class S3GhsaBronzeRepository:
    """Persist and verify immutable GHSA response pages and manifests."""

    PAGE_CONTENT_TYPE = "application/json"

    def __init__(
        self,
        *,
        client: S3GhsaBronzeClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the repository with one exact Bronze bucket."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("GHSA Bronze bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def create_page(
        self,
        *,
        page: GhsaAdvisoryApiPage,
        window: GhsaSyncWindow,
        object_key: str,
    ) -> GhsaBronzeWriteResult:
        """Create or verify one immutable exact GitHub response page."""
        metadata = {
            "advisory_type": window.ADVISORY_TYPE,
            "api_version": window.API_VERSION,
            "artifact_kind": "page",
            "mode": window.mode.value,
            "object_sha256": page.sha256,
            "source": GhsaCompleteManifest.SOURCE,
            "source_interface": GhsaCompleteManifest.SOURCE_INTERFACE,
            "sync_id": window.sync_id,
            "item_count": str(page.item_count),
        }
        return self._create_if_absent(
            object_key=object_key,
            body=page.raw_bytes,
            metadata=metadata,
        )

    def create_manifest(
        self,
        *,
        manifest: GhsaCompleteManifest,
        payload: bytes,
        object_key: str,
    ) -> GhsaBronzeWriteResult:
        """Create or verify one immutable COMPLETE attempt manifest."""
        metadata = {
            "api_version": GhsaSyncWindow.API_VERSION,
            "artifact_kind": "manifest",
            "attempt_id": manifest.attempt_id,
            "completion_status": manifest.COMPLETION_STATUS,
            "manifest_version": manifest.MANIFEST_VERSION,
            "mode": manifest.mode.value,
            "object_sha256": hashlib.sha256(payload).hexdigest(),
            "source": manifest.SOURCE,
            "source_interface": manifest.SOURCE_INTERFACE,
            "sync_id": manifest.sync_id,
        }
        return self._create_if_absent(
            object_key=object_key,
            body=payload,
            metadata=metadata,
        )

    def _create_if_absent(
        self,
        *,
        object_key: str,
        body: bytes,
        metadata: Mapping[str, str],
    ) -> GhsaBronzeWriteResult:
        """Conditionally create exact evidence or verify an existing object."""
        if not object_key.strip():
            raise ValueError("GHSA Bronze object key cannot be empty.")

        if not body:
            raise GhsaBronzeEvidenceError("GHSA Bronze object body cannot be empty.")

        self._telemetry.info(
            "Persisting immutable GHSA Bronze object",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "payload_size_bytes": len(body),
            },
        )

        try:
            with self._telemetry.span("ghsa.s3.put_object"):
                response = self._client.put_object(
                    Bucket=self._bucket_name,
                    Key=object_key,
                    Body=body,
                    ContentType=self.PAGE_CONTENT_TYPE,
                    Metadata=metadata,
                    IfNoneMatch="*",
                )
        except ClientError as exc:
            if self._extract_http_status(exc) == 412:
                return self._verify_existing(
                    object_key=object_key,
                    expected_size=len(body),
                    expected_metadata=metadata,
                )
            raise

        version_id = self._require_version_id(response.get("VersionId"))
        return GhsaBronzeWriteResult(
            key=object_key,
            version_id=version_id,
        )

    def _verify_existing(
        self,
        *,
        object_key: str,
        expected_size: int,
        expected_metadata: Mapping[str, str],
    ) -> GhsaBronzeWriteResult:
        """Verify that a pre-existing exact key carries the expected evidence."""
        response = self._client.head_object(
            Bucket=self._bucket_name,
            Key=object_key,
        )
        version_id = self._require_version_id(response.get("VersionId"))
        content_length = response.get("ContentLength")

        if type(content_length) is not int or content_length != expected_size:
            raise GhsaBronzeEvidenceError(
                "Existing GHSA Bronze object size does not match expected evidence."
            )

        if response.get("ContentType") != self.PAGE_CONTENT_TYPE:
            raise GhsaBronzeEvidenceError(
                "Existing GHSA Bronze object ContentType does not match expected evidence."
            )

        metadata_value = response.get("Metadata")

        if not isinstance(metadata_value, Mapping):
            raise GhsaBronzeEvidenceError(
                "Existing GHSA Bronze object has no valid metadata."
            )

        stored_metadata = cast(Mapping[object, object], metadata_value)

        for key, expected_value in expected_metadata.items():
            if stored_metadata.get(key) != expected_value:
                raise GhsaBronzeEvidenceError(
                    "Existing GHSA Bronze object metadata "
                    f"does not match expected evidence for '{key}'."
                )

        return GhsaBronzeWriteResult(
            key=object_key,
            version_id=version_id,
        )

    @staticmethod
    def _require_version_id(value: object) -> str:
        """Require exact versioned S3 persistence evidence."""
        if not isinstance(value, str) or not value.strip():
            raise GhsaBronzeEvidenceError(
                "GHSA Bronze object does not expose an S3 VersionId."
            )

        return value

    @staticmethod
    def _extract_http_status(error: ClientError) -> int | None:
        """Extract HTTP status from a Botocore client error."""
        response = cast(_S3ClientErrorResponse, error.response)
        metadata = response.get("ResponseMetadata", {})
        status_code = metadata.get("HTTPStatusCode")

        return status_code if isinstance(status_code, int) else None
