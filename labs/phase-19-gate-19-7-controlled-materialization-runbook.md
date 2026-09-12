# Phase 19 — Gate 19.7 Controlled Disabled Runtime Materialization Runbook

## Status

**HUMAN-ONLY preparation boundary. Terraform apply is not authorized by this runbook.**

Gate 19.7 separates resource materialization from runtime enablement:

```text
plan != apply
materialized != enabled
```

The first human action in this gate is a **fresh Terraform plan**, generated only after the Gate 19.7 tooling PR is protected-merged and its exact protected-main post-merge verification is green.

The previously admitted Gate 19.6 binary plan is historical planning evidence. It must not be reused as Gate 19.7 apply authority.

## Frozen authority

Source issue:

```text
#361
```

Machine-readable materialization contract:

```text
labs/evidence/phase-19-gate-19-7-materialization-contract-v1.json
```

Gate-specific plan input:

```text
labs/evidence/phase-19-gate-19-7-plan-input-v1.tfvars.json
```

The Gate 19.7 plan input intentionally retains the same immutable API/worker `Key + VersionId + source_code_hash` coordinates admitted in Gate 19.5 and planned in Gate 19.6.

## Disabled/non-public invariants

Any fresh plan admitted by this gate must preserve:

```text
public_async_runtime_materialized = true      # plan/materialization selection only
disable execute-api endpoint = true
OPSLENS_ASYNC_SUBMIT_ENABLED = false
OPSLENS_ASYNC_WORKER_ENABLED = false
SQS -> worker event-source mapping = false
worker reserved concurrency = 0
custom public domain = absent
provider-heavy worker executor = not composed
```

The plan must still contain exactly the retained 21 managed creates with zero update, delete, or replacement actions and no unrelated managed drift.

## Boundary before planning

Do not cross this section until all of the following are true:

1. the Gate 19.7 tooling PR has been protected-merged by a human;
2. post-merge CodeQL for that exact protected `main` SHA has completed successfully;
3. the exact protected `main` SHA has been recorded in issue #361;
4. the local worktree is clean and checked out at that exact SHA;
5. no concurrent Terraform operation is running against the dev state;
6. no IAM or runtime mutation is made to make planning succeed.

Set the reviewed protected-main SHA explicitly:

```bash
EXPECTED_HEAD="<exact protected Gate 19.7 tooling merge SHA>"
```

Synchronize and fail closed on any mismatch:

```bash
git switch main
git fetch origin
git pull --ff-only origin main

git rev-parse HEAD
git status --short

test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD" || {
  echo "STOP: unexpected protected-main SHA"
  exit 1
}

test -z "$(git status --porcelain)" || {
  echo "STOP: worktree is not clean"
  exit 1
}

terraform -chdir=infra/environments/dev fmt -check
```

## HUMAN-ONLY fresh plan

Initialize the existing dev backend and provider plugins:

```bash
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev init \
  -input=false \
  -reconfigure
```

Validate the exact configuration:

```bash
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev validate
```

Remove only prior local Gate 19.7 temporary files:

```bash
rm -f /tmp/opslens-gate19-7.tfplan \
      /tmp/opslens-gate19-7-plan.json \
      /tmp/opslens-gate19-7-plan-admission-v1.json
```

Generate exactly one fresh plan. `-lock=false` is retained so this planning boundary does not create/delete the remote S3 lock object:

```bash
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev plan \
  -input=false \
  -lock=false \
  -refresh=true \
  -var-file=../../../labs/evidence/phase-19-gate-19-7-plan-input-v1.tfvars.json \
  -out=/tmp/opslens-gate19-7.tfplan
```

Expected high-level shape before offline admission:

```text
Plan: 21 to add, 0 to change, 0 to destroy.
public_async_execute_api_endpoint_disabled = true
public_async_runtime_materialized = true
public_async_submit_enabled = false
public_async_worker_event_source_enabled = false
public_async_worker_reserved_concurrency = 0
```

Any different shape is a hard stop.

## Render provider plan JSON locally

```bash
terraform -chdir=infra/environments/dev show -json \
  /tmp/opslens-gate19-7.tfplan \
  > /tmp/opslens-gate19-7-plan.json
```

The full provider JSON remains local and must not be committed.

## Fresh-plan offline admission

Gate 19.7 first replays the retained Gate 19.6 exact-plan safety engine against the Gate 19.7 input and then binds the result to both the exact reviewed source SHA and the exact saved binary-plan SHA-256.

```bash
PYTHONPATH=src uv run python \
  scripts/verify_phase19_gate19_7_fresh_plan.py \
  --plan-json /tmp/opslens-gate19-7-plan.json \
  --plan-binary /tmp/opslens-gate19-7.tfplan \
  --expected-source-head "$EXPECTED_HEAD" \
  --output /tmp/opslens-gate19-7-plan-admission-v1.json
```

Expected marker:

```text
phase19_gate19_7_plan=PASS managed_creates=21 updates=0 deletes=0 replacements=0 plan_binary_sha256=<sha256> materialized_not_enabled=true terraform_apply_authorized=false human_apply_authorization_required=true
```

Inspect only the bounded summary:

```bash
cat /tmp/opslens-gate19-7-plan-admission-v1.json
```

Return that bounded JSON plus the Terraform plan summary and PASS marker for review. Do not return or commit the full provider plan JSON or the binary plan.

## Mandatory stop after fresh-plan admission

**STOP. Do not run Terraform apply.**

A successful fresh plan is still evidence, not mutation authority. Before any apply can be considered, Gate 19.7 requires all of the following as a separate checkpoint:

```text
fresh plan admission persisted as bounded evidence
exact source_head_sha reviewed
exact plan_binary_sha256 reviewed
exact plan_json_sha256 reviewed
protected evidence merge/post-merge verification completed
explicit HUMAN apply authorization recorded for those exact hashes
```

The preparation runbook intentionally contains **no Terraform apply command**.

## Later apply boundary, if explicitly authorized

If a later checkpoint explicitly authorizes the exact admitted plan, the human operator must first prove that the local binary plan still hashes to the admitted `plan_binary_sha256`, that the source checkpoint matches the recorded authority, and that no intervening state-changing Terraform operation occurred.

Terraform's saved-plan/state consistency checks remain an additional fail-closed control; they do not replace the explicit OpsLens authorization boundary.

## Required post-apply proof, if a later apply is authorized

A successful disabled materialization will not close Gate 19.7 by itself. Post-apply evidence must prove all of the following before the gate can close:

```text
exact admitted resources materialized
execute-api endpoint still disabled
submit switch still false
worker switch still false
SQS event-source mapping still disabled
worker reserved concurrency still 0
no custom public domain
provider-heavy worker executor still not composed
fresh convergence Terraform plan produces no unexpected managed change
bounded AWS/state verification persisted
public/provider-heavy execution count remains 0
```

Runtime composition and public/worker enablement remain later gates.

## Failure handling

If init, validate, plan, JSON rendering, or offline admission fails:

- do not run Terraform apply;
- do not broaden IAM automatically;
- do not change immutable artifact coordinates to force success;
- do not enable execute-api, submit, worker, or event-source mapping;
- do not retry automatically after drift or authorization failure;
- inspect the exact failure before deciding the next human action.

## Explicit non-authority

This runbook does not authorize:

```text
Terraform apply
runtime AWS resource mutation
IAM mutation or broadening
execute-api endpoint enablement
custom public domain creation
submit switch enablement
worker switch enablement
SQS event-source enablement
Bedrock Retrieve/model invocation through the public worker
third-party repository execution
PR #89 modification
```
