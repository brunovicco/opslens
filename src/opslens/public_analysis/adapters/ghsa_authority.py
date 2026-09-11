# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Decode one exact GHSA Silver v1 object into retained PyPI threat authority."""

from __future__ import annotations

import re
from typing import Protocol, cast

import pyarrow as pa
import pyarrow.parquet as pq

from opslens.correlation.adapters.ghsa import (
    GhsaPyPIVulnerabilityEvidence,
    GhsaSourceIdentifierEvidence,
)
from opslens.public_analysis.adapters.exact_s3_authority_object import (
    ExactS3AuthorityObject,
)
from opslens.transformation.ghsa.serialization.schema import (
    GHSA_ADVISORY_VERSIONS_SCHEMA_V1,
    GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class GhsaAuthorityDecodeError(ValueError):
    """Reject malformed or contradictory GHSA Silver source authority."""


class GhsaAuthorityObjectReader(Protocol):
    """Read one already-admitted exact physical authority object."""

    def read(self, *, object_key: str, version_id: str) -> ExactS3AuthorityObject:
        """Return exact bytes bound to the supplied immutable coordinates."""
        ...


class ExactGhsaSilverAuthorityReader:
    """Materialize one exact PyPI GHSA occurrence from immutable Silver v1 bytes."""

    def __init__(self, object_reader: GhsaAuthorityObjectReader) -> None:
        """Bind the exact-version object reader used for pre-measurement materialization."""
        self._object_reader = object_reader

    def read(
        self,
        *,
        object_key: str,
        version_id: str,
        cve_id: str,
        observed_advisory_version_id: str,
        source_index: int,
    ) -> GhsaPyPIVulnerabilityEvidence:
        """Read, validate, and project exactly one requested GHSA PyPI occurrence."""
        if not cve_id.strip():
            raise GhsaAuthorityDecodeError("GHSA cve_id cannot be empty")
        if not observed_advisory_version_id.strip():
            raise GhsaAuthorityDecodeError(
                "GHSA observed_advisory_version_id cannot be empty"
            )
        if type(source_index) is not int or source_index < 0:
            raise GhsaAuthorityDecodeError("GHSA source_index must be a non-negative integer")

        exact_object = self._object_reader.read(
            object_key=object_key,
            version_id=version_id,
        )
        row = self._decode_exact_row(
            exact_object.payload,
            observed_advisory_version_id=observed_advisory_version_id,
        )
        return self._project_occurrence(
            row,
            cve_id=cve_id,
            observed_advisory_version_id=observed_advisory_version_id,
            source_index=source_index,
        )

    @staticmethod
    def _decode_exact_row(
        payload: bytes,
        *,
        observed_advisory_version_id: str,
    ) -> dict[str, object]:
        try:
            table = pq.read_table(pa.BufferReader(payload))
        except Exception as exc:
            raise GhsaAuthorityDecodeError("GHSA authority object is not valid Parquet") from exc

        if table.schema != GHSA_ADVISORY_VERSIONS_SCHEMA_V1:
            raise GhsaAuthorityDecodeError("GHSA authority object schema is not Silver v1")

        rows = cast(list[object], table.to_pylist())
        matches = tuple(
            cast(dict[str, object], item)
            for item in rows
            if isinstance(item, dict)
            and item.get("observed_advisory_version_id") == observed_advisory_version_id
        )
        if len(matches) != 1:
            raise GhsaAuthorityDecodeError(
                "GHSA observed advisory version must resolve to exactly one Silver row"
            )
        return matches[0]

    @classmethod
    def _project_occurrence(
        cls,
        row: dict[str, object],
        *,
        cve_id: str,
        observed_advisory_version_id: str,
        source_index: int,
    ) -> GhsaPyPIVulnerabilityEvidence:
        schema_version = row.get("schema_version")
        if schema_version != GHSA_ADVISORY_VERSIONS_SCHEMA_VERSION:
            raise GhsaAuthorityDecodeError("GHSA Silver row schema_version mismatch")

        ghsa_id = cls._required_string(row, "ghsa_id")
        source_sha256 = cls._required_sha256(row, "source_advisory_sha256")
        if row.get("cve_id") != cve_id:
            raise GhsaAuthorityDecodeError("GHSA Silver row CVE identity mismatch")
        expected_observed_id = f"{ghsa_id}@sha256:{source_sha256}"
        if observed_advisory_version_id != expected_observed_id:
            raise GhsaAuthorityDecodeError(
                "GHSA Silver row observed advisory identity contradicts source hash"
            )

        identifiers = cls._identifiers(row.get("identifiers"))
        vulnerabilities = cls._object_list(row.get("vulnerabilities"), "vulnerabilities")
        count = row.get("vulnerability_entry_count")
        if type(count) is not int or count != len(vulnerabilities):
            raise GhsaAuthorityDecodeError(
                "GHSA vulnerability_entry_count does not match stored vulnerabilities"
            )

        matches = tuple(
            item for item in vulnerabilities if item.get("source_index") == source_index
        )
        if len(matches) != 1:
            raise GhsaAuthorityDecodeError(
                "GHSA source_index must resolve to exactly one vulnerability entry"
            )
        entry = matches[0]
        ecosystem = cls._required_string(entry, "ecosystem")
        if ecosystem != "pip":
            raise GhsaAuthorityDecodeError("GHSA representative authority requires pip ecosystem")

        first_patched = entry.get("first_patched_version")
        if first_patched is not None and (
            not isinstance(first_patched, str) or not first_patched.strip()
        ):
            raise GhsaAuthorityDecodeError(
                "GHSA first_patched_version must be non-empty when present"
            )

        return GhsaPyPIVulnerabilityEvidence(
            observed_advisory_version_id=observed_advisory_version_id,
            source_advisory_sha256=source_sha256,
            ghsa_id=ghsa_id,
            github_cve_id=cve_id,
            github_identifiers=identifiers,
            vulnerability_entry_id=cls._required_string(entry, "vulnerability_entry_id"),
            source_index=source_index,
            source_entry_sha256=cls._required_sha256(entry, "source_entry_sha256"),
            ecosystem_original=ecosystem,
            package_name_original=cls._required_string(entry, "package_name"),
            vulnerable_range_original=cls._required_string(
                entry, "vulnerable_version_range"
            ),
            first_patched_version_original=first_patched,
        )

    @classmethod
    def _identifiers(cls, value: object) -> tuple[GhsaSourceIdentifierEvidence, ...]:
        items = cls._object_list(value, "identifiers")
        return tuple(
            GhsaSourceIdentifierEvidence(
                identifier_type=cls._required_string(item, "type"),
                value=cls._required_string(item, "value"),
            )
            for item in items
        )

    @staticmethod
    def _object_list(value: object, name: str) -> tuple[dict[str, object], ...]:
        if not isinstance(value, list):
            raise GhsaAuthorityDecodeError(f"GHSA {name} must be a list")
        result: list[dict[str, object]] = []
        for item in value:
            if not isinstance(item, dict):
                raise GhsaAuthorityDecodeError(f"GHSA {name} entries must be objects")
            result.append(cast(dict[str, object], item))
        return tuple(result)

    @staticmethod
    def _required_string(mapping: dict[str, object], name: str) -> str:
        value = mapping.get(name)
        if not isinstance(value, str) or not value.strip():
            raise GhsaAuthorityDecodeError(f"GHSA {name} must be a non-empty string")
        return value

    @classmethod
    def _required_sha256(cls, mapping: dict[str, object], name: str) -> str:
        value = cls._required_string(mapping, name)
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise GhsaAuthorityDecodeError(f"GHSA {name} must be lowercase SHA-256")
        return value


__all__ = [
    "ExactGhsaSilverAuthorityReader",
    "GhsaAuthorityDecodeError",
    "GhsaAuthorityObjectReader",
]
