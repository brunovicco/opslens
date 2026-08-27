"""Deterministic normalization of GHSA identifiers, references, CWE, and CVSS."""

from typing import cast

from opslens.transformation.ghsa.domain.canonicalization import (
    canonicalize_json_object,
)
from opslens.transformation.ghsa.domain.collections_models import (
    GhsaAdvisoryCollections,
    GhsaAdvisoryIdentifier,
    GhsaCvssFamily,
    GhsaCvssMetric,
    GhsaCvssSeverities,
    GhsaCwe,
)
from opslens.transformation.ghsa.domain.errors import (
    InvalidGhsaAdvisoryCollectionsError,
)


class GhsaAdvisoryCollectionsTransformer:
    """Normalize structured non-package evidence from one reviewed GHSA."""

    REQUIRED_FIELDS = frozenset(
        {
            "ghsa_id",
            "cve_id",
            "identifiers",
            "references",
            "cwes",
            "cvss_severities",
        }
    )

    def transform(self, source_advisory: dict[str, object]) -> GhsaAdvisoryCollections:
        """Normalize GHSA advisory collections without interpreting package ranges."""
        missing_fields = self.REQUIRED_FIELDS - source_advisory.keys()

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise InvalidGhsaAdvisoryCollectionsError(
                f"GitHub advisory is missing required collection fields: {missing}."
            )

        try:
            result = GhsaAdvisoryCollections(
                ghsa_id=self._required_text(source_advisory, "ghsa_id"),
                cve_id=self._optional_text(source_advisory, "cve_id"),
                identifiers=self._identifiers(source_advisory),
                references=self._references(source_advisory),
                cwes=self._cwes(source_advisory),
                cvss_severities=self._cvss_severities(source_advisory),
            )
        except ValueError as exc:
            raise InvalidGhsaAdvisoryCollectionsError(
                f"Invalid GitHub advisory collections: {exc}"
            ) from exc

        return result

    def _identifiers(
        self,
        source_advisory: dict[str, object],
    ) -> tuple[GhsaAdvisoryIdentifier, ...]:
        """Preserve ordered advisory identifiers."""
        items = self._required_list(source_advisory, "identifiers")
        result: list[GhsaAdvisoryIdentifier] = []

        for index, item in enumerate(items):
            mapping = self._require_object(item, path=f"identifiers[{index}]")
            missing = {"type", "value"} - mapping.keys()

            if missing:
                raise InvalidGhsaAdvisoryCollectionsError(
                    f"GitHub advisory identifiers[{index}] is missing fields: "
                    f"{', '.join(sorted(missing))}."
                )

            result.append(
                GhsaAdvisoryIdentifier(
                    identifier_type=self._required_mapping_text(
                        mapping,
                        "type",
                        path=f"identifiers[{index}]",
                    ),
                    value=self._required_mapping_text(
                        mapping,
                        "value",
                        path=f"identifiers[{index}]",
                    ),
                )
            )

        return tuple(result)

    def _references(self, source_advisory: dict[str, object]) -> tuple[str, ...]:
        """Preserve ordered reference URLs without dereferencing them."""
        items = self._required_list(source_advisory, "references")
        result: list[str] = []

        for index, item in enumerate(items):
            if not isinstance(item, str) or not item.strip():
                raise InvalidGhsaAdvisoryCollectionsError(
                    f"GitHub advisory references[{index}] must be a non-empty string."
                )

            result.append(item)

        return tuple(result)

    def _cwes(self, source_advisory: dict[str, object]) -> tuple[GhsaCwe, ...]:
        """Preserve ordered CWE observations."""
        items = self._required_list(source_advisory, "cwes")
        result: list[GhsaCwe] = []

        for index, item in enumerate(items):
            mapping = self._require_object(item, path=f"cwes[{index}]")
            missing = {"cwe_id", "name"} - mapping.keys()

            if missing:
                raise InvalidGhsaAdvisoryCollectionsError(
                    f"GitHub advisory cwes[{index}] is missing fields: "
                    f"{', '.join(sorted(missing))}."
                )

            result.append(
                GhsaCwe(
                    cwe_id=self._required_mapping_text(
                        mapping,
                        "cwe_id",
                        path=f"cwes[{index}]",
                    ),
                    name=self._required_mapping_text(
                        mapping,
                        "name",
                        path=f"cwes[{index}]",
                    ),
                )
            )

        return tuple(result)

    def _cvss_severities(self, source_advisory: dict[str, object]) -> GhsaCvssSeverities:
        """Normalize known CVSS v3/v4 metrics and preserve exact source object."""
        value = source_advisory["cvss_severities"]
        mapping = self._require_object(value, path="cvss_severities")
        metrics: list[GhsaCvssMetric] = []

        for family in GhsaCvssFamily:
            if family.value not in mapping:
                continue

            metric_value = mapping[family.value]
            metric = self._require_object(
                metric_value,
                path=f"cvss_severities.{family.value}",
            )
            missing = {"vector_string", "score"} - metric.keys()

            if missing:
                raise InvalidGhsaAdvisoryCollectionsError(
                    f"GitHub advisory cvss_severities.{family.value} is missing fields: "
                    f"{', '.join(sorted(missing))}."
                )

            vector_string = self._required_mapping_text(
                metric,
                "vector_string",
                path=f"cvss_severities.{family.value}",
            )
            score_value = metric["score"]

            if isinstance(score_value, bool) or not isinstance(score_value, (int, float)):
                raise InvalidGhsaAdvisoryCollectionsError(
                    f"GitHub advisory cvss_severities.{family.value}.score "
                    "must be numeric."
                )

            metrics.append(
                GhsaCvssMetric(
                    family=family,
                    vector_string=vector_string,
                    score=float(score_value),
                )
            )

        canonical_json = canonicalize_json_object(mapping).decode("utf-8")

        return GhsaCvssSeverities(
            metrics=tuple(metrics),
            canonical_json=canonical_json,
        )

    @staticmethod
    def _required_text(source_advisory: dict[str, object], field_name: str) -> str:
        """Read one required non-empty top-level string."""
        value = source_advisory[field_name]

        if not isinstance(value, str) or not value.strip():
            raise InvalidGhsaAdvisoryCollectionsError(
                f"GitHub advisory field {field_name!r} must be a non-empty string."
            )

        return value

    @staticmethod
    def _optional_text(
        source_advisory: dict[str, object],
        field_name: str,
    ) -> str | None:
        """Read one nullable top-level string."""
        value = source_advisory[field_name]

        if value is None:
            return None

        if not isinstance(value, str) or not value.strip():
            raise InvalidGhsaAdvisoryCollectionsError(
                f"GitHub advisory field {field_name!r} must be a non-empty string or null."
            )

        return value

    @staticmethod
    def _required_list(
        source_advisory: dict[str, object],
        field_name: str,
    ) -> list[object]:
        """Read one required source array."""
        value = source_advisory[field_name]

        if not isinstance(value, list):
            raise InvalidGhsaAdvisoryCollectionsError(
                f"GitHub advisory field {field_name!r} must be an array."
            )

        return cast(list[object], value)

    @staticmethod
    def _require_object(value: object, *, path: str) -> dict[str, object]:
        """Require one JSON object at the given source path."""
        if not isinstance(value, dict):
            raise InvalidGhsaAdvisoryCollectionsError(
                f"GitHub advisory {path} must be an object."
            )

        return cast(dict[str, object], value)

    @staticmethod
    def _required_mapping_text(
        mapping: dict[str, object],
        field_name: str,
        *,
        path: str,
    ) -> str:
        """Read one required non-empty string from a nested source object."""
        value = mapping[field_name]

        if not isinstance(value, str) or not value.strip():
            raise InvalidGhsaAdvisoryCollectionsError(
                f"GitHub advisory {path}.{field_name} must be a non-empty string."
            )

        return value
