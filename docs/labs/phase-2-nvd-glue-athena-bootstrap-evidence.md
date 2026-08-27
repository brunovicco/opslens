# Phase 2.3G.1B — NVD Bootstrap Analytics Source Evidence

## Status

COMPLETE — one exact Bootstrap Silver COMPLETE + Parquet pair has been independently verified. The temporary Athena compatibility proof remains pending.

## Purpose

Select and verify one persisted Bootstrap Silver batch before it can be considered for the downstream analytical projection.

This does not make the Bootstrap artifact authoritative by prefix discovery alone. The analytical boundary remains:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
```

Bootstrap is a special one-time seed because the authoritative incremental watermark does not name a Bootstrap Silver Parquet object.

## Selected Bootstrap Silver COMPLETE

Candidate selected for exact verification:

```text
feed_year:
2026

feed_revision:
20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68

manifest key:
silver/nvd/cve/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68/manifest.json

manifest VersionId:
hP32acLaaZue6equWWX6PJVvcsu7RUOR
```

Observed exact S3 metadata:

```text
ETag:
"f236aec241d8ccd31549fc753efb657a"

ContentLength:
1947

ContentType:
application/json

metadata.dataset:
nvd_cve_versions

metadata.completion_status:
complete

metadata.manifest_sha256:
f7148c19d7b0ee0d7c3073c48ca18425dd97da0f85d9e2a0368ea5263e0ed31d
```

Independent hash of the exact manifest bytes:

```text
f7148c19d7b0ee0d7c3073c48ca18425dd97da0f85d9e2a0368ea5263e0ed31d
```

The exact manifest contract validated:

```text
dataset = nvd_cve_versions
schema_version = 1
completion_status = complete
source_kind = bootstrap
feed_year = 2026
feed_revision = selected exact revision
```

Logical record-set proof:

```text
a88f20256dc00827091ebaee312f5208cc45459a33caa877be1b6b84ee30377a
```

Results:

```text
NVD_2_3G_BOOTSTRAP_MANIFEST_VERSION=PASS
NVD_2_3G_BOOTSTRAP_MANIFEST_SHA256=PASS
NVD_2_3G_BOOTSTRAP_MANIFEST_CONTRACT=PASS
NVD_2_3G_BOOTSTRAP_COORDINATES=PASS
```

## Exact referenced Bootstrap Silver Parquet

The verified COMPLETE manifest names this exact Parquet evidence:

```text
key:
silver/nvd/cve/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68/part-00000.parquet

VersionId:
ucv9W1GLmaYj00PdvYp3CSBC_fPoETP_

SHA-256:
4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541

size_bytes:
36240684

row_count:
48293
```

Observed S3 metadata:

```text
ETag:
"814a5a7c420d6900206409c361f9b025"

ContentLength:
36240684

ContentType:
application/vnd.apache.parquet

metadata.row_count:
48293

metadata.dataset:
nvd_cve_versions

metadata.parquet_sha256:
4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541

metadata.source_kind:
bootstrap

metadata.source_batch_id:
feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68

metadata.schema_version:
1
```

The exact VersionId was downloaded and independently verified:

```text
actual SHA-256:
4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541

actual bytes:
36240684

Parquet leading/trailing magic:
PAR1
```

Results:

```text
NVD_2_3G_BOOTSTRAP_PARQUET_VERSION=PASS
NVD_2_3G_BOOTSTRAP_PARQUET_SHA256=PASS
NVD_2_3G_BOOTSTRAP_PARQUET_SIZE=PASS
NVD_2_3G_BOOTSTRAP_PARQUET_MAGIC=PASS
NVD_2_3G_BOOTSTRAP_PARQUET_METADATA=PASS
NVD_2_3G_BOOTSTRAP_EXACT_EVIDENCE_GATE=PASS
```

## Workgroup implication

The verified Bootstrap Parquet is:

```text
36,240,684 bytes
```

The existing Athena workgroup query cutoff is:

```text
10,485,760 bytes
```

Parquet column pruning can make actual Athena scan bytes lower than physical object size, so the 36.2 MiB object size does not by itself prove that every Bootstrap query will exceed the cutoff.

However, the Bootstrap artifact is deliberately excluded from the first compatibility query. The first SymlinkTextInputFormat spike will use only the already-verified committed incremental Parquet:

```text
4,724,916 bytes
6,749 rows
```

This minimizes variables while proving addressability, schema compatibility, complex-type reads, and measured scan behavior under the existing cost boundary.

## Symlink authority limitation to prove explicitly

A symlink file contains an S3 URI to the source object key. The existing authority model, however, binds evidence to an exact S3 VersionId and SHA-256.

Therefore the compatibility spike must distinguish two separate questions:

```text
Can Athena read the intended Parquet through SymlinkTextInputFormat?
    -> compatibility question

Can SymlinkTextInputFormat itself pin the exact authoritative VersionId?
    -> authority question
```

The permanent analytics design must not assume that a key-only S3 URI is equivalent to the exact VersionId already proven by OpsLens.

Before and after the temporary query, the spike will verify that the current S3 object VersionId and SHA-256 still match the authoritative incremental evidence. If the compatibility layer cannot preserve the exact-version property strongly enough for the permanent design, the next candidate is an immutable analytics projection created from the exact source VersionId rather than a direct symlink to the Silver key.

## Gate state

```text
NVD_2_3G_EXACT_INCREMENTAL_AUTHORITY_GATE=PASS
NVD_2_3G_EXACT_INCREMENTAL_VERSION_GATE=PASS
NVD_2_3G_EXACT_INCREMENTAL_SHA256_GATE=PASS
NVD_2_3G_INCREMENTAL_PARQUET_FORMAT_GATE=PASS
NVD_2_3G_BOOTSTRAP_DISCOVERY_GATE=PASS
NVD_2_3G_BOOTSTRAP_EXACT_EVIDENCE_GATE=PASS
NVD_2_3G_SYMLINK_PARQUET_READ_GATE=PENDING
NVD_2_3G_SCHEMA_COMPATIBILITY_GATE=PENDING
NVD_2_3G_COMPLEX_TYPE_GATE=PENDING
NVD_2_3G_PARQUET_ATHENA_CROSSCHECK_GATE=PENDING
NVD_2_3G_SCAN_LIMIT_GATE=PENDING
NVD_2_3G_AUTHORITY_ONLY_GATE=PENDING
```

## Next boundary

```text
exact incremental Parquet
    -> re-verify current object identity
    -> temporary one-entry symlink prefix
    -> temporary Athena table
    -> primitive + complex queries
    -> local PyArrow cross-check
    -> scan/latency evidence
    -> re-verify source identity
    -> delete temporary table/index
    -> decide permanent addressability model
```

No Silver mutation, authoritative-watermark mutation, scan-cutoff increase, or permanent analytics runtime is authorized by this step.
