# Phase 19 — Gate 19.7 Post-Apply Verification

## Status

**CONTROLLED MATERIALIZATION COMPLETE CANDIDATE — RUNTIME REMAINS DISABLED**

The single-use HUMAN-authorized Terraform apply succeeded for the exact admitted Gate 19.7 recovery plan.

```text
Apply complete! Resources: 5 added, 1 changed, 0 destroyed.
```

The apply authorization was consumed by this one invocation and cannot be reused.

## Bound plan identity

```text
source head SHA:
  d6546e9d48253694e3e276940ebd2388f301d8ad

protected evidence checkpoint:
  fd590df290502950b9dccc7eef93abcabff6d039

plan binary SHA-256:
  48cb15a8466cc0ce77fdbe1d827b5a0aebb88460b8e8151d8c88d3c85eb9ea55

plan JSON SHA-256:
  8a1f95ab8cbcbf96c708c6ced0d0127d862391a6f8e72c250fe5e7499d2a0bf7
```

No replan was performed. The saved binary plan was quarantined after the single apply invocation and is not reusable.

## Exact materialization delta

The state transition added exactly these five managed resource addresses:

```text
aws_apigatewayv2_integration.public_async_api_lambda[0]
aws_apigatewayv2_route.public_async_result[0]
aws_apigatewayv2_route.public_async_status[0]
aws_apigatewayv2_route.public_async_submit[0]
aws_lambda_permission.public_async_api_gateway[0]
```

The only existing-resource update was the admitted in-place API Lambda hard-disable transition:

```text
aws_lambda_function.public_async_api
reserved_concurrent_executions -> 0
```

No resources were destroyed or replaced.

## Terraform state proof

```text
lineage before: 6c958ab2-4cc6-7f96-a528-89535504f65c
lineage after:  6c958ab2-4cc6-7f96-a528-89535504f65c
lineage unchanged: true
serial before: 116
serial after:  117
serial advanced: true
removed resource addresses: []
```

## Runtime remains fail-closed

The runtime is materialized but not enabled.

```text
API id: 4f9jxjh7mj
execute-api endpoint disabled: true
OPSLENS_ASYNC_SUBMIT_ENABLED: false
API reserved concurrency: 0
OPSLENS_ASYNC_WORKER_ENABLED: false
worker reserved concurrency: 0
worker event-source mapping: Disabled
custom domain mapping present: false
provider-heavy public execution path enabled: false
```

The Lambda artifacts remained the reviewed binaries:

```text
API CodeSha256:
  mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24=

worker CodeSha256:
  DQS0ckdq14JbUZA1LaFkLbmn1C0c40nSGjn6yPbsvck=
```

Materialization of routes, integration, and API Gateway invocation permission is not runtime enablement. The default execute-api endpoint remains disabled, no custom domain is attached, API concurrency is zero, submission is disabled, worker concurrency is zero, and the worker event-source mapping remains disabled.

## Authority after apply

The HUMAN apply authorization is consumed. Authority resets fail-closed:

```text
terraform_apply_authorization_consumed=true
terraform_apply_retry_authorized=false
additional_terraform_apply_authorized=false
terraform_replan_authorized=false
terraform_destroy_authorized=false
terraform_replacement_authorized=false
terraform_import_authorized=false
terraform_state_rm_authorized=false
terraform_untaint_authorized=false
runtime_enablement_authorized=false
public_endpoint_enablement_authorized=false
worker_enablement_authorized=false
event_source_enablement_authorized=false
provider_heavy_execution_authorized=false
```

No further Terraform mutation or runtime enablement follows from this artifact.

## Next boundary

This post-apply evidence must be protected-merged and verified on protected `main` before Gate 19.7 can be recorded as complete.

After protected merge and post-merge CI success, the next phase decision must be taken separately. This evidence does not authorize public endpoint enablement, API concurrency changes, submit/worker enablement, event-source enablement, custom-domain exposure, provider-heavy execution, or any additional Terraform apply.

## Canonical evidence

```text
labs/evidence/phase-19-gate-19-7-post-apply-verification-v1.json
```

Controlling invariants:

```text
plan != apply
materialized != enabled
authorization is single-use
provider success != business authority
UNMEASURED != zero
```
