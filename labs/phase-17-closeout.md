# Phase 17 — Security Hardening — Closeout

_Date: 2026-09-10_

## Status

**COMPLETE — evidence-backed security hardening retained; Phase 18 is next.**

Phase 17 hardened only observed gaps. It did not add a generic security stack, invent a public attack surface, or broaden cloud/model/tool authority for portfolio completeness.

## Source checkpoint

```text
Gate 17.7 PR:                  #276
Gate 17.7 exact head:          ea0460e549dd1b904d139632bfc2988671e23880
Gate 17.7 protected merge:     3938c6469a979f5b574755ce9fd56a56523626dc
Phase 17 closeout issue:       #277
```

Gate 17.7 exact-head validation before merge:

```text
Security Hardening CI  34474712369 / #34 / SUCCESS
Dependency Review      34474712371 / #19 / SUCCESS
CodeQL / Python        34474712380 / #27 / SUCCESS
```

## Gate progression

```text
Gate 17.1  cross-cutting threat/control-gap inventory
             -> COMPLETE / evidence-first priorities

Gate 17.2  CI/CD and workflow authority hardening
             -> COMPLETE / required protected-main context enforced

Gate 17.3  dependency and code-scanning hardening
             -> COMPLETE / Dependency Review + CodeQL retained

Gate 17.4  adversarial authority-boundary regression
             -> COMPLETE / 8 cases / 7 threat classes

Gate 17.5  sensitive-data/logging/telemetry hardening
             -> COMPLETE / 12 Lambda handlers hardened

Gate 17.6  operational recovery / abuse-cost controls
             -> COMPLETE / bounded scheduled-ingestion pause + live proof

Gate 17.7  accumulated architecture synchronization
             -> COMPLETE / SEC17-DOC-001 closed

Gate 17.8  Phase 17 closeout
             -> COMPLETE BY THIS SLICE AFTER PROTECTED MERGE
```

## What Phase 17 changed

### 1. Merge and workflow authority became enforceable

The repository retains one universal protected-main status context:

```text
Repository security invariants
```

Security CI freezes full-SHA external actions, rejects unsafe trigger/permission drift by default, and requires checkout without persisted Git credentials where post-checkout authentication is unnecessary.

EPSS historical planning and execution identities are separated, and the long STS session is limited to the actual bounded full-backfill execution path.

The historical AgentCore mutating workflow is retired/fail-closed rather than being treated as harmless merely because its original experiment ended.

### 2. Continuous repository-native security signals exist

Gate 17.3 retained:

```text
Dependency Review   pull_request / fail-on-severity=high
CodeQL / Python     pull_request + main + weekly + manual
```

Their permissions remain bounded and they hold no AWS/OIDC authority.

```text
dependency finding != vulnerability applicability authority
code-scanning alert != runtime exploitability truth
security scan success != absence of vulnerabilities
```

### 3. Adversarial regression attacks authority boundaries

The retained deterministic suite contains eight cases across seven threat classes:

```text
public-input abuse
prompt injection / indirect instruction content
single/multi-agent capability widening
forged capability-result evidence
MCP dynamic/cross-capability abuse
A2A reference smuggling
cost/call/retry/fallback amplification
```

No first-slice case justified a business-logic redesign.

```text
adversarial test success != proof of universal safety
```

### 4. Lambda telemetry is content-minimized at the capture boundary

Across 12 Powertools Lambda handlers:

```text
log_event=False
capture_response=False
capture_error=False
```

Shared failure logging avoids implicit active-exception traceback serialization. The repository verifier prevents silent regression of those settings.

### 5. A real automated recovery gap received a bounded control

The retained recurring source-ingestion trigger surface is exactly:

```text
aws_scheduler_schedule.epss_daily
aws_scheduler_schedule.kev_daily
aws_scheduler_schedule.nvd_incremental_hourly
```

One Terraform boolean owns only their recurring-start state:

```text
scheduled_ingestion_enabled=true   -> ENABLED
scheduled_ingestion_enabled=false  -> DISABLED
```

Existing Scheduler delivery amplification remains:

```text
maximum_event_age_in_seconds = 3600
maximum_retry_attempts       = 2
```

The measured live experiment proved:

```text
default Terraform convergence
 -> exact 0 add / 3 change / 0 destroy pause plan
 -> exact saved-plan apply
 -> independent 3/3 DISABLED Scheduler reads
 -> paused-state Terraform convergence
 -> exact 0 add / 3 change / 0 destroy resume plan
 -> exact saved-plan apply
 -> independent 3/3 ENABLED Scheduler reads
 -> final default Terraform convergence
```

The experiment created and destroyed zero resources and ended in the original normal desired state.

This is a **scheduled-ingestion pause**, not a global kill switch. It does not claim to cancel already running Lambdas, accepted retries, emitted S3 events, manual paths, separate model calls, or capability authorization.

### 6. Architecture documentation now represents the retained system

Gate 17.7 closed `SEC17-DOC-001`, replacing the stale Phase-9-era accumulated architecture status with synchronized EN/PT-BR architecture through Phase 17's retained controls.

