"""Hold the GHSA observation boundary in S3, and let only one run advance it.

The boundary is one object and every scheduled run reads it, works, and writes it back.
That read-modify-write is where two runs can quietly undo each other.

Two firings can overlap: a run that is catching up across several 31-day windows takes
minutes, and the schedule does not wait for it. Both read the same boundary, both finish,
and the second write lands on top of the first — silently discarding the window the first
one actually completed, or worse, moving the boundary backwards so a stretch of advisories
is skipped by the next run.

```text
two runs != two windows
last write wins != last write is right
```

So the write is conditional on the `ETag` that was read. The loser of a race gets a
precondition failure and does nothing; its window is simply run again. Nothing is
reconciled, because there is nothing to reconcile — a window that was not committed was
not observed.

**Advancing backwards is refused before the round trip.** The caller hands over the whole
previously-read state rather than an `ETag` alone, so the store can compare instants
itself. A valid `ETag` proves nobody else wrote; it says nothing about whether this write
is progress.

```text
a valid precondition != a correct value
```

**Creation is create-only.** `initialize` refuses to overwrite an existing boundary, so a
seed cannot silently reset a corpus that has been advancing for months.
"""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.ingestion.ghsa.application.sync_watermark import (
    GhsaSyncWatermarkV1,
    parse_watermark,
    serialize_watermark,
)


class GhsaSyncWatermarkStoreError(RuntimeError):
    """Raised when the boundary cannot be read or written at all."""


class GhsaSyncWatermarkNotFoundError(GhsaSyncWatermarkStoreError):
    """Raised when no boundary has been established yet."""


class GhsaSyncWatermarkAlreadyExistsError(GhsaSyncWatermarkStoreError):
    """Raised when a seed would overwrite a boundary that already exists."""


class GhsaSyncWatermarkPreconditionFailedError(GhsaSyncWatermarkStoreError):
    """Raised when another run advanced the boundary first."""


class GhsaSyncWatermarkNotAdvancingError(GhsaSyncWatermarkStoreError):
    """Raised when a write would move the boundary backwards or leave it still."""


class _ReadableBody(Protocol):
    """The bounded streaming-body surface this adapter uses."""

    def read(self, amt: int | None = None) -> bytes:
        """Read response bytes."""
        ...

    def close(self) -> None:
        """Close the stream."""
        ...


