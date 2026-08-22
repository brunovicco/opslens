"""Tests for the explicit NVD Silver Lambda invocation envelope."""

import pytest

from opslens.transformation.nvd.adapters.inbound.invocation import (
    InvalidNvdSilverInvocationError,
    NvdSilverInvocationParserV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)

UPDATE_ID = "a" * 64

INCREMENTAL_KEY = f"bronze/nvd/cve/updates/update_id={UPDATE_ID}/manifest.json"


def test_parses_exact_incremental_manifest_coordinate() -> None:
    """Parse one valid versioned incremental COMPLETE coordinate."""
    request = NvdSilverInvocationParserV1().parse(
        {
            "schema_version": "1",
            "source_kind": "incremental",
            "manifest_key": INCREMENTAL_KEY,
            "manifest_version_id": "manifest-version-1",
        }
    )

    assert request.source_kind is NvdSilverSourceKind.INCREMENTAL
    assert request.manifest_key == INCREMENTAL_KEY
    assert request.manifest_version_id == "manifest-version-1"


def test_parses_bootstrap_manifest_coordinate() -> None:
    """Parse one valid versioned bootstrap COMPLETE coordinate."""
    key = "bronze/nvd/cve/bootstrap/feed_year=2026/feed_revision=revision-1/manifest.json"

    request = NvdSilverInvocationParserV1().parse(
        {
            "schema_version": "1",
            "source_kind": "bootstrap",
            "manifest_key": key,
            "manifest_version_id": "manifest-version-2",
        }
    )

    assert request.source_kind is NvdSilverSourceKind.BOOTSTRAP
    assert request.manifest_key == key


def test_rejects_unknown_envelope_fields() -> None:
    """Keep explicit invocation schema closed to undeclared fields."""
    with pytest.raises(
        InvalidNvdSilverInvocationError,
        match="unsupported fields",
    ):
        NvdSilverInvocationParserV1().parse(
            {
                "schema_version": "1",
                "source_kind": "incremental",
                "manifest_key": INCREMENTAL_KEY,
                "manifest_version_id": "version-1",
                "unexpected": "value",
            }
        )


def test_rejects_source_kind_key_mismatch() -> None:
    """Prevent source-kind claims from addressing another Bronze namespace."""
    with pytest.raises(
        InvalidNvdSilverInvocationError,
        match="source_kind",
    ):
        NvdSilverInvocationParserV1().parse(
            {
                "schema_version": "1",
                "source_kind": "bootstrap",
                "manifest_key": INCREMENTAL_KEY,
                "manifest_version_id": "version-1",
            }
        )


def test_rejects_unsupported_schema_version() -> None:
    """Fail closed on future invocation schemas."""
    with pytest.raises(
        InvalidNvdSilverInvocationError,
        match="schema_version",
    ):
        NvdSilverInvocationParserV1().parse(
            {
                "schema_version": "2",
                "source_kind": "incremental",
                "manifest_key": INCREMENTAL_KEY,
                "manifest_version_id": "version-1",
            }
        )
