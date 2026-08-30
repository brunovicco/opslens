#!/usr/bin/env python3
"""Build the Phase 2.4F deterministic cross-source CVE evidence bundle."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config

_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Build a read-only CVE-centered evidence bundle from NVD, KEV, EPSS, "
            "and GHSA using explicit Phase 2.4F proof coordinates."
        )
    )
    parser.add_argument(
        "--coordinates",
        default="/tmp/opslens-cross-source-coordinates.json",
        help="Path to the 2.4F-2 coordinate discovery JSON.",
    )
    parser.add_argument(
        "--selection",
        default="/tmp/opslens-cross-source-selected-cve.json",
        help="Path to the 2.4F-3 deterministic CVE selection JSON.",
    )
    parser.add_argument(
        "--profile",
        default="opslens-bootstrap",
        help="AWS profile used for read-only Athena execution.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="Maximum wait time for each Athena query.",
    )
    return parser.parse_args()


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    """Load one JSON proof input."""
    if not path.is_file():
        raise FileNotFoundError(f"{label} file does not exist: {path}")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return value


def _require_identifier(value: str, *, field: str) -> str:
    """Validate a database/workgroup identifier."""
    if not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"Invalid {field}: {value!r}")
    return value


def _require_date(value: str, *, field: str) -> str:
    """Validate one explicit YYYY-MM-DD coordinate."""
    if not _DATE_RE.fullmatch(value):
        raise ValueError(f"Invalid {field}: {value!r}")
    return value


def _require_cve(value: str) -> str:
    """Validate the canonical CVE proof key."""
    if not _CVE_RE.fullmatch(value):
        raise ValueError(f"Invalid CVE identifier: {value!r}")
    return value


def _sql_string(value: str) -> str:
    """Render a validated scalar as an Athena SQL string literal."""
    return "'" + value.replace("'", "''") + "'"


def _date_list(values: list[str], *, field: str) -> str:
    """Render a non-empty explicit date list for partition predicates."""
    if not values:
        raise ValueError(f"{field} must not be empty.")
    validated = [_require_date(value, field=field) for value in values]
    return ", ".join(_sql_string(value) for value in validated)


def _result_rows(result_set: dict[str, Any]) -> list[dict[str, str]]:
    """Convert a small Athena result set into dictionaries."""
    rows = result_set.get("Rows", [])
    if not rows:
        return []

    def values(row: dict[str, Any]) -> list[str]:
        return [item.get("VarCharValue", "") for item in row.get("Data", [])]

    header = values(rows[0])
    return [dict(zip(header, values(row), strict=False)) for row in rows[1:]]


def _nullable(value: str | None) -> str | None:
    """Normalize Athena empty values to None."""
    if value is None or value == "":
        return None
    return value


def _optional_float(value: str | None) -> float | None:
    """Parse an optional Athena floating-point value."""
    normalized = _nullable(value)
    return None if normalized is None else float(normalized)


def _optional_bool(value: str | None) -> bool | None:
    """Parse an optional Athena boolean value."""
    normalized = _nullable(value)
    if normalized is None:
        return None
    lowered = normalized.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _json_or_empty_list(value: str | None) -> list[Any]:
    """Parse a JSON array emitted by Athena."""
    normalized = _nullable(value)
    if normalized is None:
        return []
    parsed = json.loads(normalized)
    if not isinstance(parsed, list):
        raise ValueError("Expected a JSON array from Athena.")
    return parsed


def _run_query(
    athena: Any,
    *,
    sql: str,
    database: str,
    workgroup: str,
    cutoff_bytes: int,
    timeout_seconds: int,
    label: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Execute one bounded read-only Athena query and retain cost evidence."""
    response = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": database, "Catalog": "AwsDataCatalog"},
        WorkGroup=workgroup,
    )
    query_id = response["QueryExecutionId"]
    deadline = time.monotonic() + timeout_seconds

    execution: dict[str, Any]
    while True:
        execution = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
        state = execution["Status"]["State"]
        if state == "SUCCEEDED":
            break
        if state in {"FAILED", "CANCELLED"}:
            reason = execution["Status"].get("StateChangeReason", "")
            raise RuntimeError(f"Athena {label} query {state}: {reason}")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Timed out waiting for Athena {label} query {query_id}.")
        time.sleep(1)

    result = athena.get_query_results(QueryExecutionId=query_id)["ResultSet"]
    rows = _result_rows(result)
    statistics = execution.get("Statistics", {})
    scanned = int(statistics.get("DataScannedInBytes", 0))
    if scanned > cutoff_bytes:
        raise RuntimeError(
            f"Athena {label} query scanned {scanned} bytes, above cutoff {cutoff_bytes}."
        )

    evidence = {
        "query_execution_id": query_id,
        "state": execution["Status"]["State"],
        "engine_version": execution.get("EngineVersion", {}).get("EffectiveEngineVersion"),
        "data_scanned_in_bytes": scanned,
        "engine_execution_time_in_millis": statistics.get("EngineExecutionTimeInMillis"),
        "query_planning_time_in_millis": statistics.get("QueryPlanningTimeInMillis"),
        "total_execution_time_in_millis": statistics.get("TotalExecutionTimeInMillis"),
    }
    return rows, evidence


