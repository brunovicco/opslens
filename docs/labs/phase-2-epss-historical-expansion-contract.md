# Phase 2.5 — Historical EPSS Expansion Contract

_Status: 2.5A contract frozen_

## Goal

Phase 2.5 closes the remaining Phase 2 requirement for deterministic historical EPSS evidence.

The Phase 2 exit question is not "build a generic time-series platform". It is narrower:

```text
Given a CVE and an explicit EPSS snapshot date:
  -> return the EPSS score and percentile for that exact source snapshot
  -> preserve the model version / model-era context
  -> preserve exact source provenance
  -> remain reproducible and bounded in Athena
```

The current daily EPSS path remains authoritative for current snapshots. Historical expansion must extend that path without weakening its existing invariants.

## Current implemented baseline

The existing production path already has the physical shape required for historical snapshots:

```text
FIRST current EPSS
  -> EPSS ingestion Lambda
  -> bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
  -> EPSS Silver Lambda
  -> silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
  -> Glue opslens_dev.epss_scores
  -> Athena opslens-dev
```

The Glue table uses injected `snapshot_date` partition projection and the existing seven-column Silver schema:

```text
cve
EPSs
percentile
model_version
score_timestamp
source
source_sha256
```

The historical milestone should reuse this table and Silver contract if source-era compatibility can be proven. No second Glue table, crawler, Iceberg table, or new query engine is justified by the Phase 2 exit criteria.

## Authoritative historical source

Bulk historical authority is the official EPSS historical archive:

```text
repository: empiricalsec/epss_scores
upstream role: official current and historical EPSS score archive
first available score date: 2021-04-14
```

The Phase 2.5 source inventory is pinned before execution. The initial proof pin is:

```text
upstream_commit = 7ba701f5599057c496489ceecd701cbd43911f5c
commit_message   = Add EPSS scores for 2026-08-30
```

Historical files must be addressed by exact repository path under that pinned source revision. The moving `main` branch must never be the logical identity of an already-planned backfill run.

The FIRST EPSS API is a secondary validation surface, not the bulk backfill source:

- `date=YYYY-MM-DD` can retrieve historic values for a requested date;
- `scope=time-series` is bounded to the most recent 30 days;
- API rate limits and per-request semantics make it inappropriate as the authority for a complete multi-year bulk reconstruction.

## Third-party repository trust boundary

The archive repository is **data only**.

OpsLens may read:

- repository metadata;
- directory/file names;
- exact historical `.csv.gz` bytes;
- Git blob identity / upstream commit identity.

OpsLens must never execute code, workflows, scripts, or binaries from the third-party repository.

## Source-era semantics

Historical EPSS is not one homogeneous model series.

The official archive documents model boundaries that materially change score semantics:

```text
no scores before 2021-04-14
EPSS v2 begins 2022-02-04
EPSS v3 begins 2023-03-07
EPSS v4 begins 2025-03-17
EPSS v5 live model refresh begins 2026-06-15
```

A score comparison across model boundaries is valid evidence, but the model transition must remain visible. Consumers must not treat a score jump across model eras as if only the vulnerability changed.

### Pre-v2 compatibility boundary

The official archive states that starting with EPSS v2, files include a leading `#` comment containing model version and publish date. Therefore, pre-v2 snapshots cannot be assumed to satisfy the current OpsLens parser contract that requires this metadata row.

Phase 2.5 must introduce an explicit historical-source parser contract rather than silently weakening the current parser.

For every historical file, the parser must deterministically classify the physical format before producing an `EpssSnapshot`.

Allowed format families are frozen as:

```text
modern_metadata_v1
  leading metadata row beginning '#'
  explicit source model version and score timestamp
  cve,epss,percentile data contract

legacy_pre_v2
  no modern metadata row
  snapshot date derived only from the validated archive path/file name
  model era recorded explicitly as legacy/pre-v2 evidence
  actual CSV header/columns must be validated from real archive bytes before support is implemented
```

