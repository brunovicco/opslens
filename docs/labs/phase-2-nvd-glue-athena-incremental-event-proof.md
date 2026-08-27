# Phase 2.3G.4I — Permanent NVD Incremental Event Proof

Status: **COMPLETE**

## Objective

Prove the permanent incremental analytics path end to end from one legitimate authoritative watermark `s3:ObjectCreated:Put` event emitted by the normal OpsLens NVD pipeline.

The proof preserves the authority chain:

```text
incremental Bronze COMPLETE
    -> Silver COMPLETE
    -> watermark committed by Promotion
    -> S3 ObjectCreated:Put on the exact canonical watermark key
    -> analytics projector
    -> exact-VersionId Silver Parquet copy
    -> deterministic permanent incremental analytics object
```

No operator wrote, copied, replaced, or synthesized the authoritative watermark, and no manual analytics-projector invocation was used for the positive event-driven path.

## Trigger contract

The deployed bucket notification is bounded to:

```text
bucket=opslens-dev-data-487757851499-us-east-1
event=s3:ObjectCreated:Put
prefix=control/nvd/cve/incremental/
suffix=watermark.json
lambda=opslens-dev-nvd-analytics-projector
```

The inbound parser additionally requires the exact canonical object key:

```text
control/nvd/cve/incremental/watermark.json
```

and the S3 event record must carry the exact watermark `VersionId`.

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

The destination appeared four seconds after the legitimate authoritative watermark write.

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

## Event-delivery log correlation — PASS

CloudWatch logs after `NVD_4I_START_MS` contain eight records matching the new watermark VersionId or update id. They establish one correlated event-driven invocation:

```text
request_id=ea83a1dd-7284-4e27-82b8-729e5d6e94f3
xray_trace_id=1-6a8f59d3-7bba274262b6bc8d3bd9849a
cold_start=true
```

The first application record at `2026-08-26 21:25:54.293Z` states:

```text
message=Starting permanent NVD analytics projection
trigger_kind=incremental_watermark
watermark_key=control/nvd/cve/incremental/watermark.json
watermark_version_id=q9Zwn_4jdUZei_jqP6fytSy1aabtus7h
event_object_size_bytes=1287
```

The same X-Ray trace then read the exact watermark VersionId and exact Silver COMPLETE VersionId, copied the exact Silver Parquet VersionId, and verified the projected destination.

The completion record at `2026-08-26 21:25:54.562Z` states:

```text
message=Permanent NVD analytics projection completed
request_id=ea83a1dd-7284-4e27-82b8-729e5d6e94f3
status=projected
source_kind=incremental
source_batch_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
authority_state=watermark_committed
projection_date=2026-08-26
row_count=331
destination_version_id=qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl
destination_sha256=3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
```

The automated correlation assertion found the same request id in trigger and completion evidence:

```text
correlated_request_ids=['ea83a1dd-7284-4e27-82b8-729e5d6e94f3']
NVD_2_3G_4I_EVENT_LOG_CORRELATION=PASS
```

This closes the proof that the permanent object was created by the S3-triggered projector execution rather than by an operator-side action.

## Failure queue — PASS

The configured OnFailure queue was read after the successful event-driven projection:

```text
https://sqs.us-east-1.amazonaws.com/487757851499/opslens-dev-nvd-analytics-projector-failures
```

Observed queue counters:

```text
ApproximateNumberOfMessages=0
ApproximateNumberOfMessagesNotVisible=0
ApproximateNumberOfMessagesDelayed=0
NVD_2_3G_4I_FAILURE_QUEUE_EMPTY=PASS
```

No asynchronous failure was routed to the failure destination for the successful projection.

## Gate state

```text
NVD_2_3G_4I_BASELINE_WATERMARK=PASS
NVD_2_3G_4I_NEW_LEGITIMATE_WATERMARK=PASS
NVD_2_3G_4I_EVENT_DRIVEN_INVOCATION=PASS
NVD_2_3G_4I_DESTINATION_EXACT_VERSION=PASS
NVD_2_3G_4I_DESTINATION_SHA256=PASS
NVD_2_3G_4I_DESTINATION_METADATA=PASS
NVD_2_3G_4I_EVENT_LOG_CORRELATION=PASS
NVD_2_3G_4I_FAILURE_QUEUE_EMPTY=PASS
NVD_2_3G_4I=COMPLETE
```

## Conclusion

The permanent incremental path now proves, in real AWS execution:

```text
scheduled Incremental ingestion
    -> exact Silver COMPLETE
    -> Promotion commits exact authoritative watermark VersionId
    -> native S3 ObjectCreated:Put delivery
    -> strict projector trigger parsing
    -> exact watermark + Silver evidence reads
    -> exact-VersionId Silver Parquet CopyObject
    -> deterministic analytics destination
    -> exact destination VersionId/SHA/lineage verification
    -> correlated CloudWatch/X-Ray success
    -> empty OnFailure queue
```

The authority chain remained one-way. Analytics did not mutate the watermark, discover sources by prefix, or create Glue partitions.

## Next boundary

Phase 2.3G.4J will run permanent Athena queries over the clean analytics namespace, record per-query bytes scanned under the unchanged 10 MiB workgroup cutoff, and cross-check result and lineage semantics against the exact permanent Bootstrap and Incremental projections.
