"""Tests for immutable GHSA Silver persistence identity contracts."""

import pytest

from opslens.transformation.ghsa.completion.key_factory import (
    GhsaSilverKeyFactoryV1,
)
from opslens.transformation.ghsa.completion.models import (
    GhsaSilverStoredContentObjectV1,
)
from opslens.transformation.ghsa.domain.models import (
    ObservedGhsaAdvisoryVersion,
)
from opslens.transformation.ghsa.runtime.materializer import (
    GhsaSilverAttemptContextV1,
)

SYNC_ID = "1" * 64
ATTEMPT_ID = "2" * 64
PARQUET_SHA256 = "3" * 64


def _observed(
    *,
    summary: str = "Original content",
) -> ObservedGhsaAdvisoryVersion:
    """Build one deterministic advisory content version."""
    return ObservedGhsaAdvisoryVersion.from_source(
        {
            "ghsa_id": "GHSA-2345-6789-cfgh",
            "type": "reviewed",
            "summary": summary,
        }
    )


def _context(
    *,
    attempt_id: str = ATTEMPT_ID,
    manifest_version_id: str = "manifest-version",
) -> GhsaSilverAttemptContextV1:
    """Build one exact Bronze attempt context."""
    return GhsaSilverAttemptContextV1(
        sync_id=SYNC_ID,
        attempt_id=attempt_id,
        manifest_key="bronze/ghsa/advisories/manifest.json",
        manifest_version_id=manifest_version_id,
    )


def test_content_key_depends_only_on_advisory_content_identity() -> None:
    """Keep authoritative content storage independent from observations."""
    observed = _observed()
    factory = GhsaSilverKeyFactoryV1()

    key = factory.build_content_object_key(
        observed
    )

    assert key == (
        "silver/ghsa/advisory_versions/"
        "schema_version=1/"
        "ghsa_id=GHSA-2345-6789-cfgh/"
        f"source_advisory_sha256={observed.source_advisory_sha256}/"
        "record.parquet"
    )


def test_same_content_has_same_content_key_across_attempts() -> None:
    """Do not create another authoritative version for re-observation."""
    observed = _observed()
    factory = GhsaSilverKeyFactoryV1()

    first = factory.build_content_object_key(observed)
    second = factory.build_content_object_key(observed)

    assert first == second


def test_changed_content_has_different_content_key() -> None:
    """Create another content object when exact advisory content changes."""
    first = _observed(
        summary="Original content",
    )
    second = _observed(
        summary="Changed content",
    )

    factory = GhsaSilverKeyFactoryV1()

    assert (
        factory.build_content_object_key(first)
        != factory.build_content_object_key(second)
    )


def test_completion_key_is_bound_to_sync_and_attempt_identity() -> None:
    """Create one deterministic completion namespace per Bronze attempt."""
    context = _context()

    key = GhsaSilverKeyFactoryV1().build_completion_manifest_key(
        context
    )

    assert key == (
        "silver/ghsa/completions/"
        "schema_version=1/"
        f"sync_id={SYNC_ID}/"
        f"attempt_id={ATTEMPT_ID}/"
        "manifest.json"
    )


def test_completion_key_does_not_depend_on_s3_manifest_version() -> None:
    """Keep replay location stable while manifest content binds VersionId."""
    first = _context(
        manifest_version_id="version-a",
    )
    second = _context(
        manifest_version_id="version-b",
    )

    factory = GhsaSilverKeyFactoryV1()

    assert (
        factory.build_completion_manifest_key(first)
        == factory.build_completion_manifest_key(second)
    )


def test_stored_content_binds_exact_advisory_identity() -> None:
    """Bind persisted Parquet evidence to one advisory content version."""
    observed = _observed()

    stored = GhsaSilverStoredContentObjectV1(
        key=(
            GhsaSilverKeyFactoryV1()
            .build_content_object_key(observed)
        ),
        version_id="silver-version",
        observed_advisory_version_id=(
            observed.observed_advisory_version_id
        ),
        ghsa_id=observed.ghsa_id,
        source_advisory_sha256=(
            observed.source_advisory_sha256
        ),
        parquet_sha256=PARQUET_SHA256,
        size_bytes=1024,
        row_count=1,
    )

    assert stored.row_count == 1
    assert (
        stored.observed_advisory_version_id
        == observed.observed_advisory_version_id
    )


def test_rejects_stored_content_identity_mismatch() -> None:
    """Reject persisted evidence bound to another advisory content identity."""
    observed = _observed()

    with pytest.raises(
        ValueError,
        match="observed_advisory_version_id",
    ):
        GhsaSilverStoredContentObjectV1(
            key="record.parquet",
            version_id="silver-version",
            observed_advisory_version_id=(
                f"{observed.ghsa_id}@sha256:{'9' * 64}"
            ),
            ghsa_id=observed.ghsa_id,
            source_advisory_sha256=(
                observed.source_advisory_sha256
            ),
            parquet_sha256=PARQUET_SHA256,
            size_bytes=1024,
            row_count=1,
        )


@pytest.mark.parametrize(
    "row_count",
    [
        0,
        2,
    ],
)
def test_rejects_non_single_row_authoritative_content(
    row_count: int,
) -> None:
    """Enforce one physical Silver row per exact advisory content version."""
    observed = _observed()

    with pytest.raises(
        ValueError,
        match="exactly one row",
    ):
        GhsaSilverStoredContentObjectV1(
            key="record.parquet",
            version_id="silver-version",
            observed_advisory_version_id=(
                observed.observed_advisory_version_id
            ),
            ghsa_id=observed.ghsa_id,
            source_advisory_sha256=(
                observed.source_advisory_sha256
            ),
            parquet_sha256=PARQUET_SHA256,
            size_bytes=1024,
            row_count=row_count,
        )
