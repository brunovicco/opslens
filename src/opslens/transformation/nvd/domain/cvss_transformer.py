"""Deterministic normalization of NVD CVSS metric observations."""

from dataclasses import dataclass
from typing import ClassVar, cast

from opslens.transformation.nvd.domain.canonicalization import (
    canonicalize_json_object,
)
from opslens.transformation.nvd.domain.errors import (
    InvalidNvdCvssMetricsError,
)
from opslens.transformation.nvd.domain.models import (
    NvdCvssFamily,
    NvdCvssMetric,
    NvdCvssMetrics,
    NvdCvssMetricType,
)


@dataclass(frozen=True, slots=True)
class _CvssFamilySpec:
    """Describe one known NVD CVSS metric family."""

    family: NvdCvssFamily
    version: str
    severity_in_cvss_data: bool


class NvdCvssMetricsTransformer:
    """Normalize all known CVSS observations from one NVD CVE."""

    _FAMILY_SPECS: ClassVar[dict[str, _CvssFamilySpec]] = {
        "cvssMetricV2": _CvssFamilySpec(
            family=NvdCvssFamily.V2,
            version="2.0",
            severity_in_cvss_data=False,
        ),
        "cvssMetricV30": _CvssFamilySpec(
            family=NvdCvssFamily.V30,
            version="3.0",
            severity_in_cvss_data=True,
        ),
        "cvssMetricV31": _CvssFamilySpec(
            family=NvdCvssFamily.V31,
            version="3.1",
            severity_in_cvss_data=True,
        ),
        "cvssMetricV40": _CvssFamilySpec(
            family=NvdCvssFamily.V40,
            version="4.0",
            severity_in_cvss_data=True,
        ),
    }

    def transform(
        self,
        source_cve: dict[str, object],
    ) -> NvdCvssMetrics:
        """Normalize known CVSS families and identify future families."""
        metrics_value = source_cve.get("metrics")

        if metrics_value is None:
            return NvdCvssMetrics(
                metrics=(),
                unsupported_cvss_families=(),
            )

        if not isinstance(metrics_value, dict):
            raise InvalidNvdCvssMetricsError("NVD CVE metrics must be an object when present.")

        source_metrics = cast(
            dict[str, object],
            metrics_value,
        )

        normalized: list[NvdCvssMetric] = []

        # Fixed family ordering makes the Silver representation deterministic.
        for source_key, spec in self._FAMILY_SPECS.items():
            if source_key not in source_metrics:
                continue

            family_metrics = self._required_non_empty_array(
                source_metrics[source_key],
                source_key=source_key,
            )

            for index, value in enumerate(family_metrics):
                normalized.append(
                    self._metric(
                        value,
                        source_key=source_key,
                        index=index,
                        spec=spec,
                    )
                )

        unsupported = tuple(
            sorted(
                key
                for key in source_metrics
                if key.startswith("cvssMetricV") and key not in self._FAMILY_SPECS
            )
        )

        return NvdCvssMetrics(
            metrics=tuple(normalized),
            unsupported_cvss_families=unsupported,
        )

    def _metric(
        self,
        value: object,
        *,
        source_key: str,
        index: int,
        spec: _CvssFamilySpec,
    ) -> NvdCvssMetric:
        """Normalize one known-family CVSS metric observation."""
        context = f"{source_key}[{index}]"
        metric = self._object(
            value,
            context=context,
        )

        cvss_data = self._object(
            metric.get("cvssData"),
            context=f"{context}.cvssData",
        )

        version = self._required_text(
            cvss_data,
            "version",
            context=f"{context}.cvssData",
        )

        if version != spec.version:
            raise InvalidNvdCvssMetricsError(
                f"NVD {context} declares CVSS version {version!r}; expected {spec.version!r}."
            )

        if spec.severity_in_cvss_data:
            base_severity = self._required_text(
                cvss_data,
                "baseSeverity",
                context=f"{context}.cvssData",
            )
        else:
            base_severity = self._required_text(
                metric,
                "baseSeverity",
                context=context,
            )

        metric_type_text = self._required_text(
            metric,
            "type",
            context=context,
        )

        try:
            metric_type = NvdCvssMetricType(metric_type_text)
        except ValueError as exc:
            raise InvalidNvdCvssMetricsError(
                f"NVD {context}.type has unsupported value {metric_type_text!r}."
            ) from exc

        try:
            return NvdCvssMetric(
                family=spec.family,
                version=version,
                source=self._required_text(
                    metric,
                    "source",
                    context=context,
                ),
                metric_type=metric_type,
                vector_string=self._required_text(
                    cvss_data,
                    "vectorString",
                    context=f"{context}.cvssData",
                ),
                base_score=self._required_score(
                    cvss_data,
                    "baseScore",
                    context=f"{context}.cvssData",
                ),
                base_severity=base_severity,
                exploitability_score=self._optional_score(
                    metric,
                    "exploitabilityScore",
                    context=context,
                ),
                impact_score=self._optional_score(
                    metric,
                    "impactScore",
                    context=context,
                ),
                metric_json=canonicalize_json_object(metric).decode("utf-8"),
            )
        except ValueError as exc:
            raise InvalidNvdCvssMetricsError(f"Invalid NVD CVSS metric {context}: {exc}") from exc

    @staticmethod
    def _object(
        value: object,
        *,
        context: str,
    ) -> dict[str, object]:
        """Require one JSON object."""
        if not isinstance(value, dict):
            raise InvalidNvdCvssMetricsError(f"NVD {context} must be an object.")

        return cast(dict[str, object], value)

    @staticmethod
    def _required_non_empty_array(
        value: object,
        *,
        source_key: str,
    ) -> list[object]:
        """Require a present CVSS family to contain observations."""
        if not isinstance(value, list):
            raise InvalidNvdCvssMetricsError(f"NVD metrics.{source_key} must be an array.")

        items = cast(list[object], value)

        if not items:
            raise InvalidNvdCvssMetricsError(f"NVD metrics.{source_key} cannot be empty.")

        return items

    @staticmethod
    def _required_text(
        record: dict[str, object],
        field_name: str,
        *,
        context: str,
    ) -> str:
        """Read one required non-empty string."""
        value = record.get(field_name)

        if not isinstance(value, str):
            raise InvalidNvdCvssMetricsError(f"NVD {context}.{field_name} must be a string.")

        if not value.strip():
            raise InvalidNvdCvssMetricsError(f"NVD {context}.{field_name} cannot be empty.")

        return value

    @classmethod
    def _required_score(
        cls,
        record: dict[str, object],
        field_name: str,
        *,
        context: str,
    ) -> float:
        """Read one required bounded numeric score."""
        if field_name not in record:
            raise InvalidNvdCvssMetricsError(f"NVD {context} is missing {field_name!r}.")

        return cls._score(
            record[field_name],
            field_name=field_name,
            context=context,
        )

    @classmethod
    def _optional_score(
        cls,
        record: dict[str, object],
        field_name: str,
        *,
        context: str,
    ) -> float | None:
        """Read one optional bounded numeric score."""
        if field_name not in record:
            return None

        return cls._score(
            record[field_name],
            field_name=field_name,
            context=context,
        )

    @staticmethod
    def _score(
        value: object,
        *,
        field_name: str,
        context: str,
    ) -> float:
        """Require a numeric CVSS score in the inclusive 0-10 range."""
        if type(value) is int:
            score = float(value)
        elif type(value) is float:
            score = value
        else:
            raise InvalidNvdCvssMetricsError(f"NVD {context}.{field_name} must be numeric.")

        if score < 0.0 or score > 10.0:
            raise InvalidNvdCvssMetricsError(
                f"NVD {context}.{field_name} must be between 0.0 and 10.0."
            )

        return score
