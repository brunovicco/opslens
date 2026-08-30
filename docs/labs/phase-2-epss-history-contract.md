# Phase 2.5 — Historical EPSS Expansion Contract

Status: **IN PROGRESS — 2.5A source/workload contract frozen; representative source compatibility proof next**

## Objective

Phase 2.5 extends the existing daily FIRST EPSS evidence path into a reproducible historical series that can answer questions such as:

> How did the EPSS score and percentile for a CVE change over time?

The phase remains deterministic. It does not rank installed software, evaluate package-version applicability, or introduce model/agent reasoning.

The governing invariant remains:

> **Agents reason. Code verifies evidence.**

## Non-goals

Phase 2.5 does **not**:

- introduce Bedrock, RAG, agents, or natural-language-to-SQL;
- evaluate whether an installed package version is vulnerable;
- reinterpret historical EPSS scores under the newest model;
- fabricate missing daily snapshots;
- fabricate source-declared metadata for legacy files that did not contain it;
- add Iceberg, Step Functions, Glue ETL, ECS/Fargate, or another AWS service before a measured workload demonstrates a need;
- bulk-write historical objects into the current `bronze/epss/` prefix before the backfill/runtime boundary is explicitly approved.

Package/version applicability remains Phase 3 work.

## Existing forward-daily authority

The deployed forward path remains authoritative for new daily observations:

```text
FIRST current EPSS CSV
  https://epss.empiricalsecurity.com/epss_scores-current.csv.gz
        |
        v
opslens-dev-epss-ingestion
        |
        v
bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
        |
        v
S3 ObjectCreated
        |
        v
opslens-dev-epss-silver
        |
        v
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
        |
        v
opslens_dev.epss_scores
```

The daily scheduler remains independent from historical bootstrap work.

## Historical source authority

FIRST explicitly publishes historical EPSS scores as daily CSV files and points bulk/time-series consumers to the public `empiricalsec/epss_scores` archive rather than using the lookup API for bulk synchronization.

Phase 2.5 therefore adopts this split:

```text
forward daily
  -> FIRST current CSV endpoint

historical bootstrap
  -> FIRST-endorsed empiricalsec/epss_scores archive
  -> immutable Git commit pin
  -> exact archive path/blob identity
```

The historical source pin used for Phase 2.5 workload discovery is:

```text
repository: empiricalsec/epss_scores
commit:     7ba701f5599057c496489ceecd701cbd43911f5c
root tree:  2a12b2030cda9b94573bca01b67a6f0d72ab71e8
archive through: 2026-08-30
```

The archive commit is part of the historical source coordinate. A moving `main` branch is not sufficient provenance for a reproducible backfill.

## Real archive workload evidence

The repository metadata was enumerated read-only at the pinned commit using one non-recursive root tree plus one non-recursive tree per year. No score file was downloaded for this inventory.

```text
archive_start_date:       2021-04-14
archive_end_date:         2026-08-30
calendar_dates_expected:  1965
snapshot_count:           1956
missing_date_count:       9
compressed_bytes:         2,580,729,807
compressed_mib:           2461.18
GitHub API GETs:          8
score_files_downloaded:   0
```

Missing dates at the immutable pin:

```text
2021-04-22
2021-04-23
2021-04-24
2021-04-25
2021-04-26
2021-06-07
2021-06-18
2022-07-14
2024-12-01
```

These dates are source absences. OpsLens must preserve them as absences and must not synthesize snapshots.

Per-year source inventory:

| Year | Snapshots | Compressed bytes |
| --- | ---: | ---: |
| 2021 | 255 | 80,480,508 |
| 2022 | 364 | 255,574,073 |
| 2023 | 365 | 449,343,043 |
| 2024 | 365 | 562,505,621 |
| 2025 | 365 | 685,553,773 |
| 2026 through 2026-08-30 | 242 | 547,272,789 |

## EPSS model eras are evidence

Historical EPSS values span multiple model generations. A score jump at a model boundary is not automatically evidence that the underlying vulnerability changed.

The Phase 2.5 source model eras are:

| Era | Published source model version | Historical interval | Metadata comment expected | Snapshots at pin |
| --- | --- | --- | --- | ---: |
| v1 | unavailable in source file | 2021-04-14..2022-02-03 | no | 289 |
| v2 | `v2022.01.01` | 2022-02-04..2023-03-06 | yes | 395 |
| v3 | `v2023.03.01` | 2023-03-07..2025-03-16 | yes | 740 |
| v4 | `v2025.03.14` | 2025-03-17..2026-06-14 | yes | 455 |
| v5 | `v2026.06.15` | 2026-06-15..pin end | yes | 77 |

Model era and source-declared model version are related but not interchangeable provenance fields.

## Legacy v1 compatibility boundary

The current OpsLens EPSS parser requires a first non-empty metadata line beginning with `#` and requires source-declared `model_version` and `score_date` values. FIRST documents that EPSS v1 historical files did not contain this metadata line.

Therefore:

```text
current parser + v1 archive file != valid historical ingestion contract
```

Phase 2.5 must not silently manufacture a v1 comment line or pretend that a derived archive date/model era was declared by the source file.

The contract distinguishes:

```text
source-declared evidence
  metadata physically present in the exact source bytes

source-coordinate evidence
  immutable archive commit
  archive path
  Git blob identity
  date encoded by canonical archive filename/path
  documented model-era boundary
```

