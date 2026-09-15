#!/usr/bin/env python3
"""Measure what a GHSA-by-package and NVD-by-CVE projection would actually cost.

Gate 20.1 builds the only projection the request path needs. Two things decide its
physical shape, and neither should be guessed:

    how many index rows, and how wide
    how hot the worst key is

This probes both against the real Silver tables, read only, and writes the answer as
retained evidence so the Gate 20.1 store decision is evidence-backed rather than a
preference.

Two constraints found while writing this, both worth knowing before running:

**The Athena workgroup enforces a 10 MiB scan cutoff per query**
(`bytes_scanned_cutoff_per_query = 10485760`, with
`enforce_workgroup_configuration = true`), so a query cannot raise it and this script
does not try. A query killed by the cutoff is recorded as `CUTOFF_EXCEEDED` and the run
continues: "this table is larger than the demonstration-scale cutoff" is a real
measurement, not a failure to handle.

**`ghsa_advisory_versions` is not partitioned**, so any query touching it reads the whole
table. `nvd_cve_versions` is partitioned by `source_kind_partition` and
`projection_date`. That asymmetry is most of the cost difference between the two halves.

So the sizing runs in two phases. Phase A lists the S3 objects behind each Glue table:
free, immune to the cutoff, and enough on its own to answer "how big is this". Phase B
asks Athena the shape questions that object sizes cannot answer — distinct packages, rows
per package, the hottest key — and reports the bytes each one scanned.

```text
READ, NEVER WRITE. This probe creates no table, no workgroup and no object.
projected index != source of truth
```
"""

import argparse
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Protocol, cast

from _bootstrap import ensure_repository_src_on_path
from boto3.session import Session

ensure_repository_src_on_path()

from opslens.semantic_query.config import SemanticQueryCatalog  # noqa: E402
from opslens.shared.evidence import canonical_json, canonical_sha256  # noqa: E402

CORRELATION_INDEX_PROBE_CONTRACT_VERSION: Final = "opslens-correlation-index-probe:v1"

_DEFAULT_REGION: Final = "us-east-1"
_DEFAULT_GHSA_TABLE: Final = "ghsa_advisory_versions"
_DEFAULT_NVD_TABLE: Final = "nvd_cve_versions"
_WORKGROUP_SCAN_CUTOFF_BYTES: Final = 10_485_760

_TERMINAL_STATES: Final = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})
_POLL_SECONDS: Final = 2.0
_MAX_POLLS: Final = 90
_EMPTY_MAPPING: Final[Mapping[str, object]] = {}


class ProbeError(RuntimeError):
    """Raised when the probe cannot complete a measurement it was asked for."""


class _GlueClient(Protocol):
    """Only the Glue operation this probe needs."""

    def get_table(self, *, DatabaseName: str, Name: str) -> Mapping[str, object]:
        """Return one table definition."""
        ...


class _S3Paginator(Protocol):
    """Only the S3 pagination surface this probe needs."""

    def paginate(self, *, Bucket: str, Prefix: str) -> Iterable[Mapping[str, object]]:
        """Yield object listing pages."""
        ...


class _S3Client(Protocol):
    """Only the S3 operation this probe needs."""

    def get_paginator(self, operation_name: str) -> _S3Paginator:
        """Return a paginator for one listing operation."""
        ...


class _AthenaClient(Protocol):
    """Only the read-only Athena operations this probe needs."""

    def start_query_execution(
        self,
        *,
        QueryString: str,
        QueryExecutionContext: Mapping[str, str],
        WorkGroup: str,
    ) -> Mapping[str, object]:
        """Start one measurement query."""
        ...

    def get_query_execution(self, *, QueryExecutionId: str) -> Mapping[str, object]:
        """Return status and statistics for one execution."""
        ...

    def get_query_results(
        self,
        *,
        QueryExecutionId: str,
        MaxResults: int,
    ) -> Mapping[str, object]:
        """Return one bounded page of results."""
        ...


