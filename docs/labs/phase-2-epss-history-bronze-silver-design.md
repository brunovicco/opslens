# Phase 2.5C — Historical EPSS Bronze/Silver Evidence Design

Status: **2.5C-1 DESIGN COMPLETE; 2.5C-2 PARSER/SCHEMA COMPLETE; 2.5C-3 EXACT BRONZE VERSION BOUNDARY COMPLETE; 2.5C-4 NEXT**

## Purpose

Phase 2.5C defines how the immutable historical EPSS archive can coexist with the already-deployed forward-daily EPSS path without losing source provenance, fabricating legacy data, or accidentally creating an uncontrolled S3-to-Lambda fan-out.

The governing invariant remains:

> **Agents reason. Code verifies evidence.**

This document freezes the evidence and persistence contract before changing runtime code or AWS infrastructure.

## Inputs from 2.5A and 2.5B

The historical source is the FIRST-endorsed `empiricalsec/epss_scores` archive pinned to:

```text
repository: empiricalsec/epss_scores
commit:     7ba701f5599057c496489ceecd701cbd43911f5c
root tree:  2a12b2030cda9b94573bca01b67a6f0d72ab71e8
archive end: 2026-08-30
```

The immutable inventory contains 1,956 available daily snapshots from `2021-04-14` through `2026-08-30`, with nine source dates absent from the archive. Those absences remain absences.

Representative and transition-boundary source-byte proof established three physical contracts:

```text
EPSS v1 early legacy
  metadata comment: absent
  columns:          cve,epss
  percentile:       absent

EPSS v1 late legacy (observed 2022-02-03)
  metadata comment: absent
  columns:          cve,epss,percentile
  percentile:       present

EPSS v2-v5 modern
  metadata comment: present
  columns:          cve,epss,percentile
  model_version:    source-declared
  score_date:       source-declared
```

The forward/current OpsLens parser remains modern-only. The historical parser introduced in 2.5C-2 classifies both observed v1 legacy headers explicitly and delegates v2-v5 to the proven modern parser.

## Existing forward authority remains unchanged

The deployed daily path remains authoritative for dates already preserved by it:

```text
FIRST current CSV
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
```

Phase 2.5 must not rewrite those canonical daily observations merely because the same calendar dates also exist in the historical archive.

For the current `dev` evidence, the earliest already-preserved forward snapshot is:

```text
2026-08-15
```

Therefore the historical bootstrap candidate range in this environment is:

```text
archive start .. day before forward authority starts
2021-04-14 .. 2026-08-14
```

The boundary must be discovered from real target-environment evidence before a backfill; it is not a globally hard-coded product date.

If a date is already under forward authority, historical bootstrap skips it. It does not overwrite, replace, or silently choose between two source observations.

## Historical Bronze namespace

Historical source objects must **not** be written below `bronze/epss/` because the deployed S3 notification watches that namespace.

The frozen historical namespace is:

```text
bronze/epss-history/
  schema_version=1/
  archive_commit=<40-char-git-commit>/
  snapshot_date=YYYY-MM-DD/
    epss_scores.csv.gz
    manifest.json
```

Because `bronze/epss-history/` is not under `bronze/epss/`, creating historical Bronze evidence cannot directly trigger the deployed forward Silver Lambda.

### Historical source object

The gzip object preserves the exact archive bytes.

Create semantics:

```text
PutObject If-None-Match: *
```

A successful create must return an exact S3 `VersionId`.

The source identity is SHA-256 over the exact gzip bytes. Git's blob SHA-1 is preserved as archive provenance but is not used as the sole cryptographic content identity.

Required source metadata/evidence:

```text
archive_repository
archive_commit
archive_path
archive_git_blob_sha1
snapshot_date
source_sha256
compressed_size_bytes
model_era
```

`model_era` is coordinate/documentation-derived evidence. It must never be represented as though it were a literal field read from a v1 source file.

### Historical Bronze manifest

`manifest.json` is canonical JSON and is written **after** the exact gzip source object exists.