The exact representation of legacy v1 model metadata in the Silver schema remains a 2.5B design decision and must be settled after representative source-file inspection.

## Existing runtime boundary and backfill risk

The deployed daily ingestion Lambda currently uses:

```text
memory:  512 MiB
timeout: 60 seconds
source:  current daily FIRST CSV
```

The deployed Silver Lambda uses:

```text
memory:  1024 MiB
timeout: 60 seconds
```

S3 currently invokes the Silver Lambda for **every** `ObjectCreated:*` event under:

```text
bronze/epss/
```

The Silver asynchronous boundary has two retries and an SQS OnFailure destination.

Consequently, writing the 1,956 historical source objects into the current Bronze prefix would immediately create a large asynchronous fan-out. That is **not authorized** until representative file size/row/runtime behavior has been measured and the backfill orchestration boundary has been explicitly selected.

## Existing provenance/replay gaps exposed by Phase 2.5

The current EPSS Silver path predates the stricter NVD/GHSA evidence boundaries.

Today:

```text
S3 ObjectCreated parser
  -> keeps bucket/key/sequencer
  -> does not preserve source VersionId

Bronze repository
  -> GetObject by Bucket + Key
  -> not exact VersionId

Silver repository replay
  -> PutObject IfNoneMatch="*"
  -> 412 means ALREADY_EXISTS
  -> existing bytes are not re-read and verified
```

For daily forward ingestion this is idempotent at the deterministic key level, but Phase 2.5 must decide whether to harden exact Bronze-version provenance and replay verification before a historical bootstrap is permitted.

The default architectural direction is to align EPSS with the stricter evidence standard already established elsewhere in OpsLens; this is not considered complete until code/tests prove the boundary.

## Analytics boundary

The existing Glue relation already exposes:

```text
opslens_dev.epss_scores
```

with partition projection over:

```text
snapshot_date = 2021-04-14 .. NOW
```

A second base Glue table is not justified merely because historical partitions will exist.

Two analytical workloads must be measured separately:

```text
A. point-in-time lookup
   CVE + one explicit snapshot_date

B. historical trajectory
   one CVE across an explicit date interval
```

The point-in-time query should benefit from partition pruning. The trajectory query potentially touches many daily Parquet objects; whether it remains below the existing 10 MiB Athena cutoff must be proven with real historical data before deciding on any derived history projection or compaction layout.

## Historical Bronze layout

No historical Bronze key layout is frozen yet.

The design must satisfy all of the following before implementation:

- exact source archive commit/path provenance;
- deterministic snapshot identity;
- no accidental uncontrolled fan-out through the existing `bronze/epss/` notification;
- safe coexistence with the forward-daily pipeline;
- replay safety;
- a clear route to the existing or revised Silver relation.

Choosing a prefix first and discovering operational side effects later is explicitly rejected.

## Backfill orchestration

No backfill orchestration service is selected in 2.5A.

Candidates may include a bounded Lambda-based path, a controlled operator bootstrap, or another batch mechanism, but a choice requires evidence for:

- representative compressed and uncompressed file sizes;
- row counts by model era;
- parser compatibility;
- transformation time and memory;
- expected total invocations/work;
- retry/failure-recovery behavior;
- AWS cost and service quotas.

No Step Functions, Glue ETL, ECS/Fargate, or other service will be introduced only for architectural appearance or certification coverage.

## Phase 2.5 decomposition

```text
2.5A — Source/archive and workload contract
  STATUS: COMPLETE

2.5B — Representative source compatibility + parser/provenance contract
  STATUS: NEXT

2.5C — Historical Bronze/Silver runtime design and exact-version/replay hardening
  STATUS: NOT STARTED

2.5D — Bounded historical backfill implementation
  STATUS: NOT STARTED

2.5E — Real AWS backfill proof + failure/replay evidence
  STATUS: NOT STARTED

2.5F — Athena historical trajectory proof + cost decision
  STATUS: NOT STARTED

2.5G — Closeout and Phase 2 reconciliation
  STATUS: NOT STARTED
```

## 2.5A gates

```text
EPSS_HISTORY_FIRST_BULK_SOURCE_STRATEGY_GATE=PASS
EPSS_HISTORY_IMMUTABLE_ARCHIVE_PIN_GATE=PASS
EPSS_HISTORY_PINNED_ARCHIVE_DISCOVERY_GATE=PASS
EPSS_HISTORY_MISSING_DATES_PRESERVED_GATE=PASS
EPSS_HISTORY_MODEL_ERAS_EXPLICIT_GATE=PASS
EPSS_HISTORY_V1_METADATA_GAP_GATE=PASS
EPSS_HISTORY_EXISTING_EVENT_FANOUT_BOUNDARY_GATE=PASS
EPSS_HISTORY_NO_PREMATURE_BACKFILL_RUNTIME_GATE=PASS
EPSS_2_5A_GATE=PASS
```

## Next authorized gate

Phase 2.5B must inspect a bounded representative sample from the immutable archive and answer, with real source bytes:

1. What are compressed/uncompressed sizes and row counts for representative v1–v5 snapshots?
2. Which source files physically contain model/date metadata?
3. Does the current parser accept each era, and if not, why exactly?
4. What date/model information is source-declared versus derived from the immutable archive coordinate?
5. Is the current 60-second / 1-GiB Silver boundary plausibly sufficient for an individual historical snapshot before any bulk orchestration is considered?

No AWS mutation is authorized by 2.5A.
