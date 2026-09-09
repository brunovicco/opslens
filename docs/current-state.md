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
  Gate 16.2 Bounded read-only Inspector discovery              COMPLETE / BLOCKED_BY_EXISTING_IAM
  Gate 16.3 Minimum Inspector read-only IAM boundary            COMPLETE / DEDICATED TEMP ROLE
  Gate 16.4 Temporary read-role implementation + rerun          NEXT / IMPLEMENTATION AUTHORIZED
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

### Gate 16.1 — capability fit / authority boundary

Phase 16 starts by refusing to equate repository vulnerability evidence with runtime truth.

Current Amazon Inspector read surfaces selected for the first experiment:

```text
ListCoverage
ListFindings
```

Current finding dimensions relevant to OpsLens:

```text
NETWORK_REACHABILITY
PACKAGE_VULNERABILITY
CODE_VULNERABILITY
```

A critical upstream semantic boundary is frozen:

```text
NETWORK_REACHABILITY is currently EC2-only.
```

Therefore the Phase 16 evidence taxonomy is intentionally separated:

```text
runtime_coverage
runtime_vulnerability
network_reachability
code_vulnerability
```

Decision:

```text
Amazon Inspector capability fit:       YES
runtime evidence source:               INDEPENDENT AUTHORITY
Gate 16.2 experiment:                  READ-ONLY DISCOVERY ONLY
allowed APIs:                          ListCoverage + ListFindings
Inspector activation/change:           NOT AUTHORIZED
new IAM:                               NOT AUTHORIZED
hybrid routing integration:            NOT AUTHORIZED
repository/runtime auto-correlation:    NOT AUTHORIZED
```

Canonical Gate 16.1 records:

```text
docs/adr/0060-bounded-amazon-inspector-runtime-evidence-fit.md
labs/phase-16-gate-16-1-inspector-runtime-evidence-fit.md
labs/evidence/phase-16-gate-16-1-inspector-runtime-evidence-fit-v1.json
```

### Gate 16.2 — bounded read-only Inspector discovery — COMPLETE

The implementation was protected-merged before the live AWS attempt. The first main-only discovery used the already-existing `OpsLensGitHubDeployRole` without changing that role or Amazon Inspector configuration.

Measured run:

```text
workflow:                    Inspector Read-Only Discovery
run:                         34411934819 / #1
job:                         102668116801
source main SHA:             d5ba77cc98df84488928e49ea5e429234e46bc9a
workflow conclusion:         success
experiment result:           BLOCKED_BY_EXISTING_IAM
client elapsed:              103.252301 ms
ListCoverage attempted:      YES
ListCoverage outcome:        ACCESS_DENIED
AWS error:                   AccessDeniedException
ListFindings attempted:      NO / FAIL-CLOSED STOP
SDK retries:                 0
AWS mutations:               0
new IAM:                     0
model invocations:           0
capability executions:       0
```

OIDC role assumption succeeded, but the selected Inspector read was not authorized. This preserves the distinction:

```text
AWS authentication != Inspector read authorization
```

The experiment therefore completed successfully as a measurement while retrieving no Inspector runtime evidence. The access denial is terminal Gate 16.2 evidence, not permission to widen IAM.

Canonical Gate 16.2 records:

```text
labs/phase-16-gate-16-2-inspector-readonly-discovery.md
labs/evidence/phase-16-gate-16-2-inspector-readonly-discovery-v1.json
GitHub Actions run 34411934819
artifact 10127569570
artifact SHA-256 8814b313261e2ac2cde2894e7ea428e437aaa66cd0d2f47e7187759565d6738e
```

### Gate 16.3 — minimum Inspector read-only IAM boundary — COMPLETE

The measured denial was used to compare three options:

```text
A. widen OpsLensGitHubDeployRole                   REJECT
B. dedicated temporary Inspector discovery role   ACCEPT
C. stop Phase 16                                   REJECT FOR NOW
```

Accepted frozen contract:

```text
role:                       OpsLensInspectorDiscoveryRole
purpose:                    one bounded read-only Inspector experiment
OIDC subject:               repo:brunovicco@38844444/opslens@1333092779:ref:refs/heads/main
allowed actions:            inspector2:ListCoverage
                            inspector2:ListFindings
resource:                   *
region condition:           aws:RequestedRegion == us-east-1
requested STS session:      900 seconds
Inspector write actions:    0
IAM actions:                0
other AWS service actions:  0
```

AWS exposes no resource type for these two Inspector list actions, so resource-level ARN scoping is unavailable. The unavoidable `Resource = "*"` is compensated by the exact two-action allowlist, a region condition, a dedicated principal, a short requested session, and mandatory teardown after one measured run.

`OpsLensGitHubDeployRole` must not receive Inspector permissions.

Canonical Gate 16.3 records:

```text
docs/adr/0061-dedicated-temporary-inspector-discovery-role.md
labs/phase-16-gate-16-3-inspector-readonly-iam-decision.md
labs/evidence/phase-16-gate-16-3-inspector-readonly-iam-decision-v1.json
```

### Next gate — Gate 16.4

Implement the temporary dedicated role and workflow switch in the repository, prove the Terraform/CI boundary offline, then stop at the human AWS apply boundary before creating any real IAM resources.

After a human apply, run exactly one bounded Inspector discovery with the dedicated role, preserve measured evidence, and remove the experiment role/policy after the measurement unless a later retention gate explicitly decides otherwise.

Still not authorized:

```text
modify OpsLensGitHubDeployRole permissions
Inspector activation/change
hybrid routing integration
repository/runtime auto-correlation
runtime-risk composite scoring
model synthesis
agent capability execution
```

## Deferred cross-project work

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains unrelated Governed LLM Gateway work and must remain untouched unless explicitly resumed in a separate scope.
