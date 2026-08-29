"""Tests for GHSA authenticated HTTP, Secrets Manager, and S3 adapters."""

import json
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime

import pytest
from botocore.exceptions import ClientError

from opslens.ingestion.ghsa.adapters.outbound.github_api import (
    GhsaAuthenticatedPageSource,
    GhsaAuthenticationError,
    GhsaRateLimitExhaustedError,
)
from opslens.ingestion.ghsa.adapters.outbound.s3_bronze import (
    GhsaBronzeEvidenceError,
    S3GhsaBronzeRepository,
)
from opslens.ingestion.ghsa.adapters.outbound.secrets_manager import (
    CachedGhsaTokenProvider,
    SecretsManagerGhsaTokenProvider,
)
from opslens.ingestion.ghsa.application.attempt import GhsaAttemptIdFactory
from opslens.ingestion.ghsa.application.key_factory import GhsaBronzeKeyFactory
from opslens.ingestion.ghsa.application.manifest import (
    GhsaCompleteManifestFactory,
    GhsaCompleteManifestSerializer,
)
from opslens.ingestion.ghsa.application.models import GhsaBronzeWriteResult
from opslens.ingestion.ghsa.application.ports import GhsaHttpResponse
from opslens.ingestion.ghsa.application.rate_limit import GhsaRetryDelayPolicy
from opslens.ingestion.ghsa.domain.api_page import (
    GhsaAdvisoryApiPage,
    GhsaAdvisoryApiPageParser,
    GhsaAdvisoryPagination,
    GhsaRequestUrlPolicy,
)
from opslens.ingestion.ghsa.domain.sync import GhsaSyncMode, GhsaSyncWindow


class _Telemetry:
    """Minimal deterministic telemetry test double."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore informational events."""
        del message, fields

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Ignore exception events."""
        del message, fields

    def metric(self, name: str, value: float, unit: str) -> None:
        """Ignore metrics."""
        del name, value, unit

    def span(self, name: str) -> AbstractContextManager[object]:
        """Return a no-op context manager."""
        del name
        return nullcontext(object())


class _StaticCredential:
    """Return one fixed test-only credential."""

    def __init__(self, token: str = "test-token") -> None:
        """Initialize the fixed credential."""
        self.token = token
        self.calls = 0

    def get_token(self) -> str:
        """Return the fixed token."""
        self.calls += 1
        return self.token


class _FakeTransport:
    """Return a controlled sequence of HTTP responses."""

    def __init__(self, responses: list[GhsaHttpResponse]) -> None:
        """Initialize the controlled response queue."""
        self.responses = responses
        self.calls = 0
        self.headers_seen: list[dict[str, str]] = []

    def get(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> GhsaHttpResponse:
        """Return the next controlled response."""
        del url, timeout_seconds, max_response_bytes
        self.headers_seen.append(dict(headers))
        response = self.responses[self.calls]
        self.calls += 1
        return response


class _SecretsClient:
    """Minimal Secrets Manager test double."""

    def __init__(self, value: object) -> None:
        """Initialize the controlled secret value."""
        self.value = value
        self.calls = 0

    def get_secret_value(
        self,
        *,
        SecretId: str,
        VersionStage: str,
    ) -> Mapping[str, object]:
        """Return one controlled SecretString response."""
        assert SecretId == "opslens/dev/ghsa/github-token"
        assert VersionStage == "AWSCURRENT"
        self.calls += 1
        return {"SecretString": self.value}


class _S3Client:
    """Minimal versioned S3 test double."""

    def __init__(self) -> None:
        """Initialize controlled S3 responses."""
        self.put_responses: list[Mapping[str, object] | Exception] = []
        self.head_response: Mapping[str, object] = {}
        self.last_bucket: str | None = None
        self.last_key: str | None = None
        self.last_body: bytes | None = None
        self.last_content_type: str | None = None
        self.last_metadata: Mapping[str, str] | None = None
        self.last_if_none_match: str | None = None

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
        """Return or raise the next controlled PutObject result."""
        self.last_bucket = Bucket
        self.last_key = Key
        self.last_body = Body
        self.last_content_type = ContentType
        self.last_metadata = dict(Metadata)
        self.last_if_none_match = IfNoneMatch
        result = self.put_responses.pop(0)

        if isinstance(result, Exception):
            raise result

        return result

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Return one controlled exact-key HEAD result."""
        del Bucket, Key
        return self.head_response


