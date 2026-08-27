# Phase 2.3G.4K — Permanent NVD Analytics Failure / Replay / Observability Proof

Status: **IN PROGRESS**

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

## Controlled fail-closed probe

The failure probe is intentionally rejected at the inbound parser before runtime dependency construction. It uses an asynchronous Lambda invocation with a syntactically JSON payload that contains an otherwise valid Bootstrap coordinate plus one extra field.

The parser requires exactly:

```text
mode
silver_complete_key
silver_complete_version_id
```

Therefore the extra probe field must cause `InvalidNvdAnalyticsProjectionInvocationError` before any authority object is loaded or any analytics object can be written.

The controlled probe must use `InvocationType=Event` so the deployed Lambda asynchronous retry policy and OnFailure destination are exercised. With `maximum_retry_attempts=2`, the expected runtime behavior is one initial failed attempt plus up to two retries before the event is delivered to the configured SQS OnFailure destination.

The proof must not relax retry settings or change the failure destination.

## Failure evidence to retain

Retain:

```text
asynchronous invoke StatusCode
probe start timestamp
CloudWatch rejection records after the probe start
OnFailure queue message body
Lambda async destination request/response context
request payload containing the unique probe id
final response error evidence
```

The exact retry timing is provider-managed; the proof should poll rather than assume fixed retry intervals.

## Observability gates

The handler emits bounded telemetry for:

```text
NvdAnalyticsProjectionInvocation
NvdAnalyticsProjectionSuccess
NvdAnalyticsProjected / NvdAnalyticsAlreadyProjected
NvdAnalyticsProjectionInvalidInvocation
NvdAnalyticsProjectionFailure
```

The replay proof must retain start/completion logs with the same request id and `status=already_projected`.

The controlled invalid invocation must retain at least the final `NVD analytics projection invocation rejected` record corresponding to the OnFailure delivery context. If the retry attempts are visible in the same query window, retain them as additional evidence rather than treating their exact count as a correctness dependency.

4I already proved event-driven success correlation through one Lambda request id and X-Ray trace. 4K complements that positive path with replay and negative-path evidence; it does not need to manufacture a new successful authority event.

## Queue cleanup

Before the controlled failure probe, the OnFailure queue must be confirmed empty.

After receiving and validating the controlled failure message, delete only that exact received message by its receipt handle. Then re-read the queue attributes until the visible, not-visible, and delayed counts return to zero.

Queue cleanup is operational evidence cleanup only. It does not change NVD authority.

## Post-probe authority invariants

After replay and failure probing:

```text
4I exact analytics destination VersionId remains qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl
4I exact analytics SHA-256 remains 3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
Bootstrap exact analytics VersionId remains NzP5XmGl6yeMoQvmMv4JgCmixd_5N.ba
Bootstrap exact analytics SHA-256 remains 4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
failure queue returns to empty after controlled evidence cleanup
```

The current authoritative watermark may legitimately advance because its scheduler remains enabled. 4K therefore does not require the current watermark pointer to stay on the 4I VersionId; it requires the exact 4I evidence version and its exact downstream projection to remain verifiable.

## Gate state

```text
NVD_2_3G_4K_REPLAY_BASELINE=PENDING
NVD_2_3G_4K_REPLAY_RESULT=PENDING
NVD_2_3G_4K_REPLAY_VERSION_STABLE=PENDING
NVD_2_3G_4K_REPLAY_OBSERVABILITY=PENDING
NVD_2_3G_4K_FAILURE_QUEUE_BASELINE=PENDING
NVD_2_3G_4K_INVALID_INVOCATION_ACCEPTED_ASYNC=PENDING
NVD_2_3G_4K_INVALID_INVOCATION_FAIL_CLOSED=PENDING
NVD_2_3G_4K_ASYNC_ON_FAILURE=PENDING
NVD_2_3G_4K_FAILURE_OBSERVABILITY=PENDING
NVD_2_3G_4K_QUEUE_CLEANUP=PENDING
NVD_2_3G_4K_AUTHORITY_INVARIANTS=PENDING
NVD_2_3G_4K=IN_PROGRESS
```

## Completion boundary

4K is complete only when replay is verified without a new destination version, the controlled invalid invocation is proven fail-closed, asynchronous failure handling reaches the deployed SQS destination, the failure message is correlated and then cleaned up, bounded telemetry is retained, and exact pre-existing analytics evidence remains unchanged.

After 4K completion, Phase 2.3G can enter final review/merge preparation. No subsequent phase is implied automatically.