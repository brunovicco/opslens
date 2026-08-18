"""Unit tests for deterministic NVD Bootstrap Bronze keys."""

import pytest

from opslens.ingestion.nvd.application.key_factory import (
    NvdBootstrapKeyFactory,
)
from opslens.ingestion.nvd.domain.meta_parser import NvdFeedMetaParser
from opslens.ingestion.nvd.domain.source_identity import (
    NvdBootstrapSourceIdentity,
)

SOURCE_SHA256 = "10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f"


def _identity() -> NvdBootstrapSourceIdentity:
    """Build the real Phase 2.3A source identity."""
    meta_payload = (
        "lastModifiedDate:2026-08-18T03:00:12-04:00\n"
        "size:282112001\n"
        "zipSize:23938309\n"
        "gzSize:23938173\n"
        f"sha256:{SOURCE_SHA256}\n"
    ).encode()

    return NvdBootstrapSourceIdentity(
        feed_year=2026,
        meta=NvdFeedMetaParser().parse(meta_payload),
    )


def test_build_creates_expected_bootstrap_keys() -> None:
    """Build feed, META, and manifest keys under one immutable revision."""
    keys = NvdBootstrapKeyFactory().build(_identity())

    base = f"bronze/nvd/cve/bootstrap/feed_year=2026/feed_revision=20260818T070012Z-{SOURCE_SHA256}"

    assert keys.feed_key == (f"{base}/nvdcve-2.0-2026.json.gz")
    assert keys.meta_key == (f"{base}/nvdcve-2.0-2026.meta")
    assert keys.manifest_key == f"{base}/manifest.json"


def test_build_is_deterministic() -> None:
    """Return exactly the same keys for the same source identity."""
    factory = NvdBootstrapKeyFactory()
    identity = _identity()

    assert factory.build(identity) == factory.build(identity)


def test_build_places_all_objects_under_same_revision() -> None:
    """Keep feed, META, and manifest inside one source-revision prefix."""
    keys = NvdBootstrapKeyFactory().build(_identity())

    feed_parent = keys.feed_key.rsplit("/", 1)[0]
    meta_parent = keys.meta_key.rsplit("/", 1)[0]
    manifest_parent = keys.manifest_key.rsplit("/", 1)[0]

    assert feed_parent == meta_parent == manifest_parent


def test_build_supports_custom_prefix() -> None:
    """Normalize an explicitly configured Bronze prefix."""
    keys = NvdBootstrapKeyFactory(
        "/custom/nvd/bootstrap/",
    ).build(_identity())

    assert keys.feed_key.startswith("custom/nvd/bootstrap/feed_year=2026/")


@pytest.mark.parametrize(
    "prefix",
    [
        "",
        "/",
        "///",
    ],
)
def test_factory_rejects_empty_prefix(prefix: str) -> None:
    """Reject prefixes that become empty after normalization."""
    with pytest.raises(
        ValueError,
        match="prefix cannot be empty",
    ):
        NvdBootstrapKeyFactory(prefix)