No legacy column shape is invented in this contract. 2.5B must inspect representative real archive bytes and freeze exact supported legacy header semantics before production backfill.

## Snapshot identity

Logical historical snapshot identity is:

```text
snapshot_date
+ source_sha256 of exact compressed archive bytes
+ pinned upstream commit
+ exact archive path
```

The archive path must encode the same calendar date as the parsed/derived snapshot date. A mismatch fails closed.

The S3 data identity remains date-scoped:

```text
bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

Existing current-day objects must never be overwritten. Backfill is create-only and must verify an already-existing snapshot instead of replacing it.

## Provenance extension

The current Silver schema already carries `source_sha256`, source, score timestamp, model version, and the partition date. Phase 2.5 must preserve compatibility with this schema unless a real historical source requirement proves it insufficient.

Backfill execution evidence must additionally record outside the row grain:

```text
archive_repository
archive_commit_sha
archive_path
archive_blob_sha
source_sha256
snapshot_date
format_family
write_status
Bronze VersionId
Silver VersionId / replay evidence
```

This execution provenance belongs in a deterministic backfill manifest/checkpoint, not duplicated into every EPSS score row unless a later requirement proves that necessary.

## Backfill execution model

The initial architecture is a bounded, resumable operator workload, not a new always-on AWS service.

```text
pinned archive inventory
      |
      v
OpsLens historical backfill CLI
      |
      +--> fetch exact .csv.gz bytes
      +--> validate bounded size / gzip / date / format family
      +--> calculate SHA-256
      +--> create Bronze if absent
      |
      v
existing S3 ObjectCreated boundary
      |
      v
existing EPSS Silver Lambda
      |
      v
existing Silver snapshot partition
```

Why this is the first design:

- the workload is finite and one-off;
- existing S3 and Silver runtime already implement the durable data-plane path;
- adding Step Functions, Glue jobs, Batch, ECS, DynamoDB, or another Lambda is not justified before measuring the real workload;
- an operator CLI can enforce date ranges, maximum snapshots per run, resume checkpoints, retries, and dry-run inventory deterministically.

If the representative proof demonstrates that the existing Silver Lambda/event path is operationally unsuitable for bulk expansion, 2.5 may revisit the runtime decision with measured evidence.

## Backfill safety controls

The backfill CLI must support at minimum:

```text
--archive-commit <sha>      required
--start-date YYYY-MM-DD     required
--end-date YYYY-MM-DD       required
--max-snapshots N           required positive bound
--dry-run                    inventory only
--checkpoint <path>         resumable local execution evidence
```

Additional mandatory behavior:

- chronological deterministic ordering;
- bounded HTTP timeout and object-size limit;
- no unbounded concurrency;
- no source repository code execution;
- create-only Bronze writes;
- exact existing-object verification on replay;
- fail closed on date/path/header/model inconsistencies;
- explicit success/failed/skipped-existing status per snapshot;
- no delete permission requirement;
- no mutation of Glue/Athena metadata during backfill.

## Historical query semantics

The existing Glue partition strategy is retained for Phase 2 closure:

```sql
SELECT cve, epss, percentile, model_version, score_timestamp, source_sha256
FROM opslens_dev.epss_scores
WHERE snapshot_date = '<explicit-date>'
  AND cve = '<explicit-cve>';
