"""Tests for Gate 19.2 pre-measurement threat-authority composition."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

import pytest

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application import (
    representative_pre_measurement_authority as module,
)
from opslens.public_analysis.application.representative_pre_measurement_authority import (
    RepresentativeThreatAuthorityReaders,
    materialize_pre_measurement_threat_evidence,
)
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.public_analysis.application.representative_threat_authority_locators import (
    RepresentativeThreatAuthorityLocatorError,
)
from opslens.public_analysis.application.representative_threat_evidence_coordinate_loaders import (
    BundleBoundRepresentativeEpssAuthorityLoader,
    BundleBoundRepresentativeGhsaAuthorityLoader,
    BundleBoundRepresentativeKevAuthorityLoader,
    BundleBoundRepresentativeNvdAuthorityLoader,
)
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord

_CVE_ID = "CVE-2026-54770"
_GHSA_OBSERVED_ID = "ghsa-observed-1"
_NVD_OBSERVED_ID = "nvd-observed-1"
_SNAPSHOT_DATE = "2026-09-10"


@dataclass(frozen=True, slots=True)
class NoCallGhsaReader:
    """Reject accidental GHSA reads in composition-only tests."""

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        cve_id: str,
        observed_advisory_version_id: str,
        source_index: int,
    ) -> GhsaPyPIVulnerabilityEvidence:
        """Fail because composition tests must not perform source reads."""
        del object_key, version_id, cve_id, observed_advisory_version_id, source_index
        raise AssertionError("unexpected GHSA read")


@dataclass(frozen=True, slots=True)
class NoCallNvdReader:
    """Reject accidental NVD reads in composition-only tests."""

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        cve_id: str,
        observed_cve_version_id: str,
    ) -> NvdCveCoreRecord:
        """Fail because composition tests must not perform source reads."""
        del object_key, version_id, cve_id, observed_cve_version_id
        raise AssertionError("unexpected NVD read")


@dataclass(frozen=True, slots=True)
class NoCallKevReader:
    """Reject accidental KEV reads in composition-only tests."""

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        snapshot_date: str,
    ) -> KevCatalogSnapshot:
        """Fail because composition tests must not perform source reads."""
        del object_key, version_id, snapshot_date
        raise AssertionError("unexpected KEV read")


@dataclass(frozen=True, slots=True)
class NoCallEpssReader:
    """Reject accidental EPSS reads in composition-only tests."""

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        snapshot_date: str,
    ) -> EpssSnapshot:
        """Fail because composition tests must not perform source reads."""
        del object_key, version_id, snapshot_date
        raise AssertionError("unexpected EPSS read")


def _bundle() -> Mapping[str, object]:
    """Build the minimal real coordinate surface required by the parser."""
    return {
        "schema_version": 1,
        "bundle_type": "CrossSourceCveEvidenceV1",
        "read_only": True,
        "cve_id": _CVE_ID,
        "ghsa": {
            "advisory_versions": [
                {
                    "cve_id": _CVE_ID,
                    "observed_advisory_version_id": _GHSA_OBSERVED_ID,
                    "package_evidence": [{"source_index": 0}],
                }
            ]
        },
        "nvd": {
            "observations": [
                {
                    "cve_id": _CVE_ID,
                    "observed_cve_version_id": _NVD_OBSERVED_ID,
                }
            ]
        },
        "kev": {"snapshot_date": _SNAPSHOT_DATE},
        "epss": {"snapshot_date": _SNAPSHOT_DATE},
    }


def _locator_manifest() -> Mapping[str, object]:
    """Build one exact physical locator manifest matching the test bundle."""
    return {
        "schema_version": 1,
        "manifest_type": "RepresentativeThreatAuthorityLocatorManifestV1",
        "cve_id": _CVE_ID,
        "ghsa": [
            {
                "observed_advisory_version_id": _GHSA_OBSERVED_ID,
                "source_index": 0,
                "s3": {"object_key": "ghsa.parquet", "version_id": "ghsa-v1"},
            }
        ],
        "nvd": [
            {
                "observed_cve_version_id": _NVD_OBSERVED_ID,
                "s3": {"object_key": "nvd.parquet", "version_id": "nvd-v1"},
            }
        ],
        "kev": {
            "snapshot_date": _SNAPSHOT_DATE,
            "s3": {"object_key": "kev.json", "version_id": "kev-v1"},
        },
        "epss": {
            "snapshot_date": _SNAPSHOT_DATE,
            "s3": {"object_key": "epss.csv.gz", "version_id": "epss-v1"},
        },
    }


def _readers() -> RepresentativeThreatAuthorityReaders:
    """Return readers that prove this layer performs only composition."""
    return RepresentativeThreatAuthorityReaders(
        ghsa=NoCallGhsaReader(),
        nvd=NoCallNvdReader(),
        kev=NoCallKevReader(),
        epss=NoCallEpssReader(),
    )


def test_composes_admitted_manifest_into_existing_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wire all exact readers only after real coordinate and locator admission."""
    bundle = _bundle()
    readers = _readers()
    result_sentinel = cast(RepresentativeRepositoryThreatEvidence, object())
    observed: list[object] = []

    def fake_materialize(
        observed_bundle: Mapping[str, object],
        *,
        loaders: object,
    ) -> RepresentativeRepositoryThreatEvidence:
        observed.extend((observed_bundle, loaders))
        typed = cast(module.RepresentativeThreatEvidenceAuthorityLoaders, loaders)
        assert isinstance(typed.ghsa, BundleBoundRepresentativeGhsaAuthorityLoader)
        assert isinstance(typed.nvd, BundleBoundRepresentativeNvdAuthorityLoader)
        assert isinstance(typed.kev, BundleBoundRepresentativeKevAuthorityLoader)
        assert isinstance(typed.epss, BundleBoundRepresentativeEpssAuthorityLoader)
        assert typed.ghsa.source.reader is readers.ghsa
        assert typed.nvd.source.reader is readers.nvd
        assert typed.kev.source.reader is readers.kev
        assert typed.epss.source.reader is readers.epss
        return result_sentinel

    monkeypatch.setattr(module, "materialize_representative_threat_evidence", fake_materialize)

    result = materialize_pre_measurement_threat_evidence(
        bundle,
        locator_manifest=_locator_manifest(),
        readers=readers,
    )

    assert result is result_sentinel
    assert observed[0] is bundle
    assert len(observed) == 2


