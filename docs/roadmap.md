# OpsLens — Incremental Roadmap

_Last updated: 2026-09-10_

OpsLens advances in small, demonstrable, observable, reversible gates.

Default engineering loop:

```text
real gap or explicit hypothesis
 -> issue
 -> architecture/authority decision
 -> IAM / trust boundary when applicable
 -> smallest implementation or documentation slice
 -> success test
 -> meaningful failure test
 -> observability
 -> cost
 -> immutable evidence
 -> draft PR
 -> exact-head CI
 -> protected squash merge
 -> post-merge verification
 -> issue closure
```

## Current roadmap status

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | AWS Foundation | ✅ Complete |
| 1 | EPSS Vertical Slice | ✅ Complete |
| 2 | Threat Intelligence Data Lake | ✅ Complete |
| 3 | Vulnerability Correlation Engine | ✅ Complete |
| 4 | Repository Intelligence | ✅ Complete |
| 5 | Risk Prioritization Engine | ✅ Complete |
| 6 | Semantic Query Layer | ✅ Complete |
| 7 | Knowledge Retrieval with Bedrock | ✅ Complete |
| 8 | Hybrid Retrieval | ✅ Complete |
| 9 | Public Analyze Your Repository | ✅ Complete |
| 10 | Observability & Operational Excellence | ✅ Complete |
| 11 | Single-Agent Baseline | ✅ Complete |
| 12 | Multi-Agent Architecture | ✅ Complete |
| 13 | MCP | ✅ Complete — bounded offline interoperability retained |
| 14 | Amazon Bedrock AgentCore | ✅ Complete — optional lab target retained; standing experiment IAM removed |
| 15 | A2A | ✅ Complete — bounded offline reference interoperability + official SDK conformance retained |
| 16 | Runtime Exposure with Amazon Inspector | ✅ Complete — read contract proven; zero current records; temporary IAM removed |
| 17 | Security Hardening | ✅ Complete — evidence-backed hardening + measured recovery retained |
| 18 | Evaluation, Cost & Portfolio Readiness | ▶️ Next |

## Permanent engineering boundaries

> **Agents reason. Code verifies evidence.**

> **MCP is an interoperability boundary, not new business authority.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

```text
proposal != authorization
retrieval result != sufficient evidence
repository finding != runtime exposure
CI evidence != enforced merge gate
historical evidence != standing authority
dependency finding != vulnerability applicability authority
code-scanning alert != runtime exploitability truth
security scan success != absence of vulnerabilities
untrusted text != instruction authority
adversarial test success != proof of universal safety
exception text != safe telemetry by default
scheduler pause != global workload termination
Terraform apply success != independent AWS state verification
measured value != derived estimate
unmeasured != zero
portfolio summary != new technical authority
```

## Completed platform through Phase 16

Phases 0–10 established the AWS foundation, source-preserving threat-intelligence ingestion, deterministic vulnerability correlation, repository intelligence, deterministic Risk Policy v1, bounded semantic query, Bedrock Knowledge Base retrieval with Amazon S3 Vectors, hybrid evidence, governed public-analysis application boundaries, and content-minimized operational observability.

Phase 11 retained the measured single-agent Bedrock reference. Phase 12 retained deterministic specialization/handoff but rejected the measured two-model topology as the default because it added cost/latency without quality lift. Phase 13 retained bounded offline MCP interoperability. Phase 14 retained AgentCore only as an optional lab target and removed standing experiment IAM. Phase 15 retained bounded offline A2A reference interoperability plus an exact-source official SDK CI oracle. Phase 16 retained a typed read-only Inspector evidence boundary, preserved its zero-record measurement, and removed temporary Inspector IAM after the bounded experiment.

## Phase 17 — Security Hardening — COMPLETE

Purpose: evaluate the retained platform as an attacker and operator would, then harden only evidenced gaps while preserving deterministic authority and least privilege.

### Gate 17.1 — threat/control-gap inventory — COMPLETE

Established the evidence-first inventory and prioritized observed CI/CD, IAM, supply-chain, telemetry, operational recovery, and documentation risks.

Canonical records:

```text
docs/adr/0064-evidence-first-security-hardening-priorities.md
labs/phase-17-gate-17-1-threat-model.md
labs/evidence/phase-17-gate-17-1-threat-model-v1.json
```

### Gate 17.2 — CI/CD and workflow authority — COMPLETE

Retained:

```text
required PR context:                         Repository security invariants
external actions:                            full 40-hex SHA pins
checkout persisted credentials:              disabled where unnecessary
pull_request_target/workflow_run:             rejected by default
EPSS plan identity:                          read-only evidence role
EPSS execution identity:                     coordinator role
21600-second STS session:                    execute-only full-backfill path
historical AgentCore mutation workflow:      retired / fail-closed
```

Protected `main` independently rejected a direct write, proving merge enforcement.

### Gate 17.3 — dependency and code scanning — COMPLETE

Retained bounded GitHub-native signals:

```text
Dependency Review  pull_request / fail-on-severity=high / contents:read
CodeQL Python      PR + main + weekly + manual / security-events:write only where required
AWS/OIDC authority none
```

Dependabot version updates and an additional continuous `pip-audit` remain explicit deferrals.

