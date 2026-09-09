# OpsLens — Incremental Roadmap

_Last updated: 2026-09-09_

OpsLens advances in small, demonstrable, observable, reversible gates.

Default engineering loop:

```text
real gap
 -> issue
 -> architecture decision
 -> IAM / trust boundary when applicable
 -> small implementation or documentation slice
 -> success test
 -> meaningful failure test
 -> observability
 -> cost
 -> evidence
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
| 16 | Runtime Exposure with Amazon Inspector | 🚧 In progress — Gate 16.3 accepted a dedicated temporary read role; implementation/rerun next |
| 17 | Security Hardening | ⏳ Planned |
| 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planned |

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

## Completed platform through Phase 15

Phases 0–10 established the AWS foundation, threat-intelligence ingestion, deterministic vulnerability correlation, repository intelligence, risk prioritization, bounded semantic query, Bedrock Knowledge Base retrieval with Amazon S3 Vectors, hybrid evidence, governed public analysis, and operational telemetry.

Phase 11 retained the measured single-agent Bedrock reference. Phase 12 retained deterministic specialization/handoff but rejected the measured two-model topology as default. Phase 13 retained bounded offline MCP interoperability. Phase 14 retained AgentCore only as an optional lab target and removed standing experiment IAM. Phase 15 retained bounded offline A2A reference interoperability plus an exact-source official SDK CI oracle, without creating a public A2A runtime.

Canonical prior closeouts remain in ADRs, labs, immutable evidence, and Git history.

## Phase 16 — Runtime Exposure with Amazon Inspector — IN PROGRESS

Purpose: add independent runtime evidence while preserving:

> **Repository Risk != Runtime Exposure.**

### Gate 16.1 — Inspector capability fit / authority — COMPLETE

Current Inspector capability facts used by this gate:

```text
read APIs selected:       ListCoverage / ListFindings
finding types:            NETWORK_REACHABILITY / PACKAGE_VULNERABILITY / CODE_VULNERABILITY
network reachability:     EC2-only in current Inspector contract
```

Evidence taxonomy:

```text
runtime_coverage
runtime_vulnerability
network_reachability
code_vulnerability
```

These are intentionally independent. A Lambda/ECR package finding is runtime-resource vulnerability evidence, not network-reachability evidence.

Decision:

```text
Amazon Inspector capability fit:       YES
runtime evidence source:               INDEPENDENT AUTHORITY
first experiment:                      READ-ONLY DISCOVERY ONLY
allowed APIs:                          ListCoverage + ListFindings
Inspector activation/change:           NOT AUTHORIZED
new IAM:                               NOT AUTHORIZED
hybrid routing integration:            NOT AUTHORIZED
repository/runtime auto-correlation:    NOT AUTHORIZED
```

Records:

```text
docs/adr/0060-bounded-amazon-inspector-runtime-evidence-fit.md
labs/phase-16-gate-16-1-inspector-runtime-evidence-fit.md
labs/evidence/phase-16-gate-16-1-inspector-runtime-evidence-fit-v1.json
```

### Gate 16.2 — bounded read-only Inspector discovery — COMPLETE

One main-only experiment was run against the existing dev account using the already-existing `OpsLensGitHubDeployRole` and no AWS/IAM mutation.

Measured result:

```text
workflow:                 Inspector Read-Only Discovery
run:                      34411934819 / #1
job:                      102668116801
main SHA:                 d5ba77cc98df84488928e49ea5e429234e46bc9a
workflow conclusion:      success
experiment result:        BLOCKED_BY_EXISTING_IAM
client elapsed:           103.252301 ms
ListCoverage:             ACCESS_DENIED / AccessDeniedException
ListFindings:             NOT_ATTEMPTED after fail-closed stop
SDK retries:              0
AWS mutations:            0
new IAM:                  0
model invocations:        0
capability executions:    0
```

OIDC authentication and role assumption succeeded. Inspector read authorization did not. The experiment therefore proved that the current deployment role is insufficient for the selected read surface while preserving least privilege.

Records:

```text
labs/phase-16-gate-16-2-inspector-readonly-discovery.md
labs/evidence/phase-16-gate-16-2-inspector-readonly-discovery-v1.json
GitHub Actions artifact 10127569570
artifact SHA-256 8814b313261e2ac2cde2894e7ea428e437aaa66cd0d2f47e7187759565d6738e
```

### Gate 16.3 — minimum Inspector read-only IAM boundary — COMPLETE

Compared options:

```text
A. widen OpsLensGitHubDeployRole                   REJECT
B. dedicated temporary Inspector discovery role   ACCEPT
C. stop Phase 16                                   REJECT FOR NOW
```

Accepted contract:

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

The AWS Service Authorization Reference exposes no resource type for these two list actions, so `Resource = "*"` is unavoidable. The gate compensates with exact action allowlisting, regional restriction, principal separation, short requested session duration, and mandatory teardown after one measured run.

Records:

```text
docs/adr/0061-dedicated-temporary-inspector-discovery-role.md
labs/phase-16-gate-16-3-inspector-readonly-iam-decision.md
labs/evidence/phase-16-gate-16-3-inspector-readonly-iam-decision-v1.json
```

### Gate 16.4 — temporary read-role implementation + rerun — NEXT / AUTHORIZED

Implement the decision without mutating AWS automatically:

```text
Terraform temporary OpsLensInspectorDiscoveryRole
exact two-action inline/attached policy
aws:RequestedRegion == us-east-1
existing immutable main-branch OIDC trust
workflow assumes dedicated role
role-duration-seconds = 900
Terraform/CI negative-permission guardrails
```

Execution sequence:

```text
repository implementation
 -> exact-head CI
 -> protected squash merge
 -> human Terraform plan/apply
 -> one main-only Inspector discovery run
 -> preserve measured evidence
 -> remove temporary role/policy
 -> human cleanup apply
 -> independent absence verification
 -> retention/value decision
```

Still not authorized:

```text
modify OpsLensGitHubDeployRole permissions
Enable/Disable Inspector
ECR scanning changes
EC2 scan-mode changes
Lambda scan activation
EventBridge integration
suppression filters
hybrid runtime_exposure routing
runtime-risk composite scoring
model synthesis
repository/runtime automatic correlation
```

## Phase 17 — Security Hardening — PLANNED

Cross-cutting IAM, data protection, abuse resistance, dependency, threat-model, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure-path, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains separate Governed LLM Gateway work and must not be modified or merged as a side effect of Phase 16.
