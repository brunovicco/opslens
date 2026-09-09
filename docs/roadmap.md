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
 -> branch hygiene
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
| 13 | MCP | ✅ Complete — bounded offline MCP retained |
| 14 | Amazon Bedrock AgentCore | ✅ Complete — optional lab target retained; standing experiment IAM removed |
| 15 | A2A | ▶️ Next / planned |
| 16 | Runtime Exposure with Amazon Inspector | ⏳ Planned |
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

Agentic/interoperability/runtime phases preserve:

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
structured model output != trusted proposal
model selection != capability authority
MCP tool name != capability authorization
MCP tool exposure != executable argument authority
MCP call admission != capability execution
MCP capability execution != business-result transport
MCP result admission != result-projection authority
MCP result projection != public runtime exposure
MCP transport success != business/evidence truth
AgentCore hosting != business authorization
runtime authentication != capability authorization
runtime session != identity authority
runtime execution role != model/tool authority
runtime transport success != business/evidence truth
runtime telemetry != business truth
runtime deployment != runtime-exposure truth
```

## Completed foundation — Phases 0–10

Phases 0–10 are complete. Detailed architecture, evidence, AWS/IAM decisions, and failure-path records remain in ADRs, labs, and Git history.

The retained platform includes AWS foundation, threat-intelligence ingestion, deterministic vulnerability correlation, repository intelligence over immutable inert evidence, deterministic risk prioritization, bounded semantic planning and SQL compilation, Bedrock Knowledge Base retrieval with Amazon S3 Vectors, hybrid evidence composition, governed public-analysis admission, and operational telemetry contracts.

## Phase 11 — Single-Agent Baseline — COMPLETE

Retained measured reference:

```text
quality:                    6/6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
derived inference cost:     USD 0.0041921
corpus_sha256:              3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
```

This remains the default/reference reasoning architecture until a superior topology is demonstrated against frozen evidence.

## Phase 12 — Multi-Agent Architecture — COMPLETE

Retained outcome:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
```

The real two-model experiment produced no quality lift and increased invocations, tokens, latency, and cost.

## Phase 13 — MCP — COMPLETE

MCP is retained as an interoperability boundary over existing governed capability authority.

Retained contracts:

```text
mcp-capability-exposure:v1
mcp-capability-execution:v1
mcp-result-projection:v1
```

Retained path:

```text
Phase 11 typed capability authority
 -> closed MCP tool identity
 -> official MCP SDK reference-only adapter
 -> raw exact-key-set argument refusal
 -> deterministic invocation resolution + admission
 -> exactly one existing typed executor attempt
 -> existing typed result admission
 -> structured result projection for structured_security_query only
 -> bounded CVE + EPSS rows
 -> STOP before public/network runtime
```

Public/network MCP hosting remains an explicit non-claim. The MCP SDK stays development-only in the retained architecture.

## Phase 14 — Amazon Bedrock AgentCore — COMPLETE

Phase 14 evaluated managed runtime value against measured OpsLens needs instead of preselecting adoption.

### Gate 14.1 — Runtime capability fit — COMPLETE

Authorized only one bounded experiment:

```text
AgentCore Runtime:        GO TO ONE BOUNDED EXPERIMENT ONLY
first hosted boundary:    retained Phase 11 bounded reasoning
protocol:                 HTTP
authentication:           IAM SigV4
capability executions:    0
MCP runtime promotion:    not authorized
A2A:                      deferred
runtime-exposure truth:   not created
```

### Gate 14.2 — bounded Runtime experiment — COMPLETE / MEASURED

Terminal measured result:

```text
workflow run:               34378942784 / run #11 / SUCCESS
replay:                     6 / 6 PASS
input/output/total tokens:  3291 / 104 / 3395
SDK retries:                0
capability executions:      0
transport elapsed sum:      19981 ms
deploy-role invocation:     AccessDeniedException / HTTP 403
runtime cleanup:            RESOURCE_NOT_FOUND
AgentCore Runtime cost:     USD 0.002380345136128484
Bedrock inference cost:     USD 0.0041921
total observed cost:        USD 0.006572445136128483
```

The `PUBLIC` network mode was a dev-only experiment exception and is not a retained production decision.

### Gate 14.3 — Runtime retention decision — COMPLETE / RETAIN WITH CHANGES

Decision:

```text
default OpsLens reasoning runtime:            DO NOT RETAIN AgentCore
Phase 11 direct Bedrock reasoning reference: RETAIN
AgentCore implementation/evidence:           RETAIN
AgentCore deployment role:                   OPTIONAL LAB / FUTURE CONSUMER TARGET ONLY
PUBLIC network mode:                         DO NOT RETAIN
standing AgentCore Runtime resources:        DO NOT RETAIN
standing experiment-specific IAM:            DO NOT RETAIN without an active experiment
```

