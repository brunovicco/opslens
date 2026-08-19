# Phase 2.3B — NVD Bootstrap Bronze

## Status

COMPLETE

Validated on AWS in `us-east-1` on 2026-08-19 UTC.

## Objective

Phase 2.3B establishes an immutable Bronze bootstrap path for NVD CVE JSON 2.0 yearly feeds.

The implemented path is:

```text
NVD yearly-feed META
        |
        v
NVD yearly-feed GZ
        |
        v
bounded HTTP adapter
        |
        v
META contract validation
        |
        v
gzip size + decompression + source SHA-256 verification
        |
        v
deterministic source identity
        |
        v
conditional immutable S3 writes
        |
        +--> exact feed object
        +--> exact META object
        |
        v
completion manifest written last
```

This increment does not implement:

- incremental CVE API ingestion;
- watermark management;
- Silver transformation;
- Glue or Athena registration;
- GitHub Security Advisories;
- cross-source vulnerability correlation.

## Core invariant

> Agents reason. Code verifies evidence.

NVD source evidence is validated and persisted deterministically before any analytical or generative interpretation.

## AWS runtime

Lambda:

```text
function:      opslens-dev-nvd-bootstrap-ingestion
runtime:       python3.13
architecture:  x86_64
memory:        1024 MB
timeout:       180 seconds
tracing:       X-Ray Active
```

CloudWatch log group:

```text
/aws/lambda/opslens-dev-nvd-bootstrap-ingestion
retention: 14 days
```

The runtime IAM role is source-scoped.

S3 permissions:

```text
s3:GetObject
s3:PutObject
```

Resource:

```text
arn:aws:s3:::opslens-dev-data-487757851499-us-east-1/bronze/nvd/cve/bootstrap/*
```

The role does not receive `s3:ListBucket`, Glue, Athena, Scheduler, or broad S3 permissions.

## Source revision validated

Feed year:

```text
2026
```

Observed NVD META identity:

```text
lastModifiedDate: 2026-08-18T07:00:12Z
source SHA-256:   10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f
gzip bytes:       23938173
uncompressed:     282112001
```

Deterministic OpsLens feed revision:

```text
20260818T070012Z-10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f
```

## HTTP content-negotiation finding

The first real Lambda invocation reached the NVD service but failed closed:

```text
NvdSourceUnavailableError
NVD gzip source returned HTTP 406.
```

The adapter originally requested:

```http
Accept: application/octet-stream
```

A direct source probe demonstrated:

```text
Accept: application/octet-stream
HTTP status: 406
```

while:

```text
Accept: */*
HTTP status: 200
Content-Type: application/x-gzip
```

The adapter was corrected to use:

```http
Accept: */*
```

This does not weaken source integrity.

The downloaded bytes must still pass:

```text
gzip structure validation
        +
compressed size == META gzSize
        +
uncompressed size == META size
        +
SHA-256(uncompressed JSON) == META sha256
```

No Bronze evidence was written by the failed HTTP 406 invocation.

## First successful real ingestion

Invocation contract:

```json
{
  "feed_year": 2026
}
```

Lambda result:

```text
StatusCode:    200
FunctionError: null
```

The three Bronze objects were created successfully.

### Feed

Key:

```text
bronze/nvd/cve/bootstrap/feed_year=2026/feed_revision=20260818T070012Z-10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f/nvdcve-2.0-2026.json.gz
```

Evidence:

```text
size:       23938173
VersionId:  To7DT_5iOOGPGXn8ZcYjGUpL54lW65i8
object SHA: e3b48ac725eda895208fda77165d611e9a8d118304442e5b988c9108ded59739
```

### META

Key:

```text
bronze/nvd/cve/bootstrap/feed_year=2026/feed_revision=20260818T070012Z-10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f/nvdcve-2.0-2026.meta
```

Evidence:

```text
size:       168
VersionId:  B3.YI53rpiBEnHe8POj7cxsJs3gq4qHB
object SHA: fed969adf0692e84aaea70a2cd32c001b87841fddc7e1984396c437be3d38ae4
```

### Completion manifest

Key:

```text
bronze/nvd/cve/bootstrap/feed_year=2026/feed_revision=20260818T070012Z-10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f/manifest.json
```

Evidence:

```text
size:              1107
VersionId:         O9t9lPdkxd0GnvqZBBGU87mqRa5MrIRl
completion_status: complete
manifest_version:  1
```

The manifest is written only after the feed and META objects have been persisted successfully.

## Exact-version evidence binding

The persisted completion manifest references the exact immutable object versions:

```text
feed VersionId:
To7DT_5iOOGPGXn8ZcYjGUpL54lW65i8

META VersionId:
B3.YI53rpiBEnHe8POj7cxsJs3gq4qHB
```

The validation gate confirmed:

```text
NVD_COMPLETE_MANIFEST_BINDING_GATE=PASS
```

This means completion does not refer merely to logical S3 keys. It binds to the exact persisted versions that were observed and verified.

## Cryptographic evidence proof

The exact S3 object versions were downloaded independently after ingestion.

Observed hashes:

```text
feed gzip SHA-256:
e3b48ac725eda895208fda77165d611e9a8d118304442e5b988c9108ded59739

manifest feed SHA-256:
e3b48ac725eda895208fda77165d611e9a8d118304442e5b988c9108ded59739

META SHA-256:
fed969adf0692e84aaea70a2cd32c001b87841fddc7e1984396c437be3d38ae4

manifest META SHA-256:
fed969adf0692e84aaea70a2cd32c001b87841fddc7e1984396c437be3d38ae4

uncompressed JSON SHA-256:
10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f

NVD META source SHA-256:
10fb32c20bd6187fe43fa047d74772256f5b37c18029b17c5379a1f4e18f5d4f
```

