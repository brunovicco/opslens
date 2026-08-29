"""Composition root for GHSA Bronze Lambda runtime dependencies."""

from typing import Literal, Protocol, cast

from boto3.session import Session

from opslens.ingestion.ghsa.adapters.outbound.github_api import (
    GhsaAuthenticatedPageSource,
    HttpsGhsaTransport,
)
from opslens.ingestion.ghsa.adapters.outbound.s3_bronze import (
    S3GhsaBronzeClient,
    S3GhsaBronzeRepository,
)
from opslens.ingestion.ghsa.adapters.outbound.secrets_manager import (
    CachedGhsaTokenProvider,
    SecretsManagerClient,
    SecretsManagerGhsaTokenProvider,
)
from opslens.ingestion.ghsa.application.attempt import GhsaAttemptIdFactory
from opslens.ingestion.ghsa.application.key_factory import GhsaBronzeKeyFactory
from opslens.ingestion.ghsa.application.manifest import (
    GhsaCompleteManifestFactory,
    GhsaCompleteManifestSerializer,
)
from opslens.ingestion.ghsa.application.rate_limit import GhsaRetryDelayPolicy
from opslens.ingestion.ghsa.application.runtime import GhsaBronzeRuntimeService
from opslens.ingestion.ghsa.application.subdivision import GhsaWindowSubdivisionPlanner
from opslens.ingestion.ghsa.domain.api_page import GhsaAdvisoryApiPageParser
from opslens.ingestion.ghsa.runtime_config import GhsaBronzeRuntimeSettingsV1
from opslens.shared.observability.ports import OperationalTelemetry


class _AwsClientFactory(Protocol):
    """Define the AWS SDK client factory required by GHSA Bronze runtime."""

    def client(
        self,
        service_name: Literal["s3", "secretsmanager"],
    ) -> object:
        """Create one AWS service client."""
        ...


def build_ghsa_bronze_runtime(
    *,
    settings: GhsaBronzeRuntimeSettingsV1,
    telemetry: OperationalTelemetry,
    s3_client: S3GhsaBronzeClient,
    secrets_client: SecretsManagerClient,
) -> GhsaBronzeRuntimeService:
    """Compose the production-capable bounded GHSA Bronze runtime."""
    secret_source = SecretsManagerGhsaTokenProvider(
        client=secrets_client,
        secret_id=settings.github_token_secret_id,
    )
    credential_provider = CachedGhsaTokenProvider(
        source=secret_source,
        ttl_seconds=settings.secret_cache_ttl_seconds,
    )
    source = GhsaAuthenticatedPageSource(
        credential_provider=credential_provider,
        transport=HttpsGhsaTransport(),
        retry_delay_policy=GhsaRetryDelayPolicy(),
        telemetry=telemetry,
        timeout_seconds=settings.http_timeout_seconds,
        max_attempts=settings.http_max_attempts,
    )
    repository = S3GhsaBronzeRepository(
        client=s3_client,
        bucket_name=settings.bucket_name,
        telemetry=telemetry,
    )
    attempt_factory = GhsaAttemptIdFactory()
    key_factory = GhsaBronzeKeyFactory(
        prefix=settings.bronze_prefix,
    )

    return GhsaBronzeRuntimeService(
        source=source,
        repository=repository,
        parser=GhsaAdvisoryApiPageParser(),
        attempt_factory=attempt_factory,
        key_factory=key_factory,
        manifest_factory=GhsaCompleteManifestFactory(
            attempt_factory=attempt_factory,
            key_factory=key_factory,
        ),
        manifest_serializer=GhsaCompleteManifestSerializer(),
        subdivision_planner=GhsaWindowSubdivisionPlanner(),
        telemetry=telemetry,
        max_leaf_windows=settings.max_leaf_windows,
    )


def build_ghsa_bronze_runtime_from_environment(
    *,
    telemetry: OperationalTelemetry,
) -> GhsaBronzeRuntimeService:
    """Compose GHSA Bronze runtime from non-secret environment configuration."""
    settings = GhsaBronzeRuntimeSettingsV1.from_environment()
    client_factory = cast(_AwsClientFactory, Session())

    return build_ghsa_bronze_runtime(
        settings=settings,
        telemetry=telemetry,
        s3_client=cast(
            S3GhsaBronzeClient,
            client_factory.client("s3"),
        ),
        secrets_client=cast(
            SecretsManagerClient,
            client_factory.client("secretsmanager"),
        ),
    )