It binds:

```text
schema_version
snapshot_date
archive_repository
archive_commit
archive_path
archive_git_blob_sha1
model_era
source_metadata_present
source_object_key
source_object_version_id
source_sha256
compressed_size_bytes
```

The manifest is create-only and must itself have an exact S3 `VersionId`.

The immutable invocation coordinate for historical transformation is the exact manifest pair:

```text
bronze_manifest_key
bronze_manifest_version_id
```

The historical transformer must re-read that exact manifest version, then re-read the source gzip using the exact `source_object_version_id` bound by the manifest.

## Historical invocation boundary

Historical transformation is **not** S3-event driven.

The logical invocation contract is one snapshot per request:

```json
{
  "schema_version": "1",
  "bronze_manifest_key": "bronze/epss-history/.../manifest.json",
  "bronze_manifest_version_id": "<exact-s3-version-id>"
}
```

The event must reject:

- missing or extra authority-bearing coordinates;
- a manifest outside `bronze/epss-history/`;
- an empty `VersionId`;
- manifest/source identity mismatch;
- snapshot-date mismatch between manifest and canonical archive path;
- archive coordinates that are not part of the approved pinned source scope.

Whether this strict one-snapshot contract is hosted in a dedicated Lambda or driven through a bounded operator bootstrap remains a Phase 2.5D runtime decision. The trigger semantics themselves are frozen here: **explicit invocation only, never implicit historical S3 fan-out**.

## Legacy-compatible source model

Historical parsing requires a model that distinguishes source-declared fields from source-coordinate fields.

The logical snapshot contract is:

```text
snapshot_date                 required; archive coordinate
model_era                     required; documented/coordinate evidence
source_metadata_present       required boolean
source_model_version          nullable
source_score_timestamp        nullable
source_sha256                 required
raw_bytes                     required
row_count                     required
source_shape                  legacy_two_column | legacy_three_column | modern_metadata
```

For v1, metadata remains absent in both observed source shapes:

```text
early legacy:
  source_shape             = legacy_two_column
  percentile               = NULL
  source_model_version     = NULL
  source_score_timestamp   = NULL
  source_metadata_present  = false

late legacy:
  source_shape             = legacy_three_column
  percentile               = exact source value
  source_model_version     = NULL
  source_score_timestamp   = NULL
  source_metadata_present  = false
```

For v2-v5:

```text
source_shape             = modern
percentile               = source value
source_model_version     = source-declared value
source_score_timestamp   = source-declared value
source_metadata_present  = true
```

For modern files, the source-declared score date must match the immutable archive `snapshot_date`. A mismatch fails closed.

No historical parser may synthesize a percentile, model version, or score timestamp for v1.

## Silver schema evolution

The historical path continues to materialize the existing analytical relation:

```text
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

A second base EPSS table is not justified.

The minimal physical evolution is **EPSS Silver schema v2** with the same seven data columns and the same types as v1, but three legacy-unavailable fields become nullable:

| Column | Type | v2 nullability |
| --- | --- | --- |
| `cve` | string | required |
| `epss` | double | required |
| `percentile` | double | nullable |
| `model_version` | string | nullable |
| `score_timestamp` | timestamp UTC micros | nullable |
| `source` | string | required |
| `source_sha256` | string | required |

This is deliberately smaller than adding archive commit/path to every CVE row. Snapshot-level archive provenance belongs in the exact Bronze manifest and Silver completion evidence, not repeated hundreds of thousands of times in Parquet rows.

Existing schema-v1 Parquets remain valid members of the analytical relation because they contain the same columns with stronger non-null guarantees.

The Glue column types do not need to change merely because Parquet v2 permits null values.

### Silver row semantics for v1

For an EPSS v1 row:

```text
cve             = exact source CVE
epss            = exact source score
percentile      = NULL
model_version   = NULL
score_timestamp = NULL
source          = first-epss
source_sha256   = exact gzip SHA-256
```

`snapshot_date` remains the Hive/Glue partition coordinate derived from the immutable archive filename/path and validated against the Bronze manifest.

## Silver write and replay contract

Historical transformation prepares deterministic Parquet bytes before persistence.

Create semantics:

```text
PutObject If-None-Match: *
```

On successful creation, persistence returns the exact Silver `VersionId`.

A `412 Precondition Failed` is **not** sufficient replay evidence by itself.

On an existing key, replay verification must:

```text
HeadObject
  -> discover current VersionId

