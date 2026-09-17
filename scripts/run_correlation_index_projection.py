#!/usr/bin/env python3
"""Build the correlation index from Silver, and make it live only once it is whole.

Gate 20.1. The request path cannot ask Silver "what applies to these packages": it is
35,584 Parquet objects partitioned by advisory id, so the question costs a corpus scan.
This projects the answer into a store keyed by what a request actually asks about.

The order of operations is the contract, not an implementation detail:

```text
1. measure how current each source is        (the response cites this, not the clock)
2. project rows, in Python, counting what cannot be keyed
3. build the manifest from the rows produced  (never from counts passed in)
4. write every row into the manifest's own generation, which nothing is reading
5. publish the manifest, create-only
6. flip the pointer
```

Until step 6 the new generation is unreachable and the previous one still answers. A run
that dies at step 4 leaves a half-written key space nobody can address, which expires on
its own. A run that dies at step 5 leaves rows and no manifest, which is the same thing.

```text
written != readable
partially built index != index
```

Athena runs in the projection workgroup (ADR 0086), never the request path's. The
default is a plan: the queries run, the rows are mapped and counted, and nothing is
written without `--apply`.

```text
READS Silver through Athena. WRITES only the index tables and two objects.
Creates no table, no workgroup, no infrastructure.
```
"""

import argparse
import json
import sys
import time
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Protocol, cast

import boto3
from _bootstrap import ensure_repository_src_on_path
from botocore.config import Config
from botocore.exceptions import ClientError

ensure_repository_src_on_path()

from opslens.correlation_index.application.item_serialization import (  # noqa: E402
    expiry_epoch,
    ghsa_item,
    nvd_item,
    pointer_document,
)
from opslens.correlation_index.application.projection import (  # noqa: E402
    GhsaProjectionOutcome,
    ghsa_projection_sql,
    nvd_projection_sql,
    project_ghsa_rows,
    project_nvd_rows,
)
from opslens.correlation_index.application.watermarks import (  # noqa: E402
    ghsa_watermark_sql,
    nvd_watermark_sql,
)
from opslens.correlation_index.config import (  # noqa: E402
    CorrelationIndexCatalog,
)
from opslens.correlation_index.domain.index_contract import (  # noqa: E402
    CorrelationIndexManifest,
    ProjectedNvdIndexRow,
    SourceWatermark,
    build_manifest,
    index_generation,
    index_timestamp,
)
from opslens.shared.evidence import canonical_json  # noqa: E402

PROJECTION_CONTRACT_VERSION: Final = "opslens-correlation-index-projection:v1"

_DEFAULT_REGION: Final = "us-east-1"
_DEFAULT_DATABASE: Final = "opslens_dev"
_DEFAULT_WORKGROUP: Final = "opslens-dev-projection"
_DEFAULT_GHSA_TABLE: Final = "ghsa_advisory_versions"
_DEFAULT_NVD_TABLE: Final = "nvd_cve_versions"

_TERMINAL_STATES: Final = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})
_POLL_SECONDS: Final = 2.0
_MAX_POLLS: Final = 300
_RESULT_PAGE_SIZE: Final = 1000


class ProjectionRunError(RuntimeError):
    """Raised when the build cannot proceed without leaving an index that misleads."""


class _AthenaClient(Protocol):
    """Only the read-only Athena operations this build needs."""

    def start_query_execution(
        self, *, QueryString: str, QueryExecutionContext: Mapping[str, str], WorkGroup: str
    ) -> Mapping[str, object]:
        """Start one query."""
        ...

    def get_query_execution(self, *, QueryExecutionId: str) -> Mapping[str, object]:
        """Return status for one execution."""
        ...


class _ResultPaginator(Protocol):
    """The paginator that walks one execution's result pages."""

    def paginate(
        self, *, QueryExecutionId: str, PaginationConfig: Mapping[str, int]
    ) -> Iterator[Mapping[str, object]]:
        """Yield result pages."""
        ...


class _AthenaResultsClient(Protocol):
    """Only the paginated read this build needs."""

    def get_paginator(self, operation_name: str) -> _ResultPaginator:
        """Return a paginator for one operation."""
        ...


class _BatchWriter(Protocol):
    """The buffered writer the DynamoDB resource provides."""

    def put_item(self, *, Item: Mapping[str, object]) -> None:
        """Buffer one item."""
        ...

    def __enter__(self) -> "_BatchWriter":
        """Enter the buffering context."""
        ...

    def __exit__(self, *arguments: object) -> None:
        """Flush on exit."""
        ...


