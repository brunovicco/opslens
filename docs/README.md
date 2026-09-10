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
Phase 17 Security Hardening                     IN PROGRESS / Gates 17.1–17.4 complete
Phase 18 Evaluation, Cost & Portfolio           PLANNED
```

## Permanent authority separations

```text
agent proposal != authorization
handoff proposal != handoff admission
capability invocation != execution result
MCP call admission != capability execution
MCP result projection != public runtime exposure
AgentCore hosting != business authorization
A2A message != capability authorization
A2A transport success != business/evidence truth
AWS authentication != Inspector read authorization
Inspector API success != runtime evidence presence
Inspector finding != repository finding
runtime evidence correlation != capability authorization
Repository Risk != Runtime Exposure
security control name != proven enforcement
historical workflow != inert workflow
plan-only intent != write-authority requirement
CI evidence != enforced merge gate
repository checkout != persisted Git credential requirement
OIDC authentication != authorization to reuse a shared deployment role
dependency finding != vulnerability applicability authority
code-scanning alert != runtime exploitability truth
security scan success != absence of vulnerabilities
scanner output != model authority
GitHub security permission != AWS authority
scanner platform prerequisite != scanner permission requirement
untrusted text != instruction authority
retrieved content != system/developer authority
failed/forged capability result != admissible business result
adversarial test success != proof of universal safety
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

AgentCore remains an optional lab target, not the default OpsLens reasoning runtime. Standing experiment-specific GitHub IAM was removed after the measured experiment, and the historical mutating workflow is now retired/fail-closed.

### Phase 15 — A2A

A2A retains a content-addressed reference-only JSON-RPC `SendMessage` profile plus exact-source official SDK conformance in CI. No public/network A2A runtime, A2A-specific IAM, or SDK runtime dependency is retained.

Canonical closeout:

- [`adr/0059-phase15-a2a-closeout.md`](adr/0059-phase15-a2a-closeout.md)
- [`../labs/phase-15-closeout.md`](../labs/phase-15-closeout.md)
- [`../labs/evidence/phase-15-closeout-v1.json`](../labs/evidence/phase-15-closeout-v1.json)

## Phase 16 — Runtime Exposure with Amazon Inspector — complete

Phase 16 retained Amazon Inspector only as an **independent read-only runtime-evidence boundary**.

Measured successful rerun:

```text
run:                    34414116549 / #2
job:                    102675000098
ListCoverage:           SUCCESS / 1 page / 0 records / 0 retries
ListFindings:           SUCCESS / 1 page / 0 records / 0 retries
AWS mutations:          0
model invocations:      0
capability executions:  0
```

The temporary dedicated Inspector role was subsequently removed and Terraform reconverged. Zero records are evidence about the measured dev account/region/time, not proof that Inspector is globally disabled or valueless.

References:

- [`adr/0060-bounded-amazon-inspector-runtime-evidence-fit.md`](adr/0060-bounded-amazon-inspector-runtime-evidence-fit.md)
- [`adr/0061-dedicated-temporary-inspector-discovery-role.md`](adr/0061-dedicated-temporary-inspector-discovery-role.md)
- [`adr/0062-retain-inspector-read-contract-without-standing-iam-or-scan-activation.md`](adr/0062-retain-inspector-read-contract-without-standing-iam-or-scan-activation.md)
- [`adr/0063-phase16-runtime-exposure-closeout.md`](adr/0063-phase16-runtime-exposure-closeout.md)
- [`../labs/phase-16-closeout.md`](../labs/phase-16-closeout.md)
- [`../labs/evidence/phase-16-closeout-v1.json`](../labs/evidence/phase-16-closeout-v1.json)

## Phase 17 — Security Hardening — in progress

### Gate 17.1 — threat model and control-gap inventory — complete

Gate 17.1 froze an evidence-first security inventory before authorizing implementation changes.

References:

- [`adr/0064-evidence-first-security-hardening-priorities.md`](adr/0064-evidence-first-security-hardening-priorities.md)
- [`../labs/phase-17-gate-17-1-threat-model.md`](../labs/phase-17-gate-17-1-threat-model.md)
- [`../labs/evidence/phase-17-gate-17-1-threat-model-v1.json`](../labs/evidence/phase-17-gate-17-1-threat-model-v1.json)

### Gate 17.2 — CI/CD and workflow authority hardening — complete

The repository now has one universal protected-main security context:

```text
Repository security invariants
```

The active `Protect main` ruleset requires that context. Gate 17.2 also removed write/invoke-capable authority from EPSS plan-only paths, limited the six-hour STS session to real full-backfill execution, disabled persisted checkout credentials, and retired the historical AgentCore mutation path.

References:

