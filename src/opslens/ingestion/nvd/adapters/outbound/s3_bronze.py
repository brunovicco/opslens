"""Amazon S3 adapter for immutable NVD Bootstrap Bronze evidence."""

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.ingestion.nvd.application.manifest import NvdBootstrapManifest
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
    NvdBronzeWriteStatus,
)
from opslens.ingestion.nvd.domain.feed_artifact import NvdFeedArtifact
from opslens.ingestion.nvd.domain.source_identity import (
    NvdBootstrapSourceIdentity,
)
from opslens.shared.observability.ports import OperationalTelemetry


class NvdBronzeEvidenceError(RuntimeError):
    """Raised when persisted Bronze evidence cannot be verified."""


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent HTTP metadata returned by Botocore errors."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent the Botocore error fields inspected by this adapter."""

    ResponseMetadata: _S3ResponseMetadata


class S3NvdBronzeClient(Protocol):
    """Define the minimal S3 client capabilities used by NVD Bronze."""

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


class S3NvdBootstrapBronzeRepository:
    """Persist and verify immutable NVD Bootstrap Bronze evidence."""

    SOURCE = "nvd-cve"
    SOURCE_INTERFACE = "json-2.0-yearly-feed"

    FEED_CONTENT_TYPE = "application/gzip"
    META_CONTENT_TYPE = "text/plain"
    MANIFEST_CONTENT_TYPE = "application/json"

    def __init__(
        self,
        client: S3NvdBronzeClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the repository with explicit dependencies."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("NVD Bronze bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def create_feed(
        self,
        *,
        artifact: NvdFeedArtifact,
        identity: NvdBootstrapSourceIdentity,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create or verify the exact NVD gzip source artifact."""
        if artifact.meta != identity.meta:
            raise NvdBronzeEvidenceError("NVD feed artifact META does not match source identity.")

        metadata = self._source_metadata(
            identity=identity,
            artifact_kind="feed",
            object_sha256=artifact.bronze_object_sha256,
        )

        return self._create_if_absent(
            object_key=object_key,
            body=artifact.raw_gzip_bytes,
            content_type=self.FEED_CONTENT_TYPE,
            metadata=metadata,
            artifact_kind="feed",
        )

    def create_meta(
        self,
        *,
        identity: NvdBootstrapSourceIdentity,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create or verify the exact original NVD META artifact."""
        raw_meta = identity.meta.raw_bytes
        object_sha256 = hashlib.sha256(raw_meta).hexdigest()

        metadata = self._source_metadata(
            identity=identity,
            artifact_kind="meta",
            object_sha256=object_sha256,
        )

        return self._create_if_absent(
            object_key=object_key,
            body=raw_meta,
            content_type=self.META_CONTENT_TYPE,
            metadata=metadata,
            artifact_kind="meta",
        )

    def create_manifest(
        self,
        *,
        manifest: NvdBootstrapManifest,
        payload: bytes,
        object_key: str,
    ) -> NvdBronzeWriteResult:
        """Create or verify one deterministic COMPLETE manifest."""
        if not payload:
            raise NvdBronzeEvidenceError("NVD Bootstrap manifest payload cannot be empty.")

        object_sha256 = hashlib.sha256(payload).hexdigest()

        metadata = {
            "source": self.SOURCE,
            "source_interface": self.SOURCE_INTERFACE,
            "artifact_kind": "manifest",
            "feed_year": str(manifest.feed_year),
            "feed_revision": manifest.feed_revision,
            "source_sha256": manifest.source_sha256,
            "object_sha256": object_sha256,
            "manifest_version": manifest.MANIFEST_VERSION,
            "completion_status": manifest.COMPLETION_STATUS,
        }

        return self._create_if_absent(
            object_key=object_key,
            body=payload,
            content_type=self.MANIFEST_CONTENT_TYPE,
            metadata=metadata,
            artifact_kind="manifest",
        )

    def _create_if_absent(
        self,
        *,
        object_key: str,
        body: bytes,
        content_type: str,
        metadata: Mapping[str, str],
        artifact_kind: str,
    ) -> NvdBronzeWriteResult:
        """Conditionally create one object or verify the existing object."""
        if not object_key:
            raise ValueError("NVD Bronze object key cannot be empty.")

        if not body:
            raise NvdBronzeEvidenceError("NVD Bronze object body cannot be empty.")

        self._telemetry.info(
            "Persisting NVD Bootstrap Bronze object",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "artifact_kind": artifact_kind,
                "payload_size_bytes": len(body),
            },
        )

        try:
            with self._telemetry.span("nvd.s3.put_object"):
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
                    expected_sha256=metadata["object_sha256"],
                    artifact_kind=artifact_kind,
                )

            self._record_failure(
                object_key=object_key,
                artifact_kind=artifact_kind,
                http_status=status_code,
            )
            raise

        version_id = self._require_version_id(response.get("VersionId"))
        etag = self._optional_string(response.get("ETag"))

        self._telemetry.metric(
            name="NvdBronzeCreated",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="NvdBronzePayloadBytes",
            value=float(len(body)),
            unit="Bytes",
        )

        self._telemetry.info(
            "NVD Bootstrap Bronze object created",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "artifact_kind": artifact_kind,
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
        expected_sha256: str,
        artifact_kind: str,
    ) -> NvdBronzeWriteResult:
        """Resolve 412 idempotency and verify existing object provenance."""
        try:
            with self._telemetry.span("nvd.s3.head_object"):
                response = self._client.head_object(
                    Bucket=self._bucket_name,
                    Key=object_key,
                )
        except ClientError:
            self._record_failure(
                object_key=object_key,
                artifact_kind=artifact_kind,
                http_status=None,
            )
            raise

        version_id = self._require_version_id(response.get("VersionId"))

        content_length = response.get("ContentLength")

        if type(content_length) is not int:
            raise NvdBronzeEvidenceError("Existing NVD Bronze object has no valid ContentLength.")

        if content_length != expected_size:
            raise NvdBronzeEvidenceError(
                "Existing NVD Bronze object size does not match the expected immutable evidence."
            )

        content_type = response.get("ContentType")

        if content_type != expected_content_type:
            raise NvdBronzeEvidenceError(
                "Existing NVD Bronze object ContentType does not match "
                "the expected immutable evidence."
            )

        metadata_value = response.get("Metadata")

        if not isinstance(metadata_value, Mapping):
            raise NvdBronzeEvidenceError("Existing NVD Bronze object has no valid metadata.")

        metadata = cast(
            Mapping[object, object],
            metadata_value,
        )

        stored_sha256 = metadata.get("object_sha256")

        if stored_sha256 != expected_sha256:
            raise NvdBronzeEvidenceError(
                "Existing NVD Bronze object SHA-256 metadata does not "
                "match the expected immutable evidence."
            )

        etag = self._optional_string(response.get("ETag"))

        self._telemetry.metric(
            name="NvdBronzeAlreadyExists",
            value=1.0,
            unit="Count",
        )

        self._telemetry.info(
            "NVD Bootstrap Bronze object already exists and was verified",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "artifact_kind": artifact_kind,
                "version_id": version_id,
                "etag": etag,
            },
        )

        return NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.ALREADY_EXISTS,
            version_id=version_id,
            etag=etag,
        )

    def _source_metadata(
        self,
        *,
        identity: NvdBootstrapSourceIdentity,
        artifact_kind: str,
        object_sha256: str,
    ) -> dict[str, str]:
        """Build source-provenance metadata for feed and META objects."""
        return {
            "source": self.SOURCE,
            "source_interface": self.SOURCE_INTERFACE,
            "artifact_kind": artifact_kind,
            "feed_year": str(identity.feed_year),
            "feed_revision": identity.feed_revision,
            "source_last_modified_at": self._format_utc(identity.meta.last_modified_at),
            "source_sha256": identity.meta.source_sha256,
            "object_sha256": object_sha256,
        }

    def _record_failure(
        self,
        *,
        object_key: str,
        artifact_kind: str,
        http_status: int | None,
    ) -> None:
        """Record failed S3 Bronze persistence telemetry."""
        self._telemetry.metric(
            name="NvdBronzeWriteFailure",
            value=1.0,
            unit="Count",
        )
        self._telemetry.exception(
            "Failed to persist NVD Bootstrap Bronze object",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "artifact_kind": artifact_kind,
                "http_status": http_status,
            },
        )

    @staticmethod
    def _require_version_id(value: object) -> str:
        """Require an exact non-empty S3 VersionId."""
        if not isinstance(value, str) or not value:
            raise NvdBronzeEvidenceError("NVD Bronze object does not expose an S3 VersionId.")

        return value

    @staticmethod
    def _optional_string(value: object) -> str | None:
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

    @staticmethod
    def _format_utc(value: datetime) -> str:
        """Format a timezone-aware timestamp as canonical UTC."""
        return (
            value.astimezone(UTC)
            .isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        )
