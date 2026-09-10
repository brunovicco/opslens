# OpsLens — Current State

_Last updated: 2026-09-09_

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
  Gate 16.1 Inspector capability fit / authority               COMPLETE / READ-ONLY ONLY
  Gate 16.2 Existing-role read-only discovery                  COMPLETE / BLOCKED_BY_EXISTING_IAM
  Gate 16.3 Minimum Inspector read-only IAM boundary           COMPLETE / DEDICATED TEMP ROLE
  Gate 16.4 Temporary role + measured rerun                    COMPLETE / SUCCESS / ZERO RECORDS
  Gate 16.5 Temporary Inspector IAM teardown                   COMPLETE / ROLE ABSENT / CONVERGED
Phase 17   Security Hardening                                  IN PROGRESS
  Gate 17.1 Cross-cutting threat/control-gap inventory         COMPLETE / GO TO 17.2
  Gate 17.2 CI/CD and workflow authority hardening             IMPLEMENTED / RULESET ENFORCEMENT PENDING
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
Inspector coverage != vulnerability finding
Inspector finding != repository finding
Inspector package match != deployed application ownership
Inspector resource presence != network exposure
Inspector PACKAGE_VULNERABILITY != NETWORK_REACHABILITY
Inspector score != Risk Policy v1
Inspector EPSS != OpsLens source-authority replacement
Inspector finding status != business remediation state
Inspector evidence != model authority
runtime evidence correlation != capability authorization
security control name != proven enforcement
historical workflow != inert workflow
plan-only intent != write-authority requirement
CI evidence != enforced merge gate
repository checkout != persisted Git credential requirement
OIDC authentication != authorization to reuse a shared deployment role
```

Deterministic code remains authoritative for evidence identity, vulnerability applicability, risk policy, structured-query compilation, retrieval admission, capability authorization, executable input binding, result admission, handoff admission, MCP admission/projection, A2A reference identity/resolution/admission, retry/fallback policy, and runtime evidence admission/correlation.

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

Phase 12 retained deterministic specialization/handoff but rejected the measured two-model topology as the default because it produced no quality lift while increasing calls, tokens, latency, and cost.

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
Gate 14.2 PUBLIC exception:                  NOT RETAINED
Runtime Identity service-linked role:        RETAIN pending separate safety proof
historical mutating workflow:                RETIRED / FAIL-CLOSED
```

Measured successful six-case experiment cost:

```text
AgentCore Runtime:   USD 0.002380345136128484
Bedrock inference:   USD 0.0041921
total observed:      USD 0.006572445136128483
```

## Phase 15 — A2A — final retained state

```text
A2A release:                                   1.0.0
first retained binding:                       JSONRPC
operation:                                    SendMessage
content-addressed A2AReference:               RETAIN
strict raw JSON admission:                    RETAIN
Message / terminal Task metadata admission:   RETAIN
A2A fixtures / CI:                            RETAIN
official a2a-sdk exact-source CI oracle:      RETAIN FOR CI
public/network A2A runtime:                    DO NOT CREATE
standing A2A cloud resources / IAM:           NONE
a2a-sdk project/runtime dependency:           DO NOT ADD
```

Canonical closeout:

```text
docs/adr/0059-phase15-a2a-closeout.md
labs/evidence/phase-15-closeout-v1.json
```

## Phase 16 — Runtime Exposure with Amazon Inspector — COMPLETE

Phase 16 tested Amazon Inspector as an **independent runtime-evidence authority** without allowing runtime evidence to redefine repository vulnerability truth or Risk Policy v1.

### Gate 16.1 — capability fit / authority

Selected read surface:

```text
ListCoverage
ListFindings
```

Evidence dimensions remain distinct:

```text
runtime_coverage
runtime_vulnerability
network_reachability
code_vulnerability
```

Inspector activation/configuration, hybrid runtime-exposure routing, automatic repository/runtime correlation, runtime-risk composite scoring, model synthesis, and agent capability execution were not authorized.