@dataclass(frozen=True, slots=True)
class StorageMeasurement:
    """Compressed footprint of one Glue table's S3 prefix.

    Attributes:
        table: Glue table name.
        location: The `s3://` prefix the table reads from.
        object_count: Objects under that prefix.
        compressed_bytes: Total size of those objects.
        largest_object_bytes: Size of the largest single object.
        distinct_partition_prefixes: Distinct `key=value/` prefixes observed.
    """

    table: str
    location: str
    object_count: int
    compressed_bytes: int
    largest_object_bytes: int
    distinct_partition_prefixes: int


@dataclass(frozen=True, slots=True)
class QueryMeasurement:
    """One Athena measurement and what it cost to take.

    Attributes:
        label: Stable identifier for the question asked.
        state: `SUCCEEDED`, `CUTOFF_EXCEEDED`, or another terminal Athena state.
        scanned_bytes: Bytes Athena reported scanning.
        elapsed_ms: Engine execution time, when Athena reported it.
        columns: Result column names, empty when the query did not succeed.
        row: The single result row, empty when the query did not succeed.
        detail: Athena's state-change reason, when it supplied one.
    """

    label: str
    state: str
    scanned_bytes: int
    elapsed_ms: int | None
    columns: tuple[str, ...] = ()
    row: tuple[str | None, ...] = ()
    detail: str | None = None

    @property
    def succeeded(self) -> bool:
        """Report whether this measurement produced a result."""
        return self.state == "SUCCEEDED"

    def value(self, column: str) -> str | None:
        """Return one named result value, or None when unavailable.

        Args:
            column: Result column name.

        Returns:
            The value, or None when the query did not succeed or lacks the column.
        """
        if not self.succeeded or column not in self.columns:
            return None
        return self.row[self.columns.index(column)]


@dataclass(slots=True)
class ProbeRun:
    """Accumulated measurements for one probe execution."""

    storage: list[StorageMeasurement] = field(default_factory=list[StorageMeasurement])
    queries: list[QueryMeasurement] = field(default_factory=list[QueryMeasurement])


def _glue_table_location(session: Session, region: str, database: str, table: str) -> str:
    """Read one Glue table's S3 location instead of hardcoding a bucket.

    Args:
        session: Authenticated boto3 session.
        region: AWS Region holding the Glue catalog.
        database: Glue database name.
        table: Glue table name.

    Returns:
        The `s3://bucket/prefix` location the table reads from.

    Raises:
        ProbeError: If the table is missing or declares no location.
    """
    client = cast(
        _GlueClient,
        session.client("glue", region_name=region),  # pyright: ignore[reportUnknownMemberType]
    )
    try:
        response = client.get_table(DatabaseName=database, Name=table)
    except Exception as exc:
        raise ProbeError(f"could not read Glue table {database}.{table}: {exc}") from exc

    table_value = response.get("Table")
    if not isinstance(table_value, Mapping):
        raise ProbeError(f"Glue returned no table object for {database}.{table}")
    descriptor = cast(Mapping[str, object], table_value).get("StorageDescriptor")
    if not isinstance(descriptor, Mapping):
        raise ProbeError(f"{database}.{table} declares no storage descriptor")
    location = cast(Mapping[str, object], descriptor).get("Location")
    if not isinstance(location, str) or not location.startswith("s3://"):
        raise ProbeError(f"{database}.{table} declares no usable S3 location")
    return location


