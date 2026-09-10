# OpsLens — Current State

_Last updated: 2026-09-10_

This document is the authoritative implementation checkpoint for OpsLens. Detailed historical evidence remains in ADRs, gate labs, immutable evidence artifacts, merged PRs, workflow runs, and Git history.

## Status

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2    Threat Intelligence Data Lake                       COMPLETE
Phase 3    Vulnerability Correlation Engine                    COMPLETE
Phase 4    Repository Intelligence                             COMPLETE
Phase 5    Risk Prioritization Engine                          COMPLETE
Phase 6    Semantic Query Layer                                COMPLETE
Phase 7    Knowledge Retrieval with Bedrock                    COMPLETE
Phase 8    Hybrid Retrieval                                    COMPLETE
Phase 9    Public Analyze Your Repository                      COMPLETE
Phase 10   Observability & Operational Excellence              COMPLETE
Phase 11   Single-Agent Baseline                               COMPLETE
Phase 12   Multi-Agent Architecture                            COMPLETE
Phase 13   MCP                                                 COMPLETE
Phase 14   Amazon Bedrock AgentCore                            COMPLETE
Phase 15   A2A                                                 COMPLETE
Phase 16   Runtime Exposure with Amazon Inspector              COMPLETE
Phase 17   Security Hardening                                  IN PROGRESS
  Gate 17.1 Cross-cutting threat/control-gap inventory         COMPLETE
  Gate 17.2 CI/CD and workflow authority hardening             COMPLETE / REQUIRED CONTEXT ENFORCED
  Gate 17.3 Dependency and code-scanning hardening             COMPLETE / DEPENDENCY REVIEW + CODEQL
  Gate 17.4 Adversarial authority-boundary regression          COMPLETE / 8 CASES / 7 THREAT CLASSES