def _build_nvd_sql(
    *,
    cve: str,
    bootstrap_dates: list[str],
    incremental_dates: list[str],
) -> str:
    """Build the NVD source-local evidence query."""
    bootstrap_sql = _date_list(bootstrap_dates, field="NVD bootstrap projection_date")
    incremental_sql = _date_list(
        incremental_dates,
        field="NVD incremental projection_date",
    )
    return f"""
SELECT
    n.cve_id,
    n.source_kind_partition,
    n.projection_date,
    n.observed_cve_version_id,
    n.observation_id,
    n.source_kind,
    n.source_batch_id,
    CAST(n.source_observed_at AS VARCHAR) AS source_observed_at,
    CAST(n.published_at AS VARCHAR) AS published_at,
    CAST(n.last_modified_at AS VARCHAR) AS last_modified_at,
    n.vuln_status,
    n.is_rejected,
    json_format(CAST(n.cwe_ids AS JSON)) AS cwe_ids_json,
    metric.family AS cvss_family,
    metric.version AS cvss_version,
    metric.source AS cvss_source,
    metric.vector_string AS cvss_vector_string,
    metric.base_score AS cvss_base_score,
    metric.base_severity AS cvss_base_severity,
    metric.exploitability_score AS cvss_exploitability_score,
    metric.impact_score AS cvss_impact_score,
    metric.metric_json AS cvss_metric_json
FROM nvd_cve_versions n
LEFT JOIN UNNEST(n.cvss_metrics) AS t(metric) ON TRUE
WHERE n.cve_id = {_sql_string(cve)}
  AND (
        (
            n.source_kind_partition = 'bootstrap'
            AND n.projection_date IN ({bootstrap_sql})
        )
        OR
        (
            n.source_kind_partition = 'incremental'
            AND n.projection_date IN ({incremental_sql})
        )
      )
ORDER BY
    n.source_kind_partition,
    n.projection_date,
    n.observation_id,
    metric.family,
    metric.version,
    metric.source,
    metric.vector_string
""".strip()


def _build_kev_sql(*, cve: str, snapshot_date: str) -> str:
    """Build the KEV source-local evidence query."""
    return f"""
SELECT
    cve,
    vendor_project,
    product,
    vulnerability_name,
    CAST(date_added AS VARCHAR) AS date_added,
    short_description,
    required_action,
    CAST(due_date AS VARCHAR) AS due_date,
    known_ransomware_campaign_use,
    catalog_version,
    CAST(catalog_date_released AS VARCHAR) AS catalog_date_released,
    source,
    source_sha256,
    CAST(retrieved_at AS VARCHAR) AS retrieved_at
FROM kev_entries
WHERE snapshot_date = {_sql_string(snapshot_date)}
  AND cve = {_sql_string(cve)}
ORDER BY cve
""".strip()


def _build_epss_sql(*, cve: str, snapshot_date: str) -> str:
    """Build the EPSS source-local evidence query."""
    return f"""
SELECT
    cve,
    epss,
    percentile,
    model_version,
    CAST(score_timestamp AS VARCHAR) AS score_timestamp,
    source,
    source_sha256
FROM epss_scores
WHERE snapshot_date = {_sql_string(snapshot_date)}
  AND cve = {_sql_string(cve)}
ORDER BY cve
""".strip()