class _IndexTable(Protocol):
    """One index table."""

    def batch_writer(self) -> _BatchWriter:
        """Return a writer that batches and retries unprocessed items."""
        ...


class _DynamoResource(Protocol):
    """Only the table lookup this build needs."""

    def Table(self, name: str) -> _IndexTable:
        """Return one table by name."""
        ...


class _S3Client(Protocol):
    """Only the writes this build needs."""

    def put_object(self, **kwargs: object) -> Mapping[str, object]:
        """Write one object."""
        ...


@dataclass(slots=True)
class BuildOutcome:
    """What one build produced, whether or not it was applied.

    Attributes:
        ghsa: The GHSA projection, admitted and refused.
        nvd_rows: The NVD rows projected for the CVEs GHSA named.
        manifest: The manifest describing the build.
        scanned_bytes: What the queries cost, by label.
        applied: Whether anything was written.
    """

    ghsa: GhsaProjectionOutcome
    nvd_rows: tuple[ProjectedNvdIndexRow, ...]
    manifest: CorrelationIndexManifest
    scanned_bytes: dict[str, int] = field(default_factory=dict[str, int])
    applied: bool = False


def _athena(session: boto3.Session, region: str) -> _AthenaClient:
    """Build one Athena client."""
    return cast(
        _AthenaClient,
        session.client(  # pyright: ignore[reportUnknownMemberType]
            "athena",
            region_name=region,
            config=Config(retries={"max_attempts": 3, "mode": "standard"}),
        ),
    )


def _run_query(
    session: boto3.Session,
    *,
    region: str,
    database: str,
    workgroup: str,
    label: str,
    sql: str,
) -> tuple[list[dict[str, str]], int]:
    """Run one query to completion and read every result page.

    A cancelled query is a failure here, unlike in the sizing probe: a projection built
    from a truncated result set is an index that silently omits rows.

    Args:
        session: Authenticated boto3 session.
        region: AWS Region.
        database: Glue database.
        workgroup: Athena workgroup to run in.
        label: Stable name for the query, used in messages.
        sql: The statement.

    Returns:
        Every result row as a column mapping, and the bytes scanned.

    Raises:
        ProjectionRunError: If the query does not succeed, or does not finish.
    """
    client = _athena(session, region)
    started = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": database},
        WorkGroup=workgroup,
    )
    execution_id = started.get("QueryExecutionId")
    if not isinstance(execution_id, str):
        raise ProjectionRunError(f"{label} returned no execution id")

    scanned = 0
    for _ in range(_MAX_POLLS):
        described = client.get_query_execution(QueryExecutionId=execution_id)
        execution = described.get("QueryExecution")
        if not isinstance(execution, dict):
            raise ProjectionRunError(f"{label} returned no execution description")
        status = cast(Mapping[str, object], execution).get("Status")
        statistics = cast(Mapping[str, object], execution).get("Statistics")
        if isinstance(statistics, dict):
            candidate = cast(Mapping[str, object], statistics).get("DataScannedInBytes")
            if type(candidate) is int:
                scanned = candidate
        state = (
            cast(Mapping[str, object], status).get("State")
            if isinstance(status, dict)
            else None
        )
        if isinstance(state, str) and state in _TERMINAL_STATES:
            if state != "SUCCEEDED":
                reason = (
                    cast(Mapping[str, object], status).get("StateChangeReason")
                    if isinstance(status, dict)
                    else None
                )
                raise ProjectionRunError(f"{label} ended {state}: {reason}")
            break
        time.sleep(_POLL_SECONDS)
    else:
        raise ProjectionRunError(f"{label} did not finish within the polling bound")

    return list(_read_rows(session, region, execution_id, label)), scanned


