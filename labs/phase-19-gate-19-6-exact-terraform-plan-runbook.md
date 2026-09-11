# Phase 19 — Gate 19.6 Exact Terraform Plan Runbook

## Status

**HUMAN-ONLY plan boundary. No Terraform apply is authorized.**

This runbook generates the first exact Terraform plan for the disabled/non-public async runtime using the immutable API/worker artifact coordinates admitted in Gate 19.5.

The plan may perform backend/provider reads. It must not mutate runtime resources, IAM, public endpoints, or the remote Terraform lock object.

## Frozen source

Protected Gate 19.5 merge:

```text
61749bfac7b7bc9d032567e0b1870f8c1f7dedd4
```

Gate 19.6 issue: `#354`.

The reviewed Gate 19.6 PR head will be frozen before this runbook is crossed. Do not plan from an unreviewed or dirty worktree.

## Frozen plan input

Use only:

```text
labs/evidence/phase-19-gate-19-6-plan-input-v1.tfvars.json
```

It selects `public_async_runtime_materialized=true` **for planning only** and supplies the exact Gate 19.5 immutable coordinates:

```text
API VersionId:
E.jfB7dlkGCD.wHAurP7QXo4fuS_PW63

Worker VersionId:
sxiOdii4yFwR13t23xP5A8EU1JPV_7P1
```

Changing any key, VersionId, source hash, or the materialization selector invalidates the plan contract.

## Why `-lock=false`

The dev backend uses the existing versioned S3 Terraform-state bucket with `use_lockfile=true`. A normal plan may create and delete a remote lock object. Gate 19.6 is intentionally a read-only AWS/provider boundary, so the human plan command uses:

```text
-lock=false
```

This avoids the remote Terraform lock-object mutation. The operator must ensure no concurrent Terraform operation is running while this plan is generated.

## Preconditions

Before planning:

1. exact-head Gate 19.6 CI is green;
2. the PR head is the reviewed head named in the issue/PR checkpoint;
3. local worktree is clean;
4. no concurrent Terraform operation is running against `environments/dev/terraform.tfstate`;
5. existing AWS profile authority is sufficient for backend/provider reads;
6. no IAM change is made to make planning succeed;
7. no `terraform apply` command is run.

## Local preflight

```bash
git rev-parse HEAD
git status --short

terraform -chdir=infra/environments/dev fmt -check
terraform -chdir=infra/environments/dev validate
```

A dirty worktree, unexpected SHA, formatting failure, or validation failure is a hard stop.

## HUMAN-ONLY exact plan

The project has historically used the existing `opslens-bootstrap` profile for lab administration. This runbook does not grant or broaden that authority.

Initialize the existing dev backend:

```bash
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev init \
  -input=false \
  -reconfigure
```

Generate exactly one plan without acquiring the remote state lock:

```bash
rm -f /tmp/opslens-gate19-6.tfplan \
      /tmp/opslens-gate19-6-plan.json \
      /tmp/opslens-gate19-6-plan-admission-v1.json

AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev plan \
  -input=false \
  -lock=false \
  -refresh=true \
  -var-file=../../../labs/evidence/phase-19-gate-19-6-plan-input-v1.tfvars.json \
  -out=/tmp/opslens-gate19-6.tfplan
```

Do **not** run `terraform apply /tmp/opslens-gate19-6.tfplan`.

## Render plan JSON locally

`terraform show -json` reads the local binary plan and does not contact AWS:

```bash
terraform -chdir=infra/environments/dev show -json \
  /tmp/opslens-gate19-6.tfplan \
  > /tmp/opslens-gate19-6-plan.json
```

## Offline admission

```bash
PYTHONPATH=src uv run python \
  scripts/verify_phase19_gate19_6_exact_plan.py \
  --plan-json /tmp/opslens-gate19-6-plan.json \
  --output /tmp/opslens-gate19-6-plan-admission-v1.json
```

Expected marker:

```text
phase19_gate19_6_plan=PASS managed_creates=21 updates=0 deletes=0 replacements=0 execute_api_endpoint_disabled=true worker_event_source_enabled=false worker_reserved_concurrency=0 terraform_apply_authorized=false
```

The verifier fails closed if any unrelated managed change is present, any expected resource is not exactly a create, any update/delete/replace exists, immutable artifact coordinates drift, the execute-api endpoint is enabled, the worker event-source mapping is enabled, worker reserved concurrency is nonzero, or API/worker runtime switches are enabled.

## Required evidence

After PASS, inspect only the bounded summary:

```bash
cat /tmp/opslens-gate19-6-plan-admission-v1.json
```

The summary records the plan JSON SHA-256, Terraform versions, exact managed create inventory, immutable artifact coordinates, and safety decisions. Do not commit the binary plan. Do not commit credentials or unrelated provider response content.

## Failure handling

If init, plan, JSON rendering, or offline admission fails:

- do not run `terraform apply`;
- do not broaden IAM automatically;
- do not change artifact VersionIds to make the plan pass;
- do not remove disabled runtime controls;
- do not retry automatically after an authorization or drift failure;
- preserve `/tmp/opslens-gate19-6-plan.json` when available and inspect the exact failure first.

## Explicit non-authority

Gate 19.6 does not authorize:

```text
Terraform apply
runtime Lambda/SQS/DynamoDB/API Gateway creation or update
IAM role/policy mutation
execute-api endpoint enablement
custom public domain creation
submit switch enablement
worker switch enablement
SQS event-source enablement
Bedrock model invocation
Bedrock Retrieve
GitHub representative workload execution
third-party repository code execution
PR #89 changes
```

`plan != apply` remains the controlling invariant.
