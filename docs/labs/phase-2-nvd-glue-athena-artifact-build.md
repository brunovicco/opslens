# Phase 2.3G — Permanent NVD Analytics Artifact Build

Status: **IN PROGRESS**

This checkpoint begins Phase 2.3G.4G after the permanent projector runtime and Glue catalog Terraform passed local formatting, validation, TFLint, and Checkov gates.

## Objective

Produce one immutable Lambda deployment package for the permanent NVD analytics projector, prove the package is deterministic, upload it under a content-addressed S3 key, pin the exact S3 VersionId and SHA-256 in Terraform, and only then permit Terraform plan/apply.

The deployment package is built by:

```text
scripts/build_nvd_analytics_projector_lambda_package.py
```

The generated artifact is:

```text
dist/opslens-nvd-analytics-projector.zip
```

Its permanent deployment key is content-addressed:

```text
lambda/nvd-analytics-projector/<artifact-sha256>.zip
```

## Build contract

The builder follows the same deterministic ZIP strategy used by the existing NVD runtimes:

- clean staging directory on every run;
- locked `uv` dependency export;
- Linux x86_64 Python 3.13 wheels;
- stable ZIP ordering;
- fixed ZIP timestamp;
- normalized POSIX permissions;
- removal of unrelated Lambda entrypoints;
- required runtime-file validation;
- Lambda uncompressed-size guard;
- SHA-256 in hexadecimal and Lambda-compatible base64 forms.

The analytics runtime currently imports the frozen NVD Silver schema and writer-contract modules while validating COMPLETE evidence. Those modules import PyArrow at module load time, so the package intentionally reuses the locked `nvd-silver-runtime` dependency group until those constants are separated into a lightweight contract module.

## Determinism gate

Build the package twice from the same checkout:

```bash
uv run python scripts/build_nvd_analytics_projector_lambda_package.py
```

The two runs must report identical values for:

```text
sha256
sha256_base64
compressed_bytes
uncompressed_bytes
files
artifact_s3_key
```

A mismatch blocks upload and Terraform deployment.

### Local determinism proof — COMPLETE

Two consecutive builds from commit `c2b41f3` produced byte-identical deployment evidence:

```text
artifact_s3_key=lambda/nvd-analytics-projector/6ae0bf3909744d6bb5e61390885fc469c18b93ef383bd4c2380fdc874de159cf.zip
sha256=6ae0bf3909744d6bb5e61390885fc469c18b93ef383bd4c2380fdc874de159cf
sha256_base64=auC/OQl0TWu15hOQiF/EacGLk+84O9TCOA/ch03hWc8=
files=3515
compressed_bytes=67502125
uncompressed_bytes=184846905
compressed_mib=64.38
uncompressed_mib=176.28
unzipped_limit_percent=70.51
requires_s3_upload=true
```

The selected determinism fields produced an empty `diff`, and an independent local `shasum -a 256` over `dist/opslens-nvd-analytics-projector.zip` returned the same SHA-256:

```text
6ae0bf3909744d6bb5e61390885fc469c18b93ef383bd4c2380fdc874de159cf
```

`git status --short` remained empty after both builds because local build artifacts are ignored. The deterministic-build gate is therefore complete. Upload remains blocked until this proof is recorded; it may now proceed using the exact content-addressed key above.

## Upload authority

The artifact bucket is the existing versioned deployment-artifacts bucket. The upload must use the exact content-addressed key reported by the builder.

After upload, record at minimum:

```text
bucket
key
VersionId
ETag
ContentLength
sha256
sha256_base64
```

Terraform must reference the exact S3 `VersionId`; an unversioned current-object reference is not acceptable.

## Terraform pinning gate

The projector Terraform currently requires three explicit artifact inputs:

```text
nvd_analytics_projector_artifact_sha256
nvd_analytics_projector_artifact_sha256_base64
nvd_analytics_projector_artifact_version
```

No `terraform plan` or `terraform apply` is authorized until the immutable artifact has been uploaded and these coordinates are pinned in repository-controlled Terraform configuration.

## Deployment sequence

The planned order is:

```text
1. deterministic local build proof          COMPLETE
2. exact versioned S3 artifact upload       NEXT
3. pin artifact SHA-256/base64/VersionId
4. bootstrap Terraform plan/apply for new deployment permissions
5. dev Terraform plan
6. dev Terraform apply
7. exact deployed Lambda configuration verification
```

This sequence preserves the repository invariant that code, deployment authority, and the exact immutable runtime artifact are all independently verifiable.