def _read_rows(
    session: boto3.Session, region: str, execution_id: str, label: str
) -> Iterator[dict[str, str]]:
    """Yield every result row of one succeeded execution.

    Athena repeats the header on the first page only, and omits the value entirely for a
    NULL rather than sending an empty string. Both are handled here so the mapper sees a
    plain column mapping.

    Args:
        session: Authenticated boto3 session.
        region: AWS Region.
        execution_id: The succeeded execution.
        label: Stable name, used in messages.

    Yields:
        One column mapping per result row.

    Raises:
        ProjectionRunError: If a page cannot be read.
    """
    client = cast(
        _AthenaResultsClient,
        session.client("athena", region_name=region),  # pyright: ignore[reportUnknownMemberType]
    )
    pages = client.get_paginator("get_query_results").paginate(
        QueryExecutionId=execution_id,
        PaginationConfig={"PageSize": _RESULT_PAGE_SIZE},
    )

    columns: list[str] = []
    first_page = True
    for page in pages:
        result_set = page.get("ResultSet")
        if not isinstance(result_set, dict):
            raise ProjectionRunError(f"{label} returned no result set")
        typed_set = cast(Mapping[str, object], result_set)

        if not columns:
            metadata = typed_set.get("ResultSetMetadata")
            if not isinstance(metadata, dict):
                raise ProjectionRunError(f"{label} returned no column metadata")
            column_info = cast(Mapping[str, object], metadata).get("ColumnInfo")
            if not isinstance(column_info, list):
                raise ProjectionRunError(f"{label} returned no column names")
            columns = [
                str(cast(Mapping[str, object], item).get("Name", ""))
                for item in cast(list[object], column_info)
            ]

        rows = typed_set.get("Rows")
        if not isinstance(rows, list):
            continue
        typed_rows = cast(list[object], rows)
        if first_page:
            typed_rows = typed_rows[1:]
            first_page = False

        for row in typed_rows:
            data = cast(Mapping[str, object], row).get("Data")
            if not isinstance(data, list):
                continue
            values = [
                str(cast(Mapping[str, object], cell).get("VarCharValue", ""))
                for cell in cast(list[object], data)
            ]
            yield dict(zip(columns, values, strict=False))


def _watermark(
    session: boto3.Session,
    *,
    region: str,
    database: str,
    workgroup: str,
    source: str,
    sql: str,
) -> tuple[SourceWatermark, int]:
    """Read one source's freshness.

    Args:
        session: Authenticated boto3 session.
        region: AWS Region.
        database: Glue database.
        workgroup: Athena workgroup.
        source: The source name recorded in the manifest.
        sql: The watermark statement.

    Returns:
        The watermark and the bytes the query scanned.

    Raises:
        ProjectionRunError: If the source reports no instant, which would let a response
            claim a freshness nothing measured.
    """
    rows, scanned = _run_query(
        session,
        region=region,
        database=database,
        workgroup=workgroup,
        label=f"{source}_watermark",
        sql=sql,
    )
    if not rows:
        raise ProjectionRunError(f"{source} returned no watermark row")

    observed = rows[0].get("observed_through", "")
    if not observed:
        raise ProjectionRunError(
            f"{source} reports no observed instant; a response cannot state its freshness"
        )
    return (
        SourceWatermark(
            source=source,
            observed_through=_as_index_instant(observed, source=source),
            record_count=int(rows[0].get("record_count", "0") or 0),
        ),
        scanned,
    )


