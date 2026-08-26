# Phase 2.3G.4I — Permanent NVD Incremental Event Proof

Status: **IN PROGRESS**

## Objective

Prove the permanent incremental analytics path end to end from one legitimate authoritative watermark `s3:ObjectCreated:Put` event emitted by the normal OpsLens NVD pipeline.

The proof must preserve the authority chain:

```text
incremental Bronze COMPLETE
    -> Silver COMPLETE
    -> watermark committed by Promotion
    -> S3 ObjectCreated:Put on the exact canonical watermark key
    -> analytics projector
    -> exact-VersionId Silver Parquet copy
    -> deterministic permanent incremental analytics object
```

No operator may write, copy, replace, or otherwise synthesize the authoritative watermark for this proof. The event must result from the normal Incremental -> Silver -> Promotion pipeline.

## Trigger contract

The deployed bucket notification is bounded to:

```text
bucket=opslens-dev-data-487757851499-us-east-1
event=s3:ObjectCreated:Put
prefix=control/nvd/cve/incremental/
suffix=watermark.json
lambda=opslens-dev-nvd-analytics-projector
```

The inbound parser still requires the exact canonical object key:

```text
control/nvd/cve/incremental/watermark.json
```

and requires the S3 event record to carry the exact watermark `VersionId`.

## Proof strategy

The operator proof must not invoke the projector manually for the positive event-driven path.

```text
1. capture the current watermark exact VersionId as the baseline
2. capture a wall-clock proof start time
3. allow the normal scheduled NVD incremental pipeline to run
4. wait until the canonical watermark has a different VersionId
5. download and parse that exact new watermark VersionId
6. require silver_complete_promotion authority and capture its exact update_id / Silver references
7. derive the deterministic analytics destination from committed_through_at + update_id
8. verify that destination exists without a manual projector invocation
9. verify exact destination VersionId, SHA-256, size, Parquet magic, and lineage metadata against the new watermark authority
10. inspect projector logs after the proof start time for an incremental success tied to the new watermark VersionId/update_id
11. confirm the projector failure queue remains empty for the successful event
```

## Baseline watermark — PASS

The deployed scheduler was confirmed enabled with the normal production cadence:

```text
State=ENABLED
ScheduleExpression=cron(25 1/2 * * ? *)
FlexibleTimeWindow=OFF
```

Before the next legitimate run, the canonical watermark baseline was captured as:

```text
VersionId=FO2HAgT5Mw0fp8E_ekAmxMxjJRa2S8F5
ETag="908650e2ffed9a099e43429592d0d387"
ContentLength=1287
LastModified=2026-08-26T19:25:51+00:00
NVD_4I_START_MS=1787778931000
```

No operator write or manual projector invocation was used after this baseline.

## Legitimate watermark advancement — PASS

The next normal scheduled pipeline run advanced the canonical watermark to:

```text
VersionId=q9Zwn_4jdUZei_jqP6fytSy1aabtus7h
ETag="585e24ae73cefc28c9bf478486b8dee3"
ContentLength=1287
LastModified=2026-08-26T21:25:51+00:00
```

The exact new watermark VersionId was downloaded and parsed. It established:

```text
state=committed
committed_through_at=2026-08-26T21:25:00Z
commit_basis.kind=silver_complete_promotion
previous_committed_through_at=2026-08-26T19:25:00Z
update_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
logical_record_set_sha256=8e63ff4cefecea51de3ef95d42f46cca8de65e3475e7657947a665e408e70b57
```

Exact Silver COMPLETE authority:

```text
key=silver/nvd/cve/schema_version=1/source_kind=incremental/update_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc/manifest.json
VersionId=3nskcyqawvgzJ00YPkxSobnrFyuBxxz.
SHA-256=3c4efeba56f1f0d2fd6f10215ef1c06cfd9c88f4239df3efa83baa1aaf1ded94
completion_status=complete
source_kind=incremental
source_batch_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
```

Exact Silver Parquet authority:

```text
key=silver/nvd/cve/schema_version=1/source_kind=incremental/update_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc/part-00000.parquet
VersionId=y.GQSur5eyHoW.pppIrGu3eW12xT.ber
SHA-256=3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
row_count=331
size_bytes=205462
```

## Deterministic event-driven destination — PASS

From the exact committed authority, the application key contract requires:

```text
analytics/nvd/cve/schema_version=1/source_kind=incremental/projection_date=2026-08-26/update_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc.parquet
```

Without any manual projector invocation, this destination existed at:

```text
VersionId=qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl
ETag="4968a280a2cd485bbcc7f68703968fd6"
ContentLength=205462
ContentType=application/vnd.apache.parquet
LastModified=2026-08-26T21:25:55+00:00
```

The destination appeared four seconds after the legitimate authoritative watermark write, consistent with the deployed S3 event-driven projection path.

Exact lineage metadata:

```text
dataset=nvd_cve_versions
schema_version=1
source_kind=incremental
source_batch_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
row_count=331
parquet_sha256=3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
authority_source_key=silver/nvd/cve/schema_version=1/source_kind=incremental/update_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc/part-00000.parquet
authority_source_version_id=y.GQSur5eyHoW.pppIrGu3eW12xT.ber
authority_source_sha256=3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
authority_state=watermark_committed
```

The exact destination VersionId was downloaded independently. Verification returned:

```text
SHA-256=3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
size_bytes=205462
leading_magic=PAR1
trailing_magic=PAR1
NVD_2_3G_4I_DESTINATION_BYTES=PASS
```

The projected bytes therefore match the exact Silver Parquet authority.

## Event-delivery evidence — PENDING

CloudWatch evidence after `NVD_4I_START_MS=1787778931000` must still show a successful incremental projector invocation for the new authority, correlated to watermark VersionId `q9Zwn_4jdUZei_jqP6fytSy1aabtus7h` and update id `fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc`.

The SQS OnFailure queue must also remain empty for this successful event-driven projection.

## Gate state

```text
NVD_2_3G_4I_BASELINE_WATERMARK=PASS
NVD_2_3G_4I_NEW_LEGITIMATE_WATERMARK=PASS
NVD_2_3G_4I_EVENT_DRIVEN_INVOCATION=PASS
NVD_2_3G_4I_DESTINATION_EXACT_VERSION=PASS
NVD_2_3G_4I_DESTINATION_SHA256=PASS
NVD_2_3G_4I_DESTINATION_METADATA=PASS
NVD_2_3G_4I_EVENT_LOG_CORRELATION=PENDING
NVD_2_3G_4I_FAILURE_QUEUE_EMPTY=PENDING
NVD_2_3G_4I=IN_PROGRESS
```

## Next boundary

After log correlation and failure-queue verification complete 4I, Phase 2.3G.4J will run permanent Athena queries over the clean analytics prefix, record bytes scanned under the existing 10 MiB workgroup cutoff, and cross-check result/lineage semantics against the exact projected Bootstrap and Incremental evidence.
