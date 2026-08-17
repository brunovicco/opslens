"""Amazon S3 adapter for conditionally persisting CISA KEV Bronze catalogs."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.ingestion.kev.application.models import (
    RepositoryWriteResult,
    RepositoryWriteStatus,
)
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.shared.observability.ports import OperationalTelemetry


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent typed HTTP metadata returned inside an S3 client error."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent the subset of a Botocore client error used by this adapter."""

    ResponseMetadata: _S3ResponseMetadata


class S3PutObjectClient(Protocol):
    """Define the minimal S3 client capability required by this adapter."""

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
        """Conditionally create an object in Amazon S3."""
        ...


class S3BronzeCatalogRepository:
    """Persist immutable CISA KEV source observations in the S3 Bronze layer."""

    CONTENT_TYPE = "application/json"
    SOURCE_NAME = "cisa-kev"

    def __init__(
        self,
        client: S3PutObjectClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the S3 repository with explicit dependencies.

        Args:
            client: Minimal S3 PutObject-capable client.
            bucket_name: Destination Bronze S3 bucket.
            telemetry: Runtime observability implementation.
        """
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("S3 Bronze bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def create_if_absent(
        self,
        snapshot: KevCatalogSnapshot,
        object_key: str,
    ) -> RepositoryWriteResult:
        """Create an immutable Bronze catalog if its key does not exist.

        Args:
            snapshot: Validated CISA KEV catalog observation.
            object_key: Deterministic S3 object key.

        Returns:
            Repository write result describing whether the object was created
            or already existed.

        Raises:
            ClientError: If S3 returns any error other than the expected
                precondition failure used for idempotency.
        """
        self._telemetry.info(
            "Persisting CISA KEV Bronze catalog",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "snapshot_date": snapshot.snapshot_date,
                "payload_size_bytes": snapshot.payload_size_bytes,
                "record_count": snapshot.record_count,
            },
        )

        try:
            with self._telemetry.span("kev.s3.put_object"):
                response = self._client.put_object(
                    Bucket=self._bucket_name,
                    Key=object_key,
                    Body=snapshot.raw_bytes,
                    ContentType=self.CONTENT_TYPE,
                    Metadata=self._build_metadata(snapshot),
                    IfNoneMatch="*",
                )

        except ClientError as exc:
            return self._handle_client_error(
                error=exc,
                object_key=object_key,
            )

        version_id = self._optional_string(response.get("VersionId"))
        etag = self._optional_string(response.get("ETag"))

        self._telemetry.metric(
            name="KevBronzeCreated",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="KevBronzePayloadBytes",
            value=float(snapshot.payload_size_bytes),
            unit="Bytes",
        )

        self._telemetry.info(
            "CISA KEV Bronze catalog created",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "version_id": version_id,
                "etag": etag,
            },
        )

        return RepositoryWriteResult(
            status=RepositoryWriteStatus.CREATED,
            version_id=version_id,
            etag=etag,
        )

    def _handle_client_error(
        self,
        error: ClientError,
        object_key: str,
    ) -> RepositoryWriteResult:
        """Translate S3 conditional-write outcomes into application results."""
        status_code = self._extract_http_status(error)

        if status_code == 412:
            self._telemetry.metric(
                name="KevBronzeAlreadyExists",
                value=1.0,
                unit="Count",
            )

            self._telemetry.info(
                "CISA KEV Bronze catalog already exists",
                fields={
                    "bucket": self._bucket_name,
                    "object_key": object_key,
                    "http_status": status_code,
                },
            )

            return RepositoryWriteResult(
                status=RepositoryWriteStatus.ALREADY_EXISTS,
            )

        self._telemetry.metric(
            name="KevBronzeWriteFailure",
            value=1.0,
            unit="Count",
        )

        self._telemetry.exception(
            "Failed to persist CISA KEV Bronze catalog",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "http_status": status_code,
            },
        )

        raise error

    @classmethod
    def _build_metadata(
        cls,
        snapshot: KevCatalogSnapshot,
    ) -> dict[str, str]:
        """Build provenance metadata persisted alongside the raw catalog."""
        return {
            "source": cls.SOURCE_NAME,
            "catalog_version": snapshot.catalog_version,
            "date_released": cls._format_utc(snapshot.date_released),
            "retrieved_at": cls._format_utc(snapshot.retrieved_at),
            "sha256": snapshot.sha256,
            "record_count": str(snapshot.record_count),
        }

    @staticmethod
    def _format_utc(value: datetime) -> str:
        """Format a timezone-aware timestamp as canonical UTC."""
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _extract_http_status(
        error: ClientError,
    ) -> int | None:
        """Extract the HTTP status code from a Botocore client error."""
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
    def _optional_string(
        value: object,
    ) -> str | None:
        """Return a string response value when one is available."""
        return value if isinstance(value, str) else None
