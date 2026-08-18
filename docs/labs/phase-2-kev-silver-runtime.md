# Phase 2 Lab — CISA KEV Bronze-to-Silver Runtime Validation

## Purpose

Validate the first CISA KEV Bronze-to-Silver path in AWS with deterministic
evidence verification, idempotent writes, source-specific IAM, operational
telemetry, asynchronous retries, and an SQS OnFailure destination.

This lab proves the invariant:

> Agents reason. Code verifies evidence.

No model participates in KEV status, source validation, normalization,
idempotency, or failure handling.

## Scope

The validated path is:

```text
CISA KEV
    ↓
EventBridge Scheduler
    ↓
opslens-dev-kev-ingestion
    ↓
S3 Bronze JSON
    ↓
S3 ObjectCreated:Put
    ↓
opslens-dev-kev-silver
    ↓
exact Bronze VersionId read
    ↓
transport + provenance verification
    ↓
deterministic normalization
    ↓
explicit Arrow schema
    ↓
Parquet serialization
    ↓
conditional S3 Silver create
```

Failure path:

```text
KEV Silver function error
    ↓
Lambda asynchronous retry policy
    ↓
2 retries / 3 total attempts
    ↓
SQS OnFailure invocation record
```

Glue/Athena registration of the KEV Silver dataset is intentionally outside
this lab and is the next Phase 2 increment.

## AWS resources

- Region: `us-east-1`
- Account: `487757851499`
- Data bucket: `opslens-dev-data-487757851499-us-east-1`
- Artifact bucket: `opslens-dev-artifacts-487757851499-us-east-1`
- KEV ingestion Lambda: `opslens-dev-kev-ingestion`
- KEV Silver Lambda: `opslens-dev-kev-silver`
- KEV Silver failure queue: `opslens-dev-kev-silver-failures`
- KEV Silver log group: `/aws/lambda/opslens-dev-kev-silver`

The KEV Silver Lambda uses Python 3.13 on `x86_64`, 1024 MB memory, a 60-second
timeout, active X-Ray tracing, JSON logging, and AWS Lambda Powertools metrics.

## Storage contract

Bronze:

```text
bronze/kev/snapshot_date=YYYY-MM-DD/known_exploited_vulnerabilities.json
```

Silver:

```text
silver/kev/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

The Silver artifact contains 16 physical Parquet columns. `snapshot_date` is
represented by the S3 partition path.

```text
cve
vendor_project
product
vulnerability_name
date_added
short_description
required_action
due_date
known_ransomware_campaign_use
notes
cwes
catalog_version
catalog_date_released
source
source_sha256
retrieved_at
```

## Validated Bronze evidence

Snapshot:

```text
snapshot_date:
2026-08-17

catalog_version:
2026.08.14

key:
bronze/kev/snapshot_date=2026-08-17/known_exploited_vulnerabilities.json

VersionId:
yIjPm4kDS_qmI0xRVaVh8kLyc7QBIhNr

ETag:
4d6ebe76c67bfe50649db3de0ebc1d6a

size:
1583171 bytes

record_count:
1665

SHA-256:
52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79

source:
cisa-kev

retrieved_at:
2026-08-17T03:52:03.692159Z

date_released:
2026-08-14T16:34:49.039100Z
```

## Deterministic validation rules

The runtime does not trust the notification event as sufficient evidence.

For each accepted KEV Bronze event it:

1. validates the S3 event envelope;
2. requires the expected bucket and canonical KEV Bronze key;
3. requires a positive size, ETag, and exact `VersionId`;
4. reads the exact version with `s3:GetObjectVersion`;
5. verifies response bucket/key/version/ETag/size against the event;
6. verifies required Bronze metadata;
7. verifies payload SHA-256 and metadata/body provenance;
8. validates the KEV source contract;
9. rejects duplicate CVEs;
10. rejects unsupported ransomware campaign values;
11. normalizes CVE/CWE syntax deterministically;
12. serializes with an explicit Arrow schema;
13. creates the deterministic Silver key conditionally.

Additive fields in the upstream CISA payload may be ignored until explicitly
adopted, but changes to required semantics fail closed.

## Deployment artifact

The KEV Silver runtime package is built for the Lambda Linux/Python 3.13 x86_64
runtime and includes PyArrow.

Validated package:

```text
artifact:
dist/opslens-kev-silver.zip

