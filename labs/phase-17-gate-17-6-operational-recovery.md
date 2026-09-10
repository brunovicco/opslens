# Phase 17 — Gate 17.6: Operational Recovery / Scheduled-Ingestion Pause / Abuse-Cost Controls

_Date: 2026-09-10_

## Status

**IN PROGRESS — repository recovery control implemented; exact-head CI and one measured human AWS pause/resume experiment pending.**

## Objective

Harden only the operational recovery surface that actually exists in the retained OpsLens runtime.

OpsLens does not currently retain a public HTTP transport. Therefore Gate 17.6 does not invent WAF, API Gateway, tenant quotas, public rate limiting, or a fictional global kill switch solely to satisfy a checklist.

Instead, the gate asks two concrete questions:

```text
1. Are already-retained model/query cost-amplification controls still bounded?
2. Can the real recurring source-ingestion triggers be paused reversibly without destroying the platform?
```

## Source checkpoint

```text
main:  d100bc67f83689e64901c723919803bc20e93f4f
issue: #270
ADR:   0069-bounded-scheduled-ingestion-pause.md
```

Canonical machine-readable evidence:

```text
labs/evidence/phase-17-gate-17-6-operational-recovery-v1.json
```

## Existing cost / abuse controls — retain, do not recreate

Gate 17.1 already identified denial-of-wallet/resource-exhaustion risk and retained bounded controls instead of a new generic quota layer.

Observed controls at the Gate 17.6 source checkpoint:

```text
public HTTP runtime:                         NOT DEPLOYED
edge WAF/rate-limit/tenant quota:            NOT APPLICABLE TO RETAINED RUNTIME
public input:                                bounded
retrieval/context assembly:                  bounded
semantic planner max_tokens:                 256
single-agent reasoning max_tokens:           96
triage reasoning max_tokens:                 64
knowledge synthesis max_tokens:              2048
provider max-token stop handling:            fail closed where required
Athena bytes scanned cutoff per query:        10 MiB
public GitHub acquisition adaptive retries:  NONE
Gate 17.4 cost-amplification regression:     RETAIN
```

These controls operate at different boundaries. In particular:

```text
model token budget != tenant quota
query scan cutoff != request rate limit
retry bound != cost attribution
```

A public-edge quota system should be evaluated if a public runtime is later deployed; it is not evidence-backed work for the current retained topology.

## Real recurring runtime surface

The dev Terraform root contains exactly three EventBridge Scheduler resources that initiate recurring source ingestion:

```text
aws_scheduler_schedule.epss_daily
  group: opslens-dev-epss
  name:  opslens-dev-epss-daily

aws_scheduler_schedule.kev_daily
  group: opslens-dev-kev
  name:  opslens-dev-kev-daily

aws_scheduler_schedule.nvd_incremental_hourly
  group: opslens-dev-nvd-incremental
  name:  opslens-dev-nvd-incremental-hourly
  cadence: every two hours
```

Before Gate 17.6, all three hard-coded:

```hcl
state = "ENABLED"
```

All three already bounded Scheduler delivery amplification to:

```text
maximum_event_age_in_seconds = 3600
maximum_retry_attempts       = 2
```

Downstream asynchronous Lambda paths separately retain bounded retry behavior and SQS OnFailure destinations.

## Observed recovery gap — OPS17-001

The retained infrastructure had no single Terraform-owned reversible control to stop **future automatic recurring ingestion starts** while preserving:

```text
deployed Lambdas
IAM
S3 data/evidence
SQS failure evidence
S3 event-chain configuration
manual recovery paths
```

Destroying resources would be unnecessarily broad. Disabling every downstream event path or forcing Lambda concurrency to zero would also make already-admitted work and recovery semantics harder to interpret.

## Implemented control

Gate 17.6 introduces:

```hcl
variable "scheduled_ingestion_enabled" {
  type    = bool
  default = true
}
```

with one exact state mapping:

```text
true  -> ENABLED
false -> DISABLED
```

All three retained recurring schedules now use:

```hcl
state = local.scheduled_ingestion_state
```

The existing Scheduler delivery budget is also centralized without changing its values:

```text
3600-second maximum event age
2 maximum retry attempts
```

The default remains `true`, so repository merge alone is non-disruptive and should produce no runtime resource diff against the normal enabled state.