class _S3ResponseMetadata(TypedDict, total=False):
    """HTTP metadata returned by Botocore errors."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """The Botocore error fields this adapter inspects."""

    ResponseMetadata: _S3ResponseMetadata


class S3GhsaSyncWatermarkClient(Protocol):
    """The minimum S3 surface an observation boundary needs."""

    def get_object(self, **kwargs: object) -> Mapping[str, object]:
        """Read the boundary object."""
        ...

    def put_object(self, **kwargs: object) -> Mapping[str, object]:
        """Write the boundary object."""
        ...


@dataclass(frozen=True, slots=True)
class PersistedGhsaSyncWatermark:
    """One boundary, and the concurrency token that read it.

    Attributes:
        watermark: The boundary itself.
        etag: The object version this was read at, required to write over it.
        sha256: Digest of the exact retained bytes.
    """

    watermark: GhsaSyncWatermarkV1
    etag: str
    sha256: str

    def __post_init__(self) -> None:
        """Reject persisted state that cannot support a conditional write.

        Raises:
            GhsaSyncWatermarkStoreError: If the token or digest is missing.
        """
        if type(self.etag) is not str or not self.etag.strip():
            raise GhsaSyncWatermarkStoreError(
                "a persisted boundary must carry the ETag it was read at"
            )
        if type(self.sha256) is not str or len(self.sha256) != 64:
            raise GhsaSyncWatermarkStoreError(
                "a persisted boundary must carry the digest of its retained bytes"
            )


class S3GhsaSyncWatermarkStore:
    """Read and conditionally advance the GHSA observation boundary."""

    CONTENT_TYPE = "application/json"
    MAX_PAYLOAD_BYTES = 64 * 1024

    def __init__(
        self,
        *,
        client: S3GhsaSyncWatermarkClient,
        bucket_name: str,
        object_key: str,
    ) -> None:
        """Bind the object this store owns.

        Args:
            client: S3 access.
            bucket_name: Bucket holding the boundary.
            object_key: Key of the boundary object.

        Raises:
            GhsaSyncWatermarkStoreError: If either coordinate is empty.
        """
        bucket = bucket_name.strip()
        key = object_key.strip()
        if not bucket or not key:
            raise GhsaSyncWatermarkStoreError(
                "a boundary store needs both a bucket and an object key"
            )
        self._client = client
        self._bucket_name = bucket
        self._object_key = key

    def load(self) -> PersistedGhsaSyncWatermark:
        """Read the current boundary.

        Returns:
            The boundary and the token to write over it.

        Raises:
            GhsaSyncWatermarkNotFoundError: If no boundary exists yet.
            GhsaSyncWatermarkStoreError: If the object cannot be read or parsed.
        """
        try:
            response = self._client.get_object(
                Bucket=self._bucket_name, Key=self._object_key
            )
        except ClientError as exc:
            if self._status(exc) == 404:
                raise GhsaSyncWatermarkNotFoundError(
                    "no GHSA observation boundary has been established"
                ) from exc
            raise GhsaSyncWatermarkStoreError(
                f"the GHSA observation boundary could not be read: {exc}"
            ) from exc

        payload = self._body(response)
        return PersistedGhsaSyncWatermark(
            watermark=parse_watermark(payload),
            etag=self._text(response, "ETag"),
            sha256=hashlib.sha256(payload).hexdigest(),
        )

    def initialize(self, watermark: GhsaSyncWatermarkV1) -> PersistedGhsaSyncWatermark:
        """Establish the first boundary, refusing to replace one.

        Args:
            watermark: The seed boundary.

        Returns:
            The persisted boundary.

        Raises:
            GhsaSyncWatermarkAlreadyExistsError: If a boundary already exists.
            GhsaSyncWatermarkStoreError: If the write fails.
        """
        payload = self._payload(watermark)
        try:
            response = self._client.put_object(
                Bucket=self._bucket_name,
                Key=self._object_key,
                Body=payload,
                ContentType=self.CONTENT_TYPE,
                IfNoneMatch="*",
            )
        except ClientError as exc:
            if self._status(exc) in {409, 412}:
                raise GhsaSyncWatermarkAlreadyExistsError(
                    "a GHSA observation boundary already exists; seeding it again would "
                    "reset a corpus that has been advancing"
                ) from exc
            raise GhsaSyncWatermarkStoreError(
                f"the GHSA observation boundary could not be created: {exc}"
            ) from exc

        return PersistedGhsaSyncWatermark(
            watermark=watermark,
            etag=self._text(response, "ETag"),
            sha256=hashlib.sha256(payload).hexdigest(),
        )

    def advance(
        self,
        *,
        previous: PersistedGhsaSyncWatermark,
        watermark: GhsaSyncWatermarkV1,
    ) -> PersistedGhsaSyncWatermark:
        """Move the boundary forward, only if nobody else moved it first.

        Args:
            previous: The state this run read and worked from.
            watermark: The boundary that run's completed window establishes.

        Returns:
            The persisted boundary.

        Raises:
            GhsaSyncWatermarkNotAdvancingError: If the write would not move forward.
            GhsaSyncWatermarkPreconditionFailedError: If another run wrote first.
            GhsaSyncWatermarkStoreError: If the write fails.
        """
        if watermark.observed_through_at <= previous.watermark.observed_through_at:
            raise GhsaSyncWatermarkNotAdvancingError(
                "the boundary would not move forward; a valid precondition proves nobody "
                "else wrote, not that this write is progress"
            )

        payload = self._payload(watermark)
        try:
            response = self._client.put_object(
                Bucket=self._bucket_name,
                Key=self._object_key,
                Body=payload,
                ContentType=self.CONTENT_TYPE,
                IfMatch=previous.etag,
            )
        except ClientError as exc:
            status = self._status(exc)
            if status in {409, 412}:
                raise GhsaSyncWatermarkPreconditionFailedError(
                    "another run advanced the GHSA boundary first; this window was not "
                    "committed and will be run again"
                ) from exc
            if status == 404:
                raise GhsaSyncWatermarkNotFoundError(
                    "the GHSA observation boundary disappeared mid-run"
                ) from exc
            raise GhsaSyncWatermarkStoreError(
                f"the GHSA observation boundary could not be advanced: {exc}"
            ) from exc

        return PersistedGhsaSyncWatermark(
            watermark=watermark,
            etag=self._text(response, "ETag"),
            sha256=hashlib.sha256(payload).hexdigest(),
        )

    def _payload(self, watermark: GhsaSyncWatermarkV1) -> bytes:
        """Render the boundary, refusing one too large to be a boundary.

        Args:
            watermark: The boundary to render.

        Returns:
            The exact bytes to retain.

        Raises:
            GhsaSyncWatermarkStoreError: If the rendering is implausibly large.
        """
        payload = serialize_watermark(watermark)
        if len(payload) > self.MAX_PAYLOAD_BYTES:
            raise GhsaSyncWatermarkStoreError(
                "the rendered boundary is larger than a boundary can be"
            )
        return payload

    def _body(self, response: Mapping[str, object]) -> bytes:
        """Read the object body.

        Args:
            response: The S3 response.

        Returns:
            The object bytes.

        Raises:
            GhsaSyncWatermarkStoreError: If the response carries no readable body.
        """
        body = response.get("Body")
        if body is None:
            raise GhsaSyncWatermarkStoreError(
                "the GHSA boundary response carried no body"
            )
        stream = cast(_ReadableBody, body)
        try:
            return stream.read()
        finally:
            stream.close()

    @staticmethod
    def _text(response: Mapping[str, object], field: str) -> str:
        """Read one required text field from an S3 response.

        Args:
            response: The S3 response.
            field: The field name.

        Returns:
            The value.

        Raises:
            GhsaSyncWatermarkStoreError: If it is absent or not text.
        """
        value = response.get(field)
        if not isinstance(value, str) or not value.strip():
            raise GhsaSyncWatermarkStoreError(
                f"the GHSA boundary response carried no {field}"
            )
        return value

    @staticmethod
    def _status(error: ClientError) -> int | None:
        """Read the HTTP status out of a Botocore error.

        Args:
            error: The error raised.

        Returns:
            The status, or `None` when the error carries none.
        """
        response = cast(_S3ClientErrorResponse, error.response)
        metadata = response.get("ResponseMetadata")
        if metadata is None:
            return None
        return metadata.get("HTTPStatusCode")


__all__ = [
    "GhsaSyncWatermarkAlreadyExistsError",
    "GhsaSyncWatermarkNotAdvancingError",
    "GhsaSyncWatermarkNotFoundError",
    "GhsaSyncWatermarkPreconditionFailedError",
    "GhsaSyncWatermarkStoreError",
    "PersistedGhsaSyncWatermark",
    "S3GhsaSyncWatermarkClient",
    "S3GhsaSyncWatermarkStore",
]