```

Historical evidence always requires an explicit `snapshot_date` for this milestone.

OpsLens will not add a separate CVE-centered time-series projection merely to provide an unconstrained "all dates" query. If a later product requirement needs full-series scans by CVE, that must be designed against measured data volume and the 10 MiB Athena workgroup cutoff rather than introduced speculatively.

## Current vs historical semantics

There is no implicit `latest` query in the historical contract.

Current EPSS must be resolved to an explicit snapshot coordinate first. Historical EPSS uses an explicit requested date. The evidence bundle should therefore expose:

```text
current_snapshot_date = resolved explicit date
historical_snapshot_date = requested explicit date
```

and preserve each result independently.

## Model-version semantics

For modern snapshots, `model_version` comes from source metadata.

For pre-v2 snapshots where the official file format does not carry the modern metadata row, 2.5B must freeze one deterministic representation based on source-supported evidence. It must not fabricate a version number that the archive does not state.

Candidate representation:

```text
legacy-pre-v2
```

This candidate is not production-authorized until representative pre-v2 bytes are inspected and tests prove the exact legacy contract.

## Storage and cost boundary

A complete historical archive may contain thousands of daily source snapshots. Phase 2.5 must measure before bulk execution:

```text
snapshot count
compressed bytes
estimated Bronze storage
representative Silver Parquet size
estimated Silver storage
representative Lambda duration/memory
Athena bytes scanned for exact-date historical lookup
```

The existing dev Athena workgroup limit remains:

```text
10,485,760 bytes/query
```

Every historical exit query must remain below that cutoff.

No lifecycle rule may delete historical Bronze or Silver evidence required for reproducibility without an explicit architectural decision.

## Observability

Backfill evidence must make progress reconstructable without high-cardinality CloudWatch metrics.

Required execution-level fields include:

```text
run_id
archive_commit_sha
requested_start_date
requested_end_date
max_snapshots
processed
created
verified_existing
failed
first_snapshot_date
last_snapshot_date
compressed_bytes_processed
elapsed_seconds
```

Per-snapshot failures belong in structured checkpoint/run evidence and logs; raw EPSS rows must not be emitted to logs.

## Implementation gates

### 2.5A — Historical source and architecture contract

```text
EPSS_HISTORY_OFFICIAL_ARCHIVE_GATE=PASS
EPSS_HISTORY_PINNED_SOURCE_REVISION_GATE=PASS
EPSS_HISTORY_MODEL_ERA_BOUNDARY_GATE=PASS
EPSS_HISTORY_NO_THIRD_PARTY_EXECUTION_GATE=PASS
EPSS_HISTORY_REUSE_EXISTING_SILVER_GLUE_GATE=PASS
EPSS_HISTORY_NO_NEW_RUNTIME_BY_DEFAULT_GATE=PASS
EPSS_2_5A_GATE=PASS
```

### 2.5B — Real source-format probe and parser contract

Must inspect representative source bytes from at least:

```text
2021 pre-v2
2022 v2 boundary
2023 v3 boundary
2025 v4 boundary
2026 v5/current era
```

Freeze exact header/metadata semantics and regression fixtures.

### 2.5C — Bounded multi-era local/runtime proof

Backfill a very small date set spanning format/model eras. Prove:

- exact source/date identity;
- create-only Bronze;
- successful Silver materialization;
- replay creates no duplicate physical evidence;
- modern and legacy metadata semantics remain distinguishable.

### 2.5D — Backfill inventory and cost plan

Freeze the exact archive commit, complete date inventory, gaps, total source bytes, execution batch size, and estimated storage/runtime cost before full execution.

### 2.5E — Full historical archive backfill

Backfill all authoritative snapshots in the frozen scope, with resumable checkpoints and reconciliation between planned, created, existing, failed, Bronze, and Silver counts.

### 2.5F — Athena historical evidence and Phase 2 closeout

For at least one CVE with evidence on multiple dates, prove deterministic current and historical EPSS queries with explicit snapshot coordinates and bounded scans.

Then reconcile Phase 2 exit criteria before authorizing Phase 3.

## Explicit non-goals

Phase 2.5 does not:

- create a generic time-series analytics platform;
- reinterpret historical scores onto a common model scale;
- smooth or normalize score jumps across EPSS model versions;
- execute code from the EPSS archive repository;
- introduce LLMs, RAG, agents, MCP, or natural-language SQL;
- change package/version applicability logic;
- add AWS services only for certification exposure.

## Next authorized step

Only 2.5B is authorized next:

1. inspect representative exact archive bytes across model eras;
2. identify the exact pre-v2 physical CSV contract;
3. freeze parser behavior and tests;
4. do not perform any AWS backfill yet.