## Static fail-closed verification

`scripts/verify_operational_recovery.py` discovers every Terraform `aws_scheduler_schedule` resource in the dev environment and freezes the current reviewed surface.

It fails if:

```text
a new Scheduler resource appears without explicit recovery review
one of the three expected schedules disappears
any retained schedule hard-codes ENABLED/DISABLED
any retained schedule stops using the shared state control
any retained schedule stops using the shared retry/event-age budget
scheduled_ingestion_enabled stops defaulting to true
retry budget drifts away from 2 / 3600 seconds
```

Success marker:

```text
operational_recovery_invariants=PASS schedules=3 max_retries=2 max_event_age_seconds=3600
```

Dedicated workflow:

```text
.github/workflows/operational-recovery-ci.yml
permission: contents: read
AWS/OIDC authority: none
```

The universal `Security Hardening CI` independently verifies the new workflow against repository-wide action pinning, checkout credential, trigger, and permission rules.

## Operator runbook

The live operational procedure is frozen in:

```text
docs/runbooks/scheduled-ingestion-pause.md
```

The first live experiment is not authorized from an implementation branch. It occurs only after protected merge and requires a human AWS boundary.

Pause acceptance criteria:

```text
Terraform default plan before experiment: NO CHANGES
pause resource plan:                     0 add / 3 change / 0 destroy
only changed resources:                  the three Scheduler schedules
only intended operational transition:    ENABLED -> DISABLED
independent AWS reads:                    all three DISABLED
```

Resume acceptance criteria:

```text
resume resource plan:                     0 add / 3 change / 0 destroy
only changed resources:                   the same three Scheduler schedules
only intended operational transition:    DISABLED -> ENABLED
independent AWS reads:                    all three ENABLED
final default Terraform plan:             NO CHANGES / detailed exit code 0
```

Any additional resource diff means:

```text
STOP / DO NOT APPLY
```

## Important incident-time Terraform semantic

The variable defaults to `true` so normal desired state is explicit and non-disruptive.

While an operational pause is active, **every** Terraform plan/apply against the dev root must pass:

```text
-var='scheduled_ingestion_enabled=false'
```

Omitting the value during an active pause asks Terraform to restore the normal `ENABLED` state. This is a resume operation and must not be mistaken for an inert infrastructure apply.

## What the control does not claim

A successful Scheduler disable proves only that future recurring Scheduler starts are paused at the measured control-plane state.

It does not prove termination of:

```text
in-flight Lambda invocations
already accepted Scheduler retry deliveries
S3 notifications already emitted or being processed
manual invocations
historical workflows
model/tool capability paths
```

The downstream S3 event chain intentionally remains active in this first slice so already-admitted deterministic work can finish or reach its existing failure destination.

## Permanent interpretation boundaries added by Gate 17.6

```text
scheduler pause != global workload termination
scheduler state != business/evidence authority
recovery control != authorization bypass
pause request != applied AWS state
bounded retry != guaranteed delivery
failure destination != successful recovery
model token budget != tenant quota
no public runtime != proof future edge controls are unnecessary
```

## Authority impact before live experiment

```text
AWS mutations:          0
new IAM permissions:    0
new IAM principals:     0
new AWS services:       0
model invocations:      0
capability executions:  0
new public runtime:     0
PR #89 changes:         0
```

## Deferred until evidence exists

```text
public-edge WAF/rate limiting/tenant quotas
new incident IAM principal
shared-deploy-role emergency workflow
S3 event-chain kill switch
Lambda reserved-concurrency kill switch
automatic alarm-triggered remediation
broad retry-policy redesign
```

These may be evaluated later only against a concrete retained runtime and recovery requirement.

## Decision

Retain the bounded Terraform scheduled-ingestion pause if exact-head CI is green, then require one measured human disable/verify/resume/convergence experiment before Gate 17.6 is closed.

The design deliberately prefers a small reversible control over the real automatic trigger surface instead of a broad global switch whose semantics would be difficult to prove.

## AIP-C01 learning checkpoint

Operational safety for GenAI systems is not only about model guardrails. Cost and recovery controls live at several layers: model tokens, retrieval size, query scan budgets, retry policies, schedulers, concurrency, and public-edge admission. The important architecture skill is matching the control to the actual authority and failure surface rather than applying one generic pattern everywhere.