def _window() -> GhsaSyncWindow:
    """Build one small reviewed published window."""
    return GhsaSyncWindow(
        mode=GhsaSyncMode.PUBLISHED,
        start_at=datetime(2026, 8, 1, 0, 0, 0, tzinfo=UTC),
        end_at=datetime(2026, 8, 2, 0, 0, 0, tzinfo=UTC),
    )


def _payload() -> bytes:
    """Build one minimum valid GitHub advisory page."""
    return json.dumps(
        [
            {
                "ghsa_id": "GHSA-2345-6789-cfgh",
                "type": "reviewed",
                "published_at": "2026-08-01T01:00:00Z",
                "updated_at": "2026-08-01T02:00:00Z",
            }
        ],
        separators=(",", ":"),
    ).encode()


def _page_and_pagination() -> tuple[GhsaAdvisoryApiPage, GhsaAdvisoryPagination]:
    """Build one validated page and complete one-page pagination."""
    window = _window()
    page = GhsaAdvisoryApiPageParser().parse(
        _payload(),
        request_url=GhsaRequestUrlPolicy.build_initial(window),
        link_header=None,
        window=window,
    )
    return page, GhsaAdvisoryPagination(window=window, pages=(page,))


def test_authenticated_source_injects_required_headers_without_mutating_payload() -> None:
    """Send Bearer auth and the frozen API version, then return exact source bytes."""
    body = _payload()
    transport = _FakeTransport(
        [GhsaHttpResponse(status_code=200, body=body, headers={"link": "next-value"})]
    )
    source = GhsaAuthenticatedPageSource(
        credential_provider=_StaticCredential(),
        transport=transport,
        retry_delay_policy=GhsaRetryDelayPolicy(),
        telemetry=_Telemetry(),
        sleep_fn=lambda _seconds: None,
    )
    window = _window()

    fetched = source.fetch(
        request_url=GhsaRequestUrlPolicy.build_initial(window),
        window=window,
    )

    assert fetched.payload == body
    assert fetched.link_header == "next-value"
    assert transport.headers_seen == [
        {
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer test-token",
            "User-Agent": "opslens-ghsa-ingestion/0.1",
            "X-GitHub-Api-Version": "2026-03-10",
        }
    ]


def test_authenticated_source_honors_retry_after_before_retrying() -> None:
    """Sleep exactly as instructed by GitHub Retry-After before the next request."""
    sleeps: list[float] = []
    transport = _FakeTransport(
        [
            GhsaHttpResponse(
                status_code=429,
                body=b"rate limited",
                headers={"retry-after": "3"},
            ),
            GhsaHttpResponse(status_code=200, body=_payload(), headers={}),
        ]
    )
    source = GhsaAuthenticatedPageSource(
        credential_provider=_StaticCredential(),
        transport=transport,
        retry_delay_policy=GhsaRetryDelayPolicy(),
        telemetry=_Telemetry(),
        sleep_fn=sleeps.append,
    )
    window = _window()

    source.fetch(
        request_url=GhsaRequestUrlPolicy.build_initial(window),
        window=window,
    )

    assert transport.calls == 2
    assert sleeps == [3.0]


