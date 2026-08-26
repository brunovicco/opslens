# Phase 2.3G.1 — NVD Analytics Source Evidence

## Status

IN PROGRESS — committed incremental evidence verified; Bootstrap Silver candidate verification remains before the SymlinkTextInputFormat compatibility proof.

## Purpose

Resolve exact persisted NVD Silver evidence before any temporary Athena compatibility resources are created.

The analytics path remains downstream of authority:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
```

No analytical table or index may infer incremental authority from an S3 prefix alone.

## Repository baseline

Phase 2.3F was squash-merged to `main` as:

```text
6dcff6beeff63e5ec9e46ab6bc23bad798531d32
feat(phase-2): add authoritative NVD incremental runtime (#25)
```

Phase 2.3G branch:

```text
phase-2-nvd-glue-athena
```

## Current authoritative watermark

Read from:

```text
control/nvd/cve/incremental/watermark.json
```

Observed exact S3 evidence:

```text
VersionId:
S8GnyKJhDlfvmsWs3gbl9Zg8JWnQio2o

ETag:
"59f6abee97a4f41ea7148706e3f32c7e"

ContentLength:
1287

ContentType:
application/json

SHA-256:
51385b65b18a45fa7b5d3e783bd192065381344ba9bef24c074d3d1787b8c348
```

Parsed authoritative state:

```text
state:
committed

commit_basis.kind:
silver_complete_promotion

committed_through_at:
2026-08-25T23:25:00Z

update_id:
65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e
```

Result:

```text
NVD_2_3G_WATERMARK_STATE=PASS
NVD_2_3G_WATERMARK_BASIS=PASS
```

## Exact committed incremental Silver Parquet

The current authoritative watermark names the exact Silver Parquet evidence:

```text
key:
silver/nvd/cve/schema_version=1/source_kind=incremental/update_id=65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e/part-00000.parquet

VersionId:
f.L5xLSzp1eabl4R9VA8ebt6ReWEp9cm

expected SHA-256:
d95c409ef20d787632f45419a436855d0cd3d543704fe5b189af32025ad2fac8
```

Exact S3 object metadata:

```text
ETag:
"564a395e01442f3a2fca8fe48837a550"

ContentLength:
4724916

ContentType:
application/vnd.apache.parquet

row_count:
6749

dataset:
nvd_cve_versions

schema_version:
1

source_kind:
incremental

source_batch_id:
65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e
```

The exact object version was downloaded and independently hashed:

```text
expected SHA-256:
d95c409ef20d787632f45419a436855d0cd3d543704fe5b189af32025ad2fac8

actual SHA-256:
d95c409ef20d787632f45419a436855d0cd3d543704fe5b189af32025ad2fac8

Parquet magic:
PAR1
```

Results:

```text
NVD_2_3G_INCREMENTAL_VERSION=PASS
NVD_2_3G_INCREMENTAL_SHA256=PASS
NVD_2_3G_INCREMENTAL_PARQUET_MAGIC=PASS
```

This artifact is approved as the first bounded source for the Athena SymlinkTextInputFormat compatibility spike.

Its total Parquet object size is 4,724,916 bytes, below the existing Athena workgroup scan cutoff of 10,485,760 bytes. Individual query scan size must still be measured from Athena execution statistics rather than inferred from object size.

## Bootstrap Silver COMPLETE candidates

A human-operated S3 version listing was used only for discovery. This does not imply a future runtime `s3:ListBucket` requirement.

Two current Bootstrap Silver COMPLETE manifests were observed:

### Candidate 1

```text
key:
silver/nvd/cve/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260818T070012Z-10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f/manifest.json

VersionId:
yPCiSrmD1OytCmKGsNGd868pplq_j40n

LastModified:
2026-08-22T15:49:33Z

size:
1947 bytes
```

### Candidate 2

```text
key:
silver/nvd/cve/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68/manifest.json

VersionId:
hP32acLaaZue6equWWX6PJVvcsu7RUOR

LastModified:
2026-08-22T21:22:46Z

size:
1947 bytes
```

Neither Bootstrap candidate is analytically seeded yet.

The selected Bootstrap seed must be resolved from the exact manifest VersionId and then verified against the exact referenced Parquet VersionId, SHA-256, row count, and Parquet magic before its URI can enter the analytical index.

## Shell observation

The local zsh prompt emitted:

```text
RPROMPT: parameter not set
```

while `set -u` was active. The AWS commands and verification scripts still completed and produced the evidence above. This is a local prompt integration issue, not an OpsLens runtime or AWS evidence failure.

Future shell snippets for this phase should avoid leaving `nounset` enabled globally in the interactive shell.

## Gate state

```text
NVD_2_3G_EXACT_INCREMENTAL_AUTHORITY_GATE=PASS
NVD_2_3G_EXACT_INCREMENTAL_VERSION_GATE=PASS
NVD_2_3G_EXACT_INCREMENTAL_SHA256_GATE=PASS
NVD_2_3G_INCREMENTAL_PARQUET_FORMAT_GATE=PASS
NVD_2_3G_BOOTSTRAP_DISCOVERY_GATE=PASS
NVD_2_3G_BOOTSTRAP_EXACT_EVIDENCE_GATE=PENDING
NVD_2_3G_SYMLINK_PARQUET_READ_GATE=PENDING
```

## Next boundary

Before permanent Terraform resources are introduced:

```text
verify one exact Bootstrap Silver COMPLETE + Parquet pair
    -> create a temporary symlink index prefix
    -> create a temporary Athena table using SymlinkTextInputFormat
    -> prove the NVD Silver v1 schema and complex types
    -> cross-check Athena against exact Parquet evidence
    -> measure bytes scanned and latency
    -> remove temporary resources
```

No authoritative watermark mutation, Silver mutation, or permanent Glue/index runtime is authorized by this evidence step.