def _build_ghsa_advisory_sql(*, cve: str) -> str:
    """Build the GHSA advisory-version evidence query."""
    return f"""
SELECT
    ghsa_id,
    observed_advisory_version_id,
    source_advisory_sha256,
    cve_id,
    advisory_type,
    severity,
    url,
    html_url,
    repository_advisory_url,
    source_code_location,
    summary,
    CAST(published_at AS VARCHAR) AS published_at,
    CAST(updated_at AS VARCHAR) AS updated_at,
    CAST(github_reviewed_at AS VARCHAR) AS github_reviewed_at,
    CAST(nvd_published_at AS VARCHAR) AS nvd_published_at,
    CAST(withdrawn_at AS VARCHAR) AS withdrawn_at,
    is_withdrawn,
    cvss_severities_json,
    vulnerability_entry_count
FROM ghsa_advisory_versions
WHERE cve_id = {_sql_string(cve)}
ORDER BY ghsa_id, observed_advisory_version_id
""".strip()


def _build_ghsa_package_sql(*, cve: str) -> str:
    """Build the GHSA package/range evidence query without evaluating ranges."""
    return f"""
SELECT
    g.ghsa_id,
    g.observed_advisory_version_id,
    vulnerability.source_index,
    vulnerability.vulnerability_entry_id,
    vulnerability.source_entry_sha256,
    vulnerability.ecosystem,
    vulnerability.package_name,
    vulnerability.vulnerable_version_range,
    vulnerability.first_patched_version,
    json_format(CAST(vulnerability.vulnerable_functions AS JSON))
        AS vulnerable_functions_json
FROM ghsa_advisory_versions g
CROSS JOIN UNNEST(g.vulnerabilities) AS t(vulnerability)
WHERE g.cve_id = {_sql_string(cve)}
ORDER BY
    g.ghsa_id,
    g.observed_advisory_version_id,
    vulnerability.source_index,
    vulnerability.vulnerability_entry_id
""".strip()


def _normalize_nvd(rows: list[dict[str, str]], *, cve: str) -> list[dict[str, Any]]:
    """Group flattened NVD CVSS rows back under exact observation identities."""
    observations: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("cve_id") != cve:
            raise RuntimeError("NVD returned a row for a different CVE.")
        observation_id = row["observation_id"]
        existing = observations.get(observation_id)
        if existing is None:
            existing = {
                "cve_id": row["cve_id"],
                "source_kind_partition": row["source_kind_partition"],
                "projection_date": row["projection_date"],
                "observed_cve_version_id": row["observed_cve_version_id"],
                "observation_id": observation_id,
                "source_kind": row["source_kind"],
                "source_batch_id": row["source_batch_id"],
                "source_observed_at": _nullable(row.get("source_observed_at")),
                "published_at": _nullable(row.get("published_at")),
                "last_modified_at": _nullable(row.get("last_modified_at")),
                "vuln_status": _nullable(row.get("vuln_status")),
                "is_rejected": _optional_bool(row.get("is_rejected")),
                "cwe_ids": _json_or_empty_list(row.get("cwe_ids_json")),
                "cvss_metrics": [],
            }
            observations[observation_id] = existing

        family = _nullable(row.get("cvss_family"))
        if family is not None:
            existing["cvss_metrics"].append(
                {
                    "family": family,
                    "version": _nullable(row.get("cvss_version")),
                    "source": _nullable(row.get("cvss_source")),
                    "vector_string": _nullable(row.get("cvss_vector_string")),
                    "base_score": _optional_float(row.get("cvss_base_score")),
                    "base_severity": _nullable(row.get("cvss_base_severity")),
                    "exploitability_score": _optional_float(
                        row.get("cvss_exploitability_score")
                    ),
                    "impact_score": _optional_float(row.get("cvss_impact_score")),
                    "metric_json": _nullable(row.get("cvss_metric_json")),
                }
            )

    normalized = list(observations.values())
    for observation in normalized:
        observation["cvss_metrics"].sort(
            key=lambda metric: (
                metric["family"],
                metric["version"] or "",
                metric["source"] or "",
                metric["vector_string"] or "",
            )
        )
    normalized.sort(
        key=lambda observation: (
            observation["source_kind_partition"],
            observation["projection_date"],
            observation["observation_id"],
        )
    )
    return normalized