def _as_index_instant(value: str, *, source: str) -> str:
    """Render a source timestamp in the index's single form.

    Args:
        value: The source's own rendering.
        source: The source name, for the message.

    Returns:
        The instant as `YYYY-MM-DDTHH:MM:SSZ`.

    Raises:
        ProjectionRunError: If the instant cannot be read.
    """
    text = value.strip().replace(" ", "T")
    for suffix in ("Z", "+00:00"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    text = text.split(".", 1)[0]
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ProjectionRunError(
            f"{source} watermark {value!r} is not an instant this index can render"
        ) from exc
    return index_timestamp(parsed)


def build(
    session: boto3.Session,
    *,
    region: str,
    database: str,
    workgroup: str,
    ghsa_table: str,
    nvd_table: str,
    built_at: datetime,
) -> BuildOutcome:
    """Run every query and produce the rows and manifest for one build.

    Nothing is written here. The manifest's counts come from the rows this produced, so
    a manifest cannot describe an index it does not match.

    Args:
        session: Authenticated boto3 session.
        region: AWS Region.
        database: Glue database holding Silver.
        workgroup: Athena workgroup to run in.
        ghsa_table: GHSA Silver table.
        nvd_table: NVD Silver table.
        built_at: When this build ran.

    Returns:
        Everything the build produced.

    Raises:
        ProjectionRunError: If a query fails or a source reports no freshness.
    """
    scanned: dict[str, int] = {}

    ghsa_watermark, cost = _watermark(
        session,
        region=region,
        database=database,
        workgroup=workgroup,
        source="ghsa",
        sql=ghsa_watermark_sql(database, ghsa_table),
    )
    scanned["ghsa_watermark"] = cost

    nvd_watermark, cost = _watermark(
        session,
        region=region,
        database=database,
        workgroup=workgroup,
        source="nvd",
        sql=nvd_watermark_sql(database, nvd_table),
    )
    scanned["nvd_watermark"] = cost

    ghsa_results, cost = _run_query(
        session,
        region=region,
        database=database,
        workgroup=workgroup,
        label="ghsa_projection",
        sql=ghsa_projection_sql(database, ghsa_table),
    )
    scanned["ghsa_projection"] = cost
    ghsa = project_ghsa_rows(ghsa_results)

    cve_ids = sorted(
        {row.github_cve_id for row in ghsa.rows if row.github_cve_id is not None}
    )
    nvd_results, cost = _run_query(
        session,
        region=region,
        database=database,
        workgroup=workgroup,
        label="nvd_projection",
        sql=nvd_projection_sql(database, nvd_table, cve_ids),
    )
    scanned["nvd_projection"] = cost
    nvd_rows = project_nvd_rows(nvd_results)

    manifest = build_manifest(
        built_at=built_at,
        ghsa_rows=ghsa.rows,
        nvd_rows=nvd_rows,
        watermarks=[ghsa_watermark, nvd_watermark],
    )
    return BuildOutcome(
        ghsa=ghsa, nvd_rows=nvd_rows, manifest=manifest, scanned_bytes=scanned
    )


def apply_build(
    session: boto3.Session,
    outcome: BuildOutcome,
    *,
    region: str,
    catalog: CorrelationIndexCatalog,
) -> None:
    """Write the build, then make it live.

    Rows first, into a generation nothing is reading. Then the manifest, create-only.
    The pointer last, because it is the only write that changes what a request sees.

    Args:
        session: Authenticated boto3 session.
        outcome: The build to write.
        region: AWS Region.
        catalog: Where the index lives.

    Raises:
        ProjectionRunError: If a write fails.
    """
    index_id = outcome.manifest.index_id
    expires_at = expiry_epoch(
        datetime.strptime(outcome.manifest.built_at, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=UTC
        )
    )

    # The resource-level batch writer already batches at 25 and retries what DynamoDB
    # reports unprocessed. Reimplementing that here would be a second place for the
    # partial-write bug this whole design exists to avoid.
    tables = cast(
        _DynamoResource,
        session.resource("dynamodb", region_name=region),  # pyright: ignore[reportUnknownMemberType]
    )

    for table_name, items in (
        (
            catalog.ghsa_table,
            [
                ghsa_item(row, index_id=index_id, expires_at=expires_at)
                for row in outcome.ghsa.rows
            ],
        ),
        (
            catalog.nvd_table,
            [
                nvd_item(row, index_id=index_id, expires_at=expires_at)
                for row in outcome.nvd_rows
            ],
        ),
    ):
        with tables.Table(table_name).batch_writer() as writer:
            for item in items:
                writer.put_item(Item=item)

    s3 = cast(
        _S3Client,
        session.client("s3", region_name=region),  # pyright: ignore[reportUnknownMemberType]
    )
    manifest_key = catalog.manifest_key(index_id)
    try:
        s3.put_object(
            Bucket=catalog.evidence_bucket,
            Key=manifest_key,
            Body=outcome.manifest.canonical_json,
            ContentType="application/json",
            IfNoneMatch="*",
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code not in {"PreconditionFailed", "ConditionalRequestConflict"}:
            raise
        # The manifest is content-addressed, so an existing key already holds exactly
        # these bytes. Rebuilding identical content is a re-run, not a conflict.

    s3.put_object(
        Bucket=catalog.evidence_bucket,
        Key=catalog.pointer_key,
        Body=canonical_json(pointer_document(index_id, outcome.manifest.built_at)),
        ContentType="application/json",
    )
    outcome.applied = True


def _payload(outcome: BuildOutcome, catalog: CorrelationIndexCatalog) -> dict[str, object]:
    """Project the build as reviewable evidence."""
    return {
        "applied": outcome.applied,
        "authority": {
            "creates_infrastructure": False,
            "reads": "silver through athena",
            "writes": [catalog.ghsa_table, catalog.nvd_table, catalog.pointer_key],
        },
        "contract_version": PROJECTION_CONTRACT_VERSION,
        "coverage": {
            "ghsa_admitted": len(outcome.ghsa.rows),
            "ghsa_rejected": len(outcome.ghsa.rejected),
            "ghsa_accounted": outcome.ghsa.accounted_count,
            "nvd_rows": len(outcome.nvd_rows),
        },
        "index": {
            "generation": index_generation(outcome.manifest.index_id),
            "index_id": outcome.manifest.index_id,
            "manifest_key": catalog.manifest_key(outcome.manifest.index_id),
        },
        "manifest": json.loads(outcome.manifest.canonical_json),
        "rejected": [
            {
                "ghsa_id": item.ghsa_id,
                "package_name_original": item.package_name_original,
                "reason": item.reason,
            }
            for item in outcome.ghsa.rejected[:50]
        ],
        "scanned_bytes": dict(sorted(outcome.scanned_bytes.items())),
    }


def _render(payload: dict[str, object]) -> str:
    """Render one reviewer-facing summary."""
    coverage = cast(Mapping[str, object], payload["coverage"])
    index = cast(Mapping[str, object], payload["index"])
    manifest = cast(Mapping[str, object], payload["manifest"])
    scanned = cast(Mapping[str, int], payload["scanned_bytes"])

    lines = [
        "OpsLens correlation index projection",
        f"applied: {payload['applied']}",
        f"index:   {index['index_id']}",
        f"built:   {manifest['built_at']}",
        "",
        "coverage",
        f"  GHSA admitted {coverage['ghsa_admitted']}  rejected {coverage['ghsa_rejected']}"
        f"  accounted {coverage['ghsa_accounted']}",
        f"  NVD rows      {coverage['nvd_rows']}",
        "",
        "freshness",
    ]
    for item in cast(list[Mapping[str, object]], manifest["watermarks"]):
        lines.append(
            f"  {item['source']:<6} through {item['observed_through']}"
            f"  ({item['record_count']} source records)"
        )

    lines.extend(["", "scanned"])
    for label, value in scanned.items():
        lines.append(f"  {label:<18} {value / (1024 * 1024):8.2f} MiB")

    rejected = cast(list[Mapping[str, object]], payload["rejected"])
    if rejected:
        lines.extend(["", f"rejected (first {len(rejected)})"])
        lines.extend(
            f"  {item['ghsa_id']}  {item['package_name_original']!r}  {item['reason']}"
            for item in rejected
        )

    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Project Silver into the correlation index. The default is a plan: the "
            "queries run and the rows are counted, and nothing is written."
        )
    )
    parser.add_argument("--apply", action="store_true", help="actually write the index")
    parser.add_argument("--region", default=_DEFAULT_REGION, help="AWS Region")
    parser.add_argument("--profile", default=None, help="Optional local AWS profile")
    parser.add_argument("--database", default=_DEFAULT_DATABASE, help="Glue database")
    parser.add_argument(
        "--workgroup",
        default=_DEFAULT_WORKGROUP,
        help="Athena workgroup; the projection one, never the request path's",
    )
    parser.add_argument("--ghsa-table", default=_DEFAULT_GHSA_TABLE)
    parser.add_argument("--nvd-table", default=_DEFAULT_NVD_TABLE)
    parser.add_argument("--print-sql", action="store_true", help="print the statements only")
    parser.add_argument("--output", default=None, help="write canonical JSON evidence here")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one projection.

    Returns:
        0 when the build succeeded, 2 when it could not run.
    """
    namespace = _parser().parse_args(list(argv) if argv is not None else None)
    database = cast(str, namespace.database)
    ghsa_table = cast(str, namespace.ghsa_table)
    nvd_table = cast(str, namespace.nvd_table)

    if cast(bool, namespace.print_sql):
        for label, sql in (
            ("ghsa_watermark", ghsa_watermark_sql(database, ghsa_table)),
            ("nvd_watermark", nvd_watermark_sql(database, nvd_table)),
            ("ghsa_projection", ghsa_projection_sql(database, ghsa_table)),
            ("nvd_projection", nvd_projection_sql(database, nvd_table, ["CVE-2026-1"])),
        ):
            sys.stdout.write(f"-- {label}\n{sql}\n\n")
        return 0

    try:
        catalog = CorrelationIndexCatalog.from_environment()
        session = boto3.Session(profile_name=cast(str | None, namespace.profile))
        outcome = build(
            session,
            region=cast(str, namespace.region),
            database=database,
            workgroup=cast(str, namespace.workgroup),
            ghsa_table=ghsa_table,
            nvd_table=nvd_table,
            built_at=datetime.now(UTC),
        )
        if cast(bool, namespace.apply):
            apply_build(session, outcome, region=cast(str, namespace.region), catalog=catalog)
    except (ProjectionRunError, ValueError) as exc:
        print(f"correlation index projection stopped: {exc}", file=sys.stderr)
        return 2

    payload = _payload(outcome, catalog)
    print(_render(payload))

    output = cast(str | None, namespace.output)
    if output is not None:
        Path(output).write_bytes(canonical_json(payload))
        print(f"\nevidence written to {output}")

    if not outcome.applied:
        print("\nplan only. Re-run with --apply to write the index and flip the pointer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