def test_rejects_locator_drift_before_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed on locator drift before any source materialization can begin."""
    manifest = dict(_locator_manifest())
    manifest["cve_id"] = "CVE-2026-00001"
    calls = 0

    def fake_materialize(
        observed_bundle: Mapping[str, object],
        *,
        loaders: object,
    ) -> RepresentativeRepositoryThreatEvidence:
        del observed_bundle, loaders
        nonlocal calls
        calls += 1
        return cast(RepresentativeRepositoryThreatEvidence, object())

    monkeypatch.setattr(module, "materialize_representative_threat_evidence", fake_materialize)

    with pytest.raises(RepresentativeThreatAuthorityLocatorError, match="CVE identity mismatch"):
        materialize_pre_measurement_threat_evidence(
            _bundle(),
            locator_manifest=manifest,
            readers=_readers(),
        )

    assert calls == 0


def test_propagates_materialization_failure_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Propagate source/materialization failures without a retry or fallback path."""
    calls = 0

    def failing_materialize(
        observed_bundle: Mapping[str, object],
        *,
        loaders: object,
    ) -> RepresentativeRepositoryThreatEvidence:
        del observed_bundle, loaders
        nonlocal calls
        calls += 1
        raise RuntimeError("authority read failed")

    monkeypatch.setattr(module, "materialize_representative_threat_evidence", failing_materialize)

    with pytest.raises(RuntimeError, match="authority read failed"):
        materialize_pre_measurement_threat_evidence(
            _bundle(),
            locator_manifest=_locator_manifest(),
            readers=_readers(),
        )

    assert calls == 1
