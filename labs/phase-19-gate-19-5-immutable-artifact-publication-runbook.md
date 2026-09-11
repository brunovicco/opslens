# Phase 19 — Gate 19.5 Immutable Async Artifact Publication Runbook

## Status

**HUMAN-ONLY boundary. Do not run from CI or ChatGPT.**

This runbook exists only to publish the two already-admitted, content-addressed Lambda ZIP artifacts required to obtain immutable Amazon S3 `VersionId` coordinates for Gate 19.6 exact Terraform planning.

It does **not** authorize Terraform apply, IAM changes, runtime resource creation/update/delete, public endpoint enablement, or provider-heavy workload execution.

## Frozen target

```text
AWS account: 487757851499
Region:      us-east-1
bucket:      opslens-dev-artifacts-487757851499-us-east-1
bucket use:  existing versioned deployment-artifacts bucket
```

Only two keys admitted by the canonical Gate 19.5 pre-publication manifest may be written. Keys are content-addressed by the exact ZIP SHA-256.

## Why publication precedes the exact runtime plan

Gate 19.4 deliberately requires each Lambda resource to receive:

```text
S3 key
S3 VersionId
Lambda source_code_hash
```

An S3 `VersionId` does not exist until the object exists. Gate 19.5 therefore permits one narrowly scoped precursor mutation: create-only publication of the two frozen deployment artifacts. Gate 19.6 owns the first Terraform plan that may set `public_async_runtime_materialized=true` using those exact immutable coordinates.

Publication success is not deployment authority.

## Preconditions

Before publication, all of the following must hold:

1. Gate 19.5 deterministic artifact build verifier is green on the exact reviewed PR head.
2. The canonical pre-publication manifest exists at:

   `labs/evidence/phase-19-gate-19-5-prepublication-v1.json`

3. Local rebuild output exactly matches that manifest.
4. The local Git worktree is clean.
5. The existing human AWS profile resolves to account `487757851499` in `us-east-1`.
6. No IAM change is made to enable this operation. If the existing human authority cannot write the two objects, stop.
7. No prior publication evidence is silently overwritten.

## Build the exact local artifacts

From the reviewed Gate 19.5 branch or protected merge commit:

```bash
rm -rf /tmp/opslens-gate19-5-artifacts

uv run python scripts/build_phase19_async_lambda_artifacts.py \
  --output-root /tmp/opslens-gate19-5-artifacts
```

Compare the generated manifest byte-for-byte with the canonical repository manifest:

```bash
cmp \
  /tmp/opslens-gate19-5-artifacts/dist/phase-19-gate-19-5-prepublication-manifest.json \
  labs/evidence/phase-19-gate-19-5-prepublication-v1.json
```

A nonzero result is a hard stop. Do not publish.

## Publication semantics

The publisher uses:

```text
PutObject
If-None-Match: *
SDK total_max_attempts: 1
```

Amazon S3 conditional writes with `If-None-Match: *` reject creation when the same current key already exists. If the exact key already exists, the publisher admits it only after exact size/metadata and immutable-version byte verification; it does not overwrite it.

A `409 ConditionalRequestConflict` or `412 PreconditionFailed` is a hard stop for this runbook. **Do not retry automatically.** Inspect the existing immutable state first.

Reference behavior is documented by AWS under S3 conditional writes / `PutObject` `If-None-Match`.

## HUMAN-ONLY publication command

The human operator chooses an already-authorized existing profile. The project has historically used `opslens-bootstrap` for lab administration; this runbook does not grant or broaden that authority.

```bash
PYTHONPATH=src uv run python \
  scripts/publish_phase19_gate19_5_async_artifacts.py \
  --manifest labs/evidence/phase-19-gate-19-5-prepublication-v1.json \
  --artifact-root /tmp/opslens-gate19-5-artifacts \
  --profile opslens-bootstrap \
  --region us-east-1 \
  --output /tmp/opslens-gate19-5-artifact-publication-v1.json \
  --confirm I_UNDERSTAND_THIS_WRITES_EXACTLY_TWO_CREATE_ONLY_S3_OBJECTS
```

This is the only command in this runbook that may mutate AWS state.

## Required result

A successful first publication should produce two admitted entries with:

```text
publication_status: CREATED
bucket: exact frozen deployment bucket
key: exact content-addressed key
version_id: non-empty immutable S3 VersionId
verified_sha256: exact local artifact SHA-256
verified_bytes: exact local ZIP byte count
```

If an exact content-addressed object already exists from a previously successful human attempt, `EXISTING_EXACT` may be admitted without another write.

The evidence root must retain:

```text
automatic_retry_count:              0
runtime_resource_mutation_count:    0
iam_mutation_count:                 0
terraform_apply_count:              0
public_endpoint_enablement_count:   0
```

## Offline post-publication admission

After successful publication, verify the persisted evidence locally without any provider call:

```bash
PYTHONPATH=src uv run python \
  scripts/verify_phase19_gate19_5_artifact_publication.py \
  --prepublication labs/evidence/phase-19-gate-19-5-prepublication-v1.json \
  --publication /tmp/opslens-gate19-5-artifact-publication-v1.json
```

Expected final marker:

```text
phase19_gate19_5_publication=PASS
terraform_plan_input_ready=true
terraform_apply_authorized=false
```

Only after this verifier passes may the publication evidence be copied into the repository for review. Gate 19.6, not Gate 19.5, consumes the admitted `VersionId` values to generate an exact Terraform plan.

## Failure handling

If publication fails at any point:

- do not rerun automatically;
- do not change the content-addressed keys;
- do not delete or overwrite an object;
- do not broaden IAM;
- do not run Terraform plan/apply as a workaround;
- preserve `/tmp/opslens-gate19-5-artifact-publication-v1.json` when produced and inspect the exact partial state before deciding any next human action.

## Explicit non-authority

Gate 19.5 publication does not authorize:

```text
Terraform apply
API Gateway enablement
Lambda runtime creation/update
event-source enablement
SQS/DynamoDB runtime creation
IAM role/policy mutation
Bedrock model invocation
Bedrock Retrieve
GitHub representative workload execution
third-party repository code execution
PR #89 changes
```