### Gate 16.2 — existing-role discovery

The first main-only attempt used `OpsLensGitHubDeployRole` without changing it:

```text
run:                 34411934819 / #1
job:                 102668116801
result:              BLOCKED_BY_EXISTING_IAM
ListCoverage:        ACCESS_DENIED / AccessDeniedException
ListFindings:        NOT_ATTEMPTED / fail-closed
client elapsed:      103.252301 ms
SDK retries:         0
AWS mutations:       0
new IAM:             0
```

This proved:

```text
AWS authentication != Inspector read authorization
```

### Gate 16.3 — minimum read-only IAM boundary

Widening `OpsLensGitHubDeployRole` was rejected. A dedicated temporary role was accepted for one bounded rerun:

```text
OpsLensInspectorDiscoveryRole
 -> inspector2:ListCoverage
 -> inspector2:ListFindings
 -> Resource = "*"
 -> aws:RequestedRegion == us-east-1
 -> immutable GitHub OIDC main subject
 -> workflow session request 900 seconds
 -> mandatory teardown
```

### Gate 16.4 — temporary role + measured rerun

Human bootstrap created exactly:

```text
plan:   2 add / 0 change / 0 destroy
apply:  2 added / 0 changed / 0 destroyed
```

One measured run then succeeded:

```text
workflow:                    Inspector Read-Only Discovery
run:                         34414116549 / #2
job:                         102675000098
source main SHA:             bc3c79b4168ffbaa1374b50e60bb8a6d416a14c2
result:                      SUCCESS
client elapsed:              465.877452 ms
ListCoverage:                SUCCESS / 1 page / 0 records / 0 retries
ListFindings:                SUCCESS / 1 page / 0 records / 0 retries
AWS mutations:               0
new IAM during discovery:    0
model invocations:           0
capability executions:       0
artifact:                    10128371987
artifact SHA-256:            a6f917e62124b4c604891e1a83db9874e3ef34696110dfaead1af16d45a03365
```

The dedicated boundary was sufficient, but the current dev account returned no Inspector coverage or finding records. The result is current-account evidence only; it does not prove Inspector is disabled or valueless elsewhere.

### Gate 16.5 — mandatory temporary IAM teardown

Cleanup desired state was merged on `main` at:

```text
28f0194dc932569a40fc6b54e1cd8cd81aa690b2
```

Human bootstrap reviewed and applied exactly:

```text
plan:   0 add / 0 change / 2 destroy
apply:  0 added / 0 changed / 2 destroyed
```

Destroyed only:

```text
aws_iam_role_policy.github_actions_inspector_discovery
aws_iam_role.github_actions_inspector_discovery
```

Fresh post-apply plan:

```text
No changes. Your infrastructure matches the configuration.
```

Independent IAM verification:

```text
OpsLensInspectorDiscoveryRole:  ABSENT / NoSuchEntity
OpsLensGitHubDeployRole:         PRESENT
```

Retained OpsLens bootstrap Terraform contains no `inspector2:` authority and neither the create nor cleanup plan modified the shared deployment role.

### Final Phase 16 retention

```text
Inspector read-only domain/adapter contract:   RETAIN
historical discovery workflow:                 RETAIN / DISABLED BY DEFAULT
measured zero-record evidence:                 RETAIN
standing Inspector discovery IAM:              NONE
Inspector activation/configuration:             NOT CREATED
hybrid runtime_exposure routing:                NOT CREATED
repository/runtime automatic correlation:       NOT CREATED
runtime-risk composite scoring:                 NOT CREATED
model synthesis over Inspector evidence:        NOT CREATED
```

Canonical closeout:

```text
docs/adr/0063-phase16-runtime-exposure-closeout.md
labs/phase-16-closeout.md
labs/evidence/phase-16-closeout-v1.json
labs/evidence/phase-16-gate-16-5-inspector-iam-cleanup-postapply-v1.json
```

