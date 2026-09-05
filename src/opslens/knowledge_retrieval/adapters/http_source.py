"""Bounded HTTPS acquisition for allowlisted knowledge-corpus sources."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.client import HTTPSConnection
from typing import Protocol, cast
from urllib.parse import urlsplit

from opslens.knowledge_retrieval.domain import KnowledgeSourceDescriptor

MAX_SOURCE_RESPONSE_BYTES = 2 * 1024 * 1024
_CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]", re.ASCII)


class KnowledgeSourceAcquisitionError(RuntimeError):
    """Base error for bounded knowledge-source acquisition failures."""

    reason_code = "knowledge_source_acquisition_failed"


class KnowledgeSourceResponseTooLargeError(KnowledgeSourceAcquisitionError):
    """Raised when a source response exceeds its explicit byte budget."""

    reason_code = "knowledge_source_response_too_large"


class KnowledgeSourceHttpStatusError(KnowledgeSourceAcquisitionError):
    """Raised when a source does not return the single admitted success status."""

    reason_code = "knowledge_source_http_status_error"

    def __init__(self, status_code: int) -> None:
        """Create one status failure without including untrusted response content."""
        super().__init__(f"Knowledge source returned HTTP status {status_code}.")
        self.status_code = status_code


class KnowledgeSourceInvalidResponseError(KnowledgeSourceAcquisitionError):
    """Raised when source metadata or bytes violate the acquisition contract."""

    reason_code = "invalid_knowledge_source_response"


def _require_descriptor(value: object) -> KnowledgeSourceDescriptor:
    if not isinstance(value, KnowledgeSourceDescriptor):
        raise KnowledgeSourceInvalidResponseError(
            "descriptor must be a KnowledgeSourceDescriptor"
        )
    return value


def _require_body(value: object) -> bytes:
    if not isinstance(value, bytes) or not value:
        raise KnowledgeSourceInvalidResponseError("body must contain non-empty bytes")
    return value


def _require_content_type(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeSourceInvalidResponseError("content_type must not be blank")
    return value


def _require_byte_count(value: object, *, expected: int) -> int:
    if type(value) is not int or value != expected:
        raise KnowledgeSourceInvalidResponseError(
            "byte_count must exactly match the acquired body length"
        )
    return value


def _require_source_digest(value: object, *, body: bytes) -> str:
    if not isinstance(value, str):
        raise KnowledgeSourceInvalidResponseError(
            "source_bytes_sha256 must be a string"
        )
    expected_digest = hashlib.sha256(body).hexdigest()
    if value != expected_digest:
        raise KnowledgeSourceInvalidResponseError(
            "source_bytes_sha256 must exactly match the acquired body"
        )
    return value


@dataclass(frozen=True, slots=True)
class KnowledgeSourceHttpConfig:
    """Explicit local bounds for public knowledge-source HTTPS reads."""

    timeout_seconds: float = 10.0
    max_response_bytes: int = MAX_SOURCE_RESPONSE_BYTES
    user_agent: str = "OpsLens/phase7-corpus"

    def __post_init__(self) -> None:
        """Validate acquisition bounds before any network call can occur."""
        if not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 30:
            raise ValueError(
                "Knowledge source timeout must be finite and between 0 and 30 seconds."
            )
        if (
            type(self.max_response_bytes) is not int
            or not 1 <= self.max_response_bytes <= 8 * 1024 * 1024
        ):
            raise ValueError(
                "Knowledge source response budget must be between 1 byte and 8 MiB."
            )
        if (
            not self.user_agent
            or self.user_agent != self.user_agent.strip()
            or len(self.user_agent) > 128
            or _CONTROL_CHARACTER_PATTERN.search(self.user_agent) is not None
        ):
            raise ValueError("Knowledge source User-Agent must be a clean bounded string.")


class KnowledgeHttpsResponse(Protocol):
    """Minimal HTTPS response surface required by the bounded transport."""

    status: int

    def getheader(self, name: str, default: str | None = None) -> str | None:
        """Return one response header."""
        ...

    def read(self, amt: int | None = None) -> bytes:
        """Read at most the requested number of bytes."""
        ...


class KnowledgeHttpsConnection(Protocol):
    """Minimal HTTPS connection surface required by the bounded transport."""

    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None:
        """Issue one request to the already authorized source host."""
        ...

    def getresponse(self) -> KnowledgeHttpsResponse:
        """Return the HTTP response."""
        ...

    def close(self) -> None:
        """Close the connection."""
        ...


KnowledgeHttpsConnectionFactory = Callable[[str, float], KnowledgeHttpsConnection]


@dataclass(frozen=True, slots=True)
class AcquiredKnowledgeSource:
    """Exact inert source bytes plus evidence needed before normalization."""

    descriptor: KnowledgeSourceDescriptor
    body: bytes
    content_type: str
    byte_count: int
    source_bytes_sha256: str

    def __post_init__(self) -> None:
        """Verify that acquisition evidence exactly identifies the admitted bytes."""
        descriptor = _require_descriptor(self.descriptor)
        body = _require_body(self.body)
        content_type = _require_content_type(self.content_type)
        byte_count = _require_byte_count(self.byte_count, expected=len(body))
        source_bytes_sha256 = _require_source_digest(
            self.source_bytes_sha256,
            body=body,
        )
        object.__setattr__(self, "descriptor", descriptor)
        object.__setattr__(self, "body", body)
        object.__setattr__(self, "content_type", content_type)
        object.__setattr__(self, "byte_count", byte_count)
        object.__setattr__(self, "source_bytes_sha256", source_bytes_sha256)

    @classmethod
    def from_body(
        cls,
        *,
        descriptor: KnowledgeSourceDescriptor,
        body: bytes,
        content_type: str,
    ) -> AcquiredKnowledgeSource:
        """Derive immutable raw-byte identity from one admitted HTTPS body."""
        return cls(
            descriptor=descriptor,
            body=body,
            content_type=content_type,
            byte_count=len(body),
            source_bytes_sha256=hashlib.sha256(body).hexdigest(),
        )


def _default_connection_factory(
    host: str,
    timeout_seconds: float,
) -> KnowledgeHttpsConnection:
    """Create one TLS-validating standard-library HTTPS connection."""
    connection = HTTPSConnection(host, timeout=timeout_seconds)
    return cast(KnowledgeHttpsConnection, connection)


class BoundedHttpsKnowledgeSource:
    """Acquire one allowlisted public HTML source with no redirects or retries."""

    def __init__(
        self,
        *,
        config: KnowledgeSourceHttpConfig | None = None,
        connection_factory: KnowledgeHttpsConnectionFactory = _default_connection_factory,
    ) -> None:
        """Create the adapter with explicit local bounds and injectable transport."""
        self._config = config or KnowledgeSourceHttpConfig()
        self._connection_factory = connection_factory

    def acquire(self, descriptor: KnowledgeSourceDescriptor) -> AcquiredKnowledgeSource:
        """Read exact bytes from the descriptor's already-authorized canonical URI."""
        parsed = urlsplit(descriptor.canonical_uri)
        if parsed.scheme != "https" or parsed.hostname != descriptor.allowed_host:
            raise KnowledgeSourceInvalidResponseError(
                "descriptor canonical URI no longer matches its HTTPS host authorization"
            )
        try:
            port = parsed.port
        except ValueError as exc:
            raise KnowledgeSourceInvalidResponseError(
                "knowledge source canonical URI contains an invalid port"
            ) from exc
        if port not in (None, 443):
            raise KnowledgeSourceInvalidResponseError(
                "knowledge source acquisition allows only the default HTTPS port"
            )

        request_target = parsed.path or "/"
        if parsed.query:
            request_target = f"{request_target}?{parsed.query}"

        connection = self._connection_factory(
            descriptor.allowed_host,
            self._config.timeout_seconds,
        )
        try:
            connection.request(
                "GET",
                request_target,
                headers=self._headers(),
            )
            response = connection.getresponse()
            if response.status != 200:
                raise KnowledgeSourceHttpStatusError(response.status)

            content_type = response.getheader("Content-Type")
            if _base_media_type(content_type) != "text/html":
                raise KnowledgeSourceInvalidResponseError(
                    f"Knowledge source used unexpected Content-Type {content_type!r}."
                )
            content_encoding = response.getheader("Content-Encoding")
            if content_encoding is not None and content_encoding.strip().lower() != "identity":
                raise KnowledgeSourceInvalidResponseError(
                    "Knowledge source must return identity-encoded bytes."
                )

            body = _read_bounded(response, self._config.max_response_bytes)
            if not body:
                raise KnowledgeSourceInvalidResponseError(
                    "Knowledge source returned an empty body."
                )
            return AcquiredKnowledgeSource.from_body(
                descriptor=descriptor,
                body=body,
                content_type=cast(str, content_type),
            )
        except KnowledgeSourceAcquisitionError:
            raise
        except OSError as exc:
            raise KnowledgeSourceAcquisitionError(
                "Knowledge source HTTPS acquisition failed before a valid response was obtained."
            ) from exc
        finally:
            connection.close()

    def _headers(self) -> dict[str, str]:
        """Build deterministic headers with no credentials or ambient cookies."""
        return {
            "Accept": "text/html",
            "Accept-Encoding": "identity",
            "User-Agent": self._config.user_agent,
        }


def _base_media_type(content_type: str | None) -> str | None:
    """Return one lowercase media type without parameters."""
    if content_type is None:
        return None
    return content_type.split(";", maxsplit=1)[0].strip().lower()


def _read_bounded(response: KnowledgeHttpsResponse, max_bytes: int) -> bytes:
    """Reject known or observed source bodies larger than the explicit budget."""
    content_length = _optional_non_negative_int(response.getheader("Content-Length"))
    if content_length is not None and content_length > max_bytes:
        raise KnowledgeSourceResponseTooLargeError(
            "Knowledge source Content-Length exceeds the configured byte budget."
        )

    body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise KnowledgeSourceResponseTooLargeError(
            "Knowledge source body exceeds the configured byte budget."
        )
    return body


def _optional_non_negative_int(value: str | None) -> int | None:
    """Parse optional non-negative integer response metadata conservatively."""
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None