def _measure_storage(
    session: Session,
    region: str,
    table: str,
    location: str,
) -> StorageMeasurement:
    """List every object under a table's prefix and total its compressed size.

    This is the only measurement immune to the workgroup scan cutoff, so it runs first
    and always.

    Args:
        session: Authenticated boto3 session.
        region: AWS Region holding the bucket.
        table: Glue table name, for the report.
        location: The table's `s3://bucket/prefix` location.

    Returns:
        The table's compressed footprint.

    Raises:
        ProbeError: If the objects cannot be listed.
    """
    remainder = location.removeprefix("s3://")
    bucket, _, prefix = remainder.partition("/")
    client = cast(
        _S3Client,
        session.client("s3", region_name=region),  # pyright: ignore[reportUnknownMemberType]
    )

    object_count = 0
    compressed_bytes = 0
    largest = 0
    partition_prefixes: set[str] = set()

    try:
        pages = client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix)
        for page in pages:
            contents = page.get("Contents")
            if not isinstance(contents, list):
                continue
            for item in cast(list[Mapping[str, object]], contents):
                size = item.get("Size")
                key = item.get("Key")
                if not isinstance(size, int) or not isinstance(key, str):
                    continue
                object_count += 1
                compressed_bytes += size
                largest = max(largest, size)
                directory = key.rsplit("/", 1)[0]
                if "=" in directory:
                    partition_prefixes.add(directory)
    except Exception as exc:
        raise ProbeError(f"could not list s3://{bucket}/{prefix}: {exc}") from exc

    return StorageMeasurement(
        table=table,
        location=location,
        object_count=object_count,
        compressed_bytes=compressed_bytes,
        largest_object_bytes=largest,
        distinct_partition_prefixes=len(partition_prefixes),
    )


def _run_query(
    session: Session,
    region: str,
    catalog: SemanticQueryCatalog,
    *,
    label: str,
    sql: str,
) -> QueryMeasurement:
    """Execute one bounded read-only measurement query and record what it cost.

    A query killed by the workgroup scan cutoff is recorded rather than raised: the
    cutoff firing is itself a measurement.

    Args:
        session: Authenticated boto3 session.
        region: AWS Region holding the workgroup.
        catalog: Database and workgroup to address.
        label: Stable identifier for the question.
        sql: The SELECT statement to run.

    Returns:
        The measurement, successful or not.

    Raises:
        ProbeError: If Athena cannot be reached or the query never reaches a terminal
            state within the polling bound.
    """
    client = cast(
        _AthenaClient,
        session.client("athena", region_name=region),  # pyright: ignore[reportUnknownMemberType]
    )

    started = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": catalog.database},
        WorkGroup=catalog.workgroup,
    )
    execution_id = started.get("QueryExecutionId")
    if not isinstance(execution_id, str):
        raise ProbeError(f"Athena returned no execution id for {label}")

    for _ in range(_MAX_POLLS):
        response = client.get_query_execution(QueryExecutionId=execution_id)
        execution = response.get("QueryExecution")
        if not isinstance(execution, Mapping):
            raise ProbeError(f"Athena returned no execution object for {label}")
        execution_map = cast(Mapping[str, object], execution)
        status = execution_map.get("Status")
        status_map: Mapping[str, object] = (
            cast(Mapping[str, object], status) if isinstance(status, Mapping) else _EMPTY_MAPPING
        )
        state = status_map.get("State")
        if not isinstance(state, str):
            raise ProbeError(f"Athena returned no state for {label}")
        if state not in _TERMINAL_STATES:
            time.sleep(_POLL_SECONDS)
            continue

        statistics = execution_map.get("Statistics")
        statistics_map: Mapping[str, object] = (
            cast(Mapping[str, object], statistics)
            if isinstance(statistics, Mapping)
            else _EMPTY_MAPPING
        )
        scanned = statistics_map.get("DataScannedInBytes")
        elapsed = statistics_map.get("EngineExecutionTimeInMillis")
        reason = status_map.get("StateChangeReason")
        detail = reason if isinstance(reason, str) else None

        if state != "SUCCEEDED":
            cutoff = detail is not None and "cutoff" in detail.lower()
            return QueryMeasurement(
                label=label,
                state="CUTOFF_EXCEEDED" if cutoff else state,
                scanned_bytes=scanned if isinstance(scanned, int) else 0,
                elapsed_ms=elapsed if isinstance(elapsed, int) else None,
                detail=detail,
            )

        page = client.get_query_results(QueryExecutionId=execution_id, MaxResults=2)
        columns, row = _parse_single_row(page)
        return QueryMeasurement(
            label=label,
            state="SUCCEEDED",
            scanned_bytes=scanned if isinstance(scanned, int) else 0,
            elapsed_ms=elapsed if isinstance(elapsed, int) else None,
            columns=columns,
            row=row,
            detail=None,
        )

    raise ProbeError(f"{label} did not reach a terminal state within the polling bound")