SHA-256:
91f6034c678f30f0ed5aae0f81c011e5f1748a82b2cb179f010f69f7d21dfc5f

compressed bytes:
67364972

uncompressed bytes:
184284722

PyArrow:
25.0.1
```

Because the package exceeds the direct Lambda ZIP upload threshold, it is
published to the deployment artifact bucket and the Lambda deployment is
pinned to the versioned S3 artifact.

Published artifact:

```text
bucket:
opslens-dev-artifacts-487757851499-us-east-1

key:
lambda/kev-silver/91f6034c678f30f0ed5aae0f81c011e5f1748a82b2cb179f010f69f7d21dfc5f.zip

VersionId:
rKKEb2QL2VeCeD8Kts0AnTxdSz2y3VPi
```

The official Lambda Python 3.13 `linux/amd64` container was used to validate
native imports before deployment.

## IAM boundary

The KEV Silver runtime role is `OpsLensKevSilverLambdaRole`.

Its data-plane permissions are intentionally narrow:

```text
s3:GetObjectVersion
    arn:aws:s3:::opslens-dev-data-487757851499-us-east-1/bronze/kev/*

s3:PutObject
    arn:aws:s3:::opslens-dev-data-487757851499-us-east-1/silver/kev/*

sqs:SendMessage
    exact KEV Silver failure queue

CloudWatch Logs
    exact KEV Silver log group

X-Ray
    PutTraceSegments / PutTelemetryRecords
```

The role does not need `s3:ListBucket`, unversioned `s3:GetObject`, broad S3
wildcards, or SQS receive/delete/purge permissions.

The Lambda resource policy grants `s3.amazonaws.com` permission to invoke only
from the OpsLens data bucket and the same AWS account.

## S3 event wiring

The data bucket has one Terraform-managed S3 notification configuration. Both
Silver consumers coexist in that configuration.

```text
EPSS:
event:  s3:ObjectCreated:*
prefix: bronze/epss/

KEV:
event:  s3:ObjectCreated:Put
prefix: bronze/kev/
suffix: known_exploited_vulnerabilities.json
```

Keeping both Lambda destinations in the same bucket notification resource
prevents competing Terraform resources from overwriting one another.

The KEV prefix and Silver output prefix are different, so the Silver write does
not recursively invoke itself.

## First real Bronze-to-Silver execution

A real S3-shaped event referencing the canonical Bronze object version was
invoked synchronously before automatic event wiring was enabled.

Result:

```json
{
  "processed_records": 1,
  "created_records": 1,
  "already_exists_records": 0,
  "records": [
    {
      "bronze_version_id": "yIjPm4kDS_qmI0xRVaVh8kLyc7QBIhNr",
      "silver_key": "silver/kev/snapshot_date=2026-08-17/part-00000.parquet",
      "snapshot_date": "2026-08-17",
      "row_count": 1665,
      "size_bytes": 257331,
      "schema_version": 1,
      "source_sha256": "52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79",
      "status": "created"
    }
  ]
}
```

Persisted Silver evidence:

```text
key:
silver/kev/snapshot_date=2026-08-17/part-00000.parquet

VersionId:
IVVrgnUdo40wi1Ye4qmylr4XnlNtmGAp

ETag:
9043910f295bc882e6ec9321643f8424

size:
257331 bytes

content type:
application/vnd.apache.parquet

server-side encryption:
AES256
```

The S3 object metadata preserved Bronze lineage including the Bronze ETag,
Bronze VersionId, source SHA-256, row count, schema version, catalog version,
release timestamp, source, and retrieval timestamp.

## Persisted Parquet cross-check

The exact Silver object version was downloaded from S3 and inspected locally
with PyArrow.

Result:

```text
rows=1665
columns=16
row_groups=1
source_values={'cisa-kev'}
source_sha_values={'52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79'}
known_ransomware=349
unknown_ransomware=1316
empty_cwes=171

KEV_SILVER_C7C2C_PARQUET_CONTENT_GATE=PASS
```

This verifies the bytes actually persisted in AWS rather than only the Lambda
return value.

## Idempotent replay

The same event was replayed without modifying any input evidence.

Result:

```text
processed_records=1
created_records=0
already_exists_records=1
status=already_exists
```

The Silver repository uses:

```text
PutObject
If-None-Match: *
```

S3 returned HTTP `412` because the deterministic Silver key already existed.
The application treats this as a safe duplicate rather than a failure.

Because the bucket is versioned, idempotency was verified using object versions,
not merely key count.

```text
versions_before=1
versions_after=1
version_id_before=IVVrgnUdo40wi1Ye4qmylr4XnlNtmGAp
version_id_after=IVVrgnUdo40wi1Ye4qmylr4XnlNtmGAp

KEV_SILVER_C7C2B_IDEMPOTENT_VERSION_GATE=PASS
```

The replay therefore did not create a hidden second object version.

## Runtime observability

The first real transformation emitted structured application logs, Powertools
EMF metrics, X-Ray trace context, and Lambda platform telemetry.

First real run:

```text
cold_start=true
memory configured=1024 MB
maxMemoryUsedMB=176
durationMs=795.365
billedDurationMs=2112
initDurationMs=1316.493
status=success
```

Warm idempotent replay:

```text
cold_start=false
memory configured=1024 MB
maxMemoryUsedMB=194
durationMs=595.405
billedDurationMs=596
status=success
```

Key emitted metrics include:

```text
KevSilverTransformationInvocation
KevSilverNotificationRecords
KevSilverBronzeReadBytes
KevSilverCreated
KevSilverAlreadyExists
KevSilverTransformationSuccess
KevSilverTransformationCreatedRecords
KevSilverTransformationAlreadyExistsRecords
KevSilverBronzeEvidenceMismatch
KevSilverTransformationFailure
```

Although the measured memory suggests that 512 MB may be feasible, the
function remains at 1024 MB until at least one natural daily S3-triggered run is
observed. Right-sizing is an optimization step, not a correctness change.

## Asynchronous failure policy

The effective Lambda asynchronous configuration is:

```text
MaximumRetryAttempts=2
MaximumEventAgeInSeconds=3600
OnFailure=arn:aws:sqs:us-east-1:487757851499:opslens-dev-kev-silver-failures
```

The failure queue was empty before the deliberate failure lab.

## Deliberate fail-closed experiment

The test reused the exact valid Bronze key and VersionId but replaced the event
ETag with:

```text
00000000000000000000000000000000
```

The event remained parser-valid and was submitted with asynchronous Lambda
invocation.

Submission result:

```text
StatusCode=202
```

The exact S3 version could still be read. The deterministic transport evidence
check then compared the real S3 ETag with the event ETag and raised:

```text
KevBronzeEvidenceMismatchError:
S3 response ETag does not match the triggering event.
```

This is intentionally non-retryable from a domain perspective, but Lambda's
configured asynchronous function-error policy still exercised the platform
retry path for the operational lab.

Observed attempts:

```text
attempt 1: 2026-08-18T14:33:04Z
attempt 2: 2026-08-18T14:33:59Z
attempt 3: 2026-08-18T14:35:59Z
```

The OnFailure destination received the invocation record:

```text
condition=RetriesExhausted
approximateInvokeCount=3
functionError=Unhandled
errorType=KevBronzeEvidenceMismatchError
requestId=410791bc-75a4-4aed-bf3d-3e571ea9ec09
```

The request payload preserved the wrong ETag and the exact Bronze VersionId,
allowing the failure to be diagnosed from retained evidence.

## No-write-on-failure proof

The deliberate failure occurred before Silver persistence.

The versioned-bucket comparison proved:

```text
versions_before=1
versions_after=1
version_before=IVVrgnUdo40wi1Ye4qmylr4XnlNtmGAp
version_after=IVVrgnUdo40wi1Ye4qmylr4XnlNtmGAp

KEV_SILVER_C7C3C_NO_WRITE_ON_FAILURE_GATE=PASS
```

The lab SQS message was then explicitly deleted and the queue was returned to
its empty operational baseline.

## Cost evidence

Measured Lambda compute from the validated success, replay, and deliberate
failure experiments was:

```text
first real run:         2.112 GB-s
warm idempotent replay: 0.596 GB-s
failure attempt 1:      1.581 GB-s
failure attempt 2:      0.411 GB-s
failure attempt 3:      0.291 GB-s
---------------------------------
total measured:         4.991 GB-s
```

Using the AWS Lambda x86 first-tier reference price of
`USD 0.0000166667 / GB-s`, the measured compute is approximately:

```text
USD 0.00008318 before free tier and request charges
```

This is evidence for the lab workload only, not a forecast for future traffic.
Pricing is time-sensitive and must be revalidated before later cost claims.

## Terraform convergence

After event wiring, async failure configuration, deliberate failure validation,
and queue cleanup, Terraform was run with `-detailed-exitcode`.

Result:

```text
No changes.
final_plan_exit=0
KEV_SILVER_C7_FINAL_TERRAFORM_CONVERGENCE_GATE=PASS
```

## Key gates

```text
PHASE_2_2C7A_ARTIFACT_BUILD_GATE=PASS
PHASE_2_2C7A_PACKAGE_ISOLATION_GATE=PASS
PHASE_2_2C7A_DETERMINISTIC_ARTIFACT_GATE=PASS
PHASE_2_2C7A_LINUX_RUNTIME_IMPORT_GATE=PASS
PHASE_2_2C7C2B_CREATED_GATE=PASS
PHASE_2_2C7C2B_IDEMPOTENT_REPLAY_GATE=PASS
PHASE_2_2C7C2B_NO_EXTRA_VERSION_GATE=PASS
PHASE_2_2C7C2C_PARQUET_CONTENT_GATE=PASS
PHASE_2_2C7C3A_EXACT_PLAN_GATE=PASS
PHASE_2_2C7C3A_EFFECTIVE_ASYNC_CONFIG_GATE=PASS
PHASE_2_2C7C3B_EPSS_PRESERVATION_GATE=PASS
PHASE_2_2C7C3B_KEV_NOTIFICATION_GATE=PASS
PHASE_2_2C7C3B_LAMBDA_PERMISSION_GATE=PASS
PHASE_2_2C7C3C_FAILURE_EVENT_GATE=PASS
PHASE_2_2C7C3C_RETRY_EXHAUSTION_GATE=PASS
PHASE_2_2C7C3C_ONFAILURE_SQS_GATE=PASS
PHASE_2_2C7C3C_NO_WRITE_ON_FAILURE_GATE=PASS
PHASE_2_2C7_FINAL_TERRAFORM_CONVERGENCE_GATE=PASS
```

## AIP-C01 learning outcomes

This increment exercises several Professional-level concepts in one concrete
path.

### Domain 2 — Implementation and Integration

- S3 event-driven Lambda integration;
- Lambda asynchronous invocation behavior;
- retries and idempotent consumers;
- SQS OnFailure destination;
- deployment packaging with native dependencies;
- Terraform-managed event wiring.

### Domain 3 — AI Safety, Security, and Governance

- least-privilege IAM;
- exact resource scoping;
- version-pinned source evidence;
- fail-closed validation;
- preservation of diagnostic evidence without granting broad runtime authority.

### Domain 4 — Operational Efficiency and Optimization

- measured Lambda duration and memory;
- serverless/on-demand execution;
- bounded failure retries;
- measured GB-second consumption;
- explicit future right-sizing candidate rather than premature tuning.

### Domain 5 — Testing, Validation, and Troubleshooting

- real success path;
- real idempotent replay;
- persisted-byte cross-check;
- deliberate evidence mismatch;
- CloudWatch/Powertools/X-Ray inspection;
- OnFailure invocation-record analysis;
- Terraform post-apply convergence.

## Conclusion

The CISA KEV Bronze-to-Silver path is operational and fail-closed.

The validated architecture demonstrates:

```text
immutable source evidence
    + exact version reads
    + deterministic validation
    + deterministic normalization
    + idempotent version-safe persistence
    + least-privilege IAM
    + structured telemetry
    + bounded async retries
    + retained failure evidence
```

The first naturally scheduled S3 event after notification wiring remains a
non-blocking operational observation. No synthetic Bronze object is required to
close this lab because the runtime success path, idempotency, event wiring,
retry policy, OnFailure delivery, failure isolation, and Terraform convergence
have already been demonstrated.

The next implementation step is CISA KEV Glue/Athena registration and a
reproducible analytical query proving KEV membership for a specific CVE.