Phase 18   Evaluation, Cost & Portfolio Readiness              PLANNED
```

## Permanent architecture boundaries

> **Agents reason. Code verifies evidence.**

> **MCP is an interoperability boundary, not new business authority.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
MCP call admission != capability execution
MCP result projection != public runtime exposure
AgentCore hosting != business authorization
runtime deployment != runtime-exposure truth
A2A message != capability authorization
A2A transport success != business/evidence truth
A2A SDK acceptance != OpsLens admission authority
AWS authentication != Inspector read authorization
Inspector API success != runtime evidence presence
Inspector finding != repository finding
runtime evidence correlation != capability authorization
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

Deterministic code remains authoritative for evidence identity, vulnerability applicability, Risk Policy v1, structured-query compilation, retrieval admission, capability authorization, executable input binding, result admission, handoff admission, MCP admission/projection, A2A reference identity/resolution/admission, retry/fallback policy, and runtime-evidence admission/correlation.

## Retained measured reasoning reference — Phase 11

```text
provider:                     Amazon Bedrock Converse
model/profile:                us.anthropic.claude-haiku-4-5-20251001-v1:0
quality:                      6/6
model invocations:            6
input/output/total tokens:    3291 / 104 / 3395
provider latency median:      809.5 ms
client elapsed median:        977.5 ms
SDK retries:                  0
capability executions:        0
derived six-case cost:        USD 0.0041921
```

Phase 12 retained deterministic specialization/handoff but rejected the measured two-model topology as the default because it added calls, tokens, latency, and cost without measured quality lift.

## Phase 13 — MCP — final retained state

```text
mcp-capability-exposure:v1          RETAIN
mcp-capability-execution:v1         RETAIN
mcp-result-projection:v1            RETAIN
public/network MCP runtime          DO NOT RETAIN / NOT CREATED
```

## Phase 14 — AgentCore — final retained state

```text
Phase 11 direct Bedrock reasoning:          RETAIN / DEFAULT
AgentCore implementation/evidence:          RETAIN AS OPTIONAL LAB TARGET
AgentCore managed Runtime as default:        DO NOT RETAIN
standing AgentCore Runtime resources:        NONE
standing experiment-specific GitHub IAM:    REMOVED
historical mutating workflow:                RETIRED / FAIL-CLOSED
```

## Phase 15 — A2A — final retained state

```text
A2A release:                                   1.0.0
first retained binding:                       JSONRPC / SendMessage
content-addressed A2AReference:               RETAIN
strict raw JSON admission:                    RETAIN
official a2a-sdk exact-source CI oracle:      RETAIN FOR CI
public/network A2A runtime:                    DO NOT CREATE
standing A2A cloud resources / IAM:           NONE
```

Canonical closeout:

```text
docs/adr/0059-phase15-a2a-closeout.md
labs/evidence/phase-15-closeout-v1.json
```

## Phase 16 — Runtime Exposure with Amazon Inspector — COMPLETE

Phase 16 tested Amazon Inspector as an **independent read-only runtime-evidence authority** without allowing Inspector evidence to redefine repository vulnerability truth or Risk Policy v1.

Measured successful discovery:

```text
workflow:                    Inspector Read-Only Discovery
run:                         34414116549 / #2
job:                         102675000098
result:                      SUCCESS
ListCoverage:                SUCCESS / 1 page / 0 records / 0 retries
ListFindings:                SUCCESS / 1 page / 0 records / 0 retries
AWS mutations:               0
model invocations:           0
capability executions:       0
```

The dedicated temporary Inspector read role was subsequently removed with exact Terraform cleanup and independent `NoSuchEntity` verification.

Final retention:

```text
Inspector read-only domain/adapter contract:   RETAIN
historical discovery workflow:                 RETAIN / DISABLED BY DEFAULT
measured zero-record evidence:                 RETAIN
standing Inspector discovery IAM:              NONE
Inspector activation/configuration:             NOT CREATED
repository/runtime automatic correlation:       NOT CREATED
runtime-risk composite scoring:                 NOT CREATED
model synthesis over Inspector evidence:        NOT CREATED
```

Canonical closeout:

```text
docs/adr/0063-phase16-runtime-exposure-closeout.md
labs/phase-16-closeout.md
labs/evidence/phase-16-closeout-v1.json
```

## Phase 17 — Security Hardening — IN PROGRESS

### Gate 17.1 — threat/control-gap inventory — COMPLETE

Gate 17.1 reviewed retained implementation, IaC, workflows, GitHub ruleset behavior, protocol boundaries, public-input handling, model/tool authority, telemetry, and dependency-security posture before authorizing new hardening work.

Canonical evidence:

```text
docs/adr/0064-evidence-first-security-hardening-priorities.md
labs/phase-17-gate-17-1-threat-model.md
labs/evidence/phase-17-gate-17-1-threat-model-v1.json
```

Highest-priority observed gaps were missing required-status enforcement, authority mismatch in historical EPSS plan paths, and historical AgentCore reuse of shared deployment authority. Continuous dependency/code scanning was a medium-priority gap; architecture-header drift remains a low-priority documentation gap.

### Gate 17.2 — CI/CD and workflow authority hardening — COMPLETE

Gate 17.2 retained one universal PR security context:

```text
workflow: Security Hardening CI
context:  Repository security invariants
```

Repository policy now continuously enforces:

```text
external actions:                     full 40-hex SHA pins
checkout:                             persist-credentials:false
pull_request_target/workflow_run:      rejected by default
write-all / contents:write:            rejected by default
EPSS plan identity:                   OpsLensEpssHistoryEvidenceRole
EPSS execution identity:              OpsLensEpssHistoryCoordinatorRole
21600-second STS session:             full-backfill execute only
historical AgentCore mutation path:   RETIRED / FAIL-CLOSED
```

The active `Protect main` ruleset (`20873628`) requires `Repository security invariants`. A later direct write attempt to `main` was independently rejected by the ruleset, confirming that repository evidence has become merge enforcement rather than documentation-only intent.

Canonical records:

```text
docs/adr/0065-ci-cd-and-workflow-authority-hardening.md
labs/phase-17-gate-17-2-workflow-authority-hardening.md
labs/evidence/phase-17-gate-17-2-workflow-authority-hardening-v1.json
labs/phase-17-gate-17-2-main-ruleset-enforcement.md
labs/evidence/phase-17-gate-17-2-main-ruleset-enforcement-v1.json
```

### Gate 17.3 — dependency and code-scanning hardening — COMPLETE

Gate 17.3 retains two bounded GitHub-native engineering signals.

Dependency Review:

```text
action:              actions/dependency-review-action
release:             v5.0.0
exact SHA:           a1d282b36b6f3519aa1f3fc636f609c47dddb294
trigger:             pull_request
fail-on-severity:    high
permission:          contents: read
OIDC/AWS authority:  none
```

Python CodeQL:

```text
action:              github/codeql-action
release line:        v4.38.0
exact SHA:           b96794f015dfd88f77b49b1c93e0fa7110f94c63
language:            python
triggers:            pull_request / main push / weekly / manual
permissions:         contents: read + security-events: write
OIDC/AWS authority:  none
```

The first Dependency Review attempt failed only because the repository Dependency graph was disabled. After a human enabled that GitHub platform prerequisite, the unchanged read-only workflow succeeded. No permission widening was performed.

Final exact PR-head validation on `f9ee70d772d28987c45008b723e3efc07b65680e`:

```text
Repository security invariants  34424002745 / #19  SUCCESS
Dependency Review               34424002767 / #4   SUCCESS
CodeQL / Python                 34424003077 / #4   SUCCESS
```

Implementation PR #261 was protected-squash merged as:

```text
b3f4a11df1a826c850cc16f1a4e0dd44efb3edd3
```

Canonical records:

```text
docs/adr/0066-bounded-dependency-and-code-scanning-signals.md
labs/phase-17-gate-17-3-dependency-code-scanning.md
labs/evidence/phase-17-gate-17-3-dependency-code-scanning-v1.json
labs/phase-17-gate-17-3-closeout.md
labs/evidence/phase-17-gate-17-3-closeout-v1.json
```

Deferred from Gate 17.3:

```text
Dependabot version-update automation: DEFER
additional continuous pip-audit:      DEFER
broad dependency upgrades:            NOT AUTHORIZED
```

Gate 17.3 cloud/runtime impact:

```text
AWS mutations:          0
new IAM permissions:    0
new AWS services:       0
model invocations:      0
capability executions:  0
public runtime changes: 0
PR #89 changes:         0
```

### Gate 17.4 — adversarial input / prompt-injection / tool-abuse testing — COMPLETE

Gate 17.4 retained one explicit attacker-oriented regression surface over real application and protocol boundaries.

```text
cases:                 8
threat classes:        7
workflow:              Adversarial Security CI
workflow permission:   contents: read
AWS/OIDC authority:    none
model invocations:     0
capability executions: 0
```

The suite covers public request admission, structural prompt-injection separation, single/multi-agent capability widening attempts, forged result evidence, MCP dynamic/cross-capability tool abuse, A2A reference smuggling, and bounded cost-amplification attempts.

No first-slice case exposed a business-logic gap requiring remediation. This is bounded regression evidence, not a universal security claim.

Final exact implementation PR-head validation on `60010d4fcb5d6142c9748bbf764fb074dc3a4dc8`:

```text
Adversarial Security CI          34426092786 / #5  / SUCCESS
Repository security invariants   34426092824 / #25 / SUCCESS
Dependency Review                34426092798 / #10 / SUCCESS
CodeQL / Python                  34426092795 / #12 / SUCCESS
```

Implementation PR #264 was protected-squash merged as:

```text
cfad2680ca9e1977c754977ea58f9ab8865601dd
```

Canonical records:

```text
docs/adr/0067-bounded-adversarial-authority-regression-suite.md
labs/phase-17-gate-17-4-adversarial-boundaries.md
labs/evidence/phase-17-gate-17-4-adversarial-boundaries-v1.json
labs/phase-17-gate-17-4-closeout.md
labs/evidence/phase-17-gate-17-4-closeout-v1.json
```

Gate 17.4 retention:

```text
adversarial boundary suite:                 RETAIN
Adversarial Security CI:                    RETAIN
least-privilege workflow invariant:         RETAIN
live model jailbreak as authority proof:    DO NOT USE
new AWS/model/tool authority:               NOT AUTHORIZED
```

## Next

Proceed to **Gate 17.5 — sensitive-data / logging / telemetry hardening**. Inspect retained observability and failure logging for secrets, user/source text, provider payloads, protocol data, and high-cardinality identifiers before authorizing new telemetry functionality.

## Deferred cross-project work

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains unrelated Governed LLM Gateway work and must remain untouched unless explicitly resumed in a separate scope.
