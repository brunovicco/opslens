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
Phase 16   Runtime Exposure with Amazon Inspector              IN PROGRESS
  Gate 16.1 Inspector capability fit / authority               COMPLETE / GO READ-ONLY ONLY
  Gate 16.2 Existing-role read-only discovery                  COMPLETE / BLOCKED_BY_EXISTING_IAM
  Gate 16.3 Minimum Inspector read-only IAM boundary           COMPLETE / DEDICATED TEMP ROLE
  Gate 16.4 Temporary role + measured rerun                    COMPLETE / SUCCESS / ZERO RECORDS
  Gate 16.5 Temporary Inspector IAM teardown                   REPOSITORY CLEANUP / HUMAN DESTROY PENDING
Phase 17   Security Hardening                                  PLANNED
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

The Phase 12 two-model topology remains rejected as the default because it produced no quality lift while increasing invocations, tokens, latency, and cost. The deterministic specialization/handoff boundary remains retained.

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

## Phase 16 — Runtime Exposure with Amazon Inspector — IN PROGRESS

Phase 16 preserves the invariant:

> **Repository Risk != Runtime Exposure.**

### Gate 16.1 — capability fit / authority — COMPLETE

Amazon Inspector was accepted only as an independent runtime-evidence authority. The first bounded read surface was frozen to:

```text
ListCoverage
ListFindings
```

Evidence dimensions remain separate:

```text
runtime_coverage
runtime_vulnerability
network_reachability
code_vulnerability
```

Inspector activation/configuration, hybrid routing, automatic repository/runtime correlation, model synthesis, and agent capability execution were not authorized.

Canonical records:

```text
docs/adr/0060-bounded-amazon-inspector-runtime-evidence-fit.md
labs/phase-16-gate-16-1-inspector-runtime-evidence-fit.md
labs/evidence/phase-16-gate-16-1-inspector-runtime-evidence-fit-v1.json
```

### Gate 16.2 — existing-role read-only discovery — COMPLETE

The first main-only read attempt used the existing `OpsLensGitHubDeployRole` without changing it.

```text
run:                         34411934819 / #1
job:                         102668116801
source main SHA:             d5ba77cc98df84488928e49ea5e429234e46bc9a
workflow conclusion:         success
experiment result:           BLOCKED_BY_EXISTING_IAM
ListCoverage:                ACCESS_DENIED / AccessDeniedException
ListFindings:                NOT_ATTEMPTED / fail-closed
client elapsed:              103.252301 ms
SDK retries:                 0
AWS mutations:               0
new IAM:                     0
model invocations:           0
capability executions:       0
```

This proved:

```text
AWS authentication != Inspector read authorization
```

Canonical records:

```text
labs/phase-16-gate-16-2-inspector-readonly-discovery.md
labs/evidence/phase-16-gate-16-2-inspector-readonly-discovery-v1.json
```

### Gate 16.3 — minimum read-only IAM boundary — COMPLETE

Compared options:

```text
A. widen OpsLensGitHubDeployRole                   REJECT
B. dedicated temporary Inspector discovery role   ACCEPT
C. stop Phase 16                                   REJECT FOR ONE BOUNDED RERUN
```

Accepted experiment identity:

```text
OpsLensInspectorDiscoveryRole
 -> inspector2:ListCoverage
 -> inspector2:ListFindings
 -> Resource = "*"
 -> aws:RequestedRegion == us-east-1
 -> immutable GitHub OIDC main subject
 -> workflow session request 900 seconds
 -> mandatory teardown after one measured run
```

Canonical records:

```text
docs/adr/0061-dedicated-temporary-inspector-discovery-role.md
labs/phase-16-gate-16-3-inspector-readonly-iam-decision.md
labs/evidence/phase-16-gate-16-3-inspector-readonly-iam-decision-v1.json
```

### Gate 16.4 — temporary role + measured rerun — COMPLETE

Human bootstrap reviewed and applied exactly:

```text
plan:   2 add / 0 change / 0 destroy
apply:  2 added / 0 changed / 0 destroyed
```

One main-only discovery then assumed `OpsLensInspectorDiscoveryRole` successfully.

Measured result:

```text
workflow:                    Inspector Read-Only Discovery
run:                         34414116549 / #2
job:                         102675000098
source main SHA:             bc3c79b4168ffbaa1374b50e60bb8a6d416a14c2
workflow conclusion:         success
experiment result:           SUCCESS
client elapsed:              465.877452 ms
ListCoverage:                SUCCESS / 1 page / 0 records
ListFindings:                SUCCESS / 1 page / 0 records
coverage resource types:     none observed
finding resource types:      none observed
finding types:               none observed
scan statuses:               none observed
SDK retries:                 0
AWS mutations:               0
new IAM during discovery:    0
model invocations:           0
capability executions:       0
```

Actions artifact:

```text
artifact:  10128371987
digest:    sha256:a6f917e62124b4c604891e1a83db9874e3ef34696110dfaead1af16d45a03365
```

The minimum read boundary worked, but the current dev account returned no Inspector runtime evidence. The zero result does not prove service disablement or lack of value elsewhere, and it does not justify activation/configuration changes solely to manufacture demo data.

Canonical records:

```text
docs/adr/0062-retain-inspector-read-contract-without-standing-iam-or-scan-activation.md
labs/phase-16-gate-16-4-inspector-readonly-rerun.md
labs/evidence/phase-16-gate-16-4-inspector-readonly-rerun-v1.json
```

### Gate 16.5 — mandatory temporary IAM teardown — HUMAN DESTROY PENDING

The repository retained state removes the temporary Inspector role/policy from Terraform desired state. The historical discovery workflow is disabled by default and requires an explicit confirmation input before it can attempt the separately authorized temporary role again.

After this cleanup is protected-merged, the human bootstrap plane must prove an exact destroy plan, apply it, require post-apply convergence, and independently verify:

```text
OpsLensInspectorDiscoveryRole:            ABSENT
OpsLensInspectorDiscoveryReadOnly:        ABSENT with role
OpsLensGitHubDeployRole:                   PRESENT
OpsLensGitHubDeployRole Inspector access:  NONE
```

Until that AWS teardown proof is recorded, Phase 16 remains in progress.

Retained Phase 16 direction:

```text
Inspector read-only adapter/contract:        RETAIN
measured zero-evidence artifact:             RETAIN
standing Inspector discovery IAM:            DO NOT RETAIN / REMOVE
Inspector activation/configuration change:   DO NOT CREATE IN PHASE 16
repository/runtime automatic correlation:    DO NOT CREATE
runtime-risk composite scoring:              DO NOT CREATE
model synthesis over Inspector evidence:     DO NOT CREATE
```

## Deferred cross-project work

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains unrelated Governed LLM Gateway work and must remain untouched unless explicitly resumed in a separate scope.
