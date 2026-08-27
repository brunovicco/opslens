# Phase 2.3G.3C — Bootstrap Exact-Version Projection Proof

## Status

IN PROGRESS — exact Bootstrap source evidence and exact-version S3 projection materialization are complete. Ordinary-Parquet Athena validation under the unchanged 10 MiB workgroup cutoff is next.

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

## Exact-version CopyObject materialization

The source was passed to S3 as the logical, unescaped copy source with the exact source VersionId:

```text
opslens-dev-data-487757851499-us-east-1/silver/nvd/cve/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68/part-00000.parquet?versionId=ucv9W1GLmaYj00PdvYp3CSBC_fPoETP_
```

The deterministic destination was written with `If-None-Match: *` and explicit replacement metadata.

Successful S3 response:

```text
CopySourceVersionId:
ucv9W1GLmaYj00PdvYp3CSBC_fPoETP_

destination VersionId:
3MQ4Yx_EfGR01vYOt1dxoQtAn746VID5

ETag:
"814a5a7c420d6900206409c361f9b025"

ServerSideEncryption:
AES256
```

Formal copy gates:

```text
NVD_2_3G_BOOTSTRAP_EXACT_COPY_REQUEST=PASS
NVD_2_3G_BOOTSTRAP_COPY_RESPONSE_GATE=PASS
NVD_2_3G_BOOTSTRAP_COPY_SOURCE_VERSION_GATE=PASS
NVD_2_3G_BOOTSTRAP_DESTINATION_VERSION_GATE=PASS
```

The critical authority assertion passed: `CopySourceVersionId` exactly matched the previously verified Bootstrap Silver Parquet VersionId.

## Projected object exact verification

The projected object was re-opened by exact destination VersionId:

```text
VersionId:
3MQ4Yx_EfGR01vYOt1dxoQtAn746VID5

SHA-256:
4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541

ContentLength:
36240684

ContentType:
application/vnd.apache.parquet

ServerSideEncryption:
AES256
```

The exact destination bytes independently reproduced the source SHA-256 and leading/trailing `PAR1` magic.

Projected metadata:

```text
dataset=nvd_cve_versions
schema_version=1
source_kind=bootstrap
source_batch_id=feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68
row_count=48293
parquet_sha256=4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
authority_source_key=silver/nvd/cve/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68/part-00000.parquet
authority_source_version_id=ucv9W1GLmaYj00PdvYp3CSBC_fPoETP_
authority_source_sha256=4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
authority_state=bootstrap_verified_seed
```

Formal destination gates:

```text
NVD_2_3G_BOOTSTRAP_DESTINATION_VERSION_VERIFY=PASS
NVD_2_3G_BOOTSTRAP_DESTINATION_SHA256_GATE=PASS
NVD_2_3G_BOOTSTRAP_DESTINATION_SIZE_GATE=PASS
NVD_2_3G_BOOTSTRAP_CONTENT_LENGTH_GATE=PASS
NVD_2_3G_BOOTSTRAP_CONTENT_TYPE_GATE=PASS
NVD_2_3G_BOOTSTRAP_DESTINATION_PARQUET_GATE=PASS
NVD_2_3G_BOOTSTRAP_DESTINATION_METADATA_GATE=PASS
```

## Replay/idempotency proof

The exact same conditional copy was replayed against the deterministic destination. S3 returned:

```text
PreconditionFailed
```

The destination was then re-read without a VersionId and remained:

```text
3MQ4Yx_EfGR01vYOt1dxoQtAn746VID5
```

Therefore the failed replay did not create a new current version.

Formal replay gates:

```text
NVD_2_3G_BOOTSTRAP_PROJECTION_REPLAY_GATE=PASS
NVD_2_3G_BOOTSTRAP_REPLAY_VERSION_STABILITY_GATE=PASS
```

## Operational note

The first attempted source revalidation command failed because the local AWS SSO token had expired. `aws sso login --profile opslens-bootstrap` succeeded, and the exact evidence was then re-read successfully. No data-plane mutation occurred during the expired-token failure.

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
NVD_2_3G_BOOTSTRAP_EXACT_COPY_REQUEST=PASS
NVD_2_3G_BOOTSTRAP_COPY_RESPONSE_GATE=PASS
NVD_2_3G_BOOTSTRAP_COPY_SOURCE_VERSION_GATE=PASS
NVD_2_3G_BOOTSTRAP_DESTINATION_VERSION_GATE=PASS
NVD_2_3G_BOOTSTRAP_DESTINATION_VERSION_VERIFY=PASS
NVD_2_3G_BOOTSTRAP_DESTINATION_SHA256_GATE=PASS
NVD_2_3G_BOOTSTRAP_DESTINATION_SIZE_GATE=PASS
NVD_2_3G_BOOTSTRAP_DESTINATION_PARQUET_GATE=PASS
NVD_2_3G_BOOTSTRAP_DESTINATION_METADATA_GATE=PASS
NVD_2_3G_BOOTSTRAP_PROJECTION_REPLAY_GATE=PASS
NVD_2_3G_BOOTSTRAP_REPLAY_VERSION_STABILITY_GATE=PASS

Athena direct-Parquet gates: PENDING
Cleanup gates: PENDING
```

## Next proof step

Use the still-present exact Bootstrap projection for a temporary ordinary Parquet Athena table. The test must preserve the existing 10 MiB workgroup cutoff and distinguish successful bounded columnar queries from any query rejected by the cutoff. No cutoff increase is authorized by this proof.

Permanent Terraform/Lambda/Glue infrastructure remains deferred until the Bootstrap Athena proof and the permanent AWS path are proven.
