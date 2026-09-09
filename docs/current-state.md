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
  Gate 14.1 AgentCore Runtime capability-fit / authority       COMPLETE / MERGED
  Gate 14.2 First bounded HTTP/SigV4 runtime experiment        COMPLETE / MEASURED
  Gate 14.3 AgentCore Runtime retention decision               COMPLETE / RETAIN WITH CHANGES
  Gate 14.4 Standing experiment IAM cleanup                    COMPLETE / VERIFIED
Phase 15   A2A                                                 IN PROGRESS
  Gate 15.1 A2A capability fit / authority boundary            COMPLETE / GO OFFLINE ONLY
  Gate 15.1 protocol-baseline correction                       COMPLETE / A2A 1.0.0
  Gate 15.2 Reference-only A2A adapter contract                COMPLETE / MEASURED
  Gate 15.3 Official SDK conformance check                     NEXT / AUTHORIZED
Phase 16   Runtime Exposure with Amazon Inspector              PLANNED
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

Agentic/runtime/interoperability authority remains explicitly separated:

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
A2A message != capability authorization
A2A peer identity != business authority
A2A AgentCard skill != OpsLens capability authorization
A2A task state != business/evidence truth
A2A transport success != business/evidence truth
A2A artifact != admitted OpsLens evidence
A2A handoff proposal != handoff admission
A2A context/task identity != OpsLens source-task identity
A2A authentication != capability authorization
A2A protocol binding != business authority
A2A generated id != OpsLens content identity
A2A SDK acceptance != OpsLens admission authority
```

Deterministic code continues to own package/version semantics, vulnerability applicability, source evidence, KEV/EPSS/CVSS facts, Risk Policy v1, semantic-query validation, SQL compilation, retrieval/evidence admission, hybrid completeness, citation/evidence identity, public request admission, immutable repository evidence binding, capability allowlists, capability authorization, executable-input bindings, result admission, handoff admission, MCP mapping/admission/projection authority, A2A reference identity/resolution/admission authority, provider/model selection, retry/fallback policy, application session ownership, cost/execution bounds, and runtime-exposure truth.

## Retained reasoning architecture

Phase 11 remains the default/reference measured reasoning path:

```text
SingleAgentTask
 -> code-owned AgentCapability allowlist
 -> one bounded model reasoning invocation
 -> transient untrusted {decision, capability}
 -> deterministic parser
 -> AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
```

Frozen six-case reference:

```text
provider:                     Amazon Bedrock Converse
region:                       us-east-1
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

Historical reference:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
```

## Retained Phase 12 decision

Phase 12 retained deterministic specialization/handoff and comparison discipline, but did not retain the two-model topology as the default:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
```

The measured two-model topology produced no quality lift while increasing invocations, tokens, latency, and cost.

The reusable Gate 12.1 boundary remains:

```text
TriageAgentTask
 -> untrusted MultiAgentHandoffProposal
 -> deterministic source-task binding
 -> code-owned specialization mapping
 -> deterministic capability intersection
 -> AuthorizedMultiAgentHandoff | abstention | fail closed
 -> SpecialistAgentTask
```

This authority boundary is the reference input for Phase 15 A2A work, without reactivating the rejected two-model topology.

## Retained Phase 13 MCP boundary

Phase 13 is complete and retains a bounded offline MCP interoperability layer over existing capability authority:

```text
Phase 11 typed capability authority
 -> mcp-capability-exposure:v1
 -> official MCP SDK reference-only adapter
 -> raw exact-key-set argument refusal
 -> deterministic invocation resolution + admission
 -> mcp-capability-execution:v1
 -> exactly one existing typed executor attempt
 -> existing typed result admission
 -> mcp-result-projection:v1 for structured_security_query only
 -> bounded CVE + EPSS rows
 -> STOP before public/network runtime
```

MCP remains development-only in the current retained implementation. It does not create capability authorization or generic business-result authority.

Closeout evidence:

```text
labs/evidence/phase-13-closeout-v1.json
docs/adr/0051-phase13-mcp-closeout.md
```

## Phase 14 closeout — Amazon Bedrock AgentCore

Phase 14 evaluated AgentCore as a measured capability rather than assuming that managed hosting should become the default architecture.

### Gate 14.1 — capability fit

Gate 14.1 authorized one bounded experiment only:

```text
AgentCore Runtime:       GO TO ONE BOUNDED EXPERIMENT ONLY
hosted boundary:         retained Phase 11 reasoning path
protocol:                HTTP
authentication:          IAM SigV4
capability executions:   0
adaptive retries:        0
adaptive fallbacks:      0
MCP runtime promotion:   not authorized
A2A:                     deferred
runtime-exposure truth:  not created
```