def test_authenticated_source_fails_fast_when_retry_after_exceeds_wait_budget() -> None:
    """Do not sleep or retry early when GitHub requires a wait beyond the runtime budget."""
    sleeps: list[float] = []
    transport = _FakeTransport(
        [
            GhsaHttpResponse(
                status_code=429,
                body=b"rate limited",
                headers={"retry-after": "121"},
            )
        ]
    )
    source = GhsaAuthenticatedPageSource(
        credential_provider=_StaticCredential(),
        transport=transport,
        retry_delay_policy=GhsaRetryDelayPolicy(maximum_delay_seconds=120),
        telemetry=_Telemetry(),
        sleep_fn=sleeps.append,
    )
    window = _window()

    with pytest.raises(
        GhsaRateLimitExhaustedError,
        match="exceeds the bounded GHSA runtime retry budget",
    ):
        source.fetch(
            request_url=GhsaRequestUrlPolicy.build_initial(window),
            window=window,
        )

    assert transport.calls == 1
    assert sleeps == []


def test_authenticated_source_does_not_retry_unauthorized_credentials() -> None:
    """Treat 401 as a terminal credential failure rather than a retryable outage."""
    transport = _FakeTransport(
        [GhsaHttpResponse(status_code=401, body=b"unauthorized", headers={})]
    )
    source = GhsaAuthenticatedPageSource(
        credential_provider=_StaticCredential(),
        transport=transport,
        retry_delay_policy=GhsaRetryDelayPolicy(),
        telemetry=_Telemetry(),
        sleep_fn=lambda _seconds: None,
    )
    window = _window()

    with pytest.raises(GhsaAuthenticationError, match="rejected"):
        source.fetch(
            request_url=GhsaRequestUrlPolicy.build_initial(window),
            window=window,
        )

    assert transport.calls == 1


def test_authenticated_source_fails_after_bounded_rate_limit_budget() -> None:
    """Stop after the configured retry budget instead of retrying indefinitely."""
    transport = _FakeTransport(
        [
            GhsaHttpResponse(status_code=429, body=b"x", headers={"retry-after": "0"}),
            GhsaHttpResponse(status_code=429, body=b"x", headers={"retry-after": "0"}),
        ]
    )
    source = GhsaAuthenticatedPageSource(
        credential_provider=_StaticCredential(),
        transport=transport,
        retry_delay_policy=GhsaRetryDelayPolicy(),
        telemetry=_Telemetry(),
        max_attempts=2,
        sleep_fn=lambda _seconds: None,
    )
    window = _window()

    with pytest.raises(GhsaRateLimitExhaustedError, match="exhausted"):
        source.fetch(
            request_url=GhsaRequestUrlPolicy.build_initial(window),
            window=window,
        )

    assert transport.calls == 2


def test_secrets_manager_provider_reads_only_awscurrent_secret_string() -> None:
    """Load the current raw GitHub token from the dedicated secret."""
    client = _SecretsClient("  token-value  ")
    provider = SecretsManagerGhsaTokenProvider(
        client=client,
        secret_id="opslens/dev/ghsa/github-token",
    )

    assert provider.get_token() == "token-value"
    assert client.calls == 1


def test_cached_token_provider_refreshes_only_after_ttl() -> None:
    """Reuse a warm credential without calling Secrets Manager for every page."""
    times = iter([10.0, 11.0, 16.0])
    source = _StaticCredential("rotatable-token")
    provider = CachedGhsaTokenProvider(
        source=source,
        ttl_seconds=5.0,
        monotonic_fn=lambda: next(times),
    )

    assert provider.get_token() == "rotatable-token"
    assert provider.get_token() == "rotatable-token"
    assert provider.get_token() == "rotatable-token"
    assert source.calls == 2


def test_s3_repository_creates_versioned_page_with_immutable_metadata() -> None:
    """Persist one exact page conditionally and require its S3 VersionId."""
    page, _pagination = _page_and_pagination()
    client = _S3Client()
    client.put_responses.append({"VersionId": "page-version-1"})
    repository = S3GhsaBronzeRepository(
        client=client,
        bucket_name="opslens-bronze",
        telemetry=_Telemetry(),
    )
    window = _window()

    result = repository.create_page(
        page=page,
        window=window,
        object_key="bronze/ghsa/page.json",
    )

    assert result == GhsaBronzeWriteResult(
        key="bronze/ghsa/page.json",
        version_id="page-version-1",
    )
    assert client.last_if_none_match == "*"
    assert client.last_metadata is not None
    assert client.last_metadata["sync_id"] == window.sync_id
    assert client.last_metadata["object_sha256"] == page.sha256


