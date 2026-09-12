# Phase 19 — Gate 19.6 Terraform Unknown-Value Admission Note

## Status

**Verifier correction after the first human exact-plan attempt. No Terraform apply is authorized.**

The first human-operated Gate 19.6 plan from protected `main` `ffbf5897729cc5520d8d8006e60e0834bafdfe92` produced the expected managed shape:

```text
Plan: 21 to add, 0 to change, 0 to destroy.
public_async_execute_api_endpoint_disabled = true
public_async_runtime_materialized = true
public_async_submit_enabled = false
public_async_worker_event_source_enabled = false
public_async_worker_reserved_concurrency = 0
```

The offline verifier then stopped before producing admission evidence because the AWS provider represented each Lambda `environment.variables` map as plan-unknown. This is expected Terraform JSON behavior when a composite value contains members that are not known until apply; unknown values may be omitted or represented as null in `change.after`, with the corresponding uncertainty represented under `change.after_unknown`.

The failed verifier run performed no Terraform apply and no runtime/IAM/public-endpoint mutation.

## Correction

Gate 19.6 must not invent an unknown provider value merely to make admission pass. The verifier therefore now distinguishes:

```text
plan-known environment map
  -> verify the disabled runtime switch directly from change.after

provider-unknown environment map
  -> require an explicit change.after_unknown marker
  -> re-run the retained Gate 19.4 offline source/evidence verifier
  -> require the Gate 19.6 safety outputs to remain exact and plan-known
  -> continue verifying all other plan-known critical resource attributes
```

This preserves fail-closed behavior. A missing environment map without an `after_unknown` marker is rejected. Safety-output drift is rejected. Known environment maps with an enabled switch are still rejected.

## Retained authority

```text
terraform plan:                 HUMAN_ONLY / read-oriented provider boundary
terraform apply:                FORBIDDEN
runtime AWS mutation:           FORBIDDEN
IAM mutation:                   FORBIDDEN
public endpoint enablement:     FORBIDDEN
submit enablement:              FORBIDDEN
worker/event-source enablement: FORBIDDEN
provider-heavy execution:       FORBIDDEN
third-party repository exec:    FORBIDDEN
PR #89 modification:            FORBIDDEN
```

The exact plan must be regenerated from the reviewed correction head before canonical Gate 19.6 admission evidence is persisted. `plan != apply` remains the controlling invariant.
