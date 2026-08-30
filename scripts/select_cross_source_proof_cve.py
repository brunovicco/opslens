#!/usr/bin/env python3
"""Select the Phase 2.4F proof CVE from explicit analytical coordinates."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Select a deterministic GHSA-seeded proof CVE by real source overlap "
            "without mutating AWS state."
        )
    )
    parser.add_argument(
        "--coordinates",
        default="/tmp/opslens-cross-source-coordinates.json",
        help="Path to the read-only coordinate discovery JSON.",
    )
    parser.add_argument(
        "--profile",
        default="opslens-bootstrap",
        help="AWS CLI/SDK profile used for the read-only Athena proof.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="Maximum time to wait for the Athena query.",
    )
    return parser.parse_args()


def _load_coordinates(path: Path) -> dict[str, Any]:
    """Load and minimally validate discovered proof coordinates."""
    data = json.loads(path.read_text())
    if data.get("schema_version") != 1:
        raise ValueError("Coordinate discovery schema_version must be 1.")
    if data.get("read_only") is not True:
        raise ValueError("Coordinate discovery must declare read_only=true.")
    return data


def _require_identifier(value: str, *, field: str) -> str:
    """Validate an Athena identifier-like value used by the helper."""
    if not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"Invalid {field}: {value!r}")
    return value


def _require_date(value: str, *, field: str) -> str:
    """Validate a YYYY-MM-DD proof coordinate."""
    if not _DATE_RE.fullmatch(value):
        raise ValueError(f"Invalid {field}: {value!r}")
    return value


def _sql_string(value: str) -> str:
    """Render one already validated value as a SQL string literal."""
    return "'" + value.replace("'", "''") + "'"


def _date_list(values: list[str], *, field: str) -> str:
    """Validate and render a non-empty list of explicit projection dates."""
    if not values:
        raise ValueError(f"{field} must not be empty.")
    validated = [_require_date(value, field=field) for value in values]
    return ", ".join(_sql_string(value) for value in validated)


def _build_query(coordinates: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Build the bounded GHSA-seeded overlap query and proof metadata."""
    database = _require_identifier(str(coordinates["database"]), field="database")
    workgroup = _require_identifier(
        str(coordinates["athena_workgroup"]["name"]),
        field="workgroup",
    )
    epss_snapshot = _require_date(
        str(coordinates["epss"]["latest_snapshot_date"]),
        field="epss latest_snapshot_date",
    )
    kev_snapshot = _require_date(
        str(coordinates["kev"]["latest_snapshot_date"]),
        field="kev latest_snapshot_date",
    )

    bootstrap_dates_raw = coordinates["nvd"]["bootstrap"]["available_projection_dates"]
    incremental_dates_raw = coordinates["nvd"]["incremental"]["available_projection_dates"]
    bootstrap_dates = [str(value) for value in bootstrap_dates_raw]
    incremental_dates = [str(value) for value in incremental_dates_raw]

    bootstrap_sql = _date_list(bootstrap_dates, field="NVD bootstrap projection_date")
    incremental_sql = _date_list(
        incremental_dates,
        field="NVD incremental projection_date",
    )

    sql = f"""
WITH ghsa_candidates AS (
    SELECT
        cve_id,
        COUNT(*) AS ghsa_advisory_version_count,
        SUM(vulnerability_entry_count) AS ghsa_vulnerability_entry_count
    FROM ghsa_advisory_versions
    WHERE cve_id IS NOT NULL
    GROUP BY cve_id
),

epss_matches AS (
    SELECT cve
    FROM epss_scores
    WHERE snapshot_date = {_sql_string(epss_snapshot)}
      AND cve IN (SELECT cve_id FROM ghsa_candidates)
    GROUP BY cve
),

kev_matches AS (
    SELECT cve
    FROM kev_entries
    WHERE snapshot_date = {_sql_string(kev_snapshot)}
      AND cve IN (SELECT cve_id FROM ghsa_candidates)
    GROUP BY cve
),

nvd_matches AS (
    SELECT
        cve_id,
        COUNT(*) AS nvd_observation_count
    FROM nvd_cve_versions
    WHERE (
            (
                source_kind_partition = 'bootstrap'
                AND projection_date IN ({bootstrap_sql})
            )
            OR
            (
                source_kind_partition = 'incremental'
                AND projection_date IN ({incremental_sql})
            )
          )
      AND cve_id IN (SELECT cve_id FROM ghsa_candidates)
    GROUP BY cve_id
)

SELECT
    g.cve_id,
    1
      + CASE WHEN n.cve_id IS NOT NULL THEN 1 ELSE 0 END
      + CASE WHEN k.cve IS NOT NULL THEN 1 ELSE 0 END
      + CASE WHEN e.cve IS NOT NULL THEN 1 ELSE 0 END
        AS source_overlap_count,
    CASE WHEN n.cve_id IS NOT NULL THEN 1 ELSE 0 END AS has_nvd,
    CASE WHEN k.cve IS NOT NULL THEN 1 ELSE 0 END AS has_kev,
    CASE WHEN e.cve IS NOT NULL THEN 1 ELSE 0 END AS has_epss,
    g.ghsa_advisory_version_count,
    g.ghsa_vulnerability_entry_count,
    COALESCE(n.nvd_observation_count, 0) AS nvd_observation_count
FROM ghsa_candidates g
LEFT JOIN nvd_matches n
    ON g.cve_id = n.cve_id
LEFT JOIN kev_matches k
    ON g.cve_id = k.cve
LEFT JOIN epss_matches e
    ON g.cve_id = e.cve
ORDER BY
    source_overlap_count DESC,
    CASE WHEN g.ghsa_vulnerability_entry_count > 0 THEN 1 ELSE 0 END DESC,
    g.cve_id ASC
LIMIT 10
""".strip()

    metadata = {
        "database": database,
        "workgroup": workgroup,
        "epss_snapshot_date": epss_snapshot,
        "kev_snapshot_date": kev_snapshot,
        "nvd_bootstrap_projection_dates": bootstrap_dates,
        "nvd_incremental_projection_dates": incremental_dates,
    }
    return sql, metadata