def test_s3_repository_verifies_existing_object_after_precondition_failure() -> None:
    """Resolve a 412 only when exact immutable evidence already matches."""
    page, _pagination = _page_and_pagination()
    error = ClientError(
        {
            "Error": {"Code": "PreconditionFailed", "Message": "exists"},
            "ResponseMetadata": {
                "RequestId": "test-request-id",
                "HostId": "test-host-id",
                "HTTPStatusCode": 412,
                "HTTPHeaders": {},
                "RetryAttempts": 0,
            },
        },
        "PutObject",
    )
    client = _S3Client()
    client.put_responses.append(error)
    window = _window()
    client.head_response = {
        "VersionId": "existing-version",
        "ContentLength": page.size_bytes,
        "ContentType": "application/json",
        "Metadata": {
            "advisory_type": window.ADVISORY_TYPE,
            "api_version": window.API_VERSION,
            "artifact_kind": "page",
            "mode": window.mode.value,
            "object_sha256": page.sha256,
            "source": "github-ghsa",
            "source_interface": "global-security-advisories-rest",
            "sync_id": window.sync_id,
            "item_count": str(page.item_count),
        },
    }
    repository = S3GhsaBronzeRepository(
        client=client,
        bucket_name="opslens-bronze",
        telemetry=_Telemetry(),
    )

    result = repository.create_page(
        page=page,
        window=window,
        object_key="bronze/ghsa/page.json",
    )

    assert result.version_id == "existing-version"


def test_s3_repository_rejects_create_without_version_id() -> None:
    """Fail closed when the bucket does not return versioned persistence evidence."""
    page, _pagination = _page_and_pagination()
    client = _S3Client()
    client.put_responses.append({})
    repository = S3GhsaBronzeRepository(
        client=client,
        bucket_name="opslens-bronze",
        telemetry=_Telemetry(),
    )

    with pytest.raises(GhsaBronzeEvidenceError, match="VersionId"):
        repository.create_page(
            page=page,
            window=_window(),
            object_key="bronze/ghsa/page.json",
        )


def test_s3_repository_creates_versioned_complete_manifest() -> None:
    """Persist the canonical COMPLETE manifest after all page versions exist."""
    _page, pagination = _page_and_pagination()
    window = _window()
    attempt_factory = GhsaAttemptIdFactory()
    key_factory = GhsaBronzeKeyFactory()
    attempt_id = attempt_factory.build(window=window, pagination=pagination)
    page_key = key_factory.build_page_key(
        window=window,
        attempt_id=attempt_id,
        page_ordinal=1,
    )
    manifest = GhsaCompleteManifestFactory(
        attempt_factory=attempt_factory,
        key_factory=key_factory,
    ).build(
        window=window,
        pagination=pagination,
        page_writes=(
            GhsaBronzeWriteResult(
                key=page_key,
                version_id="page-version-1",
            ),
        ),
    )
    payload = GhsaCompleteManifestSerializer().serialize(manifest)
    manifest_key = key_factory.build_manifest_key(
        window=window,
        attempt_id=attempt_id,
    )
    client = _S3Client()
    client.put_responses.append({"VersionId": "manifest-version-1"})
    repository = S3GhsaBronzeRepository(
        client=client,
        bucket_name="opslens-bronze",
        telemetry=_Telemetry(),
    )

    result = repository.create_manifest(
        manifest=manifest,
        payload=payload,
        object_key=manifest_key,
    )

    assert result.key == manifest_key
    assert result.version_id == "manifest-version-1"