### Gate 14.2 — measured Runtime experiment

Terminal successful experiment:

```text
source main:                e5072ec68b421677359cebb1eb449578ef7d5b49
workflow:                   AgentCore Runtime Experiment
run:                        34378942784 / run #11 / SUCCESS
job:                        102558703872
runtime:                    opslens_dev_bounded_runtime-Cl8aNBDGzh
protocol:                   HTTP
network:                    PUBLIC — dev-only experiment exception
replay:                     6 / 6 PASS
capability executions:      0
SDK retries:                0
input/output/total tokens:  3291 / 104 / 3395
transport elapsed sum:      19981 ms
```

Negative authorization proof:

```text
OpsLensGitHubDeployRole
 -> bedrock-agentcore:InvokeAgentRuntime
 -> AccessDeniedException / HTTP 403
```

Runtime cleanup proof:

```text
Terraform:                  0 add / 0 change / 3 destroy
independent verifier:       RESOURCE_NOT_FOUND
```

Observed successful six-case cost:

```text
AgentCore Runtime:   USD 0.002380345136128484
Bedrock inference:   USD 0.004192100000000000
TOTAL:               USD 0.006572445136128483
```

No monthly extrapolation is authorized from this experiment.

### Gate 14.3 — retention decision

```text
overall decision class:                    RETAIN WITH CHANGES
default OpsLens reasoning runtime:         DO NOT RETAIN AgentCore
Phase 11 direct Bedrock reference:         RETAIN
AgentCore implementation/evidence:         RETAIN
PUBLIC network mode:                       DO NOT RETAIN
standing AgentCore Runtime resources:      DO NOT RETAIN
standing experiment-specific IAM:          CLEANUP REQUIRED
```

The unchanged Bedrock inference cost was USD 0.0041921. AgentCore added USD 0.002380345136128484 of measured Runtime compute, 56.78168784448091% relative to the inference component for this experiment. Latency remains deliberately non-normalized.

### Gate 14.4 — standing experiment IAM cleanup

Repository desired-state cleanup was protected-merged in PR #225 at:

```text
9913c3cbf5f2239d6445042a139a9cca890590c8
```

Human bootstrap:

```text
plan:   0 add / 0 change / 4 destroy
apply:  0 add / 0 change / 4 destroy
```

Post-apply convergence:

```text
No changes. Your infrastructure matches the configuration.
```

Independent IAM verification:

```text
OpsLensAgentCoreReplayRole:                 ABSENT / NoSuchEntity
OpsLensAgentCoreDeployDevAccess:            ABSENT / NoSuchEntity
AgentCore policy attachment on shared role: []
OpsLensGitHubDeployRole:                    PRESENT
AWSServiceRoleForBedrockAgentCoreRuntimeIdentity:
                                            PRESENT / intentionally retained
```

Final Phase 14 retained state:

```text
Phase 11 direct Bedrock reasoning reference:  RETAIN / DEFAULT
AgentCore implementation/evidence:           RETAIN
AgentCore managed Runtime as default:         DO NOT RETAIN
AgentCore standing Runtime resources:         NONE RETAINED
AgentCore standing experiment GitHub IAM:     REMOVED
Gate 14.2 PUBLIC network exception:           NOT RETAINED
Runtime Identity service-linked role:         RETAINED pending separate safety proof
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

## Phase 15 Gate 15.1 — A2A capability fit

Gate 15.1 originally used the historical versioned A2A `0.3.0` documentation page and incorrectly described it as the current latest stable protocol. The correction preserves that first artifact historically but supersedes its protocol-version claim.

Correct official protocol baseline verified on 2026-09-09:

```text
latest released protocol:      A2A 1.0.0
release date:                  2026-03-12
previous protocol:             0.3.0
standard bindings:             JSONRPC / GRPC / HTTP+JSON
OpsLens first binding choice:  JSONRPC
Python SDK latest observed:    1.1.4
SDK pinned by Gate 15.1:       NO
```

A2A v1.0 Agent Cards expose `supportedInterfaces`; each interface declares `url`, `protocolBinding`, and `protocolVersion`. The binding is protocol metadata, never business authority.

The capability-fit finding is unchanged:

```text
retained independently deployed OpsLens agent peer: NO
current in-process handoff requires network A2A:    NO
bounded protocol-fit hypothesis exists:            YES
```

Decision:

```text
GO TO ONE BOUNDED OFFLINE/IN-PROCESS INTEROPERABILITY EXPERIMENT
```

Decision records:

```text
docs/adr/0056-bounded-a2a-capability-fit.md
labs/phase-15-gate-15-1-a2a-capability-fit.md
labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v1.json  # historical / protocol claim superseded
labs/evidence/phase-15-gate-15-1-a2a-capability-fit-v2.json  # authoritative corrected evidence
```

## Phase 15 Gate 15.2 — bounded offline A2A reference adapter

Gate 15.2 is complete and measured. It retains a strict offline adapter over one already-admitted specialist-task reference; it does not create a distributed runtime.

Protected implementation merge:

```text
PR:                  #231
main SHA:            3a9adfdcfdd206d1c932a2d90bcb312377596b70
measurement head:    c27a2362df4971a7b619be33dcaacd2bfe2a2369
contract:            a2a-reference-interoperability:v1
A2A release:         1.0.0
binding:             JSONRPC
operation:           SendMessage
```

Retained path:

```text
pre-admitted SpecialistAgentTask
 -> deterministic content-addressed A2AReference
 -> lab-only in-memory code-owned registry
 -> strict A2A 1.0 JSON-RPC SendMessage projection
 -> raw duplicate-key + exact-shape validation
 -> code-owned reference resolution
 -> bounded Message or terminal completed Task metadata
 -> deterministic OpsLens result admission
 -> STOP before model/capability execution
