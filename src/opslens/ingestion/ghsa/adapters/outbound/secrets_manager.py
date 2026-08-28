"""AWS Secrets Manager credential adapter for GitHub advisory retrieval."""

import time
from collections.abc import Callable, Mapping
from typing import Protocol

from opslens.ingestion.ghsa.application.ports import GhsaCredentialProvider


class GhsaCredentialUnavailableError(RuntimeError):
    """Raised when the configured GitHub token cannot be loaded safely."""


class SecretsManagerClient(Protocol):
    """Define the minimum Secrets Manager operation required by GHSA ingestion."""

    def get_secret_value(
        self,
        *,
        SecretId: str,
        VersionStage: str,
    ) -> Mapping[str, object]:
        """Read one current secret version."""
        ...


class SecretsManagerGhsaTokenProvider:
    """Load the GitHub token from one dedicated Secrets Manager secret."""

    def __init__(
        self,
        *,
        client: SecretsManagerClient,
        secret_id: str,
    ) -> None:
        """Initialize one least-scope token provider."""
        normalized_secret_id = secret_id.strip()

        if not normalized_secret_id:
            raise ValueError("GHSA GitHub token secret_id cannot be empty.")

        self._client = client
        self._secret_id = normalized_secret_id

    def get_token(self) -> str:
        """Return the current raw token string without logging secret material."""
        response = self._client.get_secret_value(
            SecretId=self._secret_id,
            VersionStage="AWSCURRENT",
        )
        value = response.get("SecretString")

        if not isinstance(value, str) or not value.strip():
            raise GhsaCredentialUnavailableError(
                "GHSA GitHub token secret must contain a non-empty SecretString."
            )

        return value.strip()


class CachedGhsaTokenProvider:
    """Cache a credential provider result in memory for a bounded TTL."""

    def __init__(
        self,
        *,
        source: GhsaCredentialProvider,
        ttl_seconds: float = 300.0,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize bounded credential caching."""
        if ttl_seconds <= 0:
            raise ValueError("GHSA credential cache TTL must be positive.")

        self._source = source
        self._ttl_seconds = ttl_seconds
        self._monotonic = monotonic_fn
        self._cached_token: str | None = None
        self._expires_at = 0.0

    def get_token(self) -> str:
        """Return the cached token or refresh it after the TTL expires."""
        now = self._monotonic()

        if self._cached_token is not None and now < self._expires_at:
            return self._cached_token

        token = self._source.get_token().strip()

        if not token:
            raise GhsaCredentialUnavailableError(
                "GHSA credential provider returned an empty token."
            )

        self._cached_token = token
        self._expires_at = now + self._ttl_seconds

        return token
