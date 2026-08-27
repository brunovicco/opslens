# Legacy Lambda artifact lifecycle migration

Status: **IN PROGRESS**

## Objective

Remove the remaining local-build artifact lifecycle drift for the legacy OpsLens ingestion Lambdas without changing their data-plane behavior.

The affected functions are:

```text
opslens-dev-epss-ingestion
opslens-dev-kev-ingestion
opslens-dev-nvd-bootstrap-ingestion
```

The migration moves these functions from Terraform references to mutable local ZIP paths to the immutable deployment pattern already proven by newer OpsLens runtimes:

```text
deterministic build
    -> SHA-256
    -> content-addressed S3 key
    -> exact S3 VersionId
    -> Terraform immutable pin
```

## Why this migration exists

The final Phase 2.3G merge gate found a clean Bootstrap Terraform plan but a non-zero dev plan caused by legacy Lambda code hashes. The permanent NVD analytics projector and the other content-addressed runtimes remained converged.

The legacy ingestion Lambdas still use:

```hcl
filename         = <local dist ZIP>
source_code_hash = filebase64sha256(<local dist ZIP>)
```

That binds Terraform convergence to whichever ZIP happens to be rebuilt in the current environment.

The desired model instead binds Terraform to an exact, versioned artifact already present in the deployment bucket:

```hcl
s3_bucket         = <deployment artifact bucket>
s3_key            = "lambda/<runtime>/<sha256>.zip"
s3_object_version = <exact S3 VersionId>
source_code_hash  = <base64 SHA-256>
```

## Additional NVD Bootstrap boundary debt

The NVD Bootstrap builder historically copied the complete `opslens.ingestion.nvd` package. Later incremental-ingestion and watermark-promotion code was added under that package, so unrelated source changes could alter the Bootstrap ZIP hash.

Bootstrap is now narrowed to an explicit runtime source set containing only:

- Bootstrap Lambda handler and configuration;
- Bootstrap composition root;
- yearly-feed HTTP and S3 Bronze adapters;
- Bootstrap application contracts and service;
- yearly-feed domain models, META parsing, integrity verification, and source identity;
- shared observability required by the runtime.

Incremental and authoritative-watermark modules remain outside the Bootstrap artifact.

## Deployment-bucket retention precondition

The migration review found a second artifact-lifecycle inconsistency in the shared deployment bucket. The existing lifecycle configuration expired current objects under `lambda/` after 90 days and noncurrent versions after 30 days.

That is incompatible with repository-controlled Terraform resources that pin an exact content-addressed key and exact S3 VersionId: a valid deployment coordinate must not become unavailable merely because a fixed age threshold elapsed.

The branch therefore changes the bucket lifecycle contract to:

```text
current content-addressed Lambda object -> retained
noncurrent Lambda object version         -> eligible for cleanup after 30 days
incomplete multipart upload              -> abort after 7 days
```

Content-addressed uploads in this migration are write-once. A normal upload must use a conditional create so the same hash key is not overwritten and does not intentionally produce a noncurrent version.

This is a cross-cutting deployment-artifact safety correction. It does not migrate or alter the code of the newer Lambda runtimes.

## Scope

In scope:

```text
scripts/build_nvd_lambda_package.py
infra/environments/dev/artifacts.tf
infra/environments/dev/lambda.tf
infra/environments/dev/kev_lambda.tf
infra/environments/dev/nvd_bootstrap_lambda.tf
content-addressed uploads for the three legacy ingestion artifacts
exact Terraform artifact pins
real AWS readback and convergence proof
```

Out of scope:

```text
application behavior changes
runtime IAM widening
scheduler behavior changes
data-model changes
EPSS Silver artifact migration
KEV Silver artifact migration
NVD Silver / Incremental / Promotion / Analytics code-artifact migration
GHSA ingestion
Phase 3
```

The newer runtimes already use immutable versioned S3 artifact coordinates and are not code-migration targets here.

## Migration gates

### Gate A — package boundary — COMPLETE

NVD Bootstrap was built with the explicit runtime source set and checked against required and forbidden package members.

The proof returned:

```text
LEGACY_ARTIFACT_NVD_BOOTSTRAP_BOUNDARY=PASS
```

Examples confirmed absent include:

```text
opslens/ingestion/nvd/incremental_lambda_handler.py
opslens/ingestion/nvd/incremental_runtime_composition.py
opslens/ingestion/nvd/incremental_runtime_config.py
opslens/ingestion/nvd/application/authoritative_watermark.py
opslens/ingestion/nvd/application/incremental_service.py
opslens/ingestion/nvd/domain/api_page.py
opslens/ingestion/nvd/domain/incremental.py
opslens/ingestion/nvd/adapters/outbound/nvd_cve_api.py
opslens/ingestion/nvd/adapters/outbound/s3_authoritative_watermark.py
opslens/ingestion/nvd/adapters/outbound/s3_incremental_bronze.py
```

The Bootstrap handler and its required transitive application/runtime dependencies remained present.

### Gate B — deterministic local artifacts — COMPLETE

