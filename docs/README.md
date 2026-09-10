# OpsLens Documentation

OpsLens documentation is organized around current architecture, implementation state, incremental roadmap, ADRs, gate laboratories, and immutable evaluation/runtime evidence.

## Primary documents

- [`architecture.md`](architecture.md) — accumulated architecture baseline.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture baseline.
- [`current-state.md`](current-state.md) — authoritative implementation checkpoint.
- [`roadmap.md`](roadmap.md) — incremental phase/gate plan and completion status.
- [`adr/`](adr/) — accepted architecture decisions.
- [`../labs/`](../labs/) — gate laboratories and immutable evidence references.

## Current implementation checkpoint

```text
Phase 0  AWS Foundation                         COMPLETE
Phase 1  EPSS Vertical Slice                    COMPLETE
Phase 2  Threat Intelligence Data Lake          COMPLETE
Phase 3  Vulnerability Correlation Engine       COMPLETE
Phase 4  Repository Intelligence                COMPLETE
Phase 5  Risk Prioritization Engine             COMPLETE
Phase 6  Semantic Query Layer                   COMPLETE
Phase 7  Knowledge Retrieval with Bedrock       COMPLETE
Phase 8  Hybrid Retrieval                       COMPLETE
Phase 9  Public Analyze Your Repository         COMPLETE
Phase 10 Observability & Operational Excellence COMPLETE
Phase 11 Single-Agent Baseline                  COMPLETE
Phase 12 Multi-Agent Architecture               COMPLETE
Phase 13 MCP                                    COMPLETE
Phase 14 Amazon Bedrock AgentCore               COMPLETE
Phase 15 A2A                                    COMPLETE
Phase 16 Runtime Exposure with Inspector        COMPLETE
Phase 17 Security Hardening                     COMPLETE
Phase 18 Evaluation, Cost & Portfolio           NEXT
```

## Permanent authority separations

```text
Agents reason. Code verifies evidence.
Repository Risk != Runtime Exposure.
agent proposal != authorization
handoff proposal != handoff admission
capability invocation != execution result
execution result != admitted evidence
MCP call admission != capability execution
MCP result projection != public runtime exposure
AgentCore hosting != business authorization
A2A message != capability authorization
A2A transport success != business/evidence truth
AWS authentication != Inspector read authorization
Inspector API success != runtime evidence presence
CI evidence != enforced merge gate
historical evidence != standing authority
dependency finding != vulnerability applicability authority
code-scanning alert != runtime exploitability truth
security scan success != absence of vulnerabilities
untrusted text != instruction authority
retrieved content != system/developer authority
failed/forged capability result != admissible business result
adversarial test success != proof of universal safety
log event suppression != trace response/error suppression
exception text != safe telemetry by default
scheduler pause != global workload termination
Terraform apply success != independent AWS state verification
measured value != derived estimate
unmeasured != zero
```

## Retained measured reasoning reference

Phase 11 remains the default/reference reasoning architecture:

```text
quality:                    6/6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
derived six-case cost:      USD 0.0041921
```

## Retained interoperability/runtime decisions

### Phase 13 — MCP

MCP remains a bounded offline interoperability layer over existing typed capability authority. A public/network MCP runtime is not retained.

### Phase 14 — AgentCore

AgentCore remains an optional lab target, not the default OpsLens reasoning runtime. Standing experiment-specific GitHub IAM was removed after the measured experiment, and the historical mutating workflow is retired/fail-closed.

### Phase 15 — A2A

A2A retains a content-addressed reference-only JSON-RPC `SendMessage` profile plus exact-source official SDK conformance in CI. No public/network A2A runtime, A2A-specific IAM, or SDK runtime dependency is retained.

Canonical closeout:

- [`adr/0059-phase15-a2a-closeout.md`](adr/0059-phase15-a2a-closeout.md)
- [`../labs/phase-15-closeout.md`](../labs/phase-15-closeout.md)
- [`../labs/evidence/phase-15-closeout-v1.json`](../labs/evidence/phase-15-closeout-v1.json)

### Phase 16 — Amazon Inspector

Phase 16 retained Amazon Inspector only as an independent read-only runtime-evidence boundary. The measured dev account/region returned zero coverage/findings, and the temporary dedicated Inspector role was removed after the experiment.

Canonical closeout:

- [`adr/0063-phase16-runtime-exposure-closeout.md`](adr/0063-phase16-runtime-exposure-closeout.md)
- [`../labs/phase-16-closeout.md`](../labs/phase-16-closeout.md)
- [`../labs/evidence/phase-16-closeout-v1.json`](../labs/evidence/phase-16-closeout-v1.json)

## Phase 17 — Security Hardening — complete

Phase 17 began from a cross-cutting threat/control-gap inventory and retained only controls justified by evidence.

### Gate 17.1 — threat/control-gap inventory

- [`adr/0064-evidence-first-security-hardening-priorities.md`](adr/0064-evidence-first-security-hardening-priorities.md)
- [`../labs/phase-17-gate-17-1-threat-model.md`](../labs/phase-17-gate-17-1-threat-model.md)
- [`../labs/evidence/phase-17-gate-17-1-threat-model-v1.json`](../labs/evidence/phase-17-gate-17-1-threat-model-v1.json)

