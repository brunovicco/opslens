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

## Baseline capture

Before the next legitimate run, record the current canonical watermark identity:

```bash
aws s3api head-object \
  --bucket "$DATA_BUCKET" \
  --key control/nvd/cve/incremental/watermark.json \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" \
  --query '{VersionId:VersionId,ETag:ETag,ContentLength:ContentLength,LastModified:LastModified}' \
  --output json
```

Also capture proof start time in epoch milliseconds for later CloudWatch filtering:

```bash
export NVD_4I_START_MS="$(( $(date +%s) * 1000 ))"
echo "NVD_4I_START_MS=$NVD_4I_START_MS"
```

## Legitimate event requirement

The authoritative watermark VersionId must advance because the normal Promotion Lambda commits a new eligible incremental batch. A manually written duplicate watermark is not acceptable evidence.

The existing scheduler cadence remains the source of the incremental run. The proof may wait for the next scheduled execution rather than force an authority mutation.

## New watermark evidence

After the pipeline advances, capture the new exact watermark VersionId and download that exact version. The proof must establish:

```text
new_watermark_version_id != baseline_watermark_version_id
commit_basis.type = silver_complete_promotion
update_id = exact committed incremental batch id
committed_through_at = exact committed authority timestamp
silver_manifest.key/version_id/sha256 = exact Silver COMPLETE authority
silver_parquet.key/version_id/sha256 = exact Silver Parquet authority
```

The deterministic permanent destination is then:

```text
analytics/nvd/cve/schema_version=1/source_kind=incremental/projection_date=<UTC YYYY-MM-DD from committed_through_at>/update_id=<update_id>.parquet
```

## Destination proof

The destination must appear without a manual projector invocation. Its lineage metadata must equal the exact committed Silver authority:

```text
dataset=nvd_cve_versions
schema_version=1
source_kind=incremental
source_batch_id=<update_id>
row_count=<Silver row_count>
parquet_sha256=<exact Silver Parquet SHA-256>
authority_source_key=<exact Silver Parquet key>
authority_source_version_id=<exact Silver Parquet VersionId>
authority_source_sha256=<exact Silver Parquet SHA-256>
authority_state=watermark_committed
```

The destination bytes must hash to the exact Silver Parquet SHA-256 and begin/end with `PAR1`.

## Event-delivery evidence

CloudWatch evidence after `NVD_4I_START_MS` must show a successful incremental projector invocation for the new authority. At minimum the logs must establish the new watermark/update identity and `status=projected` (or `already_projected` only if an independently explained prior exact projection exists; that is not expected for the first legitimate post-deployment event).

The SQS OnFailure queue should remain empty after the successful event-driven projection.

## Gate state

```text
NVD_2_3G_4I_BASELINE_WATERMARK=PENDING
NVD_2_3G_4I_NEW_LEGITIMATE_WATERMARK=PENDING
NVD_2_3G_4I_EVENT_DRIVEN_INVOCATION=PENDING
NVD_2_3G_4I_DESTINATION_EXACT_VERSION=PENDING
NVD_2_3G_4I_DESTINATION_SHA256=PENDING
NVD_2_3G_4I_DESTINATION_METADATA=PENDING
NVD_2_3G_4I_EVENT_LOG_CORRELATION=PENDING
NVD_2_3G_4I_FAILURE_QUEUE_EMPTY=PENDING
NVD_2_3G_4I=IN_PROGRESS
```

## Next boundary

After 4I is complete, Phase 2.3G.4J will run permanent Athena queries over the clean analytics prefix, record bytes scanned under the existing 10 MiB workgroup cutoff, and cross-check result/lineage semantics against the exact projected Bootstrap and Incremental evidence.