Each affected package was built twice from the same repository state. Both copies were compared by SHA-256, byte size, and `cmp`.

EPSS ingestion:

```text
sha256=6eee3ca9297b4f393afed6d15c28de39a684c05b64bdbb02d8916edb2f04d348
sha256_base64=bu48qSl7Tzk6/tbRXCjeOaaEwFtkvbsC2JFu2y8E00g=
bytes=17538328
LEGACY_ARTIFACT_EPSS_DETERMINISTIC=PASS
```

KEV ingestion:

```text
sha256=8c443677bfe292b6d8b99520b473e7318836dfad65e4a014c1b86cfce3044ef6
sha256_base64=jEQ2d7/ikrbYuZUgtHPnMYg2361l5KAUwbhs/OMETvY=
bytes=17538806
LEGACY_ARTIFACT_KEV_DETERMINISTIC=PASS
```

NVD Bootstrap ingestion:

```text
sha256=4baa4ddc3a3d841eb9c0ca77fe10a8796dcd9bd1a444df8b06ad5a55f23db74e
sha256_base64=S6pN3Do9hB65wMp3/hCoeW3Nm9GkRN+LBq1aVfI9t04=
bytes=17546498
LEGACY_ARTIFACT_NVD_BOOTSTRAP_DETERMINISTIC=PASS
```

Repository quality checks at this checkpoint also passed:

```text
uv run ruff check .   -> PASS
uv run pyright        -> 0 errors, 0 warnings, 0 informations
uv run pytest -q      -> PASS
git diff --check      -> PASS
git status --short    -> clean
```

### Gate C0 — durable deployment-artifact retention — IN PROGRESS

Before creating new immutable coordinates, the deployment bucket lifecycle must be applied so current content-addressed Lambda objects are no longer subject to fixed 90-day expiration.

Required proof:

```text
current lambda/* expiration absent
noncurrent_version_expiration = 30 days
abort incomplete multipart uploads = 7 days
```

The plan/apply must not replace or destroy the deployment bucket.

### Gate C — immutable artifact upload — PENDING

Upload each exact ZIP to the versioned deployment bucket with a content-addressed key:

```text
lambda/epss-ingestion/6eee3ca9297b4f393afed6d15c28de39a684c05b64bdbb02d8916edb2f04d348.zip
lambda/kev-ingestion/8c443677bfe292b6d8b99520b473e7318836dfad65e4a014c1b86cfce3044ef6.zip
lambda/nvd-bootstrap-ingestion/4baa4ddc3a3d841eb9c0ca77fe10a8796dcd9bd1a444df8b06ad5a55f23db74e.zip
```

Each upload must be write-once and must record and independently verify:

```text
key
VersionId
ContentLength
ETag
ChecksumSHA256
metadata.sha256
local SHA-256 == exact downloaded-version SHA-256
```

No Terraform Lambda pin is committed before these exact coordinates are known.

### Gate D — Terraform pinning — PENDING

Replace the three local `filename` references with exact S3 artifact coordinates and static base64 SHA-256 values.

The intended Terraform change surface is limited to the deployment-artifact lifecycle correction, the three ingestion Lambda code deployments, and any provider-derived scheduler policy readback caused solely by those Lambda updates.

No unrelated runtime, IAM, data, Glue, or analytics changes are accepted.

### Gate E — AWS deployment evidence — PENDING

After an approved plan and apply, read back the three Lambda configurations and verify their AWS `CodeSha256` values against the pinned artifacts.

Where safe and useful, execute a source-specific smoke/idempotency check without weakening the evidence model.

### Gate F — convergence — PENDING

The closeout requirement is a global dev plan with:

```text
No changes. Your infrastructure matches the configuration.
```

The migration is not complete until the legacy artifact exception identified during Phase 2.3G is gone.

## Current gate state

```text
LEGACY_ARTIFACT_NVD_BOOTSTRAP_BOUNDARY=PASS
LEGACY_ARTIFACT_EPSS_DETERMINISTIC=PASS
LEGACY_ARTIFACT_KEV_DETERMINISTIC=PASS
LEGACY_ARTIFACT_NVD_BOOTSTRAP_DETERMINISTIC=PASS
LEGACY_ARTIFACT_DEPLOYMENT_RETENTION=PENDING
LEGACY_ARTIFACT_EXACT_VERSION_UPLOAD=PENDING
LEGACY_ARTIFACT_TERRAFORM_PIN=PENDING
LEGACY_ARTIFACT_LAMBDA_READBACK=PENDING
LEGACY_ARTIFACT_NO_DRIFT=PENDING
LEGACY_ARTIFACT_MIGRATION=IN_PROGRESS
```

## Architectural result

After completion, all deployed OpsLens Lambda runtimes will use the same artifact lifecycle principle:

```text
build output is evidence
artifact identity is cryptographic
content-addressed current artifacts remain durable
S3 object version is exact deployment provenance
Terraform consumes immutable coordinates
rebuilding locally does not redefine deployed infrastructure
```

This is an infrastructure/deployment-lifecycle correction only. It does not change the project invariant:

> **Agents reason. Code verifies evidence.**
