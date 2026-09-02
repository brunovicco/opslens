"""Canonical reproducible evidence records for Phase 3 vulnerability correlation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import cast

from opslens.correlation.adapters.ghsa import GhsaPyPICorrelationDecision
from opslens.correlation.domain.aliases import CveAliasReconciliationEvidence
from opslens.correlation.domain.errors import InvalidCorrelationEvidenceRecordError
from opslens.correlation.domain.pypi_ranges import CorrelationResult

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SCHEMA_VERSION = "1"
_ENGINE = "opslens.phase3.pypi.v1"


@dataclass(frozen=True, slots=True)
class Phase3CorrelationEvidenceRecordV1:
    """One canonical, content-addressed Phase 3 correlation decision record."""

    canonical_json: bytes
    evidence_sha256: str
    result: CorrelationResult

    def __post_init__(self) -> None:
        """Validate hash, canonical encoding, schema, and result consistency."""
        if not self.canonical_json:
            raise InvalidCorrelationEvidenceRecordError(
                "Phase 3 correlation evidence JSON cannot be empty."
            )
        if _SHA256_PATTERN.fullmatch(self.evidence_sha256) is None:
            raise InvalidCorrelationEvidenceRecordError(
                "Phase 3 correlation evidence SHA-256 must be lowercase hexadecimal."
            )
        calculated_sha256 = hashlib.sha256(self.canonical_json).hexdigest()
        if calculated_sha256 != self.evidence_sha256:
            raise InvalidCorrelationEvidenceRecordError(
                "Phase 3 correlation evidence SHA-256 does not match canonical JSON."
            )

        try:
            parsed = cast(object, json.loads(self.canonical_json.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidCorrelationEvidenceRecordError(
                "Phase 3 correlation evidence must contain valid UTF-8 JSON."
            ) from exc

        if not isinstance(parsed, dict):
            raise InvalidCorrelationEvidenceRecordError(
                "Phase 3 correlation evidence must contain a JSON object."
            )
        payload = cast(dict[str, object], parsed)
        if _canonical_json(payload) != self.canonical_json:
            raise InvalidCorrelationEvidenceRecordError(
                "Phase 3 correlation evidence must use Canonical JSON v1."
            )
        if payload.get("schema_version") != _SCHEMA_VERSION:
            raise InvalidCorrelationEvidenceRecordError(
                "Phase 3 correlation evidence schema version is unsupported."
            )
        if payload.get("engine") != _ENGINE:
            raise InvalidCorrelationEvidenceRecordError(
                "Phase 3 correlation evidence engine identifier is invalid."
            )

        decision = payload.get("decision")
        if not isinstance(decision, dict):
            raise InvalidCorrelationEvidenceRecordError(
                "Phase 3 correlation evidence requires a decision object."
            )
        decision_object = cast(dict[str, object], decision)
        if decision_object.get("affected_status") != self.result.value:
            raise InvalidCorrelationEvidenceRecordError(
                "Phase 3 correlation record result does not match canonical decision evidence."
            )

    @property
    def correlation_record_id(self) -> str:
        """Return the stable content-addressed identity of this correlation record."""
        return f"correlation:v1@sha256:{self.evidence_sha256}"


def build_phase3_correlation_evidence_record(
    *,
    decision: GhsaPyPICorrelationDecision,
    alias: CveAliasReconciliationEvidence,
) -> Phase3CorrelationEvidenceRecordV1:
    """Assemble one canonical record from applicability and source-preserving alias evidence."""
    _validate_component_binding(decision=decision, alias=alias)

    source = decision.source
    applicability = decision.applicability

    identifier_payloads: list[object] = [
        {
            "type": identifier.identifier_type,
            "value": identifier.value,
        }
        for identifier in source.github_identifiers
    ]
    clause_payloads: list[object] = []
    first_patched_version_canonical: str | None = None

    if applicability is not None:
        clause_payloads = [
            {
                "operator": clause.operator.value,
                "bound_original": clause.bound_original,
                "bound_canonical": clause.bound_canonical,
                "matched": clause.matched,
            }
            for clause in applicability.parsed_clauses
        ]
        first_patched_version_canonical = applicability.first_patched_version_canonical

    ghsa_payload: dict[str, object] = {
        "ghsa_id": source.ghsa_id,
        "observed_advisory_version_id": source.observed_advisory_version_id,
        "source_advisory_sha256": source.source_advisory_sha256,
        "vulnerability_entry_id": source.vulnerability_entry_id,
        "source_index": source.source_index,
        "source_entry_sha256": source.source_entry_sha256,
        "github_cve_id": source.github_cve_id,
        "github_identifiers": identifier_payloads,
        "ecosystem_original": source.ecosystem_original,
        "package_name_original": source.package_name_original,
        "vulnerable_range_original": source.vulnerable_range_original,
        "first_patched_version_original": source.first_patched_version_original,
    }
    nvd_payload: dict[str, object] = {
        "link_state": alias.state.value,
        "reason_code": alias.reason_code,
        "cve_id": alias.nvd_cve_id,
        "observed_cve_version_id": alias.nvd_observed_cve_version_id,
        "source_cve_sha256": alias.nvd_source_cve_sha256,
        "source_identifier": alias.nvd_source_identifier,
        "vulnerability_status": alias.nvd_vulnerability_status,
    }
    installed_payload: dict[str, object] = {
        "ecosystem_original": decision.installed_ecosystem_original,
        "package_name_original": decision.installed_package_name_original,
        "package_name_canonical": decision.installed_package_name_canonical,
        "version_original": decision.installed_version_original,
        "version_canonical": decision.installed_version_canonical,
        "purl_original": decision.installed_purl_original,
        "purl_canonical": decision.installed_purl_canonical,
    }
    decision_payload: dict[str, object] = {
        "affected_status": decision.result.value,
        "reason_code": decision.reason_code,
        "package_identity_matched": decision.package_identity_matched,
        "source_package_name_canonical": decision.source_package_name_canonical,
        "vulnerable_range_original": source.vulnerable_range_original,
        "parsed_clauses": clause_payloads,
        "first_patched_version_original": source.first_patched_version_original,
        "first_patched_version_canonical": first_patched_version_canonical,
    }
    payload: dict[str, object] = {
        "schema_version": _SCHEMA_VERSION,
        "engine": _ENGINE,
        "installed": installed_payload,
        "source_evidence": {
            "ghsa": ghsa_payload,
            "nvd_alias": nvd_payload,
        },
        "decision": decision_payload,
    }

    canonical_json = _canonical_json(payload)
    evidence_sha256 = hashlib.sha256(canonical_json).hexdigest()
    return Phase3CorrelationEvidenceRecordV1(
        canonical_json=canonical_json,
        evidence_sha256=evidence_sha256,
        result=decision.result,
    )


def _validate_component_binding(
    *,
    decision: GhsaPyPICorrelationDecision,
    alias: CveAliasReconciliationEvidence,
) -> None:
    """Require applicability and alias evidence to refer to the same exact GHSA occurrence."""
    source = decision.source
    expected_pairs = (
        (alias.ghsa_id, source.ghsa_id, "GHSA id"),
        (
            alias.ghsa_observed_advisory_version_id,
            source.observed_advisory_version_id,
            "GHSA observed advisory version",
        ),
        (
            alias.ghsa_source_advisory_sha256,
            source.source_advisory_sha256,
            "GHSA source advisory hash",
        ),
        (
            alias.ghsa_vulnerability_entry_id,
            source.vulnerability_entry_id,
            "GHSA vulnerability entry",
        ),
        (alias.github_cve_id, source.github_cve_id, "GitHub CVE assertion"),
    )
    for alias_value, source_value, field_name in expected_pairs:
        if alias_value != source_value:
            raise InvalidCorrelationEvidenceRecordError(
                f"Correlation evidence components disagree on {field_name}."
            )

    applicability = decision.applicability
    if applicability is not None:
        if applicability.result is not decision.result:
            raise InvalidCorrelationEvidenceRecordError(
                "Applicability result does not match the correlation decision result."
            )
        if applicability.reason_code != decision.reason_code:
            raise InvalidCorrelationEvidenceRecordError(
                "Applicability reason does not match the correlation decision reason."
            )

    if decision.package_identity_matched is True and applicability is None:
        raise InvalidCorrelationEvidenceRecordError(
            "A matched package identity requires applicability evidence."
        )
    if decision.package_identity_matched is False and applicability is not None:
        raise InvalidCorrelationEvidenceRecordError(
            "A package identity mismatch cannot contain range applicability evidence."
        )


def _canonical_json(payload: dict[str, object]) -> bytes:
    """Encode the Phase 3 evidence payload with deterministic Canonical JSON v1."""
    try:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise InvalidCorrelationEvidenceRecordError(
            "Phase 3 correlation evidence contains a non-canonicalizable value."
        ) from exc
    return text.encode("utf-8")