### Gate 17.2 — CI/CD and workflow authority

Retained protected-main enforcement, repository-wide workflow-security invariants, EPSS plan/execution identity separation, and historical AgentCore mutation-path retirement.

- [`adr/0065-ci-cd-and-workflow-authority-hardening.md`](adr/0065-ci-cd-and-workflow-authority-hardening.md)
- [`../labs/phase-17-gate-17-2-workflow-authority-hardening.md`](../labs/phase-17-gate-17-2-workflow-authority-hardening.md)
- [`../labs/phase-17-gate-17-2-main-ruleset-enforcement.md`](../labs/phase-17-gate-17-2-main-ruleset-enforcement.md)

### Gate 17.3 — dependency and code scanning

Retained bounded Dependency Review and Python CodeQL. Their outputs remain engineering signals rather than vulnerability-applicability or runtime-exploitability authority.

- [`adr/0066-bounded-dependency-and-code-scanning-signals.md`](adr/0066-bounded-dependency-and-code-scanning-signals.md)
- [`../labs/phase-17-gate-17-3-closeout.md`](../labs/phase-17-gate-17-3-closeout.md)
- [`../labs/evidence/phase-17-gate-17-3-closeout-v1.json`](../labs/evidence/phase-17-gate-17-3-closeout-v1.json)

### Gate 17.4 — adversarial authority regression

Retained eight deterministic cases across seven threat classes with zero AWS/model/capability execution authority.

- [`adr/0067-bounded-adversarial-authority-regression-suite.md`](adr/0067-bounded-adversarial-authority-regression-suite.md)
- [`../labs/phase-17-gate-17-4-closeout.md`](../labs/phase-17-gate-17-4-closeout.md)
- [`../labs/evidence/phase-17-gate-17-4-closeout-v1.json`](../labs/evidence/phase-17-gate-17-4-closeout-v1.json)

### Gate 17.5 — telemetry hardening

Retained explicit event/response/error capture suppression across 12 Powertools Lambda handlers plus repository regression verification.

- [`adr/0068-content-minimized-lambda-telemetry.md`](adr/0068-content-minimized-lambda-telemetry.md)
- [`../labs/phase-17-gate-17-5-closeout.md`](../labs/phase-17-gate-17-5-closeout.md)
- [`../labs/evidence/phase-17-gate-17-5-closeout-v1.json`](../labs/evidence/phase-17-gate-17-5-closeout-v1.json)

### Gate 17.6 — operational recovery / abuse-cost

Retained a Terraform-owned pause over exactly the three recurring source-ingestion schedules and measured one exact pause/verify/resume/convergence cycle.

```text
scheduled_ingestion_enabled=true   -> ENABLED
scheduled_ingestion_enabled=false  -> DISABLED
maximum_event_age_in_seconds       = 3600
maximum_retry_attempts             = 2
```

The control is a scheduled-ingestion pause, not a global kill switch.

- [`adr/0069-bounded-scheduled-ingestion-pause.md`](adr/0069-bounded-scheduled-ingestion-pause.md)
- [`runbooks/scheduled-ingestion-pause.md`](runbooks/scheduled-ingestion-pause.md)
- [`../labs/phase-17-gate-17-6-closeout.md`](../labs/phase-17-gate-17-6-closeout.md)
- [`../labs/evidence/phase-17-gate-17-6-closeout-v1.json`](../labs/evidence/phase-17-gate-17-6-closeout-v1.json)

### Gate 17.7 — architecture synchronization

Closed `SEC17-DOC-001` and synchronized the EN/PT-BR accumulated architecture to the retained Phase 17 state.

- [`../labs/phase-17-gate-17-7-architecture-sync.md`](../labs/phase-17-gate-17-7-architecture-sync.md)
- [`../labs/evidence/phase-17-gate-17-7-architecture-sync-v1.json`](../labs/evidence/phase-17-gate-17-7-architecture-sync-v1.json)

### Phase 17 closeout

- [`adr/0070-phase17-security-hardening-closeout.md`](adr/0070-phase17-security-hardening-closeout.md)
- [`../labs/phase-17-closeout.md`](../labs/phase-17-closeout.md)
- [`../labs/evidence/phase-17-closeout-v1.json`](../labs/evidence/phase-17-closeout-v1.json)

Explicit Phase 17 deferrals remain visible: Dependabot version updates, extra continuous `pip-audit`, broad dependency upgrades, public edge controls without a public runtime, a global kill switch, broad S3/Lambda emergency stop controls, automatic remediation, public MCP/A2A runtimes, and AgentCore as default runtime.

## Next — Phase 18

**Evaluation, Cost & Portfolio Readiness** is next.

Gate 18.1 starts with a cross-phase evidence inventory and comparability matrix. It must distinguish `MEASURED`, `DERIVED`, `UNMEASURED`, and `NOT_APPLICABLE` values before producing consolidated quality/latency/cost/security summaries.

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains a separate deferred integration and stays outside Phase 18 unless explicitly resumed.
