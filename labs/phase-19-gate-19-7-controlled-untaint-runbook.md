# Phase 19 — Gate 19.7 Controlled Terraform-State Untaint Runbook

## Status

**HUMAN-ONLY state-reconciliation boundary. `terraform untaint` is not authorized by this runbook. Terraform apply is not authorized.**

The first Gate 19.7 apply partially materialized the disabled runtime and failed while setting API Lambda reserved concurrency. Terraform marked the already-created API Lambda as tainted. A subsequent fresh recovery plan was correctly rejected because it proposed replacing that Lambda:

```text
Plan: 6 to add, 0 to change, 1 to destroy.
aws_lambda_function.public_async_api: ["delete", "create"]
action_reason: replace_because_tainted
```

Bounded diagnosis proves:

```text
Terraform state status: tainted
remote Lambda state: Active
remote Lambda last update status: Successful
remote Lambda configuration matches reviewed source: true
remote Lambda artifact hash matches admitted artifact: true
OPSLENS_ASYNC_SUBMIT_ENABLED: false
reserved concurrency: not configured / not observed
replacement authorized: false
terraform apply authorized: false
terraform untaint authorized: false
```

The rejected recovery plan is quarantined and permanently non-authoritative.

```text
plan != apply
materialized != enabled
failed plan != retry authority
state reconciliation != AWS mutation
```

## Canonical evidence

Replacement diagnosis:

```text
labs/evidence/phase-19-gate-19-7-replacement-diagnosis-v1.json
```

Controlled untaint contract:

```text
labs/evidence/phase-19-gate-19-7-untaint-contract-v1.json
```

Offline contract verifier:

```text
scripts/verify_phase19_gate19_7_untaint_contract.py
```

## Why untaint is the candidate recovery

Terraform uses tainted state to force replacement of an object during the next plan. The remote API Lambda is currently healthy and matches the reviewed configuration, so replacement would be more destructive than necessary. The candidate recovery is therefore to remove only Terraform's taint marker after a fresh human checkpoint proves that the state and remote object have not changed.

This operation changes Terraform state only. It is **not** treated as an AWS runtime mutation or as deployment authority. It is still a protected human boundary because it changes the authoritative Terraform state.

## Frozen target

Only this exact instance may ever be considered for Gate 19.7 untaint:

```text
aws_lambda_function.public_async_api[0]
```

No wildcard, module-wide operation, second resource, import, `state rm`, replacement, destroy, apply, quota mutation, IAM mutation, or runtime enablement is in scope.

## Required protected checkpoint

Before any untaint authorization can be requested, all of the following must be true:

1. this untaint evidence/tooling PR is protected-merged by a human;
2. exact protected-main post-merge CodeQL is green;
3. the exact protected-main SHA is recorded in issue #361;
4. the local worktree is clean at that exact SHA;
5. the rejected recovery plan remains quarantined;
6. no Terraform apply, import, state removal, untaint, quota change, IAM broadening, or runtime enablement has occurred since the diagnosis;
7. a fresh HUMAN-only read checkpoint captures the current Terraform state lineage and serial;
8. that same checkpoint proves the target is still tainted and the remote Lambda still matches the reviewed configuration;
9. a separate explicit HUMAN authorization is recorded for the exact target and state checkpoint.

The static contract must pass first:

```bash
PYTHONPATH=src uv run python \
  scripts/verify_phase19_gate19_7_untaint_contract.py
```

Expected marker:

```text
phase19_gate19_7_untaint_contract=PASS target=aws_lambda_function.public_async_api[0] taint_confirmed=true remote_config_matches=true state_mutation_authorized=false terraform_untaint_authorized=false terraform_apply_authorized=false human_untaint_authorization_required=true
```

## HUMAN-ONLY pre-authorization read checkpoint

This checkpoint is read-only. It must run only after the protected merge checkpoint above is satisfied.

Set the exact protected-main SHA supplied during review:

```bash
EXPECTED_HEAD="<exact protected untaint-checkpoint merge SHA>"
PROFILE="opslens-bootstrap"
REGION="us-east-1"
EXPECTED_ACCOUNT="487757851499"
```

Synchronize fail-closed:

```bash
git switch main
git fetch origin
git pull --ff-only origin main

test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD" || {
  echo "STOP: unexpected protected-main SHA"
  exit 1
}

test -z "$(git status --porcelain)" || {
  echo "STOP: worktree is not clean"
  exit 1
}
```

Verify identity and pull the current state read-only:

```bash
ACCOUNT="$(
  aws sts get-caller-identity \
    --profile "$PROFILE" \
    --query Account \
    --output text
)"

test "$ACCOUNT" = "$EXPECTED_ACCOUNT" || {
  echo "STOP: unexpected AWS account"
  exit 1
}

AWS_PROFILE="$PROFILE" \
terraform -chdir=infra/environments/dev state pull \
  > /tmp/opslens-gate19-7-pre-untaint-state.json
```

Read the remote API Lambda without mutating it:

```bash
aws lambda get-function-configuration \
  --function-name opslens-dev-public-analysis-api \
  --profile "$PROFILE" \
  --region "$REGION" \
  --output json \
  > /tmp/opslens-gate19-7-pre-untaint-api.json

: > /tmp/opslens-gate19-7-pre-untaint-concurrency.json
aws lambda get-function-concurrency \
  --function-name opslens-dev-public-analysis-api \
  --profile "$PROFILE" \
  --region "$REGION" \
  --output json \
  > /tmp/opslens-gate19-7-pre-untaint-concurrency.json
```

The bounded readiness artifact must contain only:

```text
protected source SHA
AWS account and region
Terraform state lineage and serial
target address
target state status
target tainted boolean
remote Lambda state and last-update status
remote Lambda artifact hash
remote Lambda reviewed configuration-match boolean
submit switch
reserved-concurrency observation semantics
rejected recovery-plan quarantine status
all state/apply/runtime authorities false
```

Do not persist the full Terraform state, full provider plan JSON, credentials, or binary plan in the repository.

## Mandatory authorization stop

After the bounded read checkpoint is reviewed:

**STOP. Do not run `terraform untaint`.**

The command is intentionally omitted from this pre-authorization runbook. If the checkpoint is admitted, a separate explicit HUMAN authorization must bind:

```text
exact protected-main SHA
Terraform state lineage
Terraform state serial
exact target address: aws_lambda_function.public_async_api[0]
operation: terraform untaint
```

Only after that explicit authorization may a one-target state mutation command be provided.

## Required post-untaint sequence

If a future explicit HUMAN authorization is granted and the single state mutation succeeds, the next steps are still bounded:

```text
prove the target is no longer tainted
prove the remote Lambda configuration did not change
generate a new fresh recovery Terraform plan
require exactly five missing creates
allow at most one in-place update to aws_lambda_function.public_async_api
require zero deletes
require zero replacements
run the dedicated recovery-plan verifier
persist only bounded admission evidence
STOP before Terraform apply
```

A successful untaint does **not** authorize Terraform apply.

## Explicit non-authority

This runbook does not authorize:

```text
terraform untaint
terraform apply
terraform import
terraform state rm
terraform plan -replace
resource replacement or destroy
Lambda quota mutation
IAM mutation or broadening
execute-api endpoint enablement
submit switch enablement
API or worker concurrency above zero
worker enablement
SQS event-source enablement
custom public domain creation
provider-heavy public execution
third-party repository execution
PR #89 modification
```