def _normalize_kev(rows: list[dict[str, str]], *, cve: str) -> dict[str, Any] | None:
    """Validate KEV cardinality and normalize one optional snapshot row."""
    if len(rows) > 1:
        raise RuntimeError(f"KEV returned {len(rows)} rows for one CVE/snapshot.")
    if not rows:
        return None
    row = rows[0]
    if row.get("cve") != cve:
        raise RuntimeError("KEV returned a row for a different CVE.")
    return {key: _nullable(value) for key, value in row.items()}


def _normalize_epss(rows: list[dict[str, str]], *, cve: str) -> dict[str, Any] | None:
    """Validate EPSS cardinality and normalize one optional snapshot row."""
    if len(rows) > 1:
        raise RuntimeError(f"EPSS returned {len(rows)} rows for one CVE/snapshot.")
    if not rows:
        return None
    row = rows[0]
    if row.get("cve") != cve:
        raise RuntimeError("EPSS returned a row for a different CVE.")
    return {
        "cve": row["cve"],
        "epss": float(row["epss"]),
        "percentile": float(row["percentile"]),
        "model_version": _nullable(row.get("model_version")),
        "score_timestamp": _nullable(row.get("score_timestamp")),
        "source": _nullable(row.get("source")),
        "source_sha256": _nullable(row.get("source_sha256")),
    }


def _normalize_ghsa(
    advisory_rows: list[dict[str, str]],
    package_rows: list[dict[str, str]],
    *,
    cve: str,
) -> list[dict[str, Any]]:
    """Attach exact GHSA package evidence to its advisory content version."""
    advisories: dict[str, dict[str, Any]] = {}
    for row in advisory_rows:
        if row.get("cve_id") != cve:
            raise RuntimeError("GHSA returned an advisory row for a different CVE.")
        observed_id = row["observed_advisory_version_id"]
        if observed_id in advisories:
            raise RuntimeError(f"Duplicate GHSA advisory content identity: {observed_id}")
        advisories[observed_id] = {
            "ghsa_id": row["ghsa_id"],
            "observed_advisory_version_id": observed_id,
            "source_advisory_sha256": row["source_advisory_sha256"],
            "cve_id": row["cve_id"],
            "advisory_type": _nullable(row.get("advisory_type")),
            "severity": _nullable(row.get("severity")),
            "url": _nullable(row.get("url")),
            "html_url": _nullable(row.get("html_url")),
            "repository_advisory_url": _nullable(row.get("repository_advisory_url")),
            "source_code_location": _nullable(row.get("source_code_location")),
            "summary": _nullable(row.get("summary")),
            "published_at": _nullable(row.get("published_at")),
            "updated_at": _nullable(row.get("updated_at")),
            "github_reviewed_at": _nullable(row.get("github_reviewed_at")),
            "nvd_published_at": _nullable(row.get("nvd_published_at")),
            "withdrawn_at": _nullable(row.get("withdrawn_at")),
            "is_withdrawn": _optional_bool(row.get("is_withdrawn")),
            "cvss_severities_json": _nullable(row.get("cvss_severities_json")),
            "vulnerability_entry_count": int(row["vulnerability_entry_count"]),
            "package_evidence": [],
        }

    for row in package_rows:
        observed_id = row["observed_advisory_version_id"]
        advisory = advisories.get(observed_id)
        if advisory is None:
            raise RuntimeError(
                f"GHSA package evidence references unknown advisory content: {observed_id}"
            )
        if row.get("ghsa_id") != advisory["ghsa_id"]:
            raise RuntimeError("GHSA package/advisory identity mismatch.")
        advisory["package_evidence"].append(
            {
                "source_index": int(row["source_index"]),
                "vulnerability_entry_id": row["vulnerability_entry_id"],
                "source_entry_sha256": row["source_entry_sha256"],
                "ecosystem": row["ecosystem"],
                "package_name": row["package_name"],
                "vulnerable_version_range": row["vulnerable_version_range"],
                "first_patched_version": _nullable(row.get("first_patched_version")),
                "vulnerable_functions": _json_or_empty_list(
                    row.get("vulnerable_functions_json")
                ),
                "range_evaluation_performed": False,
            }
        )

    normalized = list(advisories.values())
    for advisory in normalized:
        packages = advisory["package_evidence"]
        packages.sort(
            key=lambda item: (
                item["source_index"],
                item["vulnerability_entry_id"],
            )
        )
        if len(packages) != advisory["vulnerability_entry_count"]:
            raise RuntimeError(
                "GHSA vulnerability_entry_count does not equal materialized package evidence."
            )
    normalized.sort(
        key=lambda advisory: (
            advisory["ghsa_id"],
            advisory["observed_advisory_version_id"],
        )
    )
    return normalized