Documentation remains descriptive evidence, not execution authority.

## Original observed-gap disposition

```text
SEC17-CICD-001  CLOSED / required CI is enforced by protected main
SEC17-CICD-003  CLOSED / checkout credentials are not persisted by default
SEC17-IAM-002   CLOSED / EPSS plan and execution authority separated
SEC17-IAM-003   CLOSED / historical AgentCore mutation path retired
SEC17-SUPPLY-001 CLOSED FOR RETAINED SCOPE / Dependency Review + CodeQL retained
SEC17-DOC-001   CLOSED / accumulated architecture synchronized
OPS17-001       CLOSED / bounded recurring-ingestion pause retained and measured
```

The supply-chain closure does not imply automated version updates or a second continuous dependency-audit engine. Those are explicit deferrals.

## Final retained Phase 17 posture

```text
protected-main security context:              RETAIN / ENFORCED
repository workflow security verifier:        RETAIN
Dependency Review:                            RETAIN
CodeQL Python:                                RETAIN
adversarial authority regression suite:       RETAIN
content-minimized Lambda telemetry controls:  RETAIN
telemetry safety verifier:                    RETAIN
bounded scheduled-ingestion pause:            RETAIN
operational recovery runbook:                 RETAIN
EN/PT-BR synchronized architecture:           RETAIN
```

## Explicit deferrals / not-created surfaces

```text
Dependabot version-update automation:          DEFER
additional continuous pip-audit:               DEFER
broad dependency upgrades:                     NOT AUTHORIZED BY PHASE 17
independent approval requirement:              DEFER UNTIL GOVERNANCE NEED EXISTS
public WAF/rate limit/tenant quota:             NOT APPLICABLE WITHOUT PUBLIC RUNTIME
public HTTP runtime:                           NOT CREATED
global kill switch:                            NOT CREATED
S3 event-chain kill switch:                    NOT CREATED
Lambda concurrency kill switch:                NOT CREATED
automatic alarm remediation:                   NOT CREATED
standing Inspector experiment IAM:             NONE
Inspector activation to manufacture evidence:  NOT CREATED
public MCP/A2A runtime:                        NOT CREATED
AgentCore default runtime:                     NOT RETAINED
```

## Authority and cost impact of Gate 17.8

Gate 17.8 is documentation/evidence closeout only:

```text
AWS mutations:          0
new IAM permissions:    0
new IAM principals:     0
new AWS services:       0
runtime mutations:      0
model invocations:      0
capability executions:  0
incremental AWS cost:   USD 0.00
PR #89 touched:         false
```

No synthetic USD amount is assigned to earlier phases that reported cost as unmeasured. Phase 18 must preserve measured, derived, and unmeasured categories separately.

## Permanent interpretation boundaries reinforced

```text
Agents reason. Code verifies evidence.
Repository Risk != Runtime Exposure.
CI evidence != enforced merge gate
security scan success != absence of vulnerabilities
scanner output != model authority
untrusted text != instruction authority
retrieved content != system/developer authority
failed/forged capability result != admissible business result
adversarial test success != proof of universal safety
log event suppression != trace response/error suppression
exception text != safe telemetry by default
scheduler pause != global workload termination
Terraform apply success != independent AWS state verification
bounded retry != guaranteed delivery
model token budget != tenant quota
historical evidence != standing authority
```

## Canonical Phase 17 records

```text
docs/adr/0064-evidence-first-security-hardening-priorities.md
docs/adr/0065-ci-cd-and-workflow-authority-hardening.md
docs/adr/0066-bounded-dependency-and-code-scanning-signals.md
docs/adr/0067-bounded-adversarial-authority-regression-suite.md
docs/adr/0068-content-minimized-lambda-telemetry.md
docs/adr/0069-bounded-scheduled-ingestion-pause.md
docs/adr/0070-phase17-security-hardening-closeout.md

labs/phase-17-gate-17-1-threat-model.md
labs/phase-17-gate-17-2-workflow-authority-hardening.md
labs/phase-17-gate-17-2-main-ruleset-enforcement.md
labs/phase-17-gate-17-3-dependency-code-scanning.md
labs/phase-17-gate-17-3-closeout.md
labs/phase-17-gate-17-4-adversarial-boundaries.md
labs/phase-17-gate-17-4-closeout.md
labs/phase-17-gate-17-5-telemetry-safety.md
labs/phase-17-gate-17-5-closeout.md
labs/phase-17-gate-17-6-operational-recovery.md
labs/phase-17-gate-17-6-closeout.md
labs/phase-17-gate-17-7-architecture-sync.md
labs/phase-17-closeout.md
```

## AIP-C01 learning checkpoint

Phase 17 reinforces professional-level design by separating prevention, detection, authorization, observability, recovery, and cost controls instead of treating "security" as one layer. The useful control is the smallest one mapped to a real threat and authority surface, with measurable success and failure semantics.

## Next phase

**Phase 18 — Evaluation, Cost & Portfolio Readiness.**

Start by consolidating existing evidence and defining which measurements are comparable before creating new experiments. Do not manufacture production claims from dev/lab data and do not add runtime authority merely for presentation.