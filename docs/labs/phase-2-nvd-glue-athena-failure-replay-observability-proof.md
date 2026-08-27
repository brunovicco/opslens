# Phase 2.3G.4K — Permanent NVD Analytics Failure / Replay / Observability Proof

Status: **COMPLETE**

## Objective

Close the permanent NVD analytics runtime with controlled production-like evidence for replay, fail-closed invocation handling, Lambda asynchronous retries, OnFailure delivery, bounded observability, and post-probe cleanup without mutating NVD Silver authority or manufacturing a new authoritative watermark.

4K is the final proof boundary of Phase 2.3G. It does not authorize GHSA ingestion or Phase 3 work.

## Permanent runtime boundary under test

```text
exact invocation authority
    -> strict inbound parser
    -> exact evidence loading
    -> deterministic destination key
    -> conditional CopyObject
    -> exact replay verification
    -> bounded telemetry
    -> asynchronous failure destination when execution is exhausted
```

Permanent Lambda:

```text
opslens-dev-nvd-analytics-projector
```

Permanent OnFailure queue:

```text
opslens-dev-nvd-analytics-projector-failures
```

Async policy remains:

```text
maximum_event_age_in_seconds=3600
maximum_retry_attempts=2
OnFailure=SQS
```

## Exact replay authority fixed for this proof

The already-projected 4I incremental authority is reused. No new source data is introduced.

```text
watermark key=control/nvd/cve/incremental/watermark.json
watermark VersionId=q9Zwn_4jdUZei_jqP6fytSy1aabtus7h
watermark size=1287
committed_through_at=2026-08-26T21:25:00Z
update_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
Silver Parquet VersionId=y.GQSur5eyHoW.pppIrGu3eW12xT.ber
Silver Parquet SHA-256=3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
analytics destination=analytics/nvd/cve/schema_version=1/source_kind=incremental/projection_date=2026-08-26/update_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc.parquet
analytics VersionId=qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl
analytics SHA-256=3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
```

The replay proof may invoke the same already-authorized S3 event shape manually, but it must not write the watermark, Silver, or analytics namespace directly.

## Replay contract under test

The S3 projection adapter uses `IfNoneMatch="*"`. An existing deterministic destination is not treated as success by assumption. HTTP 412 becomes an application-level replay-required signal, after which the current destination is read and its exact VersionId, metadata, size, SHA-256, and Parquet magic bytes are reverified against the authorized Silver source.

Expected replay result:

```text
status=already_projected
source_kind=incremental
source_batch_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
authority_state=watermark_committed
projection_date=2026-08-26
row_count=331
destination_version_id=qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl
destination_sha256=3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
```

A successful replay must leave the current destination VersionId unchanged.

## Observed replay proof — PASS

The deployed runtime was synchronously invoked with the exact already-authorized 4I S3 event coordinates. All replay gates passed:

```text
NVD_2_3G_4K_FAILURE_QUEUE_BASELINE=PASS
NVD_2_3G_4K_REPLAY_BASELINE=PASS
NVD_2_3G_4K_REPLAY_RESULT=PASS
NVD_2_3G_4K_REPLAY_VERSION_STABLE=PASS
NVD_2_3G_4K_REPLAY_OBSERVABILITY=PASS
```

Observed completion telemetry:

```text
request_id=60b0b3a0-1656-4f68-b0e4-29d862bfd2b6
status=already_projected
source_kind=incremental
source_batch_id=fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
projection_date=2026-08-26
row_count=331
destination_version_id=qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl
destination_sha256=3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
xray_trace_id=1-6a8f81eb-648ea14f0a7a5a73733fd7c4
```

The destination VersionId remained unchanged after replay. The runtime therefore treated the existing deterministic object as a replay only after exact current-object verification; it did not create a replacement version.

## Controlled fail-closed probe

The failure probe was intentionally rejected at the inbound parser before runtime dependency construction. It used an asynchronous Lambda invocation with a syntactically valid JSON payload that contained an otherwise valid Bootstrap coordinate plus one extra `probe_id` field.

The parser requires exactly:

```text
mode
silver_complete_key
silver_complete_version_id
```

Probe identifier:

```text
nvd-4k-invalid-e452b86441fd44f38ff8691886dd871a
```

The intentionally invalid `bootstrap_seed` payload was accepted by Lambda asynchronously with:

```text
StatusCode=202
NVD_2_3G_4K_INVALID_INVOCATION_ACCEPTED_ASYNC=PASS
```

After provider-managed retries, the configured SQS OnFailure destination received the matching event:

```text
MessageId=0fd52397-308d-4349-9b69-912d56c22fff
requestContext.requestId=d0c1cd4f-504c-4a2c-96e9-01e1bb638547
requestContext.condition=RetriesExhausted
requestContext.approximateInvokeCount=3
responseContext.executedVersion=$LATEST
responseContext.functionError=Unhandled
responsePayload.errorType=InvalidNvdAnalyticsProjectionInvocationError
```

The final error message was:

