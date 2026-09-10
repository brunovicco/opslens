# ADR 0069 — Bounded Scheduled-Ingestion Pause

- Status: Accepted
- Date: 2026-09-10
- Phase: 17 — Security Hardening
- Gate: 17.6 — Operational recovery / kill-switch / abuse-cost controls

## Context

OpsLens has no retained public HTTP transport, so WAF, edge rate limiting, tenant quotas, and a public-request kill switch are not current runtime controls to implement. Model paths already have bounded input/context/output budgets, explicit `max_tokens`, fail-closed stop-reason handling, and measured cost evidence. Athena also retains a 10 MiB bytes-scanned cutoff per query.

The real continuously automated surface is narrower: three EventBridge Scheduler resources start recurring source ingestion in the dev environment.

```text
aws_scheduler_schedule.epss_daily
aws_scheduler_schedule.kev_daily
aws_scheduler_schedule.nvd_incremental_hourly
```

Before Gate 17.6, every schedule hard-coded `state = "ENABLED"`. Each schedule already bounded Scheduler delivery amplification to a 3600-second maximum event age and two retries, and downstream asynchronous Lambda paths retained independent OnFailure SQS destinations.

The missing control was therefore not a global platform kill switch. It was a reversible, Terraform-owned way to stop **future recurring source-ingestion starts** without destroying Lambdas, IAM, persisted evidence, or data.

## Decision

Introduce one Terraform boolean:

```text
scheduled_ingestion_enabled
```

with normal/default value `true`.

All three retained source schedules derive their state from the same mapping:

```text
true  -> ENABLED
false -> DISABLED
```

The same operational-control module freezes the existing Scheduler delivery budget:

```text
maximum_event_age_in_seconds = 3600
maximum_retry_attempts       = 2
```

A repository verifier discovers every `aws_scheduler_schedule` in the dev Terraform root and fails if the schedule set changes without explicit review, if any retained schedule hard-codes state, or if a schedule stops using the shared retry/event-age contract.

A dedicated read-only GitHub Actions workflow executes that verifier. Existing Terraform CI remains responsible for HCL formatting, validation, TFLint, and Checkov.

The first live proof is intentionally deferred until after protected merge. A human may perform a measured `false -> true` experiment only when the Terraform pause plan shows exactly three in-place schedule updates and no other resource changes.

## Scope semantics

This control is deliberately named a **scheduled-ingestion pause**, not a global kill switch.

`DISABLED` prevents future Scheduler-triggered starts for the three recurring ingestion schedules. It does not claim to cancel or revoke:

```text
in-flight Lambda invocations
already accepted Scheduler retry deliveries
S3 notifications already emitted or being processed
manual Lambda invocations
historical/manual workflows
model calls initiated through separate non-scheduled paths
tool/capability authorization
```

Downstream S3 event processing remains enabled so already-admitted work can complete or reach its existing failure destination.

## Alternatives rejected

### Add API Gateway/WAF/rate limiting

Rejected because no public HTTP runtime is retained. Building public-edge controls solely for portfolio completeness would create infrastructure without a protected surface.

### Add a new standing incident IAM role

Rejected for the first slice. Repository design and a bounded human experiment can prove the recovery mechanism without creating new standing cloud authority.

### Reuse the shared GitHub deploy role in a new emergency workflow

Rejected for the first slice. Existing deployment authority is not automatically incident-control authority, and no new operational workflow needs to inherit unrelated deployment permissions.

### Disable S3 notifications or Lambda concurrency simultaneously

Rejected as too broad for the first measured control. It could interrupt already-admitted deterministic transformation/recovery work and would make recovery semantics harder to interpret.

### Destroy schedules or Lambdas

Rejected because recovery should be fast and reversible without removing deployed code, IAM, or evidence.

## Operational consequence

The default remains `true`, so merging this ADR and Terraform implementation does not disable workloads.

During an active pause, operators must explicitly keep `scheduled_ingestion_enabled=false` on every Terraform plan/apply. A later ordinary apply using the default `true` is a resume operation and must not be treated as an inert infrastructure apply. The runbook makes this behavior explicit.

## Security and authority boundaries

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

No model, agent, MCP, A2A, or Inspector component can set this Terraform variable as business authority.

## AWS / IAM impact before measured experiment

```text
AWS mutations:          0
new IAM permissions:    0
new IAM principals:     0
new AWS services:       0
model invocations:      0
capability executions:  0
```

The later measured disable/verify/re-enable experiment is a separate explicit human AWS mutation boundary.

## Consequences

Positive:

- recurring source ingestion can be paused without resource destruction;
- the pause surface is exact and reviewable;
- normal state remains unchanged by merge;
- existing retry-cost boundaries become shared and regression-checked;
- no standing recovery IAM is added;
- future new Scheduler resources cannot silently bypass the recovery contract.

Trade-offs:

- the control does not stop in-flight or downstream already-admitted work;
- a live proof still requires a human Terraform apply;
- pause state is an explicit Terraform input rather than a separate persistent operational control plane, so all incident-time plans/applies must keep the false value until recovery is intended.

## Evidence

```text
issue: #270
labs/phase-17-gate-17-6-operational-recovery.md
labs/evidence/phase-17-gate-17-6-operational-recovery-v1.json
scripts/verify_operational_recovery.py
docs/runbooks/scheduled-ingestion-pause.md
```

## AIP-C01 learning checkpoint

A production GenAI platform should distinguish **where cost can actually be generated** from generic security checklists. Token budgets, query scan limits, retry bounds, trigger controls, and public-edge quotas solve different problems. A kill switch is useful only when its scope and authority are explicit; a vague global switch can be less safe than a small reversible control over the real automated trigger surface.