Gate:

```text
NVD_REAL_CRYPTOGRAPHIC_EVIDENCE_GATE=PASS
```

Therefore:

```text
persisted gzip bytes
        ==
manifest gzip evidence

persisted META bytes
        ==
manifest META evidence

SHA-256(decompressed JSON)
        ==
NVD source SHA-256
```

## Idempotent replay

The same 2026 feed revision was invoked again.

The response returned:

```text
feed_status:     already_exists
meta_status:     already_exists
manifest_status: already_exists
```

The exact VersionIds remained:

```text
feed:
To7DT_5iOOGPGXn8ZcYjGUpL54lW65i8

META:
B3.YI53rpiBEnHe8POj7cxsJs3gq4qHB

manifest:
O9t9lPdkxd0GnvqZBBGU87mqRa5MrIRl
```

Gates:

```text
NVD_REPLAY_SAME_SOURCE_GATE=PASS
NVD_REAL_IDEMPOTENT_REPLAY_GATE=PASS
NVD_REPLAY_NO_NEW_OBJECT_VERSION_GATE=PASS
```

S3 object-version enumeration before and after replay was identical.

This proves that duplicate ingestion does not create additional logical evidence or additional S3 object versions.

## Conditional-write behavior

Bronze persistence uses conditional object creation.

Conceptually:

```text
PutObject
If-None-Match: *
        |
        +--> created
        |
        +--> 412
              |
              v
        HEAD existing object
              |
              v
        verify size + metadata evidence
              |
              v
        already_exists
```

An existing object is not trusted merely because its key exists.

The runtime verifies the expected stored evidence before returning `already_exists`.

## Observability

The successful create invocation emitted:

```text
NvdBootstrapIngestionInvocation = 1
NvdSourceFetchSuccess            = 2
NvdBronzeCreated                 = 3
NvdBootstrapIngestionSuccess     = 1
```

The replay emitted:

```text
NvdBootstrapIngestionInvocation = 1
NvdSourceFetchSuccess            = 2
NvdBronzeAlreadyExists           = 3
NvdBootstrapIngestionSuccess     = 1
```

Structured logs preserve source artifact type, payload size, object key, VersionId, status, request ID, and X-Ray trace correlation.

## Runtime measurements

First successful create:

```text
duration:        38480 ms
billed duration: 39410 ms
configured RAM:  1024 MB
max memory used: 125 MB
cold init:       ~930 ms
```

Observed idempotent replay:

```text
duration:        19927 ms
billed duration: 20850 ms
configured RAM:  1024 MB
max memory used: 126 MB
cold init:       ~923 ms
```

An overlapping invocation also completed successfully:

```text
duration:        84837 ms
max memory used: 138 MB
```

The source download dominates execution time and varies significantly with external network/source behavior.

For Phase 2.3B, the validated configuration remains:

```text
memory:  1024 MB
timeout: 180 seconds
```

No memory reduction is made from the observed low RAM usage because Lambda CPU allocation and network/runtime behavior must also be considered.

## Terraform proof

Initial infrastructure plan:

```text
Plan: 4 to add, 0 to change, 0 to destroy.
```

Created resources:

```text
aws_cloudwatch_log_group.nvd_bootstrap_ingestion
aws_iam_role.nvd_bootstrap_ingestion_lambda
aws_iam_role_policy.nvd_bootstrap_lambda_runtime
aws_lambda_function.nvd_bootstrap_ingestion
```

After the HTTP content-negotiation correction:

```text
Plan: 0 to add, 1 to change, 0 to destroy.
```

Only the NVD Lambda package changed.

Final convergence:

```text
No changes. Your infrastructure matches the configuration.
```

## Phase 2.3B validation gates

```text
NVD_SOURCE_INTEGRITY_GATE=PASS
NVD_BOOTSTRAP_SOURCE_IDENTITY_GATE=PASS
NVD_BOOTSTRAP_MANIFEST_GATE=PASS
NVD_HTTP_ADAPTER_GATE=PASS
NVD_BRONZE_REPOSITORY_GATE=PASS
NVD_MANIFEST_RETRY_DETERMINISM_GATE=PASS
NVD_BOOTSTRAP_APPLICATION_SERVICE_GATE=PASS
NVD_BOOTSTRAP_COMPOSITION_GATE=PASS
NVD_LAMBDA_RUNTIME_GATE=PASS
NVD_LAMBDA_ARTIFACT_DETERMINISM_GATE=PASS
NVD_TERRAFORM_PLAN_SCOPE_GATE=PASS
NVD_TERRAFORM_APPLY_GATE=PASS
NVD_TERRAFORM_CONVERGENCE_GATE=PASS
NVD_REAL_INVOCATION_GATE=PASS
NVD_COMPLETE_MANIFEST_BINDING_GATE=PASS
NVD_REAL_CRYPTOGRAPHIC_EVIDENCE_GATE=PASS
NVD_REAL_IDEMPOTENT_REPLAY_GATE=PASS
NVD_REPLAY_NO_NEW_OBJECT_VERSION_GATE=PASS
NVD_2_3B_GATE=PASS
```

## Result

Phase 2.3B establishes a real NVD Bootstrap Bronze implementation with:

- deterministic source revision identity;
- exact source integrity validation;
- immutable versioned S3 evidence;
- deterministic completion manifest;
- exact VersionId binding;
- conditional-write idempotency;
- replay without additional object versions;
- source-scoped IAM;
- structured logs, metrics, and X-Ray traces;
- Terraform-managed AWS runtime;
- successful real NVD source ingestion.

The next NVD increment is:

```text
Phase 2.3C — Incremental CVE API 2.0 + Watermark
```

Phase 2.3C must preserve the same evidence-first principles while introducing closed `lastModified` windows and deterministic watermark advancement.
