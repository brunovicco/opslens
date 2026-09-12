# Phase 19 — Gate 19.7 Recovery V2 Apply Boundary

## Status

**PLAN ADMITTED — APPLY AUTHORITY PENDING**

This document freezes the next human boundary after recovery-plan-v2 admission.

Exact identities:

```text
source_head_sha=d6546e9d48253694e3e276940ebd2388f301d8ad
plan_binary_sha256=48cb15a8466cc0ce77fdbe1d827b5a0aebb88460b8e8151d8c88d3c85eb9ea55
plan_json_sha256=8a1f95ab8cbcbf96c708c6ced0d0127d862391a6f8e72c250fe5e7499d2a0bf7
```

Exact admitted action shape:

```text
5 managed creates
1 managed in-place update: aws_lambda_function.public_async_api
0 managed deletes
0 managed replacements
api reserved concurrency after: 0
worker reserved concurrency after: 0
```

No apply authority exists merely because the plan and offline verifier passed.

A future HUMAN apply authorization, if granted, must explicitly bind the exact source SHA, binary-plan SHA-256, provider-plan JSON SHA-256, and admitted action shape above. Any mismatch invalidates the authorization.

Until then:

```text
terraform_apply_authorized=false
runtime_enablement_authorized=false
public_endpoint_enablement_authorized=false
submit_enablement_authorized=false
worker_enablement_authorized=false
event_source_enablement_authorized=false
replacement_authorized=false
destroy_authorized=false
```

The GitHub/Terraform CLI suggestion to apply a saved plan is informational only and is not OpsLens authority.

Controlling invariants:

```text
plan != apply
materialized != enabled
failed plan != retry authority
```
