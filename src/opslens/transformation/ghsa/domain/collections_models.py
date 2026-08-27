"""Structured GHSA advisory collection models for Silver evidence."""

import json
import math
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from opslens.transformation.ghsa.domain.canonicalization import (
    canonicalize_json_object,
)

_GHSA_PATTERN = re.compile(r"^GHSA(?:-[23456789cfghjmpqrvwx]{4}){3}$")
_CVE_PATTERN = re.compile(r"^CVE-[0-9]{4}-[0-9]{4,}$")
_CWE_PATTERN = re.compile(r"^CWE-[0-9]+$")


@dataclass(frozen=True, slots=True)
class GhsaAdvisoryIdentifier:
    """Preserve one identifier emitted by the GitHub advisory source."""

    identifier_type: str
    value: str

    def __post_init__(self) -> None:
        """Validate known identifier shapes while preserving unknown types."""
        if not self.identifier_type.strip():
            raise ValueError("GHSA identifier type cannot be empty.")

        if not self.value.strip():
            raise ValueError("GHSA identifier value cannot be empty.")

        if self.identifier_type == "GHSA" and _GHSA_PATTERN.fullmatch(self.value) is None:
            raise ValueError("GHSA identifier value must use canonical GHSA format.")

        if self.identifier_type == "CVE" and _CVE_PATTERN.fullmatch(self.value) is None:
            raise ValueError("GHSA CVE identifier value must use canonical CVE format.")


@dataclass(frozen=True, slots=True)
class GhsaCwe:
    """Preserve one GitHub-provided CWE observation."""

    cwe_id: str
    name: str

    def __post_init__(self) -> None:
        """Validate the structured CWE evidence."""
        if _CWE_PATTERN.fullmatch(self.cwe_id) is None:
            raise ValueError("GHSA cwe_id must use canonical CWE format.")

        if not self.name.strip():
            raise ValueError("GHSA CWE name cannot be empty.")


class GhsaCvssFamily(StrEnum):
    """Represent CVSS families exposed by the versioned GHSA REST contract."""

    V3 = "cvss_v3"
    V4 = "cvss_v4"


@dataclass(frozen=True, slots=True)
class GhsaCvssMetric:
    """Preserve one structured GitHub CVSS severity observation."""

    family: GhsaCvssFamily
    vector_string: str
    score: float

    def __post_init__(self) -> None:
        """Validate known CVSS family and score invariants."""
        if not self.vector_string.strip():
            raise ValueError("GHSA CVSS vector_string cannot be empty.")

        expected_prefix = {
            GhsaCvssFamily.V3: "CVSS:3.",
            GhsaCvssFamily.V4: "CVSS:4.0/",
        }[self.family]

        if not self.vector_string.startswith(expected_prefix):
            raise ValueError(
                f"GHSA {self.family.value} vector does not match the expected CVSS family."
            )

        if not math.isfinite(self.score):
            raise ValueError("GHSA CVSS score must be finite.")

        if self.score < 0.0 or self.score > 10.0:
            raise ValueError("GHSA CVSS score must be between 0.0 and 10.0.")


@dataclass(frozen=True, slots=True)
class GhsaCvssSeverities:
    """Preserve normalized known CVSS metrics plus exact source JSON."""

    metrics: tuple[GhsaCvssMetric, ...]
    canonical_json: str

    def __post_init__(self) -> None:
        """Validate canonical source preservation and family uniqueness."""
        try:
            parsed = cast(object, json.loads(self.canonical_json))
        except json.JSONDecodeError as exc:
            raise ValueError("GHSA cvss_severities canonical_json must be valid JSON.") from exc

        if not isinstance(parsed, dict):
            raise ValueError("GHSA cvss_severities canonical_json must contain an object.")

        source_object = cast(dict[str, object], parsed)
        expected = canonicalize_json_object(source_object).decode("utf-8")

        if expected != self.canonical_json:
            raise ValueError("GHSA cvss_severities must use Canonical JSON v1.")

        families = tuple(metric.family for metric in self.metrics)

        if len(families) != len(set(families)):
            raise ValueError("GHSA cvss_severities cannot contain duplicate known families.")


@dataclass(frozen=True, slots=True)
class GhsaAdvisoryCollections:
    """Represent normalized non-package structured evidence for one GHSA."""

    ghsa_id: str
    cve_id: str | None
    identifiers: tuple[GhsaAdvisoryIdentifier, ...]
    references: tuple[str, ...]
    cwes: tuple[GhsaCwe, ...]
    cvss_severities: GhsaCvssSeverities

    def __post_init__(self) -> None:
        """Validate collection-level consistency with primary identifiers."""
        if _GHSA_PATTERN.fullmatch(self.ghsa_id) is None:
            raise ValueError("GHSA collections ghsa_id must use canonical GHSA format.")

        if self.cve_id is not None and _CVE_PATTERN.fullmatch(self.cve_id) is None:
            raise ValueError("GHSA collections cve_id must use canonical CVE format.")

        ghsa_values = tuple(
            identifier.value
            for identifier in self.identifiers
            if identifier.identifier_type == "GHSA"
        )

        if self.ghsa_id not in ghsa_values:
            raise ValueError("GHSA identifiers must contain the primary ghsa_id.")

        if any(value != self.ghsa_id for value in ghsa_values):
            raise ValueError("GHSA identifiers cannot contain a different GHSA identifier.")

        if self.cve_id is not None:
            cve_values = tuple(
                identifier.value
                for identifier in self.identifiers
                if identifier.identifier_type == "CVE"
            )

            if self.cve_id not in cve_values:
                raise ValueError("GHSA identifiers must contain the primary cve_id when present.")

        for reference in self.references:
            if not reference.strip():
                raise ValueError("GHSA references cannot contain empty values.")
