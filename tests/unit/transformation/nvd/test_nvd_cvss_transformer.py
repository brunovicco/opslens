"""Tests for deterministic NVD CVSS normalization."""

import pytest

from opslens.transformation.nvd.domain.cvss_transformer import (
    NvdCvssMetricsTransformer,
)
from opslens.transformation.nvd.domain.errors import (
    InvalidNvdCvssMetricsError,
)
from opslens.transformation.nvd.domain.models import (
    NvdCvssFamily,
    NvdCvssMetric,
    NvdCvssMetricType,
)


def _v31_metric(
    *,
    source: str = "nvd@nist.gov",
    metric_type: str = "Primary",
) -> dict[str, object]:
    """Return one representative CVSS v3.1 metric."""
    return {
        "source": source,
        "type": metric_type,
        "cvssData": {
            "version": "3.1",
            "vectorString": ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
            "baseScore": 9.8,
            "baseSeverity": "CRITICAL",
        },
        "exploitabilityScore": 3.9,
        "impactScore": 5.9,
    }


def test_absent_metrics_are_valid() -> None:
    """Represent absence of CVSS assessments as an empty collection."""
    result = NvdCvssMetricsTransformer().transform({})

    assert result.metrics == ()
    assert result.unsupported_cvss_families == ()


def test_multiple_v31_observations_are_preserved() -> None:
    """Preserve all source-qualified assessments without choosing a winner."""
    source: dict[str, object] = {
        "metrics": {
            "cvssMetricV31": [
                _v31_metric(
                    source="cna@example.com",
                    metric_type="Secondary",
                ),
                _v31_metric(
                    source="nvd@nist.gov",
                    metric_type="Primary",
                ),
            ]
        }
    }

    result = NvdCvssMetricsTransformer().transform(source)

    assert len(result.metrics) == 2
    assert result.metrics[0].source == "cna@example.com"
    assert result.metrics[0].metric_type is NvdCvssMetricType.SECONDARY
    assert result.metrics[1].source == "nvd@nist.gov"
    assert result.metrics[1].metric_type is NvdCvssMetricType.PRIMARY


