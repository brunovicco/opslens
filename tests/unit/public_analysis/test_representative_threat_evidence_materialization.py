"""Tests for Gate 19.2 threat-authority materialization composition."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import cast

import pytest

from opslens.correlation.adapters.ghsa import GhsaPyPIVulnerabilityEvidence
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.application import (
    representative_threat_evidence_materialization as module,
)
from opslens.public_analysis.application.representative_repository_analysis import (
    RepresentativeRepositoryThreatEvidence,
)
from opslens.public_analysis.application.representative_threat_evidence_materialization import (
    RepresentativeThreatEvidenceAuthorityLoaders,
    materialize_representative_threat_evidence,
)
from opslens.transformation.nvd.domain.models import NvdCveCoreRecord


def _bundle_call_log() -> list[Mapping[str, object]]:
    """Return one explicitly typed mutable call log for strict Pyright."""
    return []


@dataclass(slots=True)
class FakeGhsaLoader:
    """Return one typed GHSA sentinel while recording exact bundle identity."""

    calls: list[Mapping[str, object]] = field(default_factory=_bundle_call_log)

    def load(
        self,
        bundle: Mapping[str, object],
    ) -> tuple[GhsaPyPIVulnerabilityEvidence, ...]:
        """Record one load and return a typed sentinel."""
        self.calls.append(bundle)
        return (cast(GhsaPyPIVulnerabilityEvidence, object()),)


@dataclass(slots=True)
class FakeNvdLoader:
    """Return one typed NVD sentinel while recording exact bundle identity."""

    calls: list[Mapping[str, object]] = field(default_factory=_bundle_call_log)

    def load(self, bundle: Mapping[str, object]) -> tuple[NvdCveCoreRecord, ...]:
        """Record one load and return a typed sentinel."""
        self.calls.append(bundle)
        return (cast(NvdCveCoreRecord, object()),)


@dataclass(slots=True)
class FakeKevLoader:
    """Return one typed KEV sentinel while recording exact bundle identity."""

    calls: list[Mapping[str, object]] = field(default_factory=_bundle_call_log)

    def load(self, bundle: Mapping[str, object]) -> KevCatalogSnapshot:
        """Record one load and return a typed sentinel."""
        self.calls.append(bundle)
        return cast(KevCatalogSnapshot, object())


@dataclass(slots=True)
class FakeEpssLoader:
    """Return one typed EPSS sentinel while recording exact bundle identity."""

    calls: list[Mapping[str, object]] = field(default_factory=_bundle_call_log)

    def load(self, bundle: Mapping[str, object]) -> EpssSnapshot:
        """Record one load and return a typed sentinel."""
        self.calls.append(bundle)
        return cast(EpssSnapshot, object())


@dataclass(slots=True)
class FailingNvdLoader:
    """Fail once to prove the coordinator does not retry or fall back."""

    calls: int = 0

    def load(self, bundle: Mapping[str, object]) -> tuple[NvdCveCoreRecord, ...]:
        """Raise the configured source failure on the first and only call."""
        del bundle
        self.calls += 1
        raise RuntimeError("nvd source unavailable")


def _bundle() -> Mapping[str, object]:
    """Return a minimal opaque bundle for composition-only tests."""
    return {
        "schema_version": 1,
        "bundle_type": "CrossSourceCveEvidenceV1",
        "read_only": True,
        "cve_id": "CVE-2026-54770",
    }


def test_materialization_loads_each_authority_once_then_admits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require one source read each and one final admission against the same bundle."""
    bundle = _bundle()
    ghsa = FakeGhsaLoader()
    nvd = FakeNvdLoader()
    kev = FakeKevLoader()
    epss = FakeEpssLoader()
    authority_sentinel = object()
    result_sentinel = cast(RepresentativeRepositoryThreatEvidence, object())
    constructed: list[dict[str, object]] = []
    admitted: list[tuple[Mapping[str, object], object]] = []

    def fake_authority(**kwargs: object) -> object:
        constructed.append(dict(kwargs))
        return authority_sentinel

    def fake_admit(
        observed_bundle: Mapping[str, object],
        *,
        authority: object,
    ) -> RepresentativeRepositoryThreatEvidence:
        admitted.append((observed_bundle, authority))
        return result_sentinel

    monkeypatch.setattr(module, "RepresentativeThreatEvidenceAuthority", fake_authority)
    monkeypatch.setattr(module, "admit_representative_threat_evidence", fake_admit)

    result = materialize_representative_threat_evidence(
        bundle,
        loaders=RepresentativeThreatEvidenceAuthorityLoaders(
            ghsa=ghsa,
            nvd=nvd,
            kev=kev,
            epss=epss,
        ),
    )

    assert result is result_sentinel
    assert ghsa.calls == [bundle]
    assert nvd.calls == [bundle]
    assert kev.calls == [bundle]
    assert epss.calls == [bundle]
    assert len(constructed) == 1
    assert admitted == [(bundle, authority_sentinel)]


def test_materialization_propagates_loader_failure_without_retry_or_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stop on source failure without retrying, admitting, or reading later sources."""
    bundle = _bundle()
    ghsa = FakeGhsaLoader()
    nvd = FailingNvdLoader()
    kev = FakeKevLoader()
    epss = FakeEpssLoader()
    admissions = 0

    def fake_admit(
        observed_bundle: Mapping[str, object],
        *,
        authority: object,
    ) -> RepresentativeRepositoryThreatEvidence:
        del observed_bundle, authority
        nonlocal admissions
        admissions += 1
        return cast(RepresentativeRepositoryThreatEvidence, object())

    monkeypatch.setattr(module, "admit_representative_threat_evidence", fake_admit)

    with pytest.raises(RuntimeError, match="nvd source unavailable"):
        materialize_representative_threat_evidence(
            bundle,
            loaders=RepresentativeThreatEvidenceAuthorityLoaders(
                ghsa=ghsa,
                nvd=nvd,
                kev=kev,
                epss=epss,
            ),
        )

    assert ghsa.calls == [bundle]
    assert nvd.calls == 1
    assert kev.calls == []
    assert epss.calls == []
    assert admissions == 0
