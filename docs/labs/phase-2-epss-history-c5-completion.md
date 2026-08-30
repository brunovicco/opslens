# Phase 2.5C-5 — Historical EPSS Completion Evidence and Explicit Invocation

Status: **COMPLETE — completion evidence is written last from exact Bronze/Silver evidence; 2.5C-6 NEXT**

## Purpose

Phase 2.5C-5 closes the one-snapshot historical transformation composition boundary defined by the Phase 2.5C design.

The increment proves that an historical EPSS observation can move through the deterministic path:

```text
explicit invocation
  -> exact Bronze manifest VersionId
  -> exact Bronze source VersionId
  -> historical source validation
  -> deterministic Silver v2 Parquet preparation
  -> create-only or byte-for-byte replay-verified Silver persistence
  -> deterministic completion manifest
  -> create-only or byte-for-byte replay-verified completion persistence
```

The completion manifest is written **last**. It cannot claim success before the exact source evidence and exact persisted Silver evidence are available.

The governing invariant remains:

> **Agents reason. Code verifies evidence.**

## Scope completed

C5 adds only application/domain composition and exact S3 adapters required by the already-frozen historical evidence contract.

It does **not**:

- ingest the historical archive into AWS;
- run a historical backfill;
- add or change Terraform;
- create a Lambda, Step Functions state machine, queue, scheduler, or other AWS runtime;
- change the deployed forward-daily EPSS ingestion path;
- create an implicit S3-triggered historical fan-out.

## Historical Silver preparation

The exact Bronze source bytes already verified by C3 are now converted into deterministic Silver v2 preparation through a dedicated historical transformer.

The preparation path revalidates the parsed source against Bronze manifest evidence:

```text
parsed source SHA-256 == manifest source_sha256
parsed model era      == manifest model_era
metadata presence     == manifest source_metadata_present
```

It then serializes the existing canonical Silver relation using the existing Silver writer and key contract:

```text
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

### Legacy v1 evidence remains nullable

The historical transformer does not fabricate unavailable evidence.

For an early EPSS v1 two-column source:

```text
cve             = source value
epss            = source value
percentile      = NULL
model_version   = NULL
score_timestamp = NULL
source          = first-epss
source_sha256   = exact source gzip SHA-256
snapshot_date   = exact archive coordinate
```

A real gzip-to-parser-to-transformer test proves those nullable fields remain `None` before physical Parquet serialization.

Late-v1 source percentile values remain source-preserved, while v2-v5 use source-declared modern metadata already validated by the historical parser.

## Strict explicit invocation contract

C5 accepts exactly one authority-bearing event shape:

```json
{
  "schema_version": "1",
  "bronze_manifest_key": "bronze/epss-history/.../manifest.json",
  "bronze_manifest_version_id": "<exact-s3-version-id>"
}
```

The invocation parser rejects:

```text
missing fields
extra fields
schema_version other than string "1"
empty manifest key
empty manifest VersionId
manifest key outside bronze/epss-history
non-canonical snapshot date
archive commit different from the approved pinned revision
```

The archive revision is an explicit constructor dependency, not read from a mutable branch name.

The current approved historical archive edition remains:

```text
empiricalsec/epss_scores
7ba701f5599057c496489ceecd701cbd43911f5c
```

## Forward-authority boundary

The explicit composition receives `first_forward_snapshot_date` as an external authoritative environment coordinate.

Before reading Bronze or attempting any Silver/completion write:

```text
historical snapshot_date < first_forward_snapshot_date
  -> eligible

historical snapshot_date >= first_forward_snapshot_date
  -> fail closed
```

A unit test proves an overlapping date fails before any downstream read or write call occurs.

The boundary is not globally hard-coded into the historical domain. Discovery of the real target-environment boundary remains a later bootstrap/runtime concern.

## Completion manifest

Completion evidence is stored separately from queryable EPSS Parquet:

```text
silver/epss-history/completions/
  schema_version=1/
  archive_commit=<commit>/
  snapshot_date=YYYY-MM-DD/
    manifest.json
```

The manifest binds:

```text
schema_version
snapshot_date
archive_commit
bronze_manifest_key
bronze_manifest_version_id
source_object_key
source_object_version_id
source_sha256
silver_key
silver_version_id
silver_sha256
silver_schema_version
row_count
replay_status
```

`replay_status` describes how the canonical Silver object became acceptable for this transformation:

```text
created
replay_verified
```

The manifest is canonical compact JSON with sorted keys and a final newline. Its exact bytes receive their own SHA-256 before persistence.

## Completion is written last

The application composition order is explicit and tested:

```text
1. parse explicit invocation
2. reject forward-authority overlap
3. read exact Bronze manifest/source evidence
4. validate invocation coordinates against Bronze evidence
5. prepare deterministic Silver
6. create or exact-replay-verify Silver
7. build completion evidence from exact Bronze + persisted Silver
8. create or exact-replay-verify completion manifest
```

The unit proof records the application call order as:

```text
bronze
prepare
silver
completion_build
completion_write
```

No completion artifact can be built before exact Silver persistence evidence exists because the completion factory requires `HistoricalEpssSilverPersistenceResultV1`.

## Completion persistence and replay

Completion persistence uses the same immutable evidence discipline established for Silver C4:

```text
PutObject If-None-Match: *
```

Successful creation requires a non-empty S3 `VersionId`.

HTTP `412 Precondition Failed` does **not** mean success. It requires exact replay verification:

```text
HeadObject
  -> current VersionId
  -> ContentLength