def main() -> None:
    """Execute source-local queries, validate invariants, and print the proof bundle."""
    args = _parse_args()
    if args.timeout_seconds <= 0:
        raise ValueError("timeout-seconds must be positive.")

    coordinates = _load_json(Path(args.coordinates), label="coordinates")
    selection = _load_json(Path(args.selection), label="selection")
    if coordinates.get("schema_version") != 1 or coordinates.get("read_only") is not True:
        raise ValueError("Coordinates must be schema_version=1 and read_only=true.")
    if selection.get("schema_version") != 1 or selection.get("read_only") is not True:
        raise ValueError("Selection must be schema_version=1 and read_only=true.")

    cve = _require_cve(str(selection["selected_cve"]))
    selected_candidate = selection["selected_candidate"]
    if selected_candidate.get("cve_id") != cve:
        raise ValueError("Selection candidate CVE does not match selected_cve.")

    database = _require_identifier(str(coordinates["database"]), field="database")
    workgroup = _require_identifier(
        str(coordinates["athena_workgroup"]["name"]), field="workgroup"
    )
    epss_snapshot = _require_date(
        str(coordinates["epss"]["latest_snapshot_date"]),
        field="EPSS snapshot_date",
    )
    kev_snapshot = _require_date(
        str(coordinates["kev"]["latest_snapshot_date"]),
        field="KEV snapshot_date",
    )
    bootstrap_dates = [
        _require_date(str(value), field="NVD bootstrap projection_date")
        for value in coordinates["nvd"]["bootstrap"]["available_projection_dates"]
    ]
    incremental_dates = [
        _require_date(str(value), field="NVD incremental projection_date")
        for value in coordinates["nvd"]["incremental"]["available_projection_dates"]
    ]
    cutoff = int(coordinates["athena_workgroup"]["bytes_scanned_cutoff_per_query"])
    region = str(coordinates["region"])

    session = boto3.Session(profile_name=args.profile, region_name=region)
    athena = session.client(
        "athena",
        config=Config(retries={"mode": "standard", "max_attempts": 5}),
    )

    nvd_rows, nvd_query = _run_query(
        athena,
        sql=_build_nvd_sql(
            cve=cve,
            bootstrap_dates=bootstrap_dates,
            incremental_dates=incremental_dates,
        ),
        database=database,
        workgroup=workgroup,
        cutoff_bytes=cutoff,
        timeout_seconds=args.timeout_seconds,
        label="NVD",
    )
    kev_rows, kev_query = _run_query(
        athena,
        sql=_build_kev_sql(cve=cve, snapshot_date=kev_snapshot),
        database=database,
        workgroup=workgroup,
        cutoff_bytes=cutoff,
        timeout_seconds=args.timeout_seconds,
        label="KEV",
    )
    epss_rows, epss_query = _run_query(
        athena,
        sql=_build_epss_sql(cve=cve, snapshot_date=epss_snapshot),
        database=database,
        workgroup=workgroup,
        cutoff_bytes=cutoff,
        timeout_seconds=args.timeout_seconds,
        label="EPSS",
    )
    ghsa_advisory_rows, ghsa_advisory_query = _run_query(
        athena,
        sql=_build_ghsa_advisory_sql(cve=cve),
        database=database,
        workgroup=workgroup,
        cutoff_bytes=cutoff,
        timeout_seconds=args.timeout_seconds,
        label="GHSA advisory",
    )
    ghsa_package_rows, ghsa_package_query = _run_query(
        athena,
        sql=_build_ghsa_package_sql(cve=cve),
        database=database,
        workgroup=workgroup,
        cutoff_bytes=cutoff,
        timeout_seconds=args.timeout_seconds,
        label="GHSA package",
    )

    nvd_observations = _normalize_nvd(nvd_rows, cve=cve)
    kev_entry = _normalize_kev(kev_rows, cve=cve)
    epss_score = _normalize_epss(epss_rows, cve=cve)
    ghsa_advisories = _normalize_ghsa(
        ghsa_advisory_rows,
        ghsa_package_rows,
        cve=cve,
    )

    actual = {
        "has_nvd": int(bool(nvd_observations)),
        "has_kev": int(kev_entry is not None),
        "has_epss": int(epss_score is not None),
        "nvd_observation_count": len(nvd_observations),
        "ghsa_advisory_version_count": len(ghsa_advisories),
        "ghsa_vulnerability_entry_count": sum(
            len(advisory["package_evidence"]) for advisory in ghsa_advisories
        ),
    }
    expected_fields = tuple(actual)
    for field in expected_fields:
        expected = int(selected_candidate[field])
        if actual[field] != expected:
            raise RuntimeError(
                f"Selection invariant mismatch for {field}: expected {expected}, "
                f"observed {actual[field]}."
            )

    overlap_count = 1 + actual["has_nvd"] + actual["has_kev"] + actual["has_epss"]
    if overlap_count != int(selected_candidate["source_overlap_count"]):
        raise RuntimeError("Source overlap count changed since deterministic selection.")

    first_patched_count = sum(
        1
        for advisory in ghsa_advisories
        for package in advisory["package_evidence"]
        if package["first_patched_version"] is not None
    )

    query_evidence = {
        "nvd": nvd_query,
        "kev": kev_query,
        "epss": epss_query,
        "ghsa_advisories": ghsa_advisory_query,
        "ghsa_packages": ghsa_package_query,
    }
    total_scanned = sum(
        int(evidence["data_scanned_in_bytes"]) for evidence in query_evidence.values()
    )

    output = {
        "schema_version": 1,
        "bundle_type": "CrossSourceCveEvidenceV1",
        "read_only": True,
        "cve_id": cve,
        "proof_coordinates": {
            "epss_snapshot_date": epss_snapshot,
            "kev_snapshot_date": kev_snapshot,
            "nvd_bootstrap_projection_dates": bootstrap_dates,
            "nvd_incremental_projection_dates": incremental_dates,
            "ghsa_relation": "historical_exact_content_versions",
            "database": database,
            "athena_workgroup": workgroup,
            "athena_engine_version": coordinates["athena_workgroup"]["engine_version"][
                "EffectiveEngineVersion"
            ],
            "bytes_scanned_cutoff_per_query": cutoff,
        },
        "nvd": {
            "exists": bool(nvd_observations),
            "observation_count": len(nvd_observations),
            "observations": nvd_observations,
            "canonical_cvss_selected": False,
        },
        "kev": {
            "snapshot_date": kev_snapshot,
            "is_kev": kev_entry is not None,
            "entry": kev_entry,
            "absence_semantics": (
                None
                if kev_entry is not None
                else "not present in the selected KEV snapshot"
            ),
        },
        "epss": {
            "snapshot_date": epss_snapshot,
            "evidence_present": epss_score is not None,
            "score": epss_score,
        },
        "ghsa": {
            "relation_semantics": "historical exact-content versions; no implicit current",
            "advisory_version_count": len(ghsa_advisories),
            "vulnerability_entry_count": actual["ghsa_vulnerability_entry_count"],
            "first_patched_version_present_count": first_patched_count,
            "range_evaluation_performed": False,
            "advisory_versions": ghsa_advisories,
        },
        "source_local_invariants": {
            "selection_expectations_match": True,
            "source_overlap_count": overlap_count,
            "nvd_observation_count": actual["nvd_observation_count"],
            "kev_row_count": len(kev_rows),
            "epss_row_count": len(epss_rows),
            "ghsa_advisory_version_count": actual["ghsa_advisory_version_count"],
            "ghsa_vulnerability_entry_count": actual["ghsa_vulnerability_entry_count"],
            "ghsa_package_count_matches_advisory_counts": True,
        },
        "phase3_boundary": {
            "package_ranges_preserved": True,
            "first_patched_versions_preserved": True,
            "installed_version_evaluation_performed": False,
            "repository_exploitability_decision_performed": False,
        },
        "query_evidence": query_evidence,
        "cost_evidence": {
            "per_query_cutoff_bytes": cutoff,
            "every_query_below_cutoff": True,
            "total_data_scanned_in_bytes_across_independent_queries": total_scanned,
            "note": "The workgroup cutoff is enforced per query, not on this aggregate.",
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
