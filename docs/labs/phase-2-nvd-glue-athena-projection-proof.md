# Phase 2.3G.3A — Exact-Version NVD Analytics Projection Proof

## Status

COMPLETE — exact-version server-side materialization passed for the committed incremental NVD Silver Parquet.

## Purpose

Prove that OpsLens can turn authoritative Silver evidence bound to an exact S3 `VersionId` and SHA-256 into a clean, append-only analytics Parquet object without weakening the evidence chain.

The downstream state remains:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

`analytics_projected` is not an authority source and cannot advance the watermark.

## Authoritative source

Historical authoritative watermark:

```text
key:
control/nvd/cve/incremental/watermark.json

VersionId:
S8GnyKJhDlfvmsWs3gbl9Zg8JWnQio2o

committed_through_at:
2026-08-25T23:25:00Z

update_id:
65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e
```

The watermark commit basis named the exact Silver Parquet:

```text
key:
silver/nvd/cve/schema_version=1/source_kind=incremental/update_id=65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e/part-00000.parquet

VersionId:
f.L5xLSzp1eabl4R9VA8ebt6ReWEp9cm

SHA-256:
d95c409ef20d787632f45419a436855d0cd3d543704fe5b189af32025ad2fac8

size_bytes:
4724916

row_count:
6749
```

The exact source version was re-read before projection and independently verified.

Results:

```text
NVD_2_3G_PROJECTION_WATERMARK_STATE=PASS
NVD_2_3G_PROJECTION_WATERMARK_BASIS=PASS
NVD_2_3G_PROJECTION_UPDATE_ID=PASS
NVD_2_3G_PROJECTION_SOURCE_KEY=PASS
NVD_2_3G_PROJECTION_SOURCE_VERSION_REFERENCE=PASS
NVD_2_3G_PROJECTION_SOURCE_SHA_REFERENCE=PASS
NVD_2_3G_PROJECTION_SOURCE_VERSION_GATE=PASS
NVD_2_3G_PROJECTION_SOURCE_SHA256_GATE=PASS
NVD_2_3G_PROJECTION_SOURCE_SIZE_GATE=PASS
```

## Destination absence

Temporary deterministic destination:

```text
analytics-spike/nvd/cve/exact-projection/schema_version=1/source_kind=incremental/update_id=65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e/part-00000.parquet
```

`HeadObject` returned `404 Not Found` before creation.

Result:

```text
NVD_2_3G_PROJECTION_DESTINATION_ABSENT_GATE=PASS
NVD_2_3G_PROJECTION_DESTINATION_RECHECK=PASS
```

## CopySource encoding finding

The first CLI attempt pre-URL-encoded the S3 key before passing it to `aws s3api copy-object`. That produced:

```text
NoSuchVersion
The specified version doesnot exist.
```

The source version itself was valid. The failure was caused by double handling of the copy-source key encoding.

The corrected CLI copy source was passed as the unescaped logical value:

```text
opslens-dev-data-487757851499-us-east-1/silver/nvd/cve/schema_version=1/source_kind=incremental/update_id=65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e/part-00000.parquet?versionId=f.L5xLSzp1eabl4R9VA8ebt6ReWEp9cm
```

The future boto3/botocore adapter should not hand-build this encoded string. It should use the structured source form:

```python
CopySource={
    "Bucket": source_bucket,
    "Key": source_key,
    "VersionId": source_version_id,
}
```

This keeps exact-version intent explicit and delegates request encoding to the AWS SDK.

## Exact CopyObject evidence

The corrected conditional server-side copy succeeded:

```text
CopySourceVersionId:
f.L5xLSzp1eabl4R9VA8ebt6ReWEp9cm

Destination VersionId:
A29.Nmc0IQUFAmxsNLAk9hLiG7ETLY42

ServerSideEncryption:
AES256

ETag:
"564a395e01442f3a2fca8fe48837a550"
```

