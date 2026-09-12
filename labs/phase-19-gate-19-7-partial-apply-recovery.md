# Phase 19 — Gate 19.7 Partial-Apply Recovery

## Status

**RECOVERY PREPARATION — APPLY NOT AUTHORIZED**

The first human-authorized Gate 19.7 materialization attempt failed after partially creating the disabled runtime. The failed saved plan is permanently quarantined and is not retry authority.

```text
plan != apply
materialized != enabled
failed apply != retry authority
```

## Observed failure

The admitted plan requested API Lambda reserved concurrency `2`. AWS rejected `PutFunctionConcurrency` because the dev account concurrency limit is `10` and that reservation would reduce unreserved concurrency below AWS's required minimum.

This was not an IAM or artifact-integrity failure. Both deployed Lambda `CodeSha256` values match the immutable Gate 19.5 artifacts.

Canonical bounded reconciliation:

```text
labs/evidence/phase-19-gate-19-7-failed-apply-reconciliation-v1.json
```

Observed Terraform state after the failed apply:

```text
expected Gate 19.7 managed resources: 21
managed expected resources:          16
missing expected resources:           5
unexpected public-async resources:    0
```

Missing resources:

```text
aws_apigatewayv2_integration.public_async_api_lambda
aws_apigatewayv2_route.public_async_result
aws_apigatewayv2_route.public_async_status
aws_apigatewayv2_route.public_async_submit
aws_lambda_permission.public_async_api_gateway
```

Observed live controls remained fail-closed:

```text
execute-api endpoint:          disabled
API submit switch:             false
API reserved concurrency:      UNCONFIGURED / not zero
worker switch:                 false
worker reserved concurrency:   0
worker event-source mapping:   Disabled
```

`UNCONFIGURED` is not relabeled as zero. `UNMEASURED != zero` remains authoritative.

## Recovery design

Gate 19.4 remains historical evidence: its configured API reserved concurrency was `2` at that gate. Recovery does not rewrite that history.

Gate 19.7 adds a narrowly scoped Terraform override:

```text
infra/environments/dev/public_async_runtime_recovery_override.tf
```

The override changes only the current materialization behavior:

```text
API reserved concurrency:    0
worker reserved concurrency: 0
```

This strengthens the disabled boundary. Even if a non-public invocation path were accidentally introduced before the later enablement gate, the API Lambda has no execution concurrency.

The override is temporary recovery/current-state configuration, not a claim that Gate 19.4 originally used zero API concurrency.

Machine-readable recovery authority:

```text
labs/evidence/phase-19-gate-19-7-recovery-contract-v1.json
```

Offline recovery-contract verifier:

```text
scripts/verify_phase19_gate19_7_recovery_contract.py
```

Future recovery-plan verifier:

```text
scripts/verify_phase19_gate19_7_recovery_plan.py
```

## Expected fresh recovery plan

A new HUMAN-only Terraform plan is mandatory after this recovery PR is protected-merged and exact-SHA post-merge verification succeeds.

The failed plan must not be reused.

The recovery plan is expected to contain exactly:

```text
CREATE:
  aws_apigatewayv2_integration.public_async_api_lambda
  aws_apigatewayv2_route.public_async_result
  aws_apigatewayv2_route.public_async_status
  aws_apigatewayv2_route.public_async_submit
  aws_lambda_permission.public_async_api_gateway

UPDATE:
  aws_lambda_function.public_async_api
    reserved_concurrent_executions -> 0

DELETE:      0
REPLACEMENT: 0
```

Any additional managed change is a hard stop.

The recovery-plan verifier also requires the existing Gate 19.7 immutable artifact coordinates and safety outputs to remain unchanged.

## Human-only recovery planning boundary

After protected merge and exact-SHA CodeQL success, the human operator may synchronize to that exact protected-main SHA and run a new read-oriented plan:

```bash
EXPECTED_HEAD="<protected recovery merge SHA>"

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

AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev init \
  -input=false \
  -reconfigure

AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev validate

rm -f \
  /tmp/opslens-gate19-7-recovery.tfplan \
  /tmp/opslens-gate19-7-recovery-plan.json \
  /tmp/opslens-gate19-7-recovery-plan-admission-v1.json

AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev plan \
  -input=false \
  -lock=false \
  -refresh=true \
  -var-file=../../../labs/evidence/phase-19-gate-19-7-plan-input-v1.tfvars.json \
  -out=/tmp/opslens-gate19-7-recovery.tfplan

terraform -chdir=infra/environments/dev show -json \
  /tmp/opslens-gate19-7-recovery.tfplan \
  > /tmp/opslens-gate19-7-recovery-plan.json

PYTHONPATH=src uv run python \
  scripts/verify_phase19_gate19_7_recovery_plan.py \
  --plan-json /tmp/opslens-gate19-7-recovery-plan.json \
  --plan-binary /tmp/opslens-gate19-7-recovery.tfplan \
  --expected-source-head "$EXPECTED_HEAD" \
  --output /tmp/opslens-gate19-7-recovery-plan-admission-v1.json
```

Expected verifier marker:

```text
phase19_gate19_7_recovery_plan=PASS creates=5 updates=1 deletes=0 replacements=0 ... api_reserved_concurrency=0 materialized_not_enabled=true terraform_apply_authorized=false human_apply_authorization_required=true
```

Return only the Terraform high-level summary, verifier PASS marker, and bounded admission JSON. Do not commit or return the full provider plan JSON or binary plan.

## Mandatory stop

A successful recovery plan is still not apply authority.

After offline admission:

```text
STOP
terraform_apply_authorized=false
```

The bounded recovery-plan admission must be persisted through a protected evidence PR and verified on its exact protected merge SHA. A new, separate explicit HUMAN apply authorization must bind the exact recovery source SHA, binary-plan SHA-256, and plan-JSON SHA-256.

## Explicit non-authority

This recovery preparation does not authorize:

```text
retry of the failed Gate 19.7 plan
terraform apply of the recovery plan
runtime/public enablement
execute-api endpoint enablement
submit switch enablement
worker enablement
SQS event-source enablement
positive API reserved concurrency
positive worker reserved concurrency
provider-heavy execution
IAM broadening
custom domain creation
PR #89 modification
third-party repository execution
```