def _result_rows(result_set: dict[str, Any]) -> list[dict[str, str]]:
    """Convert Athena result rows into dictionaries keyed by the header row."""
    rows = result_set.get("Rows", [])
    if not rows:
        return []

    def values(row: dict[str, Any]) -> list[str]:
        return [item.get("VarCharValue", "") for item in row.get("Data", [])]

    header = values(rows[0])
    return [dict(zip(header, values(row), strict=False)) for row in rows[1:]]


def _candidate(row: dict[str, str]) -> dict[str, Any]:
    """Normalize one ranked Athena candidate row."""
    integer_fields = {
        "source_overlap_count",
        "has_nvd",
        "has_kev",
        "has_epss",
        "ghsa_advisory_version_count",
        "ghsa_vulnerability_entry_count",
        "nvd_observation_count",
    }
    return {
        key: int(value) if key in integer_fields else value
        for key, value in row.items()
    }


def main() -> None:
    """Execute the read-only deterministic candidate selection proof."""
    args = _parse_args()
    if args.timeout_seconds <= 0:
        raise ValueError("timeout-seconds must be positive.")

    coordinates = _load_coordinates(Path(args.coordinates))
    sql, proof_coordinates = _build_query(coordinates)

    region = str(coordinates["region"])
    session = boto3.Session(profile_name=args.profile, region_name=region)
    athena = session.client(
        "athena",
        config=Config(retries={"mode": "standard", "max_attempts": 5}),
    )

    response = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={
            "Database": proof_coordinates["database"],
            "Catalog": "AwsDataCatalog",
        },
        WorkGroup=proof_coordinates["workgroup"],
    )
    query_id = response["QueryExecutionId"]

    deadline = time.monotonic() + args.timeout_seconds
    execution: dict[str, Any]
    while True:
        execution = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
        state = execution["Status"]["State"]
        if state == "SUCCEEDED":
            break
        if state in {"FAILED", "CANCELLED"}:
            reason = execution["Status"].get("StateChangeReason", "")
            raise RuntimeError(f"Athena candidate query {state}: {reason}")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Timed out waiting for Athena query {query_id}.")
        time.sleep(1)

    result = athena.get_query_results(QueryExecutionId=query_id)["ResultSet"]
    candidates = [_candidate(row) for row in _result_rows(result)]
    if not candidates:
        raise RuntimeError("No GHSA CVE candidates were returned.")

    statistics = execution.get("Statistics", {})
    output = {
        "schema_version": 1,
        "read_only": True,
        "selection_rule": [
            "source_overlap_count DESC",
            "GHSA package evidence present DESC",
            "cve_id ASC",
        ],
        "proof_coordinates": proof_coordinates,
        "query_execution_id": query_id,
        "state": execution["Status"]["State"],
        "engine_version": execution.get("EngineVersion", {}).get("EffectiveEngineVersion"),
        "data_scanned_in_bytes": statistics.get("DataScannedInBytes"),
        "engine_execution_time_in_millis": statistics.get("EngineExecutionTimeInMillis"),
        "query_planning_time_in_millis": statistics.get("QueryPlanningTimeInMillis"),
        "total_execution_time_in_millis": statistics.get("TotalExecutionTimeInMillis"),
        "selected_cve": candidates[0]["cve_id"],
        "selected_candidate": candidates[0],
        "ranked_candidates": candidates,
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
