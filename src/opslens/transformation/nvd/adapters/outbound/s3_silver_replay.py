"""Amazon S3 exact replay verification for NVD Silver Parquet."""

from hashlib import sha256
from typing import Protocol, TypedDict

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverStoredObjectV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverParquetArtifactV1,
)


class NvdSilverParquetReplayMismatchError(ValueError):
    """Raised when persisted Silver evidence differs from the expected artifact."""


class S3ObjectBody(Protocol):
    """Define the readable S3 body capability required for exact replay."""

    def read(self) -> bytes:
        """Read the complete object payload."""
        ...

    def close(self) -> None:
        """Release response-body resources."""
        ...


class S3HeadObjectResponse(TypedDict, total=False):
    """Represent the HeadObject response fields required by replay."""

    ContentLength: int
    VersionId: str


class S3GetObjectVersionResponse(TypedDict, total=False):
    """Represent exact GetObject response fields required by replay."""

    Body: S3ObjectBody
    ContentLength: int
    VersionId: str


class S3NvdSilverReplayClient(Protocol):
    """Define the minimal S3 capabilities required for exact replay."""

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3HeadObjectResponse:
        """Read metadata for the current object version."""
        ...

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectVersionResponse:
        """Read one exact object version."""
        ...


class S3NvdSilverParquetReplayVerifier:
    """Verify that an existing Silver key contains the expected exact artifact."""

    def __init__(
        self,
        *,
        client: S3NvdSilverReplayClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize exact replay verification dependencies."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("S3 NVD Silver replay bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def verify_current(
        self,
        *,
        key: str,
        artifact: NvdSilverParquetArtifactV1,
    ) -> NvdSilverStoredObjectV1:
        """Verify current-key replay using an exact immutable S3 version."""
        normalized_key = key.strip()

        if not normalized_key:
            raise ValueError("NVD Silver replay object key cannot be empty.")

        fields = {
            "bucket": self._bucket_name,
            "object_key": normalized_key,
            "expected_sha256": artifact.parquet_sha256,
            "expected_size_bytes": artifact.size_bytes,
            "source_kind": artifact.source_kind.value,
            "source_batch_id": artifact.source_batch_id,
        }

        self._telemetry.info(
            "Verifying existing NVD Silver Parquet replay",
            fields=fields,
        )

        try:
            with self._telemetry.span("nvd.silver.s3.head_parquet_current"):
                head = self._client.head_object(
                    Bucket=self._bucket_name,
                    Key=normalized_key,
                )

            current_version_id = self._require_version_id(
                head.get("VersionId"),
                context="HeadObject",
            )

            head_content_length = self._require_content_length(
                head.get("ContentLength"),
                context="HeadObject",
            )

            if head_content_length != artifact.size_bytes:
                raise NvdSilverParquetReplayMismatchError(
                    "Current NVD Silver object size does not match the deterministic artifact."
                )

            with self._telemetry.span("nvd.silver.s3.get_parquet_version"):
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=normalized_key,
                    VersionId=current_version_id,
                )

                body = response.get("Body")

                if body is None:
                    raise NvdSilverParquetReplayMismatchError(
                        "Exact NVD Silver GetObject response is missing Body."
                    )

                try:
                    payload = body.read()
                finally:
                    body.close()

            stored = self._verify_exact_payload(
                key=normalized_key,
                version_id=current_version_id,
                response=response,
                payload=payload,
                artifact=artifact,
            )

        except NvdSilverParquetReplayMismatchError:
            self._telemetry.metric(
                name="NvdSilverParquetReplayMismatch",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Existing NVD Silver Parquet replay does not match",
                fields=fields,
            )
            raise
        except Exception:
            self._telemetry.metric(
                name="NvdSilverParquetReplayFailure",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Failed to verify existing NVD Silver Parquet replay",
                fields=fields,
            )
            raise

        self._telemetry.metric(
            name="NvdSilverParquetReplayVerified",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="NvdSilverParquetReplayReadBytes",
            value=float(len(payload)),
            unit="Bytes",
        )

        self._telemetry.info(
            "Existing NVD Silver Parquet replay verified",
            fields={
                **fields,
                "version_id": stored.version_id,
            },
        )

        return stored

    @classmethod
    def _verify_exact_payload(
        cls,
        *,
        key: str,
        version_id: str,
        response: S3GetObjectVersionResponse,
        payload: bytes,
        artifact: NvdSilverParquetArtifactV1,
    ) -> NvdSilverStoredObjectV1:
        """Require exact physical equality with the deterministic artifact."""
        response_version_id = cls._require_version_id(
            response.get("VersionId"),
            context="GetObject",
        )

        if response_version_id != version_id:
            raise NvdSilverParquetReplayMismatchError(
                "Exact NVD Silver GetObject VersionId does not match "
                "the discovered current version."
            )

        content_length = cls._require_content_length(
            response.get("ContentLength"),
            context="GetObject",
        )

        if content_length != artifact.size_bytes:
            raise NvdSilverParquetReplayMismatchError(
                "Exact NVD Silver object ContentLength does not match the deterministic artifact."
            )

        if len(payload) != artifact.size_bytes:
            raise NvdSilverParquetReplayMismatchError(
                "Exact NVD Silver payload size does not match the deterministic artifact."
            )

        persisted_sha256 = sha256(payload).hexdigest()

        if persisted_sha256 != artifact.parquet_sha256:
            raise NvdSilverParquetReplayMismatchError(
                "Exact NVD Silver payload SHA-256 does not match the deterministic artifact."
            )

        if payload != artifact.parquet_bytes:
            raise NvdSilverParquetReplayMismatchError(
                "Exact NVD Silver payload bytes do not match the deterministic artifact."
            )

        return NvdSilverStoredObjectV1(
            key=key,
            version_id=version_id,
            sha256=persisted_sha256,
            size_bytes=len(payload),
            row_count=artifact.row_count,
        )

    @staticmethod
    def _require_version_id(
        value: object,
        *,
        context: str,
    ) -> str:
        """Require a non-empty S3 VersionId."""
        if not isinstance(value, str) or not value.strip():
            raise NvdSilverParquetReplayMismatchError(
                f"NVD Silver {context} response requires VersionId."
            )

        return value

    @staticmethod
    def _require_content_length(
        value: object,
        *,
        context: str,
    ) -> int:
        """Require a positive S3 ContentLength."""
        if type(value) is not int or value <= 0:
            raise NvdSilverParquetReplayMismatchError(
                f"NVD Silver {context} response requires positive ContentLength."
            )

        return value
