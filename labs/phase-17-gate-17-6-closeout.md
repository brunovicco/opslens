# Phase 17 — Gate 17.6 Closeout: Measured Scheduled-Ingestion Recovery

_Date: 2026-09-10_

## Status

**COMPLETE — repository control retained and one human AWS pause/verify/resume/convergence experiment succeeded.**

## Source checkpoint

```text
implementation PR:        #273
implementation head:      ce68642f9e90ff3515ff33e0afac40fc08acba8c
protected squash merge:   08b5cd8dc3416529455cd2d123127b6dc3dae748
experiment source main:   08b5cd8dc3416529455cd2d123127b6dc3dae748
issue:                    #270
ADR:                      0069-bounded-scheduled-ingestion-pause.md
```

The experiment was performed from protected `main` after the Gate 17.6 implementation merge. Shell output supplied for the experiment did not contain wall-clock timestamps, so this record preserves the experiment date and exact source commit without inventing more precise timing.

## Repository implementation proof

Exact implementation PR-head CI was green before merge:

```text
Operational Recovery CI   34431690226 / #1   SUCCESS
Security Hardening CI     34431690203 / #32  SUCCESS
Terraform CI              34431690191 / #275 SUCCESS
Dependency Review         34431690259 / #17  SUCCESS
CodeQL / Python           34431690199 / #23  SUCCESS
```

Retained control:

```text
scheduled_ingestion_enabled=true   -> ENABLED
scheduled_ingestion_enabled=false  -> DISABLED

maximum_event_age_in_seconds       = 3600
maximum_retry_attempts             = 2
```

Affected recurring Scheduler resources remain exactly:

```text
aws_scheduler_schedule.epss_daily
aws_scheduler_schedule.kev_daily
aws_scheduler_schedule.nvd_incremental_hourly
```

## Measured live experiment

### 1. Normal-state convergence

Before the operational mutation, Terraform compared the real dev environment to the normal/default configuration and returned:

```text
No changes. Your infrastructure matches the configuration.
terraform_default_plan_exit_code=0
```

This established a clean starting point with no unrelated drift.

### 2. Bounded pause plan

The inspected saved plan proposed exactly:

```text
Plan: 0 to add, 3 to change, 0 to destroy.
```

Only these state transitions were present:

```text
aws_scheduler_schedule.epss_daily
  ENABLED -> DISABLED

aws_scheduler_schedule.kev_daily
  ENABLED -> DISABLED

aws_scheduler_schedule.nvd_incremental_hourly
  ENABLED -> DISABLED
```

No Lambda, IAM, S3, SQS, target ARN, schedule group, schedule expression, payload, or retry-budget change was observed.

### 3. Pause apply

Terraform applied only the previously inspected saved plan:

```text
Apply complete! Resources: 0 added, 3 changed, 0 destroyed.
```

### 4. Independent AWS control-plane verification

Direct `aws scheduler get-schedule` reads reported:

```text
opslens-dev-epss-daily              DISABLED
opslens-dev-kev-daily               DISABLED
opslens-dev-nvd-incremental-hourly  DISABLED
```

This independently verified the Scheduler control-plane state instead of treating Terraform apply success as sufficient evidence.

### 5. Paused-state convergence

Terraform was then run with the explicit incident-time value:

```text
scheduled_ingestion_enabled=false
```

Result:

```text
No changes. Your infrastructure matches the configuration.
terraform_paused_plan_exit_code=0
```

### 6. Bounded resume plan

The inspected saved resume plan proposed exactly:

```text
Plan: 0 to add, 3 to change, 0 to destroy.
```

Only the inverse state transitions were present:

```text
aws_scheduler_schedule.epss_daily
  DISABLED -> ENABLED

aws_scheduler_schedule.kev_daily
  DISABLED -> ENABLED

aws_scheduler_schedule.nvd_incremental_hourly
  DISABLED -> ENABLED
```

### 7. Resume apply

Terraform applied only the inspected resume plan:

```text
Apply complete! Resources: 0 added, 3 changed, 0 destroyed.
```

### 8. Independent resumed-state verification

Direct Scheduler reads reported:

```text
opslens-dev-epss-daily              ENABLED
opslens-dev-kev-daily               ENABLED
opslens-dev-nvd-incremental-hourly  ENABLED
```

### 9. Final default convergence

A final Terraform plan using the normal/default value returned:

```text
No changes. Your infrastructure matches the configuration.
terraform_final_plan_exit_code=0
```

The dev environment therefore ended in the same normal desired state from which the experiment started.

## Gate decision

Gate 17.6 is complete.

The measured evidence proves that the retained recovery control can:

```text
normal convergence
 -> exact three-resource pause plan
 -> exact pause apply
 -> independent DISABLED verification
 -> paused-state convergence
 -> exact three-resource resume plan
 -> exact resume apply
 -> independent ENABLED verification
 -> final default convergence
```

The experiment does **not** claim termination of in-flight Lambda work, cancellation of already accepted Scheduler retries, suppression of already emitted S3 events, or revocation of manual/model/tool authority.

## Authority and cost impact

```text
new IAM permissions:       0
new IAM principals:        0
new AWS services:          0
new public runtime:        0
model invocations:         0
capability executions:     0
resources created:         0
resources destroyed:       0
reversible state updates:  6 total across pause + resume
final desired state:       ENABLED / converged
PR #89 modification:       0
```

## Retained interpretation boundaries

```text
scheduler pause != global workload termination
scheduler state != business/evidence authority
recovery control != authorization bypass
pause request != applied AWS state
Terraform apply success != independent AWS state verification
bounded retry != guaranteed delivery
failure destination != successful recovery
model token budget != tenant quota
no public runtime != proof future edge controls are unnecessary
```

## Next security-hardening decision

Gate 17.1 identified architecture-document header drift as a lower-priority documentation gap. After Gate 17.6 closeout, evaluate that concrete remaining gap before declaring Phase 17 complete. Do not add another runtime/security control without new evidence.

## AIP-C01 learning checkpoint

A recovery control is credible when its scope, authority, reversibility, and verification path are explicit. Terraform desired state, an AWS control-plane read, retry budgets, token budgets, and request-rate controls answer different operational questions. Professional-level design requires matching each control to the actual failure and cost surface rather than describing all of them as a generic kill switch.