```text
NVD analytics bootstrap_seed must contain exactly mode, silver_complete_key, and silver_complete_version_id.
```

The OnFailure `requestPayload` retained the unique probe id and exact Bootstrap coordinates, proving that the message corresponded to the controlled test rather than an unrelated runtime failure.

Formal async-destination gate:

```text
NVD_2_3G_4K_ASYNC_ON_FAILURE=PASS
```

Operational note: while polling before the OnFailure message existed, AWS CLI returned no message payload and the local helper attempted to decode an empty file, producing `JSONDecodeError`. This was a local polling-script issue only; Lambda subsequently delivered the exact correlated OnFailure message.

## Fail-closed and observability proof — PASS

CloudWatch was queried from the controlled probe start time and returned three rejection records for the exact final asynchronous request id:

```text
request_id=d0c1cd4f-504c-4a2c-96e9-01e1bb638547
message=NVD analytics projection invocation rejected
exception_name=InvalidNvdAnalyticsProjectionInvocationError
xray_trace_id=1-6a8f8431-1bc07297442944da64cc7515
```

Observed rejection timestamps were approximately:

```text
2026-08-27T00:26:28Z
2026-08-27T00:27:28Z
2026-08-27T00:29:15Z
```

Each retained stack trace terminated at the strict inbound parser boundary:

```text
analytics_projection_lambda_handler.lambda_handler
    -> NvdAnalyticsProjectionInvocationParserV1.parse
    -> _parse_bootstrap_seed
    -> InvalidNvdAnalyticsProjectionInvocationError
```

For that request id the proof found no `Starting permanent NVD analytics projection`, no `Permanent NVD analytics projection completed`, and no runtime dependency initialization failure record. The invalid invocation therefore did not cross the projection execution boundary or initialize the projection runtime.

Formal gates:

```text
NVD_2_3G_4K_INVALID_INVOCATION_FAIL_CLOSED=PASS
NVD_2_3G_4K_FAILURE_OBSERVABILITY=PASS
```

## Queue cleanup — PASS

The OnFailure queue was empty before the controlled probe. After receiving and validating the exact controlled failure message, only that message was deleted using its receipt handle.

The queue then returned:

```text
ApproximateNumberOfMessages=0
ApproximateNumberOfMessagesNotVisible=0
ApproximateNumberOfMessagesDelayed=0
NVD_2_3G_4K_QUEUE_CLEANUP=PASS
```

Queue cleanup was operational evidence cleanup only and did not change NVD authority.

## Post-probe authority invariants — PASS

After replay, asynchronous retry exhaustion, SQS evidence capture, and cleanup, the exact permanent analytics evidence remained unchanged:

```text
Incremental analytics VersionId=qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl
Incremental ContentLength=205462
Incremental SHA-256=3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9

Bootstrap analytics VersionId=NzP5XmGl6yeMoQvmMv4JgCmixd_5N.ba
Bootstrap ContentLength=36240684
Bootstrap SHA-256=4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
```

The exact 4I authoritative watermark evidence also remained independently retrievable:

```text
VersionId=q9Zwn_4jdUZei_jqP6fytSy1aabtus7h
ContentLength=1287
```

The current authoritative watermark pointer is allowed to advance through the still-enabled scheduler; 4K requires the exact 4I evidence version and its downstream projection to remain verifiable, which they do.

Formal gate:

```text
NVD_2_3G_4K_AUTHORITY_INVARIANTS=PASS
```

## Gate state

```text
NVD_2_3G_4K_REPLAY_BASELINE=PASS
NVD_2_3G_4K_REPLAY_RESULT=PASS
NVD_2_3G_4K_REPLAY_VERSION_STABLE=PASS
NVD_2_3G_4K_REPLAY_OBSERVABILITY=PASS
NVD_2_3G_4K_FAILURE_QUEUE_BASELINE=PASS
NVD_2_3G_4K_INVALID_INVOCATION_ACCEPTED_ASYNC=PASS
NVD_2_3G_4K_INVALID_INVOCATION_FAIL_CLOSED=PASS
NVD_2_3G_4K_ASYNC_ON_FAILURE=PASS
NVD_2_3G_4K_FAILURE_OBSERVABILITY=PASS
NVD_2_3G_4K_QUEUE_CLEANUP=PASS
NVD_2_3G_4K_AUTHORITY_INVARIANTS=PASS
NVD_2_3G_4K=COMPLETE
```

## Completion boundary

4K is complete. Replay was verified without creating a new destination version; a controlled invalid asynchronous invocation was rejected before runtime construction; Lambda exhausted the configured retry budget and delivered the correlated event to SQS OnFailure; bounded CloudWatch/X-Ray evidence proved fail-closed behavior; the exact message was cleaned up; and pre-existing Bootstrap, Incremental, and exact watermark evidence remained unchanged.

The implementation and AWS evidence boundary of Phase 2.3G is therefore complete. The branch may now proceed to final repository review, quality gates, Terraform no-drift confirmation, and PR merge preparation. GHSA ingestion and Phase 3 are not implied by this closeout.