def test_all_known_cvss_families_are_supported() -> None:
    """Normalize CVSS v2.0, v3.0, v3.1, and v4.0."""
    source: dict[str, object] = {
        "metrics": {
            "cvssMetricV2": [
                {
                    "source": "nvd@nist.gov",
                    "type": "Primary",
                    "cvssData": {
                        "version": "2.0",
                        "vectorString": "AV:N/AC:L/Au:N/C:C/I:C/A:C",
                        "baseScore": 10.0,
                    },
                    "baseSeverity": "HIGH",
                    "exploitabilityScore": 10.0,
                    "impactScore": 10.0,
                }
            ],
            "cvssMetricV30": [
                {
                    "source": "cna@example.com",
                    "type": "Secondary",
                    "cvssData": {
                        "version": "3.0",
                        "vectorString": ("CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
                        "baseScore": 9.8,
                        "baseSeverity": "CRITICAL",
                    },
                }
            ],
            "cvssMetricV31": [_v31_metric()],
            "cvssMetricV40": [
                {
                    "source": "cna@example.com",
                    "type": "Secondary",
                    "cvssData": {
                        "version": "4.0",
                        "vectorString": (
                            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"
                        ),
                        "baseScore": 9.3,
                        "baseSeverity": "CRITICAL",
                    },
                }
            ],
        }
    }

    result = NvdCvssMetricsTransformer().transform(source)

    assert tuple(metric.family for metric in result.metrics) == (
        NvdCvssFamily.V2,
        NvdCvssFamily.V30,
        NvdCvssFamily.V31,
        NvdCvssFamily.V40,
    )


def test_v2_base_severity_is_read_from_metric_wrapper() -> None:
    """Read the NVD CVSS v2 severity from the metric wrapper."""
    source: dict[str, object] = {
        "metrics": {
            "cvssMetricV2": [
                {
                    "source": "nvd@nist.gov",
                    "type": "Primary",
                    "cvssData": {
                        "version": "2.0",
                        "vectorString": "AV:N/AC:L/Au:N/C:C/I:C/A:C",
                        "baseScore": 10.0,
                    },
                    "baseSeverity": "HIGH",
                }
            ]
        }
    }

    result = NvdCvssMetricsTransformer().transform(source)

    assert result.metrics[0].base_severity == "HIGH"


def test_v4_does_not_require_v2_v3_subscores() -> None:
    """Allow CVSS v4 observations without exploitability or impact subscores."""
    source: dict[str, object] = {
        "metrics": {
            "cvssMetricV40": [
                {
                    "source": "cna@example.com",
                    "type": "Primary",
                    "cvssData": {
                        "version": "4.0",
                        "vectorString": (
                            "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"
                        ),
                        "baseScore": 9.3,
                        "baseSeverity": "CRITICAL",
                    },
                }
            ]
        }
    }

    metric = NvdCvssMetricsTransformer().transform(source).metrics[0]

    assert metric.exploitability_score is None
    assert metric.impact_score is None


def test_known_family_version_mismatch_fails_closed() -> None:
    """Reject a known metric family whose cvssData version disagrees."""
    metric = _v31_metric()
    cvss_data = metric["cvssData"]
    assert isinstance(cvss_data, dict)
    cvss_data["version"] = "2.0"

    with pytest.raises(
        InvalidNvdCvssMetricsError,
        match=r"expected '3\.1'",
    ):
        NvdCvssMetricsTransformer().transform({"metrics": {"cvssMetricV31": [metric]}})


def test_known_family_must_be_an_array() -> None:
    """Reject malformed known-family containers."""
    with pytest.raises(
        InvalidNvdCvssMetricsError,
        match="cvssMetricV31 must be an array",
    ):
        NvdCvssMetricsTransformer().transform({"metrics": {"cvssMetricV31": {}}})


def test_known_metric_requires_cvss_data() -> None:
    """Reject a known CVSS observation without cvssData."""
    with pytest.raises(
        InvalidNvdCvssMetricsError,
        match="cvssData must be an object",
    ):
        NvdCvssMetricsTransformer().transform(
            {
                "metrics": {
                    "cvssMetricV31": [
                        {
                            "source": "nvd@nist.gov",
                            "type": "Primary",
                        }
                    ]
                }
            }
        )


def test_boolean_score_fails_closed() -> None:
    """Reject bool even though bool is an int subclass in Python."""
    metric = _v31_metric()
    cvss_data = metric["cvssData"]
    assert isinstance(cvss_data, dict)
    cvss_data["baseScore"] = True

    with pytest.raises(
        InvalidNvdCvssMetricsError,
        match="baseScore must be numeric",
    ):
        NvdCvssMetricsTransformer().transform({"metrics": {"cvssMetricV31": [metric]}})


def test_out_of_range_score_fails_closed() -> None:
    """Reject a CVSS score outside the defined zero-to-ten range."""
    metric = _v31_metric()
    cvss_data = metric["cvssData"]
    assert isinstance(cvss_data, dict)
    cvss_data["baseScore"] = 10.1

    with pytest.raises(
        InvalidNvdCvssMetricsError,
        match=r"between 0\.0 and 10\.0",
    ):
        NvdCvssMetricsTransformer().transform({"metrics": {"cvssMetricV31": [metric]}})


def test_future_cvss_family_is_recorded_without_failure() -> None:
    """Record an unknown future CVSS family for completion warnings."""
    source: dict[str, object] = {
        "metrics": {
            "cvssMetricV50": [
                {
                    "future": "opaque-to-silver-v1",
                }
            ]
        }
    }

    result = NvdCvssMetricsTransformer().transform(source)

    assert result.metrics == ()
    assert result.unsupported_cvss_families == ("cvssMetricV50",)


def test_non_cvss_metric_family_is_not_reported_as_unknown_cvss() -> None:
    """Ignore SSVC and other non-CVSS metrics in the CVSS transformer."""
    source: dict[str, object] = {
        "metrics": {
            "ssvcV203": [
                {
                    "source": "example",
                }
            ]
        }
    }

    result = NvdCvssMetricsTransformer().transform(source)

    assert result.metrics == ()
    assert result.unsupported_cvss_families == ()


def test_metric_json_preserves_complete_canonical_metric() -> None:
    """Preserve the complete metric observation as canonical JSON."""
    metric = _v31_metric()

    result = NvdCvssMetricsTransformer().transform({"metrics": {"cvssMetricV31": [metric]}})

    metric_json = result.metrics[0].metric_json

    assert '"cvssData":' in metric_json
    assert '"exploitabilityScore":3.9' in metric_json
    assert '"impactScore":5.9' in metric_json
    assert " " not in metric_json


def test_cvss_domain_model_rejects_non_finite_score() -> None:
    """Reject non-finite scores even when constructing the domain model directly."""
    with pytest.raises(
        ValueError,
        match="baseScore must be finite",
    ):
        NvdCvssMetric(
            family=NvdCvssFamily.V31,
            version="3.1",
            source="nvd@nist.gov",
            metric_type=NvdCvssMetricType.PRIMARY,
            vector_string=("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
            base_score=float("nan"),
            base_severity="CRITICAL",
            exploitability_score=None,
            impact_score=None,
            metric_json="{}",
        )


def test_v2_base_severity_is_optional() -> None:
    """Accept a schema-valid CVSS v2 metric without baseSeverity."""
    source: dict[str, object] = {
        "metrics": {
            "cvssMetricV2": [
                {
                    "source": "nvd@nist.gov",
                    "type": "Primary",
                    "cvssData": {
                        "version": "2.0",
                        "vectorString": "AV:N/AC:L/Au:N/C:C/I:C/A:C",
                        "baseScore": 10.0,
                    },
                }
            ]
        }
    }

    metric = NvdCvssMetricsTransformer().transform(source).metrics[0]

    assert metric.base_severity is None


def test_empty_known_cvss_family_is_valid() -> None:
    """Accept a known CVSS family with no observations."""
    source: dict[str, object] = {
        "metrics": {
            "cvssMetricV31": [],
        }
    }

    result = NvdCvssMetricsTransformer().transform(source)

    assert result.metrics == ()