Overall classification:

```text
RETAIN WITH CHANGES
```

The six-case quality/model/token evidence was unchanged relative to Phase 11. AgentCore added USD 0.002380345136128484 of measured Runtime cost, or 56.78168784448091% relative to the unchanged USD 0.0041921 inference component. Raw latency boundaries were not normalized into a percentage comparison.

### Gate 14.4 — standing experiment IAM cleanup — COMPLETE / VERIFIED

Repository cleanup was merged in PR #225 at:

```text
9913c3cbf5f2239d6445042a139a9cca890590c8
```

Exact-head CI:

```text
AgentCore CI: 34396085154 / run #63 / PASS
Terraform CI: 34396085123 / run #267 / PASS
```

Human bootstrap plan and apply:

```text
plan:   0 add / 0 change / 4 destroy
apply:  0 add / 0 change / 4 destroy
```

Destroyed exactly:

```text
aws_iam_policy.github_actions_agentcore_deploy
aws_iam_role.github_actions_agentcore_replay
aws_iam_role_policy.github_actions_agentcore_replay
aws_iam_role_policy_attachment.github_actions_agentcore_deploy
```

Post-apply convergence:

```text
No changes. Your infrastructure matches the configuration.
```

Independent verification:

```text
OpsLensAgentCoreReplayRole:                 ABSENT
OpsLensAgentCoreDeployDevAccess:            ABSENT
AgentCore deploy policy attachment:         []
OpsLensGitHubDeployRole:                    PRESENT
AWSServiceRoleForBedrockAgentCoreRuntimeIdentity:
                                            PRESENT / intentionally retained
```

The service-linked role remains protected because safe account-level deletion has not been proven.

### Final retained Phase 14 architecture

```text
Phase 11 direct Bedrock reasoning:           DEFAULT / RETAIN
AgentCore implementation/evidence:           RETAIN AS OPTIONAL LAB TARGET
AgentCore managed Runtime as default:         DO NOT RETAIN
standing AgentCore Runtime resources:         NONE
standing experiment-specific GitHub IAM:     REMOVED
Gate 14.2 PUBLIC exception:                   NOT RETAINED
Runtime Identity service-linked role:         RETAIN pending separate safety proof
```

Evidence:

```text
docs/adr/0052-agentcore-runtime-capability-fit.md
docs/adr/0053-bounded-agentcore-direct-code-public-network-experiment.md
docs/adr/0054-retain-agentcore-only-as-optional-lab-target.md
docs/adr/0055-remove-standing-agentcore-experiment-iam.md
labs/evidence/phase-14-gate-14-2-final-runtime-experiment-v1.json
labs/evidence/phase-14-gate-14-3-agentcore-retention-decision-v1.json
labs/evidence/phase-14-gate-14-4-agentcore-iam-cleanup-postapply-v1.json
```

## Phase 15 — A2A — NEXT / PLANNED

A2A is not adopted merely because it is next in sequence. Phase 15 begins with capability fit and a concrete service-boundary problem.

The first gate must determine:

```text
which existing agent/service boundary requires A2A interoperability
why the current in-process handoff is insufficient
what identity/message/provenance contract is required
what remains proposal/admission authority
what remains capability authorization
what replay/idempotency/failure semantics are needed
what observability and cost evidence are required
whether a network runtime is actually necessary
```

Permanent Phase 15 constraints:

```text
A2A message != capability authorization
A2A peer identity != business authority
A2A transport success != business/evidence truth
A2A handoff proposal != handoff admission
A2A must not assume AgentCore hosting
A2A must not promote MCP into public runtime as a side effect
```

Implementation starts only after that first evidence-backed gate freezes the boundary.

## Phase 16 — Runtime Exposure with Amazon Inspector — PLANNED

Add independent runtime evidence while preserving:

> **Repository Risk != Runtime Exposure.**

## Phase 17 — Security Hardening — PLANNED

Perform cross-cutting IAM, data protection, abuse, threat-model, dependency, and operational hardening.

## Phase 18 — Evaluation, Cost & Portfolio Readiness — PLANNED

Consolidate quality, latency, cost, failure, architecture, and portfolio evidence.

## Deferred cross-project integration

OpsLens PR #89 remains separate consumer-side work for the Governed LLM Gateway project. It must not be modified or merged as a side effect of Phase 14 closeout or Phase 15 planning.