## Phase 17 — Security Hardening — IN PROGRESS

### Gate 17.1 — cross-cutting threat model and control-gap inventory

Gate 17.1 reviewed retained implementation, IaC, workflows, GitHub main ruleset evidence, historical lab boundaries, and current external security guidance before authorizing any new runtime or cloud authority.

Canonical evidence:

```text
labs/evidence/phase-17-gate-17-1-threat-model-v1.json
docs/adr/0064-evidence-first-security-hardening-priorities.md
labs/phase-17-gate-17-1-threat-model.md
```

Observed high-priority gaps:

```text
SEC17-CICD-001  main ruleset does not require CI status checks
SEC17-IAM-002   EPSS plan-only paths assume write/invoke-capable coordinator authority
SEC17-IAM-003   historical AgentCore workflow retains shared deploy-role mutation authority
```

Observed medium-priority gaps:

```text
SEC17-CICD-003  checkout credentials persist by default where authenticated git is unnecessary
SEC17-SUPPLY-001 repository-local continuous dependency security automation not observed
```

Observed low-priority documentation gap:

```text
SEC17-DOC-001   accumulated architecture headers still describe Phase 9 / Phase 10 as current
```

Important proven controls remain retained and are explicitly recorded as non-gaps: immutable main-only GitHub OIDC trust, full-SHA action pinning in sampled workflows, no observed privileged `pull_request_target`/`workflow_run` triggers, bounded public request/repository acquisition, proposal-only semantic planning, untrusted retrieved-content handling, deterministic agent authorization/result admission, raw MCP/A2A admission, content-minimized telemetry, and bounded model token/call behavior.

### Gate 17.2 — CI/CD and workflow authority hardening — IMPLEMENTED / ENFORCEMENT PENDING

Gate 17.2 closes the repository-side workflow-authority gaps without changing AWS IAM or introducing new services.

Retained implementation:

```text
universal workflow:                     Security Hardening CI
universal check context:                Repository security invariants
external action pins:                   full 40-hex SHA required
checkout persisted credentials:         forbidden by default
pull_request_target/workflow_run:        forbidden by default
EPSS plan role:                         OpsLensEpssHistoryEvidenceRole
EPSS execute role:                      OpsLensEpssHistoryCoordinatorRole
21600-second session:                   full-backfill execute path only
historical AgentCore mutation workflow: RETIRED / FAIL-CLOSED
shared deploy role in AgentCore lab:     NOT REFERENCED
```

Implementation-validation evidence:

```text
head SHA:      dd2b5cea01009d8acbfe73f135fc5a7c8380aba7
workflow run:  34420383193 / Security Hardening CI #12
conclusion:    SUCCESS
AWS mutations: 0
new IAM:       0
PR #89 changes: 0
```

Canonical records:

```text
docs/adr/0065-ci-cd-and-workflow-authority-hardening.md
labs/phase-17-gate-17-2-workflow-authority-hardening.md
labs/evidence/phase-17-gate-17-2-workflow-authority-hardening-v1.json
```

The remaining Gate 17.2 boundary is GitHub platform administration. After protected merge and exact final-head CI, active ruleset `Protect main` (`20873628`) must require:

```text
Repository security invariants
```

Until that independent ruleset proof exists:

```text
Security Hardening CI success != enforced merge gate
```

Gate 17.2 cloud/runtime impact:

```text
AWS mutations:          0
new IAM permissions:    0
new AWS services:       0
model invocations:      0
capability executions:  0
public runtime changes: 0
Inspector activation:   0
PR #89 changes:         0
```

## Next

Complete Gate 17.2 by enforcing and independently verifying the universal required status context in the active GitHub `main` ruleset. Only after that evidence should Phase 17 proceed to a separate dependency/code-scanning hardening decision.

## Deferred cross-project work

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains unrelated Governed LLM Gateway work and must remain untouched unless explicitly resumed in a separate scope.
