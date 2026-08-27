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

The migration will move these functions from Terraform references to mutable local ZIP paths to the immutable deployment pattern already proven by newer OpsLens runtimes:

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

Bootstrap is now being narrowed to an explicit runtime source set containing only:

- Bootstrap Lambda handler and configuration;
- Bootstrap composition root;
- yearly-feed HTTP and S3 Bronze adapters;
- Bootstrap application contracts and service;
- yearly-feed domain models, META parsing, integrity verification, and source identity;
- shared observability required by the runtime.

Incremental and authoritative-watermark modules remain outside the Bootstrap artifact.

## Scope

In scope:

```text
scripts/build_nvd_lambda_package.py
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
NVD Silver / Incremental / Promotion / Analytics artifact migration
GHSA ingestion
Phase 3
```

The newer runtimes already use immutable versioned S3 artifact coordinates and are not part of this migration.

## Migration gates

### Gate A — package boundary

Build NVD Bootstrap with the explicit runtime source set and prove that unrelated incremental/watermark modules are absent from the ZIP.

Expected examples of excluded source:

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

The Bootstrap handler and all of its transitive application/runtime dependencies must remain present.

### Gate B — deterministic local artifacts

Build each affected package twice from the same repository state:

```text
EPSS ingestion
KEV ingestion
NVD Bootstrap ingestion
```

For each runtime:

```text
SHA256_BUILD_1 == SHA256_BUILD_2
SIZE_BUILD_1   == SIZE_BUILD_2
```

### Gate C — immutable artifact upload

Upload each exact ZIP to the versioned deployment bucket with a content-addressed key:

```text
lambda/epss-ingestion/<sha256>.zip
lambda/kev-ingestion/<sha256>.zip
lambda/nvd-bootstrap-ingestion/<sha256>.zip
```

Record and independently verify:

```text
key
VersionId
ContentLength
ETag
SHA-256
```

No Terraform pin is committed before these exact coordinates are known.

### Gate D — Terraform pinning

Replace the three local `filename` references with exact S3 artifact coordinates and static base64 SHA-256 values.

The intended Terraform change surface is limited to the three ingestion Lambda code deployments and any provider-derived scheduler policy readback caused solely by those Lambda updates.

No unrelated runtime, IAM, data, Glue, or analytics changes are accepted.

### Gate E — AWS deployment evidence

After an approved plan and apply, read back the three Lambda configurations and verify their AWS `CodeSha256` values against the pinned artifacts.

Where safe and useful, execute a source-specific smoke/idempotency check without weakening the evidence model.

### Gate F — convergence

The closeout requirement is a global dev plan with:

```text
No changes. Your infrastructure matches the configuration.
```

The migration is not complete until the legacy artifact exception identified during Phase 2.3G is gone.

## Architectural result

After completion, all deployed OpsLens Lambda runtimes will use the same artifact lifecycle principle:

```text
build output is evidence
artifact identity is cryptographic
S3 object version is exact deployment provenance
Terraform consumes immutable coordinates
rebuilding locally does not redefine deployed infrastructure
```

This is an infrastructure/deployment-lifecycle correction only. It does not change the project invariant:

> **Agents reason. Code verifies evidence.**