### Gate 17.4 — adversarial authority regression — COMPLETE

Retained eight deterministic cases across seven threat classes covering public input, prompt injection, capability widening, forged results, MCP, A2A, and amplification attempts.

```text
AWS/OIDC authority:    none
model invocations:     0
capability executions: 0
```

### Gate 17.5 — telemetry hardening — COMPLETE

Across 12 retained Powertools Lambda handlers:

```text
automatic input-event logging:    disabled
automatic trace response capture: disabled
automatic trace error capture:    disabled
implicit exception traceback:     disabled
repository verifier:              retained
```

### Gate 17.6 — operational recovery / abuse-cost controls — COMPLETE

One Terraform control governs exactly the three recurring source-ingestion schedules:

```text
scheduled_ingestion_enabled=true   -> ENABLED
scheduled_ingestion_enabled=false  -> DISABLED
```

Scheduler delivery remains bounded to 3600 seconds of event age and two retries.

The measured human AWS experiment proved exact three-resource pause/resume plans and applies, independent `DISABLED`/`ENABLED` reads, and final Terraform convergence. No resources were created or destroyed.

```text
scheduled-ingestion pause != global kill switch
```

### Gate 17.7 — architecture synchronization — COMPLETE

Closed `SEC17-DOC-001` by synchronizing the accumulated EN/PT-BR architecture with the retained platform.

```text
PR:                       #276
exact head:               ea0460e549dd1b904d139632bfc2988671e23880
protected merge:          3938c6469a979f5b574755ce9fd56a56523626dc
Security Hardening CI:    34474712369 / #34 / SUCCESS
Dependency Review:        34474712371 / #19 / SUCCESS
CodeQL / Python:          34474712380 / #27 / SUCCESS
```

### Gate 17.8 — Security Hardening closeout — COMPLETE BY CLOSEOUT PR

Canonical closeout:

```text
docs/adr/0070-phase17-security-hardening-closeout.md
labs/phase-17-closeout.md
labs/evidence/phase-17-closeout-v1.json
```

Final retained Phase 17 posture:

```text
protected-main security enforcement          RETAIN
Dependency Review + CodeQL                    RETAIN
adversarial authority regression              RETAIN
content-minimized Lambda telemetry            RETAIN
telemetry safety verifier                     RETAIN
bounded scheduled-ingestion pause             RETAIN
operational recovery runbook                  RETAIN
synchronized EN/PT-BR architecture            RETAIN
```

Explicitly not created or deferred:

```text
Dependabot version-update automation          DEFER
additional continuous pip-audit               DEFER
broad dependency upgrades                     NOT AUTHORIZED BY PHASE 17
mandatory independent review                  DEFER UNTIL GOVERNANCE NEED EXISTS
public WAF/rate limiting/tenant quota         NOT APPLICABLE WITHOUT PUBLIC RUNTIME
public HTTP runtime                           NOT CREATED
global platform kill switch                   NOT CREATED
S3/Lambda broad emergency stop controls       NOT CREATED
automatic alarm remediation                   NOT CREATED
standing Inspector experiment IAM             NONE
public MCP/A2A runtime                        NOT CREATED
AgentCore as default runtime                  NOT RETAINED
```

## Phase 18 — Evaluation, Cost & Portfolio Readiness — NEXT

Purpose: consolidate the evidence generated across prior phases into a coherent evaluation, cost, reliability, security, and portfolio view without converting unlike measurements into false precision.

### Gate 18.1 — cross-phase evidence inventory and comparability matrix — NEXT

Before new experiments, inventory the existing immutable evidence set and classify each metric/value as:

```text
MEASURED
DERIVED
UNMEASURED
NOT_APPLICABLE
```

Build an explicit comparability matrix for quality, latency, cost, retries, capability executions, retrieval/groundedness, security regressions, and cloud/runtime measurements.

Exit criteria:

- every retained headline metric points to a canonical evidence artifact;
- values from different workloads are not silently compared as equivalents;
- measured vs derived vs unmeasured is explicit;
- no composite score is introduced without an explicit later hypothesis;
- zero AWS/IAM/runtime mutation is required for the first slice.

### Candidate Gate 18.2 — consolidated evaluation and reliability view

Use Gate 18.1 comparability decisions to build independent evaluation dimensions. Preserve failure-path evidence and rejected hypotheses rather than showing success-only metrics.

### Candidate Gate 18.3 — cost accounting and budget envelope

Consolidate measured provider/runtime costs, Athena scan boundaries, token budgets, retry limits, and unmeasured infrastructure dimensions. Do not equate an unmeasured value with zero.

### Candidate Gate 18.4 — portfolio/demo evidence pack and AIP-C01 synchronization

Improve discoverability and recruiter/architect-facing presentation only after the underlying measurements are traceable. Synchronize learning-map references where evidence exists.

### Candidate Gate 18.5 — Phase 18 / project-readiness closeout

Close only after the evidence pack, cost/evaluation boundaries, and project-facing documentation agree with the retained implementation.

## Deferred cross-project integration

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains separate Governed LLM Gateway work and must not be modified or merged as a side effect of Phase 18 unless explicitly re-authorized.
