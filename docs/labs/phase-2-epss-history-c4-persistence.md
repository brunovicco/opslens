# Phase 2.5C-4 — Historical EPSS Deterministic Silver Persistence

Status: **COMPLETE — exact create-only persistence and byte-for-byte replay verification proven; 2.5C-5 NEXT**

## Purpose

Phase 2.5C-4 implements only the historical EPSS Silver persistence boundary frozen by the Phase 2.5C design.

This increment does **not** create historical Bronze objects, perform an AWS backfill, add Terraform resources, select a historical runtime, or write completion manifests.

The governing invariant remains:

> **Agents reason. Code verifies evidence.**

## Scope completed

The historical path now has a persistence model that represents:

```text
prepared deterministic Parquet bytes
  -> exact SHA-256
  -> exact byte size
  -> row count
  -> Silver schema version

persisted S3 object evidence
  -> deterministic key
  -> exact S3 VersionId
  -> exact SHA-256
  -> exact byte size
  -> row count
  -> Silver schema version

persistence outcome
  -> created
  -> replay_verified
```

The existing forward-daily `S3SilverEpssArtifactRepository` remains unchanged. Historical persistence is isolated behind dedicated historical adapters and application orchestration.

## Create-only Silver contract

Historical Silver creation uses:

```text
PutObject
  If-None-Match: *
```

A successful create is accepted only when S3 returns a non-empty exact `VersionId`.

A successful HTTP write without `VersionId` fails closed because the persistence operation would otherwise lack the exact immutable S3 coordinate required by later completion evidence.

The deterministic historical Silver object remains in the canonical analytical namespace:

```text
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

No separate base historical EPSS table or alternate query namespace was introduced.

## Existing-key replay contract

S3 HTTP `412 Precondition Failed` is **not** treated as idempotent success.

Instead:

```text
PutObject If-None-Match: *
  -> 412
  -> HistoricalEpssSilverAlreadyExistsError
  -> exact replay verifier
```

The replay verifier performs:

```text
HeadObject(Bucket, Key)
  -> require current VersionId
  -> require positive ContentLength
  -> require size == prepared deterministic artifact

GetObject(
  Bucket,
  Key,
  VersionId=<exact version discovered by HeadObject>
)
  -> require returned VersionId == discovered VersionId
  -> require ContentLength == prepared size
  -> read exact bytes
  -> require payload length == prepared size
  -> recompute SHA-256
  -> require SHA-256 == prepared SHA-256
  -> require byte-for-byte equality
```

Only after all checks pass does the persistence result become:

```text
replay_verified
```

A same-size object with different bytes is rejected.

## Concurrent write boundary

S3 HTTP `409 ConditionalRequestConflict` remains distinct from replay success.

It raises an explicit concurrent-write error and is not converted into `replay_verified`.

Any bounded retry policy belongs to a later orchestration boundary; C4 does not hide a concurrent write behind an unverified success.

## Exact persistence evidence

The implementation adds:

```text
src/opslens/transformation/epss/history/models.py
  HistoricalEpssSilverArtifactV1
  HistoricalEpssSilverStoredObjectV1
  HistoricalEpssSilverReplayStatus
  HistoricalEpssSilverPersistenceResultV1

src/opslens/transformation/epss/history/persistence.py
  PersistHistoricalEpssSilver
  HistoricalEpssSilverAlreadyExistsError
  repository/replay ports

src/opslens/transformation/epss/adapters/outbound/s3_history_silver.py
  create-only S3 persistence
  exact VersionId requirement
  412/409 classification

src/opslens/transformation/epss/adapters/outbound/s3_history_silver_replay.py
  current-version discovery
  exact-version read
  size/SHA-256/byte equality verification
```

The application persistence service also validates that repository evidence matches the exact prepared artifact before returning success.

## Regression and validation proof

Temporary CI validation was executed on:

```text
workflow: Validate EPSS History 2.5C-4
run:      33341501477
commit:   5ffb26ed9313c8d04287dce74f753d3009d99689
result:   SUCCESS
```

The validation performed:

```text
uv lock --check
uv sync --frozen
ruff
pyright
pytest tests/unit/ingestion/epss tests/unit/transformation/epss
```

Observed results:

```text
Ruff:    PASS
Pyright: 0 errors, 0 warnings
EPSS ingestion/transformation regression tests: PASS
```

The temporary validation workflow was removed after the successful proof and is not part of the steady-state repository surface.

## C4 gates

```text
EPSS_HISTORY_SILVER_CREATE_ONLY_GATE=PASS
EPSS_HISTORY_SILVER_VERSION_ID_GATE=PASS
EPSS_HISTORY_SILVER_412_REQUIRES_REPLAY_GATE=PASS
EPSS_HISTORY_SILVER_EXACT_REPLAY_GATE=PASS
EPSS_HISTORY_SILVER_REPLAY_MISMATCH_FAIL_CLOSED_GATE=PASS
EPSS_HISTORY_SILVER_CONCURRENT_WRITE_DISTINCT_GATE=PASS
EPSS_HISTORY_C4_RUFF_GATE=PASS
EPSS_HISTORY_C4_PYRIGHT_GATE=PASS
EPSS_HISTORY_C4_REGRESSION_GATE=PASS
EPSS_2_5C4_GATE=PASS
```

## AWS and cost boundary

C4 changed no AWS state.

```text
new AWS resources:       0
Terraform changes:       0
historical backfill:     0 snapshots
historical S3 writes:    0
new scheduler/runtime:   0
```

The implementation defines the future exact S3 operations but does not exercise them against the dev environment yet.

## Phase 2.5C status after C4

```text
2.5C-1 — evidence/storage/runtime contract
  COMPLETE

2.5C-2 — legacy-capable source model + parser + Silver schema v2
  COMPLETE

2.5C-3 — exact historical Bronze manifest reader + VersionId boundary
  COMPLETE

2.5C-4 — deterministic Silver persistence + verified replay
  COMPLETE

2.5C-5 — completion evidence + strict explicit invocation composition
  NEXT

2.5C-6 — repository regression and contract closeout
  NOT STARTED
```

The earlier Bronze/Silver design document remains the frozen pre-implementation design record. This C4 evidence note is the implementation-status authority for the completed C4 gate until the Phase 2.5C closeout reconciles the consolidated design document.

## Next authorized step

Implement only **2.5C-5**:

```text
completion evidence
+ strict explicit historical invocation composition
```

The completion manifest must be written last and may claim success only after exact Bronze evidence has been read, deterministic Silver has been created or byte-for-byte replay-verified, and all exact S3 VersionIds are available.

Do not start the historical backfill, create a scheduler, or add a new AWS runtime in C5.
