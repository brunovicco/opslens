"""Amazon S3 adapter for reading exact CISA KEV Bronze object versions."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol, TypedDict, cast

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.kev.adapters.inbound.s3_event import (
    KevBronzeObjectReference,
)


class KevBronzeEvidenceMismatchError(ValueError):
    """Raised when S3 evidence disagrees with the triggering object reference."""


class S3ObjectBody(Protocol):
    """Define the readable S3 response-body capability used by this adapter."""

    def read(self) -> bytes:
        """Read the complete S3 object payload."""
        ...

    def close(self) -> None:
        """Release the underlying response-body resources."""
        ...


class S3GetObjectVersionResponse(TypedDict, total=False):
    """Represent the subset of a versioned S3 GetObject response we require."""

    Body: S3ObjectBody
    ContentLength: int
    ETag: str
    VersionId: str
    Metadata: Mapping[str, str]


class S3GetObjectVersionClient(Protocol):
    """Define the exact-version S3 read capability required by KEV Silver."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectVersionResponse:
        """Read one exact immutable S3 object version."""
        ...


@dataclass(frozen=True, slots=True)
class KevBronzeObject:
    """Represent KEV Bronze evidence read from one exact S3 object version."""

    reference: KevBronzeObjectReference
    raw_bytes: bytes
    metadata: Mapping[str, str]
    version_id: str
    etag: str
    content_length: int


class S3VersionedKevBronzeRepository:
    """Read exact immutable KEV Bronze versions and verify transport evidence."""

    def __init__(
        self,
        *,
        client: S3GetObjectVersionClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the repository with explicit dependencies.

        Args:
            client: Minimal S3 versioned-GetObject-capable client.
            bucket_name: Expected OpsLens data bucket.
            telemetry: Runtime observability implementation.
        """
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("S3 Bronze bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def get(
        self,
        reference: KevBronzeObjectReference,
    ) -> KevBronzeObject:
        """Read and verify the exact Bronze object version from the event.

        Args:
            reference: Validated immutable object reference from the S3 event.

        Returns:
            Bronze bytes and S3 metadata after transport-evidence validation.

        Raises:
            KevBronzeEvidenceMismatchError: If the event reference and the
                returned S3 object disagree.
            Exception: If the underlying S3 read fails.
        """
        if reference.bucket != self._bucket_name:
            raise KevBronzeEvidenceMismatchError(
                "KEV Bronze event bucket does not match the configured repository bucket."
            )

        self._telemetry.info(
            "Reading exact CISA KEV Bronze object version",
            fields={
                "bucket": reference.bucket,
                "object_key": reference.key,
                "version_id": reference.version_id,
            },
        )

        try:
            with self._telemetry.span("kev.silver.s3.get_object_version"):
                response = self._client.get_object(
                    Bucket=reference.bucket,
                    Key=reference.key,
                    VersionId=reference.version_id,
                )

                body = response.get("Body")

                if body is None:
                    raise KevBronzeEvidenceMismatchError(
                        "Versioned S3 GetObject response is missing Body."
                    )

                try:
                    payload = body.read()
                finally:
                    body.close()

        except KevBronzeEvidenceMismatchError:
            self._record_evidence_mismatch(reference)
            raise
        except Exception:
            self._telemetry.metric(
                name="KevSilverBronzeReadFailure",
                value=1.0,
                unit="Count",
            )

            self._telemetry.exception(
                "Failed to read exact CISA KEV Bronze object version",
                fields={
                    "bucket": reference.bucket,
                    "object_key": reference.key,
                    "version_id": reference.version_id,
                },
            )
            raise

        try:
            bronze_object = self._verify_response(
                reference=reference,
                response=response,
                payload=payload,
            )
        except KevBronzeEvidenceMismatchError:
            self._record_evidence_mismatch(reference)
            raise

        self._telemetry.metric(
            name="KevSilverBronzeReadBytes",
            value=float(len(payload)),
            unit="Bytes",
        )

        self._telemetry.info(
            "Exact CISA KEV Bronze object version verified",
            fields={
                "bucket": reference.bucket,
                "object_key": reference.key,
                "version_id": bronze_object.version_id,
                "payload_size_bytes": len(payload),
            },
        )

        return bronze_object

    def _verify_response(
        self,
        *,
        reference: KevBronzeObjectReference,
        response: S3GetObjectVersionResponse,
        payload: bytes,
    ) -> KevBronzeObject:
        """Cross-check transport evidence returned by S3 against the event."""
        version_id = self._require_response_string(
            response.get("VersionId"),
            field_name="VersionId",
        )

        etag = self._require_response_string(
            response.get("ETag"),
            field_name="ETag",
        )

        content_length = response.get("ContentLength")

        if type(content_length) is not int or content_length <= 0:
            raise KevBronzeEvidenceMismatchError(
                "Versioned S3 GetObject response ContentLength must be positive."
            )

        metadata_value = response.get("Metadata")

        if not isinstance(metadata_value, Mapping):
            raise KevBronzeEvidenceMismatchError(
                "Versioned S3 GetObject response Metadata must be a mapping."
            )

        metadata = cast(Mapping[object, object], metadata_value)

        if not all(
            isinstance(key, str) and isinstance(value, str) for key, value in metadata.items()
        ):
            raise KevBronzeEvidenceMismatchError(
                "Versioned S3 GetObject metadata must contain only string keys and values."
            )

        normalized_metadata = {cast(str, key): cast(str, value) for key, value in metadata.items()}

        response_etag = self._normalize_etag(etag)
        event_etag = self._normalize_etag(reference.etag)

        if version_id != reference.version_id:
            raise KevBronzeEvidenceMismatchError(
                "S3 response VersionId does not match the triggering event."
            )

        if response_etag != event_etag:
            raise KevBronzeEvidenceMismatchError(
                "S3 response ETag does not match the triggering event."
            )

        if content_length != reference.size_bytes:
            raise KevBronzeEvidenceMismatchError(
                "S3 response ContentLength does not match the triggering event."
            )

        if len(payload) != content_length:
            raise KevBronzeEvidenceMismatchError(
                "S3 response ContentLength does not match the bytes actually read."
            )

        return KevBronzeObject(
            reference=reference,
            raw_bytes=payload,
            metadata=MappingProxyType(normalized_metadata),
            version_id=version_id,
            etag=response_etag,
            content_length=content_length,
        )

    def _record_evidence_mismatch(
        self,
        reference: KevBronzeObjectReference,
    ) -> None:
        """Emit source-specific telemetry for evidence-contract failures."""
        self._telemetry.metric(
            name="KevSilverBronzeEvidenceMismatch",
            value=1.0,
            unit="Count",
        )

        self._telemetry.exception(
            "CISA KEV Bronze transport evidence mismatch",
            fields={
                "bucket": reference.bucket,
                "object_key": reference.key,
                "version_id": reference.version_id,
            },
        )

    @staticmethod
    def _require_response_string(
        value: object,
        *,
        field_name: str,
    ) -> str:
        """Require one non-empty string from a versioned GetObject response."""
        if not isinstance(value, str) or not value:
            raise KevBronzeEvidenceMismatchError(
                f"Versioned S3 GetObject response {field_name} must be non-empty."
            )

        return value

    @staticmethod
    def _normalize_etag(value: str) -> str:
        """Normalize the optional HTTP quotes surrounding an S3 ETag."""
        normalized = value.strip()

        if len(normalized) >= 2 and normalized.startswith('"') and normalized.endswith('"'):
            return normalized[1:-1]

        return normalized