GetObject(VersionId=<exact-current-version>)
  -> returned VersionId equality
  -> ContentLength equality
  -> exact payload length
  -> SHA-256 equality
  -> byte-for-byte equality
```

Only then may completion persistence return `replay_verified`.

HTTP `409 ConditionalRequestConflict` remains a distinct concurrent-write failure and is not silently converted into success.

## Implementation surface

C5 adds:

```text
src/opslens/transformation/epss/history/preparation.py
  historical source rows -> canonical nullable Silver v2
  exact deterministic Parquet preparation

src/opslens/transformation/epss/history/completion.py
  completion manifest model
  canonical serializer/factory
  completion persistence orchestration

src/opslens/transformation/epss/history/invocation.py
  strict invocation parser
  approved archive revision gate
  forward-authority gate
  one-snapshot explicit application composition

src/opslens/transformation/epss/adapters/outbound/s3_history_completion.py
  create-only completion persistence
  exact VersionId requirement
  412/409 classification

src/opslens/transformation/epss/adapters/outbound/s3_history_completion_replay.py
  exact current-version completion replay verification
```

Dedicated tests cover preparation, completion contract, invocation ordering, forward-boundary rejection, S3 create evidence, and exact completion replay.

## Validation proof

A temporary branch-only CI workflow was used as an implementation gate and removed after the final successful run.

The final proof is:

```text
workflow: Validate EPSS History 2.5C-5
run:      33342420455
commit:   fc1b9b6886e2fc30d77a13cfe2110fd4cc9562d4
result:   SUCCESS
```

Validation executed:

```text
uv lock --check
uv sync --frozen
ruff
pyright
pytest tests/unit/ingestion/epss tests/unit/transformation/epss
```

Observed final results:

```text
Ruff:    PASS
Pyright: 0 errors, 0 warnings, 0 informations
EPSS ingestion/transformation regression tests: 167 PASS
```

Two temporary validation iterations failed before the final green proof:

```text
run 33342243744
  Ruff contract/style findings
  -> corrected before continuing

run 33342331032
  strict Pyright findings in test doubles and untyped direct PyArrow inspection
  -> test doubles were typed to their exact protocols
  -> nullable-value proof was moved to typed domain records before serialization
```

Neither failure was bypassed by weakening global lint/type rules.

## C5 gates

```text
EPSS_HISTORY_COMPLETION_CANONICAL_MANIFEST_GATE=PASS
EPSS_HISTORY_COMPLETION_WRITTEN_LAST_GATE=PASS
EPSS_HISTORY_COMPLETION_VERSION_ID_GATE=PASS
EPSS_HISTORY_COMPLETION_EXACT_REPLAY_GATE=PASS
EPSS_HISTORY_EXPLICIT_INVOCATION_ONLY_GATE=PASS
EPSS_HISTORY_APPROVED_ARCHIVE_REVISION_GATE=PASS
EPSS_HISTORY_FORWARD_AUTHORITY_BOUNDARY_GATE=PASS
EPSS_HISTORY_V1_NO_FABRICATED_SILVER_GATE=PASS
EPSS_HISTORY_C5_LINT_RERUN_GATE=PASS
EPSS_HISTORY_C5_TYPING_RERUN_GATE=PASS
EPSS_2_5C5_GATE=PASS
```

## AWS and cost boundary

C5 changed no AWS state.

```text
new AWS resources:       0
Terraform changes:       0
historical backfill:     0 snapshots
historical S3 writes:    0
new scheduler/runtime:   0
```

The new S3 adapters define future operations only. Unit tests use deterministic fakes and the validation workflow uses GitHub-hosted CI; it does not invoke the historical data plane in AWS.

## Phase 2.5C status after C5

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
  COMPLETE

2.5C-6 — repository regression and contract closeout
  NEXT
```

The consolidated Phase 2.5C design document remains the frozen pre-implementation design record. C4 and C5 implementation evidence notes are the status authorities for those completed gates until C6 performs the consolidated repository/contract closeout.

## Next authorized step

Perform only **2.5C-6 — repository regression and contract closeout**.

C6 should reconcile the consolidated Phase 2.5C design/status documentation with the implemented C3-C5 evidence, run the broad repository regression appropriate to this increment, verify the forward-daily EPSS path has not changed semantically, verify no temporary validation workflow or unintended infrastructure change remains, and freeze the next Phase 2.5 gate.

Do not begin historical AWS backfill or select/create a historical runtime before C6 is closed.