The S3 response itself therefore proves that the exact authoritative source version was copied.

Results:

```text
NVD_2_3G_EXACT_COPY_REQUEST=PASS
NVD_2_3G_COPY_RESPONSE_GATE=PASS
NVD_2_3G_COPY_SOURCE_VERSION_GATE=PASS
NVD_2_3G_PROJECTION_DESTINATION_VERSION_GATE=PASS
```

## Destination evidence

The exact destination `VersionId` was read and independently downloaded.

Observed:

```text
VersionId:
A29.Nmc0IQUFAmxsNLAk9hLiG7ETLY42

ContentLength:
4724916

ContentType:
application/vnd.apache.parquet

ServerSideEncryption:
AES256

SHA-256:
d95c409ef20d787632f45419a436855d0cd3d543704fe5b189af32025ad2fac8
```

The projected bytes retained valid Parquet leading/trailing `PAR1` magic.

The projected object SHA-256 exactly equals the authoritative Silver source SHA-256.

Bounded lineage metadata persisted:

```text
dataset=nvd_cve_versions
schema_version=1
source_kind=incremental
source_batch_id=65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e
row_count=6749
parquet_sha256=d95c409ef20d787632f45419a436855d0cd3d543704fe5b189af32025ad2fac8
authority_source_key=silver/nvd/cve/schema_version=1/source_kind=incremental/update_id=65e286bda04b0447d71c869e15c31f8ac27621dc86362bcc3bdf79fc0d78bb0e/part-00000.parquet
authority_source_version_id=f.L5xLSzp1eabl4R9VA8ebt6ReWEp9cm
authority_source_sha256=d95c409ef20d787632f45419a436855d0cd3d543704fe5b189af32025ad2fac8
authority_state=watermark_committed
```

Results:

```text
NVD_2_3G_PROJECTION_DESTINATION_VERSION_VERIFY=PASS
NVD_2_3G_PROJECTION_DESTINATION_SHA256_GATE=PASS
NVD_2_3G_PROJECTION_DESTINATION_SIZE_GATE=PASS
NVD_2_3G_PROJECTION_CONTENT_LENGTH_GATE=PASS
NVD_2_3G_PROJECTION_CONTENT_TYPE_GATE=PASS
NVD_2_3G_PROJECTION_DESTINATION_PARQUET_GATE=PASS
NVD_2_3G_PROJECTION_METADATA_GATE=PASS
```

## Replay behavior

The exact same conditional `CopyObject` was replayed against the deterministic destination key.

Observed:

```text
PreconditionFailed
At least one of the pre-conditions you specified did not hold
```

The CLI returned non-zero and the gate required that specific conditional failure class.

After replay, a current `HeadObject` still resolved to:

```text
A29.Nmc0IQUFAmxsNLAk9hLiG7ETLY42
```

No second current destination version replaced the proven object.

Results:

```text
NVD_2_3G_PROJECTION_REPLAY_GATE=PASS
NVD_2_3G_PROJECTION_REPLAY_VERSION_STABILITY_GATE=PASS
```

## Result

The exact-version materialization concept is proven for the committed incremental batch:

```text
historical committed watermark
    -> exact Silver key + VersionId + SHA-256
    -> CopyObject exact source version
    -> CopySourceVersionId verified
    -> new versioned analytics object
    -> identical SHA-256
    -> bounded lineage metadata
    -> deterministic replay rejected
```

This closes Phase 2.3G.3A.

## Next boundary

The temporary projected object remains intentionally present for Phase 2.3G.3B.

Next:

```text
normal Parquet Athena table
    -> clean exact-projection prefix
    -> primitive + nested-type queries
    -> PyArrow cross-check
    -> measured scan bytes / latency
    -> cleanup temporary table and exact projection version
```

Only after direct Athena compatibility passes should the same exact-version projection pattern be repeated for the verified Bootstrap seed and then promoted into permanent Terraform/runtime infrastructure.