def _parse_single_row(page: Mapping[str, object]) -> tuple[tuple[str, ...], tuple[str | None, ...]]:
    """Read one aggregate result row and its column names.

    Args:
        page: One `GetQueryResults` response.

    Returns:
        The column names and the single data row.
    """
    result_set = page.get("ResultSet")
    if not isinstance(result_set, Mapping):
        return (), ()
    result_map = cast(Mapping[str, object], result_set)
    metadata = result_map.get("ResultSetMetadata")
    columns: tuple[str, ...] = ()
    if isinstance(metadata, Mapping):
        column_info = cast(Mapping[str, object], metadata).get("ColumnInfo")
        if isinstance(column_info, list):
            columns = tuple(
                str(cast(Mapping[str, object], item).get("Name", ""))
                for item in cast(list[object], column_info)
                if isinstance(item, Mapping)
            )
    rows = result_map.get("Rows")
    if not isinstance(rows, list) or len(cast(list[object], rows)) < 2:
        return columns, ()
    data_row = cast(list[Mapping[str, object]], rows)[1]
    data = data_row.get("Data")
    if not isinstance(data, list):
        return columns, ()
    values: list[str | None] = []
    for datum in cast(list[object], data):
        if not isinstance(datum, Mapping):
            values.append(None)
            continue
        raw = cast(Mapping[str, object], datum).get("VarCharValue")
        values.append(raw if isinstance(raw, str) else None)
    return columns, tuple(values)


def _ghsa_shape_sql(database: str, table: str) -> str:
    """Build the GHSA index-shape query.

    Counts only what the projection would actually store: the fields
    `GhsaPyPIVulnerabilityEvidence` needs, for the latest observed version of each
    non-withdrawn advisory, unnested to one row per (package, advisory) pair.
    """
    return f'''
WITH ranked AS (
  SELECT ghsa_id, cve_id, is_withdrawn, vulnerabilities,
         ROW_NUMBER() OVER (PARTITION BY ghsa_id ORDER BY updated_at DESC) AS rn
  FROM "{database}"."{table}"
),
pairs AS (
  SELECT
    lower(regexp_replace(v.package_name, '[-_.]+', '-')) AS package,
    r.ghsa_id,
    r.cve_id,
    length(coalesce(v.package_name, ''))
      + length(coalesce(v.vulnerable_version_range, ''))
      + length(coalesce(v.first_patched_version, ''))
      + length(coalesce(v.vulnerability_entry_id, ''))
      + length(coalesce(v.source_entry_sha256, ''))
      + length(r.ghsa_id) + 96 AS projected_bytes
  FROM ranked r
  CROSS JOIN UNNEST(r.vulnerabilities) AS t (v)
  WHERE r.rn = 1 AND NOT r.is_withdrawn AND v.ecosystem = 'pip'
)
SELECT
  count(*) AS index_rows,
  count(DISTINCT package) AS distinct_packages,
  count(DISTINCT ghsa_id) AS distinct_advisories,
  count(DISTINCT cve_id) AS distinct_cves,
  sum(projected_bytes) AS projected_bytes_total,
  max(projected_bytes) AS projected_bytes_max_row
FROM pairs
'''.strip()


def _ghsa_hot_key_sql(database: str, table: str) -> str:
    """Build the per-package distribution query, which decides hot-key risk."""
    return f'''
WITH ranked AS (
  SELECT ghsa_id, is_withdrawn, vulnerabilities,
         ROW_NUMBER() OVER (PARTITION BY ghsa_id ORDER BY updated_at DESC) AS rn
  FROM "{database}"."{table}"
),
pairs AS (
  SELECT lower(regexp_replace(v.package_name, '[-_.]+', '-')) AS package
  FROM ranked r
  CROSS JOIN UNNEST(r.vulnerabilities) AS t (v)
  WHERE r.rn = 1 AND NOT r.is_withdrawn AND v.ecosystem = 'pip'
),
per_package AS (
  SELECT package, count(*) AS advisories FROM pairs GROUP BY package
)
SELECT
  cast(approx_percentile(advisories, 0.5) AS varchar) AS p50_advisories_per_package,
  cast(approx_percentile(advisories, 0.95) AS varchar) AS p95_advisories_per_package,
  cast(max(advisories) AS varchar) AS max_advisories_per_package
FROM per_package
'''.strip()


