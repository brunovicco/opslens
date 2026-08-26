# Phase 2.3G.4H — Permanent NVD Bootstrap Seed Proof

Status: **IN PROGRESS**

## Objective

Project the already-verified historical NVD Bootstrap Silver batch into the permanent clean analytics namespace by invoking the deployed projector with one explicit exact `bootstrap_seed` request.

This proof must preserve the authority distinction:

```text
silver_complete
    !=
bootstrap_verified_seed
    -> analytics_projected
```

Bootstrap is not discovered by prefix and is not automatically projected from every Silver COMPLETE event. The invocation carries the exact Silver COMPLETE key and VersionId already proven in Phase 2.3G.1B.

## Exact authorized Bootstrap source

```text
feed_year=2026
feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68
```

Exact Silver COMPLETE:

```text
key=silver/nvd/cve/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68/manifest.json
VersionId=hP32acLaaZue6equWWX6PJVvcsu7RUOR
SHA-256=f7148c19d7b0ee0d7c3073c48ca18425dd97da0f85d9e2a0368ea5263e0ed31d
size_bytes=1947
```

The COMPLETE manifest names the exact source Parquet:

```text
key=silver/nvd/cve/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68/part-00000.parquet
VersionId=ucv9W1GLmaYj00PdvYp3CSBC_fPoETP_
SHA-256=4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
size_bytes=36240684
row_count=48293
logical_record_set_sha256=a88f20256dc00827091ebaee312f5208cc45459a33caa877be1b6b84ee30377a
```

## Deterministic permanent destination

The feed revision timestamp encodes `2026-08-22`, so the application key contract requires exactly:

```text
analytics/nvd/cve/schema_version=1/source_kind=bootstrap/projection_date=2026-08-22/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68.parquet
```

Expected permanent lineage metadata:

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

## Proof sequence

The 4H operator proof is intentionally exact and does not use `ListBucket` or prefix discovery:

```text
1. re-read exact source COMPLETE VersionId
2. confirm deterministic destination does not already exist
3. invoke deployed Lambda with exact bootstrap_seed coordinates
4. require status=projected and exact expected lineage fields
5. read exact destination VersionId returned by Lambda
6. verify destination size/content type/metadata
7. download exact destination VersionId and independently verify SHA-256 + PAR1
8. invoke the identical bootstrap_seed request again
9. require status=already_projected with the same exact destination VersionId/SHA
10. confirm replay created no replacement current version
```

The runtime itself performs exact COMPLETE validation, exact source-Parquet coordinate validation, structured `CopySource={Bucket, Key, VersionId}`, conditional `IfNoneMatch="*"`, `CopySourceVersionId` verification, and exact destination byte/SHA/metadata verification before returning success.

## Expected first invocation result

```text
status=projected
source_kind=bootstrap
source_batch_id=feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68
authority_state=bootstrap_verified_seed
projection_date=2026-08-22
row_count=48293
destination_key=analytics/nvd/cve/schema_version=1/source_kind=bootstrap/projection_date=2026-08-22/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68.parquet
destination_sha256=4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
```

`destination_version_id` is assigned by S3 and must be captured from the Lambda response.

## Expected replay result

The second identical invocation must not overwrite or replace the deterministic destination. A conditional-write collision is accepted only after exact verification of the already-current destination:

```text
status=already_projected
destination_version_id=<same exact VersionId as first invocation>
destination_sha256=4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
```

## Gate state

```text
NVD_2_3G_4H_SOURCE_EXACT_COMPLETE=PENDING
NVD_2_3G_4H_DESTINATION_ABSENT=PENDING
NVD_2_3G_4H_FIRST_PROJECTION=PENDING
NVD_2_3G_4H_DESTINATION_EXACT_VERSION=PENDING
NVD_2_3G_4H_DESTINATION_SHA256=PENDING
NVD_2_3G_4H_DESTINATION_METADATA=PENDING
NVD_2_3G_4H_REPLAY_EXACT_VERIFICATION=PENDING
NVD_2_3G_4H=IN_PROGRESS
```

## Next boundary

After 4H is complete, Phase 2.3G.4I will prove the event-driven incremental path from an authoritative watermark `ObjectCreated:Put` event into the same permanent analytics namespace. 4H does not mutate the authoritative watermark and does not start Athena validation; permanent Athena query/cost/lineage proof remains Phase 2.3G.4J.
