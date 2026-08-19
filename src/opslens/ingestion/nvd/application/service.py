"""Application service orchestrating NVD Bootstrap Bronze ingestion."""

from opslens.ingestion.nvd.application.key_factory import (
    NvdBootstrapKeyFactory,
)
from opslens.ingestion.nvd.application.manifest import (
    NvdBootstrapManifestFactory,
    NvdBootstrapManifestSerializer,
)
from opslens.ingestion.nvd.application.models import (
    NvdBootstrapIngestionResult,
)
from opslens.ingestion.nvd.application.ports import (
    NvdBootstrapBronzeRepository,
    NvdYearlyFeedSource,
)
from opslens.ingestion.nvd.domain.feed_integrity import (
    NvdFeedIntegrityVerifier,
)
from opslens.ingestion.nvd.domain.meta_parser import NvdFeedMetaParser
from opslens.ingestion.nvd.domain.source_identity import (
    NvdBootstrapSourceIdentity,
)


class IngestNvdBootstrapFeed:
    """Orchestrate deterministic ingestion of one NVD yearly feed."""

    def __init__(
        self,
        *,
        source: NvdYearlyFeedSource,
        repository: NvdBootstrapBronzeRepository,
        meta_parser: NvdFeedMetaParser,
        integrity_verifier: NvdFeedIntegrityVerifier,
        key_factory: NvdBootstrapKeyFactory,
        manifest_factory: NvdBootstrapManifestFactory,
        manifest_serializer: NvdBootstrapManifestSerializer,
    ) -> None:
        """Initialize the use case through explicit dependency injection."""
        self._source = source
        self._repository = repository
        self._meta_parser = meta_parser
        self._integrity_verifier = integrity_verifier
        self._key_factory = key_factory
        self._manifest_factory = manifest_factory
        self._manifest_serializer = manifest_serializer

    def execute(
        self,
        *,
        feed_year: int,
    ) -> NvdBootstrapIngestionResult:
        """Fetch, verify, persist, and complete one NVD yearly-feed revision.

        The completion manifest is always persisted last. Therefore its
        existence is evidence that both source artifacts were already
        persisted or verified and their exact S3 VersionIds were known.

        Args:
            feed_year: Four-digit NVD yearly-feed identifier.

        Returns:
            Verified persistence evidence for all three Bronze objects.
        """
        self._validate_feed_year(feed_year)

        meta_payload = self._source.fetch_meta(feed_year)
        meta = self._meta_parser.parse(meta_payload)

        gzip_payload = self._source.fetch_gzip(feed_year)

        artifact = self._integrity_verifier.verify(
            payload=gzip_payload,
            meta=meta,
        )

        identity = NvdBootstrapSourceIdentity(
            feed_year=feed_year,
            meta=meta,
        )

        keys = self._key_factory.build(identity)

        feed_write = self._repository.create_feed(
            artifact=artifact,
            identity=identity,
            object_key=keys.feed_key,
        )

        meta_write = self._repository.create_meta(
            identity=identity,
            object_key=keys.meta_key,
        )

        manifest = self._manifest_factory.build(
            artifact=artifact,
            identity=identity,
            keys=keys,
            feed_version_id=feed_write.version_id,
            meta_version_id=meta_write.version_id,
        )

        manifest_payload = self._manifest_serializer.serialize(manifest)

        manifest_write = self._repository.create_manifest(
            manifest=manifest,
            payload=manifest_payload,
            object_key=keys.manifest_key,
        )

        return NvdBootstrapIngestionResult(
            feed_year=identity.feed_year,
            feed_revision=identity.feed_revision,
            source_sha256=identity.meta.source_sha256,
            feed_key=keys.feed_key,
            meta_key=keys.meta_key,
            manifest_key=keys.manifest_key,
            feed_write=feed_write,
            meta_write=meta_write,
            manifest_write=manifest_write,
        )

    @staticmethod
    def _validate_feed_year(feed_year: int) -> None:
        """Reject invalid yearly-feed identifiers before network access."""
        if type(feed_year) is not int:
            raise ValueError("NVD feed year must be an integer.")

        if feed_year < 1000 or feed_year > 9999:
            raise ValueError("NVD feed year must contain exactly four digits.")
