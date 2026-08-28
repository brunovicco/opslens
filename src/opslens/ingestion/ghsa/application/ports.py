"""Application ports for GHSA authenticated retrieval and Bronze persistence."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from opslens.ingestion.ghsa.application.manifest import GhsaCompleteManifest
from opslens.ingestion.ghsa.application.models import GhsaBronzeWriteResult
from opslens.ingestion.ghsa.domain.api_page import GhsaAdvisoryApiPage
from opslens.ingestion.ghsa.domain.sync import GhsaSyncWindow


@dataclass(frozen=True, slots=True)
class GhsaHttpResponse:
    """Represent one bounded HTTP response without exposing credentials."""

    status_code: int
    body: bytes
    headers: Mapping[str, str]

    def __post_init__(self) -> None:
        """Validate the minimum transport response contract."""
        if type(self.status_code) is not int or self.status_code < 100:
            raise ValueError("GHSA HTTP status_code must be a valid integer status.")


@dataclass(frozen=True, slots=True)
class GhsaFetchedPage:
    """Represent exact source bytes plus the source pagination Link header."""

    payload: bytes
    link_header: str | None

    def __post_init__(self) -> None:
        """Require one non-empty exact source response body."""
        if not self.payload:
            raise ValueError("GHSA fetched page payload cannot be empty.")


class GhsaCredentialProvider(Protocol):
    """Provide the GitHub token without exposing its storage implementation."""

    def get_token(self) -> str:
        """Return one non-empty GitHub API token."""
        ...


class GhsaHttpTransport(Protocol):
    """Execute one HTTPS GET against the already allowlisted GitHub URL."""

    def get(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> GhsaHttpResponse:
        """Return one bounded response without following redirects."""
        ...


class GhsaBronzeRepository(Protocol):
    """Persist exact GHSA pages and COMPLETE manifests."""

    def create_page(
        self,
        *,
        page: GhsaAdvisoryApiPage,
        window: GhsaSyncWindow,
        object_key: str,
    ) -> GhsaBronzeWriteResult:
        """Create or verify one immutable Bronze response page."""
        ...

    def create_manifest(
        self,
        *,
        manifest: GhsaCompleteManifest,
        payload: bytes,
        object_key: str,
    ) -> GhsaBronzeWriteResult:
        """Create or verify one immutable COMPLETE manifest."""
        ...
