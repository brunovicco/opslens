# Phase 2.3G.4H — Permanent NVD Bootstrap Seed Proof

Status: **COMPLETE**

## Objective

Project the already-verified historical NVD Bootstrap Silver batch into the permanent clean analytics namespace by invoking the deployed projector with one explicit exact `bootstrap_seed` request.

The proof preserves the authority distinction:

```text
silver_complete
    !=
bootstrap_verified_seed
    -> analytics_projected
```

Bootstrap was not discovered by prefix and was not automatically projected from every Silver COMPLETE event. The invocation carried the exact Silver COMPLETE key and VersionId already proven in Phase 2.3G.1B.

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
ETag="f236aec241d8ccd31549fc753efb657a"
ContentType=application/json
```

The exact Silver COMPLETE VersionId was re-read immediately before projection. Its independently downloaded bytes hashed to the same SHA-256, so the seed authority was revalidated before any analytics write.

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

The feed revision timestamp encodes `2026-08-22`, so the application key contract required exactly:

```text
analytics/nvd/cve/schema_version=1/source_kind=bootstrap/projection_date=2026-08-22/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68.parquet
```

A preflight `HeadObject` on this exact key returned `404 Not Found`, proving that the first invocation was not relying on a pre-existing destination.

## First permanent projection — PASS

The deployed Lambda was invoked synchronously with exactly:

```json
{
  "mode": "bootstrap_seed",
  "silver_complete_key": "silver/nvd/cve/schema_version=1/source_kind=bootstrap/feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68/manifest.json",
  "silver_complete_version_id": "hP32acLaaZue6equWWX6PJVvcsu7RUOR"
}
```

AWS returned `StatusCode=200`. The application response was:

```text
request_id=5e5e3ccc-ff6f-4119-9ba9-e1865c01415f
status=projected
source_kind=bootstrap
source_batch_id=feed_year=2026/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68
authority_state=bootstrap_verified_seed
projection_date=2026-08-22
row_count=48293
destination_key=analytics/nvd/cve/schema_version=1/source_kind=bootstrap/projection_date=2026-08-22/feed_revision=20260822T070013Z-f10b8dc5388f72172740b476be73ca9e24ab6834aa502ff9cbb3a733973d6d68.parquet
destination_version_id=NzP5XmGl6yeMoQvmMv4JgCmixd_5N.ba
destination_sha256=4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
```

The response contract assertions passed:

```text
NVD_2_3G_4H_FIRST_PROJECTION=PASS
```

## Exact destination evidence — PASS

An exact `HeadObject` using destination VersionId `NzP5XmGl6yeMoQvmMv4JgCmixd_5N.ba` returned:

```text
ContentLength=36240684
ContentType=application/vnd.apache.parquet
ETag="814a5a7c420d6900206409c361f9b025"
```

Exact lineage metadata:

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

The exact destination VersionId was downloaded independently. Verification returned:

```text
SHA-256=4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
size_bytes=36240684
leading_magic=PAR1
trailing_magic=PAR1
NVD_2_3G_4H_DESTINATION_BYTES=PASS
```

The projected bytes therefore match the exact authorized Silver Parquet identity.

## Replay proof — PASS

The identical `bootstrap_seed` invocation was executed again. AWS returned `StatusCode=200`, and the application response was:

```text
request_id=603f1dec-e05a-4ef0-945a-2f5c87b2c1a9
status=already_projected
destination_version_id=NzP5XmGl6yeMoQvmMv4JgCmixd_5N.ba
destination_sha256=4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
```

The replay assertion passed:

```text
NVD_2_3G_4H_REPLAY=PASS
```

A current-object `HeadObject` after replay still returned exactly:

```text
VersionId=NzP5XmGl6yeMoQvmMv4JgCmixd_5N.ba
```

No replacement current version was created. The conditional-write collision was accepted only after exact verification of the already-projected destination.

## Gate state

```text
NVD_2_3G_4H_SOURCE_EXACT_COMPLETE=PASS
NVD_2_3G_4H_DESTINATION_ABSENT=PASS
NVD_2_3G_4H_FIRST_PROJECTION=PASS
NVD_2_3G_4H_DESTINATION_EXACT_VERSION=PASS
NVD_2_3G_4H_DESTINATION_SHA256=PASS
NVD_2_3G_4H_DESTINATION_METADATA=PASS
NVD_2_3G_4H_REPLAY_EXACT_VERIFICATION=PASS
NVD_2_3G_4H=COMPLETE
```

## Conclusion

The permanent Bootstrap path now proves:

```text
exact verified Silver COMPLETE
    -> explicit bootstrap_verified_seed authority
    -> exact-VersionId Silver Parquet CopyObject
    -> deterministic clean analytics key
    -> exact destination VersionId/SHA/metadata verification
    -> idempotent replay without replacement
```

The runtime did not mutate the authoritative watermark, use prefix discovery, or require Glue partition writes.

## Next boundary

Phase 2.3G.4I will prove the event-driven incremental path from a legitimate authoritative watermark `ObjectCreated:Put` event into the permanent analytics namespace. The proof must use a watermark produced by the normal NVD Incremental -> Silver -> Promotion pipeline rather than writing or replacing the authoritative watermark manually.