GetObject(VersionId=<exact-current-version>)
  -> read exact existing bytes

compare
  -> byte equality
  -> SHA-256 equality
```

If bytes differ at the same deterministic Silver key, the run fails closed as a content conflict. It must not overwrite or silently accept the object.

A transient concurrent-create conflict is bounded and must not be converted into an unverified success.

## Silver completion evidence

Historical transformation records completion separately from the queryable Parquet namespace:

```text
silver/epss-history/completions/
  schema_version=1/
  archive_commit=<commit>/
  snapshot_date=YYYY-MM-DD/
    manifest.json
```

The completion manifest is written **last**, after Silver content has been created or byte-for-byte replay-verified.

It binds:

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

Completion persistence is also create-only with exact-VersionId replay verification.

A completion object may never claim success for a partially persisted or unverified Silver snapshot.

## Forward/backfill coexistence rule

Historical bootstrap is allowed to materialize only dates strictly before the discovered forward-authority boundary.

```text
historical date < first forward canonical date
  -> eligible for historical bootstrap

historical date >= first forward canonical date
  -> skip; forward evidence remains authoritative
```

This avoids forcing two acquisition channels to compete for the same deterministic Silver date key.

The bootstrap run must record the discovered boundary in its run evidence.

## IAM implications for the future runtime

No IAM change is made by this design document.

A future historical transformer requires only the narrow capabilities implied by the exact contract:

```text
Bronze history:
  s3:GetObjectVersion

Silver EPSS content:
  s3:PutObject
  s3:GetObject
  s3:GetObjectVersion

Silver history completion:
  s3:PutObject
  s3:GetObject
  s3:GetObjectVersion
```

No delete permission is required.

`ListBucket` is not a transformation-runtime requirement when exact keys are supplied by the invocation contract.

Archive discovery/backfill coordination may need separately scoped read/list authority, but that must not be added to the Silver transformation identity by convenience.

## Failure modes

The 2.5C implementation must fail closed on at least:

```text
invalid archive path/date
unknown model-era coordinate within the pinned scope
bad gzip
bad CSV header for the expected era
unknown or malformed legacy v1 header/row shape
modern metadata missing
modern metadata/date mismatch
modern model-version/date-era mismatch
source SHA mismatch
Bronze VersionId mismatch
Silver replay byte mismatch
completion replay byte mismatch
attempt to bootstrap a forward-authority date
```

Retryable transport/AWS errors remain distinct from deterministic source/contract failures.

## Cost boundary

2.5C adds no AWS resource and performs no AWS backfill.

The representative 2.5B evidence suggests one modern snapshot is individually plausible within the existing Silver compute envelope, but 1,956 snapshots are a batch workload and must be costed separately.

The chosen design avoids:

- a second copy of archive provenance on every CVE row;
- an additional base Glue table;
- Glue crawler usage;
- Step Functions before a durable orchestration need exists;
- Iceberg before update/query economics justify it;
- accidental 1,956-event Lambda fan-out.

## AIP-C01 learning relevance

This increment reinforces:

```text
Domain 1
  data preparation, schema evolution, immutable evidence

Domain 2
  event-driven vs explicit invocation boundaries, idempotency, retries

Domain 3
  least privilege and authority separation

Domain 4
  batch/offline workload reasoning, Parquet cost discipline

Domain 5
  exact replay validation and source-contract failure testing
```

No GenAI service is introduced because none is required for this deterministic data-plane problem.

## 2.5C implementation sub-gates

```text
2.5C-1 — evidence/storage/runtime contract
  STATUS: COMPLETE