```

Reference-only protocol fields:

```text
handoff_id
specialist_task_id
reference_sha256
```

The protocol does not author task text, capability scope, specialization authority, model/provider selection, executable inputs, SQL, URLs, credentials, retry/fallback policy, or business results.

SDK/dependency decision:

```text
official Python SDK inspected: 1.1.4
a2a-sdk runtime dependency:   0
a2a-sdk dev dependency:       0 for Gate 15.2
new runtime dependencies:     0
```

The official SDK remains reference evidence only at this gate because the selected wire profile can be validated with deterministic stdlib code. SDK acceptance is not OpsLens admission authority.

Measured local evidence:

```text
Agent Card bytes:          582
protocol requests:         2
peer handler attempts:     2
request bytes total:       1308
response bytes total:      989
client elapsed sum:        0.353039 ms
handler elapsed sum:       0.239397 ms
retries:                   0
model invocations:         0
capability executions:     0
new AWS resources:         0
new IAM roles/policies:    0
incremental AWS cost:      USD 0.00
```

These latency values are local process measurements only and are not production/network SLO evidence.

Validation history:

```text
first A2A CI:  34403479455 / #1 — functional experiment PASS, Ruff RUF022 FAIL
remediation:   c27a2362df4971a7b619be33dcaacd2bfe2a2369 — export ordering only
measured CI:   34405966213 / #2 — SUCCESS, 25 pytest tests, Pyright 0 errors
final PR head: 033038238dd84cd15c4cddfbf159b568b917ef50
A2A CI:        34406512226 / #7  — SUCCESS
Multi-Agent:   34406512227 / #42 — SUCCESS
AgentCore CI:  34406512228 / #70 — SUCCESS
```

Retained Gate 15.2 claims:

```text
content-addressed reference projection:       PROVEN
raw fail-closed protocol admission:           PROVEN
Message metadata admission:                   PROVEN
terminal completed Task metadata admission:   PROVEN
cross-implementation SDK conformance:         NOT YET PROVEN
network/runtime interoperability:              NOT PROVEN
business-result authority:                     NOT CREATED
```

Records:

```text
docs/adr/0057-bounded-offline-a2a-reference-adapter.md
labs/phase-15-gate-15-2-bounded-offline-a2a-reference-adapter.md
labs/evidence/phase-15-gate-15-2-bounded-offline-a2a-reference-adapter-v1.json
```

## Deferred Governed LLM Gateway integration

PR #89 remains open/draft and is separate cross-project work for the Governed LLM Gateway. It remains untouched and must be re-evaluated independently before any merge.

Preserved branch/head:

```text
feat/governed-gateway-semantic-planner
3781831795d500b05fa4bc602d50f376b4b1539f
```

## Next authorized action

Phase 15 Gate 15.3 only:

> Run one bounded offline conformance check using the official Python A2A SDK as an independent protocol oracle for the already-frozen happy-path Agent Card and `SendMessage` profile, while keeping OpsLens raw validation, content identity, and result admission authoritative.

Gate 15.3 must keep network deployment, AWS/IAM changes, model invocations, capability executions, and business-result transport at zero. A real network peer remains deferred until a concrete independent consumer requirement exists.
