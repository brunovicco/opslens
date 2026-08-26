# Phase 2.3G.3C — Bootstrap Exact-Version Projection Proof

## Status

IN PROGRESS — exact Bootstrap COMPLETE evidence, exact Bootstrap Parquet evidence, and clean destination absence have been re-verified. CopyObject materialization is next.

## Purpose

Repeat the proven exact-version analytics projection pattern for the independently verified NVD Bootstrap seed before permanent analytics infrastructure is introduced.

Bootstrap is a one-time seed path. It is not named by the authoritative incremental watermark, so its analytical eligibility is established from an exact verified Silver COMPLETE + Parquet pair.

The authority/materialization boundary remains:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

For Bootstrap, `analytics_eligible` means the exact Silver COMPLETE and exact Parquet evidence have been independently verified as a seed. `analytics_projected` remains downstream materialization only and cannot authorize or advance the incremental watermark.

## Selected Bootstrap seed

```text
feed_year:
2026

feed_revision:
20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68

source_batch_id:
feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68
```

### Exact Silver COMPLETE

```text
key:
silver/nvd/cve/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68/manifest.json

VersionId:
hP32acLaaZue6equWWX6PJVvcsu7RUOR

SHA-256:
f7148c19d7b0ee0d7c3073c48ca18425dd97da0f85d9e2a0368ea5263e0ed31d

bytes:
1947

completion_status:
complete
```

Revalidation gates:

```text
NVD_2_3G_BOOTSTRAP_SEED_MANIFEST_VERSION_GATE=PASS
NVD_2_3G_BOOTSTRAP_SEED_MANIFEST_SHA256_GATE=PASS
NVD_2_3G_BOOTSTRAP_SEED_MANIFEST_SIZE_GATE=PASS
NVD_2_3G_BOOTSTRAP_SEED_MANIFEST_DATASET_GATE=PASS
NVD_2_3G_BOOTSTRAP_SEED_COMPLETE_GATE=PASS
NVD_2_3G_BOOTSTRAP_SEED_MANIFEST_METADATA_SHA_GATE=PASS
```

## Exact Bootstrap Silver Parquet

```text
key:
silver/nvd/cve/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68/part-00000.parquet

VersionId:
ucv9W1GLmaYj00PdvYp3CSBC_fPoETP_

SHA-256:
4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541

bytes:
36240684

rows:
48293
```

Observed source metadata revalidated:

```text
dataset=nvd_cve_versions
schema_version=1
source_kind=bootstrap
source_batch_id=feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68
row_count=48293
parquet_sha256=4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
```

Exact-version download independently revalidated the same SHA-256, physical byte count, and leading/trailing `PAR1` magic.

Source gates:

```text
NVD_2_3G_BOOTSTRAP_PROJECTION_SOURCE_VERSION_GATE=PASS
NVD_2_3G_BOOTSTRAP_PROJECTION_SOURCE_SHA256_GATE=PASS
NVD_2_3G_BOOTSTRAP_PROJECTION_SOURCE_SIZE_GATE=PASS
NVD_2_3G_BOOTSTRAP_PROJECTION_SOURCE_PARQUET_GATE=PASS
NVD_2_3G_BOOTSTRAP_PROJECTION_SOURCE_METADATA_GATE=PASS
```

## Temporary projection destination

Candidate proof key:

```text
analytics-spike/nvd/cve/exact-projection/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68/part-00000.parquet
```

A current-key HeadObject returned 404 before materialization:

```text
NVD_2_3G_BOOTSTRAP_PROJECTION_DESTINATION_ABSENT_GATE=PASS
```

No destination object has been created by this proof yet.

## Operational note

The first attempted revalidation command failed because the local AWS SSO token had expired. `aws sso login --profile opslens-bootstrap` succeeded, and the exact evidence was then re-read successfully. No data-plane mutation occurred during the expired-token failure.

## Next proof step

```text
exact Bootstrap COMPLETE
    +
exact Bootstrap Parquet VersionId + SHA-256
    -> CopyObject from exact source VersionId
    -> If-None-Match: * deterministic destination
    -> require CopySourceVersionId match
    -> require non-empty destination VersionId
    -> exact destination hash/metadata verification
    -> replay must fail closed
    -> ordinary Parquet Athena proof under existing 10 MiB cutoff
```

Projected metadata will use:

```text
dataset=nvd_cve_versions
schema_version=1
source_kind=bootstrap
source_batch_id=<exact Bootstrap batch id>
row_count=48293
parquet_sha256=<exact source/destination SHA-256>
authority_source_key=<exact Bootstrap Silver Parquet key>
authority_source_version_id=<exact Bootstrap Silver Parquet VersionId>
authority_source_sha256=<exact Bootstrap Silver Parquet SHA-256>
authority_state=bootstrap_verified_seed
```

## Cost boundary

The physical Bootstrap Parquet is 36,240,684 bytes, which is larger than the existing 10 MiB Athena workgroup cutoff. That does not imply every columnar query will exceed the cutoff. The cutoff will not be raised for this proof; actual scan bytes will be measured.

## Current gate state

```text
NVD_2_3G_BOOTSTRAP_SEED_MANIFEST_VERSION_GATE=PASS
NVD_2_3G_BOOTSTRAP_SEED_MANIFEST_SHA256_GATE=PASS
NVD_2_3G_BOOTSTRAP_SEED_COMPLETE_GATE=PASS
NVD_2_3G_BOOTSTRAP_PROJECTION_SOURCE_VERSION_GATE=PASS
NVD_2_3G_BOOTSTRAP_PROJECTION_SOURCE_SHA256_GATE=PASS
NVD_2_3G_BOOTSTRAP_PROJECTION_SOURCE_SIZE_GATE=PASS
NVD_2_3G_BOOTSTRAP_PROJECTION_SOURCE_PARQUET_GATE=PASS
NVD_2_3G_BOOTSTRAP_PROJECTION_SOURCE_METADATA_GATE=PASS
NVD_2_3G_BOOTSTRAP_PROJECTION_DESTINATION_ABSENT_GATE=PASS

CopyObject exact-version gates: PENDING
Replay gate: PENDING
Athena direct-Parquet gates: PENDING
Cleanup gates: PENDING
```

Permanent Terraform/Lambda/Glue infrastructure remains deferred until this Bootstrap proof and the permanent AWS path are proven.