2.5C-2 — legacy-capable source model + parser + Silver schema v2
  STATUS: COMPLETE

2.5C-3 — exact historical Bronze manifest reader + VersionId boundary
  STATUS: COMPLETE

2.5C-4 — deterministic Silver persistence + verified replay
  STATUS: NEXT

2.5C-5 — completion evidence + strict explicit invocation composition
  STATUS: NOT STARTED

2.5C-6 — repository regression and contract closeout
  STATUS: NOT STARTED
```

## 2.5C-1 gates

```text
EPSS_HISTORY_SEPARATE_BRONZE_NAMESPACE_GATE=PASS
EPSS_HISTORY_NO_IMPLICIT_S3_FANOUT_GATE=PASS
EPSS_HISTORY_EXACT_MANIFEST_VERSION_COORDINATE_GATE=PASS
EPSS_HISTORY_V1_NO_FABRICATED_FIELDS_GATE=PASS
EPSS_HISTORY_SILVER_V2_NULLABILITY_GATE=PASS
EPSS_HISTORY_FORWARD_AUTHORITY_BOUNDARY_GATE=PASS
EPSS_HISTORY_VERIFIED_REPLAY_DESIGN_GATE=PASS
EPSS_HISTORY_COMPLETION_WRITTEN_LAST_DESIGN_GATE=PASS
EPSS_HISTORY_LEAST_PRIVILEGE_DESIGN_GATE=PASS
EPSS_HISTORY_NO_AWS_MUTATION_2_5C1_GATE=PASS
EPSS_2_5C1_GATE=PASS
```

## 2.5C-2 gates

```text
EPSS_HISTORY_LEGACY_TWO_COLUMN_SOURCE_GATE=PASS
EPSS_HISTORY_LEGACY_THREE_COLUMN_SOURCE_GATE=PASS
EPSS_HISTORY_LATE_V1_PERCENTILE_PRESERVATION_GATE=PASS
EPSS_HISTORY_V1_NO_FABRICATED_METADATA_GATE=PASS
EPSS_HISTORY_MODERN_PARSER_COMPATIBILITY_GATE=PASS
EPSS_HISTORY_SILVER_SCHEMA_V2_GATE=PASS
EPSS_HISTORY_SILVER_V2_NULLABLE_LEGACY_FIELDS_GATE=PASS
EPSS_HISTORY_REAL_FORMAT_BOUNDARY_GATE=PASS
EPSS_HISTORY_RUFF_GATE=PASS
EPSS_HISTORY_PYRIGHT_GATE=PASS
EPSS_HISTORY_UNIT_TEST_GATE=PASS
EPSS_2_5C2_GATE=PASS
```

## 2.5C-3 gates

The exact historical Bronze authority boundary is implemented and was validated successfully in CI before the temporary C3 validation workflow was removed.

```text
EPSS_HISTORY_EXACT_MANIFEST_VERSION_READ_GATE=PASS
EPSS_HISTORY_EXACT_SOURCE_VERSION_READ_GATE=PASS
EPSS_HISTORY_MANIFEST_COORDINATE_VALIDATION_GATE=PASS
EPSS_HISTORY_SOURCE_SHA_BINDING_GATE=PASS
EPSS_HISTORY_GIT_BLOB_IDENTITY_BINDING_GATE=PASS
EPSS_HISTORY_C3_FINAL_NARROWING_GATE=PASS
EPSS_2_5C3_GATE=PASS
```

C3 proves that historical transformation authority is the exact manifest `VersionId`, which in turn binds the exact source object `VersionId`, source SHA-256, Git blob identity, archive path, snapshot date, and model era. It does not create historical Bronze objects in AWS and does not authorize bulk backfill.

## Next authorized step

Implement only **2.5C-4**: deterministic Silver persistence with exact `VersionId` capture and byte-for-byte verified replay at the deterministic Silver key. Do not implement completion manifests, create historical Bronze objects in AWS, or start bulk backfill yet.
