"""Amazon S3 adapter for reading EPSS Bronze artifacts."""

from typing import Protocol, TypedDict

from opslens.shared.observability.ports import OperationalTelemetry


class S3ObjectBody(Protocol):
    """Define the readable S3 response-body capability used by this adapter."""

    def read(self) -> bytes:
        """Read the complete object payload."""
        ...

    def close(self) -> None:
        """Release the underlying response-body resources."""
        ...


class S3GetObjectResponse(TypedDict):
    """Represent the subset of an S3 GetObject response used by this adapter."""

    Body: S3ObjectBody


class S3GetObjectClient(Protocol):
    """Define the minimal S3 client capability required by this adapter."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3GetObjectResponse:
        """Read an object from Amazon S3."""
        ...


class S3BronzeEpssSnapshotRepository:
    """Read immutable EPSS source artifacts from the S3 Bronze layer."""

    def __init__(
        self,
        client: S3GetObjectClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the Bronze repository.

        Args:
            client: Minimal S3 GetObject-capable client.
            bucket_name: Source data bucket.
            telemetry: Runtime observability implementation.
        """
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("S3 Bronze bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def get(self, key: str) -> bytes:
        """Read one immutable Bronze EPSS artifact.

        Args:
            key: Canonical Bronze object key.

        Returns:
            Gzip-compressed EPSS source bytes.
        """
        normalized_key = key.strip()

        if not normalized_key:
            raise ValueError("S3 Bronze object key cannot be empty.")

        self._telemetry.info(
            "Reading EPSS Bronze snapshot",
            fields={
                "bucket": self._bucket_name,
                "object_key": normalized_key,
            },
        )

        try:
            with self._telemetry.span("epss.s3.get_object"):
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=normalized_key,
                )

                body = response["Body"]

                try:
                    payload = body.read()
                finally:
                    body.close()

        except Exception:
            self._telemetry.metric(
                name="EpssBronzeReadFailure",
                value=1.0,
                unit="Count",
            )

            self._telemetry.exception(
                "Failed to read EPSS Bronze snapshot",
                fields={
                    "bucket": self._bucket_name,
                    "object_key": normalized_key,
                },
            )

            raise

        self._telemetry.metric(
            name="EpssBronzeReadBytes",
            value=float(len(payload)),
            unit="Bytes",
        )

        self._telemetry.info(
            "EPSS Bronze snapshot read",
            fields={
                "bucket": self._bucket_name,
                "object_key": normalized_key,
                "payload_size_bytes": len(payload),
            },
        )

        return payload
