# Phase 19 — Gate 19.7 Partial Materialization Recovery Runbook

## Status

**HUMAN-ONLY recovery planning boundary. Terraform apply is not authorized by this runbook.**

The first Gate 19.7 apply attempt failed after partially materializing the disabled runtime. The failed saved plan is quarantined and permanently non-reusable.

```text
plan != apply
materialized != enabled
failed plan != retry authority
```

## Failure evidence

Canonical bounded reconciliation:

```text
labs/evidence/phase-19-gate-19-7-failed-apply-reconciliation-v1.json
```

Canonical recovery contract:

```text
labs/evidence/phase-19-gate-19-7-recovery-contract-v1.json
```

Observed partial state:

```text
expected Gate 19.7 managed resources: 21
managed after failed apply:             16
missing managed resources:               5
unexpected public_async resources:       0
```

The five missing resources are exactly:

```text
aws_apigatewayv2_integration.public_async_api_lambda
aws_apigatewayv2_route.public_async_result
aws_apigatewayv2_route.public_async_status
aws_apigatewayv2_route.public_async_submit
aws_lambda_permission.public_async_api_gateway
```

The failed plan remains frozen as non-authority:

```text
plan_binary_sha256: 4f9c7a07e792da2dfbde7ba38ecfb8286386a2fc7eba8ef79ae346b4a53e757d
plan_json_sha256:   5918eb69040af7ae3e7aa3fc428e4488b9ae6de98ebf8a0251f9faed2892580a
retry_authorized:   false
reusable:           false
```

## Recovery design

The failed operation attempted to configure API Lambda reserved concurrency to `2`. The AWS account concurrency limit is `10`, and Lambda rejected that reservation because it would reduce the account's unreserved concurrency below the service minimum of `10`.

Gate 19.7 recovery does **not** broaden IAM or mutate the account quota to force the historical configured limit. Instead, the live recovery source hard-disables the API Lambda with:

```text
API reserved concurrency = 0
worker reserved concurrency = 0
```

The original Gate 19.4 configured value of `2` remains historical evidence only. It is not current runtime authority.

The retained disabled/non-public controls are:

```text
public_async_runtime_materialized = true
execute-api endpoint disabled
OPSLENS_ASYNC_SUBMIT_ENABLED = false
API reserved concurrency = 0
OPSLENS_ASYNC_WORKER_ENABLED = false
worker reserved concurrency = 0
SQS -> worker event-source mapping = false
custom public domain = absent
provider-heavy worker executor = not composed
```

## Required merge checkpoint

Do not generate a recovery plan until all of the following are true:

1. the Gate 19.7 recovery PR has been protected-merged by a human;
2. exact protected-main post-merge CodeQL is green;
3. the exact protected-main SHA is recorded in issue #361;
4. the local worktree is clean and checked out at that exact SHA;
5. the failed plan remains quarantined and is not renamed back or reused;
6. no Terraform apply, state import/removal, quota change, IAM broadening, or runtime enablement has occurred since the bounded reconciliation.

Set the reviewed recovery source explicitly:

```bash
EXPECTED_HEAD="<exact protected Gate 19.7 recovery merge SHA>"
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

test -f /tmp/opslens-gate19-7.tfplan.DO_NOT_RETRY || {
  echo "STOP: failed plan quarantine marker is missing"
  exit 1
}

terraform -chdir=infra/environments/dev fmt -check
```

## HUMAN-ONLY fresh recovery plan

Initialize the existing dev backend and provider plugins:

```bash
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev init \
  -input=false \
  -reconfigure
```

Validate source:

```bash
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev validate
```

Remove only new recovery-plan temporary files. Do **not** remove or reuse the quarantined failed plan.

```bash
rm -f /tmp/opslens-gate19-7-recovery.tfplan \
      /tmp/opslens-gate19-7-recovery-plan.json \
      /tmp/opslens-gate19-7-recovery-plan-admission-v1.json
```

Generate exactly one fresh recovery plan against the current remote state:

```bash
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev plan \
  -input=false \
  -lock=false \
  -refresh=true \
  -var-file=../../../labs/evidence/phase-19-gate-19-7-plan-input-v1.tfvars.json \
  -out=/tmp/opslens-gate19-7-recovery.tfplan
```

Expected bounded shape:

```text
managed creates: exactly 5, matching the frozen missing inventory
managed updates: 0 or 1
if an update exists: aws_lambda_function.public_async_api only
managed deletes: 0
managed replacements: 0
API reserved concurrency after: 0
worker reserved concurrency after: 0
execute-api endpoint disabled after: true
submit switch after: false
worker switch after: false
event-source mapping after: false
```

A typical Terraform summary is expected to be:

```text
Plan: 5 to add, 1 to change, 0 to destroy.
```

Provider normalization may make the API concurrency transition a no-op; therefore the offline verifier admits zero or one update, but never an update to any other existing resource.

Any other managed action is a hard stop.

## Render provider plan JSON locally

```bash
terraform -chdir=infra/environments/dev show -json \
  /tmp/opslens-gate19-7-recovery.tfplan \
  > /tmp/opslens-gate19-7-recovery-plan.json
```

The full provider JSON remains local and must not be committed.

## Offline recovery-plan admission

```bash
PYTHONPATH=src uv run python \
  scripts/verify_phase19_gate19_7_fresh_plan.py \
  --recovery \
  --plan-json /tmp/opslens-gate19-7-recovery-plan.json \
  --plan-binary /tmp/opslens-gate19-7-recovery.tfplan \
  --expected-source-head "$EXPECTED_HEAD" \
  --output /tmp/opslens-gate19-7-recovery-plan-admission-v1.json
```

Expected marker:

```text
phase19_gate19_7_recovery_plan=PASS managed_creates=5 managed_updates=<0-or-1> deletes=0 replacements=0 plan_binary_sha256=<sha256> api_reserved_concurrency=0 worker_reserved_concurrency=0 materialized_not_enabled=true terraform_apply_authorized=false human_apply_authorization_required=true
```

Inspect only the bounded admission:

```bash
cat /tmp/opslens-gate19-7-recovery-plan-admission-v1.json
```

Return the Terraform high-level summary, PASS marker, and bounded admission JSON for review.

## Mandatory stop

**STOP. Do not run Terraform apply.**

A fresh recovery plan requires a new protected evidence checkpoint and a new explicit HUMAN apply authorization bound to its exact:

```text
source_head_sha
plan_binary_sha256
plan_json_sha256
```

The previous HUMAN authorization was consumed by the failed apply attempt. It does not authorize recovery retry.

## Explicit non-authority

This runbook does not authorize:

```text
retry of /tmp/opslens-gate19-7.tfplan.DO_NOT_RETRY
terraform apply of the recovery plan
terraform import or state rm
Lambda quota mutation
IAM broadening
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