def _nvd_shape_sql(database: str, table: str) -> str:
    """Build the NVD index-shape query.

    The port needs five scalar fields per CVE, so this reads only those columns. On a
    columnar table that is a far narrower read than the GHSA query.
    """
    return f'''
WITH ranked AS (
  SELECT cve_id, source_identifier, vuln_status,
         ROW_NUMBER() OVER (PARTITION BY cve_id ORDER BY last_modified_at DESC) AS rn
  FROM "{database}"."{table}"
)
SELECT
  count(*) AS distinct_cves,
  sum(length(cve_id)
      + length(coalesce(source_identifier, ''))
      + length(coalesce(vuln_status, '')) + 64) AS projected_bytes_total
FROM ranked
WHERE rn = 1
'''.strip()


def _parser() -> argparse.ArgumentParser:
    """Build the probe's command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Measure the GHSA-by-package and NVD-by-CVE projection before Gate 20.1 "
            "picks a store. Read-only; creates nothing."
        ),
    )
    parser.add_argument("--region", default=_DEFAULT_REGION, help="AWS Region (default: us-east-1)")
    parser.add_argument("--profile", default=None, help="Optional local AWS profile")
    parser.add_argument("--ghsa-table", default=_DEFAULT_GHSA_TABLE, help="GHSA Silver table")
    parser.add_argument("--nvd-table", default=_DEFAULT_NVD_TABLE, help="NVD Silver table")
    parser.add_argument(
        "--storage-only",
        action="store_true",
        help="run only the free S3 sizing and skip every Athena query",
    )
    parser.add_argument(
        "--print-sql",
        action="store_true",
        help="print the measurement SQL and exit without touching AWS",
    )
    parser.add_argument(
        "--format", dest="output_format", choices=("text", "json"), default="text",
        help="reviewer output projection",
    )
    parser.add_argument("--output", default=None, help="also write canonical JSON evidence here")
    return parser


def _payload(
    run: ProbeRun,
    *,
    catalog: SemanticQueryCatalog,
    region: str,
    ghsa_table: str,
    nvd_table: str,
) -> dict[str, object]:
    """Project the run as a content-addressable payload."""
    payload: dict[str, object] = {
        "contract_version": CORRELATION_INDEX_PROBE_CONTRACT_VERSION,
        "authority": {
            "read_only": True,
            "creates_infrastructure": False,
            "workgroup_scan_cutoff_bytes": _WORKGROUP_SCAN_CUTOFF_BYTES,
            "workgroup_configuration_enforced": True,
        },
        "target": {
            "region": region,
            "database": catalog.database,
            "workgroup": catalog.workgroup,
            "ghsa_table": ghsa_table,
            "nvd_table": nvd_table,
        },
        "storage": [
            {
                "table": item.table,
                "location": item.location,
                "object_count": item.object_count,
                "compressed_bytes": item.compressed_bytes,
                "largest_object_bytes": item.largest_object_bytes,
                "distinct_partition_prefixes": item.distinct_partition_prefixes,
            }
            for item in run.storage
        ],
        "queries": [
            {
                "label": item.label,
                "state": item.state,
                "scanned_bytes": item.scanned_bytes,
                "elapsed_ms": item.elapsed_ms,
                "result": dict(zip(item.columns, item.row, strict=False)),
                "detail": item.detail,
            }
            for item in run.queries
        ],
    }
    payload["probe_id"] = (
        f"{CORRELATION_INDEX_PROBE_CONTRACT_VERSION}@sha256:{canonical_sha256(payload)}"
    )
    return payload


def _render_text(payload: dict[str, object]) -> str:
    """Render one reviewer-facing summary."""
    target = cast(Mapping[str, object], payload["target"])
    lines = [
        "OpsLens correlation index sizing probe",
        f"region: {target['region']}  database: {target['database']}  "
        f"workgroup: {target['workgroup']}",
        f"measured at: {datetime.now(UTC).isoformat(timespec='seconds')}",
        "",
        "storage (free, immune to the workgroup scan cutoff)",
    ]
    for item in cast(list[Mapping[str, object]], payload["storage"]):
        compressed = cast(int, item["compressed_bytes"])
        lines.append(
            f"  {item['table']:<24} {item['object_count']:>7} objects  "
            f"{compressed / 1_048_576:>10.1f} MiB  "
            f"{item['distinct_partition_prefixes']:>5} partition prefixes"
        )

    queries = cast(list[Mapping[str, object]], payload["queries"])
    if queries:
        lines.extend(("", "measurements"))
        for item in queries:
            scanned = cast(int, item["scanned_bytes"])
            lines.append(
                f"  {item['label']:<28} {item['state']:<16} "
                f"scanned {scanned / 1_048_576:>8.2f} MiB"
            )
            result = cast(Mapping[str, object], item["result"])
            for key, value in sorted(result.items()):
                lines.append(f"      {key} = {value}")
            detail = item.get("detail")
            if detail:
                lines.append(f"      detail: {detail}")

    lines.extend((
        "",
        f"probe: {payload['probe_id']}",
        "authority: read-only measurement; creates no table, workgroup or object",
        "scope: sizing evidence for Gate 20.1, not a projection",
    ))
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the probe and emit one reviewer projection.

    Args:
        argv: Command-line arguments, or None to read `sys.argv`.

    Returns:
        0 when every requested measurement was taken or explicitly recorded as
        cut off, 2 when the probe could not run at all.
    """
    namespace = _parser().parse_args(list(argv) if argv is not None else None)
    catalog = SemanticQueryCatalog.from_environment()
    ghsa_table = cast(str, namespace.ghsa_table)
    nvd_table = cast(str, namespace.nvd_table)
    region = cast(str, namespace.region)

    if cast(bool, namespace.print_sql):
        for label, sql in (
            ("ghsa_shape", _ghsa_shape_sql(catalog.database, ghsa_table)),
            ("ghsa_hot_key", _ghsa_hot_key_sql(catalog.database, ghsa_table)),
            ("nvd_shape", _nvd_shape_sql(catalog.database, nvd_table)),
        ):
            sys.stdout.write(f"-- {label}\n{sql}\n\n")
        return 0

    session = Session(profile_name=cast(str | None, namespace.profile))
    run = ProbeRun()

    try:
        for table in (ghsa_table, nvd_table):
            location = _glue_table_location(session, region, catalog.database, table)
            run.storage.append(_measure_storage(session, region, table, location))

        if not cast(bool, namespace.storage_only):
            for label, sql in (
                ("ghsa_shape", _ghsa_shape_sql(catalog.database, ghsa_table)),
                ("ghsa_hot_key", _ghsa_hot_key_sql(catalog.database, ghsa_table)),
                ("nvd_shape", _nvd_shape_sql(catalog.database, nvd_table)),
            ):
                run.queries.append(
                    _run_query(session, region, catalog, label=label, sql=sql)
                )
    except ProbeError as exc:
        print(f"correlation index probe rejected: {exc}", file=sys.stderr)
        return 2

    payload = _payload(
        run,
        catalog=catalog,
        region=region,
        ghsa_table=ghsa_table,
        nvd_table=nvd_table,
    )

    output = cast(str | None, namespace.output)
    if output is not None:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json(payload) + b"\n")

    if cast(str, namespace.output_format) == "json":
        sys.stdout.write(canonical_json(payload).decode("utf-8") + "\n")
    else:
        sys.stdout.write(_render_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