- [`adr/0065-ci-cd-and-workflow-authority-hardening.md`](adr/0065-ci-cd-and-workflow-authority-hardening.md)
- [`../labs/phase-17-gate-17-2-workflow-authority-hardening.md`](../labs/phase-17-gate-17-2-workflow-authority-hardening.md)
- [`../labs/evidence/phase-17-gate-17-2-workflow-authority-hardening-v1.json`](../labs/evidence/phase-17-gate-17-2-workflow-authority-hardening-v1.json)
- [`../labs/phase-17-gate-17-2-main-ruleset-enforcement.md`](../labs/phase-17-gate-17-2-main-ruleset-enforcement.md)
- [`../labs/evidence/phase-17-gate-17-2-main-ruleset-enforcement-v1.json`](../labs/evidence/phase-17-gate-17-2-main-ruleset-enforcement-v1.json)

### Gate 17.3 — dependency and code-scanning hardening — complete

Retained controls:

```text
Dependency Review
  actions/dependency-review-action v5.0.0
  exact SHA a1d282b36b6f3519aa1f3fc636f609c47dddb294
  fail-on-severity high
  contents: read

CodeQL / Python
  github/codeql-action v4.38.0
  exact SHA b96794f015dfd88f77b49b1c93e0fa7110f94c63
  contents: read + security-events: write
```

The first Dependency Review run correctly exposed a GitHub platform prerequisite: the repository Dependency graph was disabled. After a human enabled it, the unchanged read-only workflow succeeded. No scanner permission widening and no AWS/IAM change occurred.

Final exact PR-head validation:

```text
Repository security invariants  34424002745 / #19  SUCCESS
Dependency Review               34424002767 / #4   SUCCESS
CodeQL / Python                 34424003077 / #4   SUCCESS
```

PR #261 was protected-squash merged as `b3f4a11df1a826c850cc16f1a4e0dd44efb3edd3`.

References:

- [`adr/0066-bounded-dependency-and-code-scanning-signals.md`](adr/0066-bounded-dependency-and-code-scanning-signals.md)
- [`../labs/phase-17-gate-17-3-dependency-code-scanning.md`](../labs/phase-17-gate-17-3-dependency-code-scanning.md)
- [`../labs/evidence/phase-17-gate-17-3-dependency-code-scanning-v1.json`](../labs/evidence/phase-17-gate-17-3-dependency-code-scanning-v1.json)
- [`../labs/phase-17-gate-17-3-closeout.md`](../labs/phase-17-gate-17-3-closeout.md)
- [`../labs/evidence/phase-17-gate-17-3-closeout-v1.json`](../labs/evidence/phase-17-gate-17-3-closeout-v1.json)

### Gate 17.4 — adversarial authority-boundary regression — complete

Gate 17.4 added a dedicated offline attacker-oriented suite over real retained boundaries, not a synthetic policy layer.

```text
cases:                 8
threat classes:        7
workflow:              Adversarial Security CI
workflow permission:   contents: read
AWS/OIDC authority:    none
model invocations:     0
capability executions: 0
```

Coverage includes public-request abuse, structural prompt injection, single/multi-agent capability widening, forged result binding, MCP dynamic/cross-capability tool abuse, A2A reference smuggling, and bounded amplification attempts.

Final exact implementation PR-head validation:

```text
Adversarial Security CI          34426092786 / #5  / SUCCESS
Repository security invariants   34426092824 / #25 / SUCCESS
Dependency Review                34426092798 / #10 / SUCCESS
CodeQL / Python                  34426092795 / #12 / SUCCESS
```

PR #264 was protected-squash merged as `cfad2680ca9e1977c754977ea58f9ab8865601dd`.

References:

- [`adr/0067-bounded-adversarial-authority-regression-suite.md`](adr/0067-bounded-adversarial-authority-regression-suite.md)
- [`../labs/phase-17-gate-17-4-adversarial-boundaries.md`](../labs/phase-17-gate-17-4-adversarial-boundaries.md)
- [`../labs/evidence/phase-17-gate-17-4-adversarial-boundaries-v1.json`](../labs/evidence/phase-17-gate-17-4-adversarial-boundaries-v1.json)
- [`../labs/phase-17-gate-17-4-closeout.md`](../labs/phase-17-gate-17-4-closeout.md)
- [`../labs/evidence/phase-17-gate-17-4-closeout-v1.json`](../labs/evidence/phase-17-gate-17-4-closeout-v1.json)

No first-slice test justified business-logic redesign or new cloud/model/tool authority. `adversarial test success != proof of universal safety` remains a permanent interpretation boundary.

## Next

Gate 17.5 will inspect sensitive-data, logging, telemetry, failure-path, protocol-payload, and high-cardinality exposure before new observability functionality is authorized.

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains a separate deferred integration and must stay untouched unless explicitly resumed.
