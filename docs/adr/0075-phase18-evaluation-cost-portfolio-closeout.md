# ADR 0075 — Close Phase 18 at the Evidence-Backed Evaluation, Cost, and Portfolio Boundary

- Status: Accepted
- Date: 2026-09-10
- Phase: 18 — Evaluation, Cost & Portfolio Readiness
- Gate: 18.5 — Phase closeout
- Issue: #289

## Context

Phase 18 began after the Phase 17 security closeout with a deliberately narrow rule: consolidate existing evidence before creating new experiments.

The completed sequence is:

```text
18.1  cross-phase evidence inventory and comparability
18.2  consolidated evaluation and reliability view
18.3  cost accounting and configured budget envelopes
18.4  evidence-bound portfolio and AIP-C01 mapping
18.5  phase closeout
```

Gate 18.4 was protected-squash-merged through PR #288 as `4a8e5d3d98504451cef26df4e9f274f2f9fd8dd0` after exact-head Security Hardening, Dependency Review, Evaluation Readiness, AgentCore, and CodeQL checks succeeded.

No remaining inconsistency in the Phase 18 evidence chain justifies another benchmark or runtime experiment before closeout.

## Decision

Close Phase 18 and retain its evaluation, cost-accounting, portfolio, and certification-learning surfaces as **evidence projections**, not new execution or business authority.

### Evidence classification and comparability

Retain the four-state evidence vocabulary:

```text
MEASURED
DERIVED
UNMEASURED
NOT_APPLICABLE
```

Retain explicit comparability admission before aggregation.

```text
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
same unit != same measurement semantics
one experiment != production distribution
```

### Evaluation and reliability

Retain independent evaluation dimensions rather than one composite readiness score. Negative/rejected-default evidence remains visible and architecture-relevant.

```text
phase7-isolation-grounding-failure
phase12-two-model-no-lift
phase14-agentcore-not-default
phase16-zero-records-not-zero-exposure
```

### Cost and resource accounting

Retain historical observed/derived cost evidence and configured limits as separate classes. Do not aggregate unrelated workloads or extrapolate production monthly TCO without a frozen workload and supporting evidence.

```text
configured limit != measured utilization
historical experiment cost != production TCO
cost artifact != production run rate
```

### Portfolio evidence

Retain the portfolio pack as a deterministic projection over admitted Gate 18.2/18.3 evidence. Numeric claims must remain source-bound to their original classification, value, unit, and scope.

```text
portfolio claim != new evidence authority
portfolio summary != production readiness score
```

### AIP-C01 learning map

Retain the current task-to-evidence map as a study and evidence-navigation aid.

```text
AIP-C01 topic != product requirement
PARTIAL != EVIDENCED
STUDY_ONLY != implemented
exam coverage != certification guarantee
```

No AWS service is introduced solely to improve certification coverage.

## Retained standing architecture

Phase 18 does not alter the standing runtime architecture or deterministic authority boundaries established by earlier phases. Source provenance, vulnerability applicability, Risk Policy, query/SQL admission, retrieval/evidence admission, capability authorization, result admission, and operational recovery remain deterministic responsibilities.

AgentCore remains an optional historical lab target rather than the default runtime. MCP and A2A remain bounded/offline interoperability surfaces. Inspector remains an independent read-only runtime-evidence boundary. Phase 17 security and recovery controls remain authoritative.

## Explicit non-claims

Phase 18 does not create or claim:

```text
public HTTP production runtime
production SLO from bounded lab metrics
production TCO or monthly run rate
public MCP/A2A runtime
AgentCore as default runtime
zero runtime exposure from zero Inspector records
global platform kill switch
configured limits as measured utilization
certification readiness score or pass probability
```

## Gate 18.5 authority impact

```text
AWS mutations:          0
IAM mutations:          0
new AWS services:       0
runtime mutations:      0
model invocations:      0
capability executions:  0
benchmark replays:      0
pricing refresh:        false
production TCO created: false
business authority:     unchanged
PR #89 modification:    0
```

## Post-Phase-18 boundary

Do not pre-authorize a Phase 19 implementation theme.

The next phase must be selected from observed product/evidence gaps after this closeout is merged. Possible future directions may be evaluated separately, including productization, deployment, additional measured evaluation, or a re-evaluation of the deferred Governed LLM Gateway integration. None is authorized by this ADR.

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred work unless explicitly resumed.

## Canonical evidence

```text
labs/phase-18-closeout.md
labs/evidence/phase-18-closeout-v1.json
labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json
labs/evidence/phase-18-gate-18-2-consolidated-view-v1.json
labs/evidence/phase-18-gate-18-2-decision-signals-v1.json
labs/evidence/phase-18-gate-18-3-cost-accounting-v1.json
labs/evidence/phase-18-gate-18-4-portfolio-evidence-pack-v1.json
labs/evidence/phase-18-gate-18-4-aip-c01-evidence-map-v1.json
```

## Consequence

Phase 18 is complete at an evidence-backed boundary. The repository has a traceable chain from raw retained measurements to comparability, evaluation/reliability interpretation, bounded cost accounting, portfolio claims, and certification-learning mapping without manufacturing production claims or widening runtime authority.
