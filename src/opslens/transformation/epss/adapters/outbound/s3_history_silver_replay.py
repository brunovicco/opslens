"""Amazon S3 exact replay verification for historical EPSS Silver Parquet."""

from hashlib import sha256
from typing import Protocol, TypedDict

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.epss.history.models import (
    HistoricalEpssSilverArtifactV1,
    HistoricalEpssSilverStoredObjectV1,
)


class HistoricalEpssSilverReplayMismatchError(ValueError):
    """Raised when persisted historical Silver differs from prepared bytes."""


class S3ObjectBody(Protocol):
    """Define the readable S3 response-body capability required for replay."""

    def read(self) -> bytes:
        """Read complete object bytes."""
        ...

    def close(self) -> None:
        """Release response-body resources."""
        ...


class S3HistoricalEpssSilverHeadResponse(TypedDict, total=False):
    """Represent current-object evidence required from HeadObject."""

    ContentLength: int
    VersionId: str


class S3HistoricalEpssSilverGetResponse(TypedDict, total=False):
    """Represent exact-version evidence required from GetObject."""

    Body: S3ObjectBody
    ContentLength: int
    VersionId: str


class S3HistoricalEpssSilverReplayClient(Protocol):
    """Define minimal S3 capabilities required for exact Silver replay."""

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3HistoricalEpssSilverHeadResponse:
        """Discover the current exact object version."""
        ...

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3HistoricalEpssSilverGetResponse:
        """Read one exact object version."""
        ...


class S3HistoricalEpssSilverReplayVerifier:
    """Verify existing historical EPSS Silver against deterministic bytes."""

    def __init__(
        self,
        *,
        client: S3HistoricalEpssSilverReplayClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize exact replay dependencies."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("Historical EPSS Silver replay bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def verify_current(
        self,
        *,
        key: str,
        artifact: HistoricalEpssSilverArtifactV1,
    ) -> HistoricalEpssSilverStoredObjectV1:
        """Verify the current key by reading one explicitly discovered S3 version."""
        normalized_key = key.strip()

        if not normalized_key:
            raise ValueError("Historical EPSS Silver replay object key cannot be empty.")

        fields = {
            "bucket": self._bucket_name,
            "object_key": normalized_key,
            "expected_sha256": artifact.parquet_sha256,
            "expected_size_bytes": artifact.size_bytes,
            "row_count": artifact.row_count,
            "schema_version": artifact.schema_version,
        }

        self._telemetry.info(
            "Verifying existing historical EPSS Silver replay",
            fields=fields,
        )

        try:
            with self._telemetry.span("epss.history.silver.s3.head_parquet_current"):
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
                raise HistoricalEpssSilverReplayMismatchError(
                    "Current historical EPSS Silver object size does not match prepared bytes."
                )

            with self._telemetry.span("epss.history.silver.s3.get_parquet_version"):
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=normalized_key,
                    VersionId=current_version_id,
                )
                body = response.get("Body")

                if body is None:
                    raise HistoricalEpssSilverReplayMismatchError(
                        "Exact historical EPSS Silver GetObject response is missing Body."
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
        except HistoricalEpssSilverReplayMismatchError:
            self._telemetry.metric(
                name="EpssHistorySilverReplayMismatch",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Existing historical EPSS Silver replay does not match",
                fields=fields,
            )
            raise
        except Exception:
            self._telemetry.metric(
                name="EpssHistorySilverReplayFailure",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Failed to verify existing historical EPSS Silver replay",
                fields=fields,
            )
            raise

        self._telemetry.metric(
            name="EpssHistorySilverReplayVerified",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="EpssHistorySilverReplayReadBytes",
            value=float(len(payload)),
            unit="Bytes",
        )
        self._telemetry.info(
            "Existing historical EPSS Silver replay verified",
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
        response: S3HistoricalEpssSilverGetResponse,
        payload: bytes,
        artifact: HistoricalEpssSilverArtifactV1,
    ) -> HistoricalEpssSilverStoredObjectV1:
        """Require exact physical equality with the prepared deterministic artifact."""
        response_version_id = cls._require_version_id(
            response.get("VersionId"),
            context="GetObject",
        )

        if response_version_id != version_id:
            raise HistoricalEpssSilverReplayMismatchError(
                "Exact historical EPSS Silver GetObject VersionId does not match HeadObject."
            )

        content_length = cls._require_content_length(
            response.get("ContentLength"),
            context="GetObject",
        )

        if content_length != artifact.size_bytes:
            raise HistoricalEpssSilverReplayMismatchError(
                "Exact historical EPSS Silver ContentLength does not match prepared bytes."
            )
        if len(payload) != artifact.size_bytes:
            raise HistoricalEpssSilverReplayMismatchError(
                "Exact historical EPSS Silver payload size does not match prepared bytes."
            )

        persisted_sha256 = sha256(payload).hexdigest()

        if persisted_sha256 != artifact.parquet_sha256:
            raise HistoricalEpssSilverReplayMismatchError(
                "Exact historical EPSS Silver SHA-256 does not match prepared bytes."
            )
        if payload != artifact.parquet_bytes:
            raise HistoricalEpssSilverReplayMismatchError(
                "Exact historical EPSS Silver bytes do not match prepared bytes."
            )

        return HistoricalEpssSilverStoredObjectV1(
            key=key,
            version_id=version_id,
            parquet_sha256=persisted_sha256,
            size_bytes=len(payload),
            row_count=artifact.row_count,
            schema_version=artifact.schema_version,
        )

    @staticmethod
    def _require_version_id(value: object, *, context: str) -> str:
        """Require a non-empty exact S3 VersionId."""
        if not isinstance(value, str) or not value.strip():
            raise HistoricalEpssSilverReplayMismatchError(
                f"Historical EPSS Silver {context} response requires VersionId."
            )
        return value

    @staticmethod
    def _require_content_length(value: object, *, context: str) -> int:
        """Require a positive S3 ContentLength."""
        if type(value) is not int or value <= 0:
            raise HistoricalEpssSilverReplayMismatchError(
                f"Historical EPSS Silver {context} response requires positive ContentLength."
            )
        return value
