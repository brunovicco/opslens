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
Phase 15   A2A                                                 NEXT / PLANNED
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

Agentic/runtime authority remains explicitly separated:

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

Deterministic code continues to own package/version semantics, vulnerability applicability, source evidence, KEV/EPSS/CVSS facts, Risk Policy v1, semantic-query validation, SQL compilation, retrieval/evidence admission, hybrid completeness, citation/evidence identity, public request admission, immutable repository evidence binding, capability allowlists, capability authorization, executable-input bindings, result admission, handoff admission, MCP mapping/admission/projection authority, provider/model selection, retry/fallback policy, application session ownership, cost/execution bounds, and runtime-exposure truth.

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

References:

```text
docs/adr/0052-agentcore-runtime-capability-fit.md
labs/phase-14-gate-14-1-agentcore-runtime-capability-fit.md
```

### Gate 14.2 — measured Runtime experiment

Terminal successful experiment:

```text
source main:                e5072ec68b421677359cebb1eb449578ef7d5b49
workflow:                   AgentCore Runtime Experiment
run:                        34378942784 / run #11 / SUCCESS
job:                        102558703872
runtime:                    opslens_dev_bounded_runtime-Cl8aNBDGzh
runtime version:            1
protocol:                   HTTP
network:                    PUBLIC — dev-only experiment exception
artifact SHA256:            a846034ad646c4f6383ac08e47d9ed065b4a9f3349c14104db49a2d510b3ec88
Phase 11 corpus SHA256:     3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
replay:                     6 / 6 PASS
HTTP responses:             200
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
AgentCore CPU:       USD 0.000488269512361131
AgentCore memory:    USD 0.001892075623767353
AgentCore Runtime:   USD 0.002380345136128484
Bedrock inference:   USD 0.004192100000000000
------------------------------------------------
TOTAL:               USD 0.006572445136128483
```

No monthly extrapolation is authorized from this experiment.

Immutable evidence:

```text
labs/evidence/phase-14-gate-14-2-final-runtime-experiment-v1.json
```

### Gate 14.3 — retention decision

Gate 14.3 recorded:

```text
overall decision class:                    RETAIN WITH CHANGES
default OpsLens reasoning runtime:         DO NOT RETAIN AgentCore
Phase 11 direct Bedrock reference:         RETAIN
AgentCore implementation/evidence:         RETAIN
AgentCore active deployment role:          OPTIONAL LAB / FUTURE CONSUMER TARGET ONLY
PUBLIC network mode:                       DO NOT RETAIN
standing AgentCore Runtime resources:      DO NOT RETAIN
standing experiment-specific IAM:          CLEANUP REQUIRED
```

Comparable quality/efficiency evidence:

```text
Phase 11:  6/6, 6 model calls, 3291/104/3395 tokens
AgentCore: 6/6, 6 model calls, 3291/104/3395 tokens
```

The unchanged Bedrock inference cost was USD 0.0041921. AgentCore added USD 0.002380345136128484 of measured Runtime compute, 56.78168784448091% relative to the inference component for this experiment.

Latency remains deliberately non-normalized:

```text
Phase 11 client elapsed sum:     8279 ms
Gate 14.2 transport elapsed sum: 19981 ms
normalized percentage delta:     NOT PROVEN
```

Decision records:

```text
docs/adr/0054-retain-agentcore-only-as-optional-lab-target.md
labs/phase-14-gate-14-3-agentcore-retention-decision.md
labs/evidence/phase-14-gate-14-3-agentcore-retention-decision-v1.json
```

### Gate 14.4 — standing experiment IAM cleanup

Repository desired-state cleanup was protected-merged in PR #225:

```text
merge SHA:                 9913c3cbf5f2239d6445042a139a9cca890590c8
exact-head AgentCore CI:   34396085154 / run #63 / PASS
exact-head Terraform CI:   34396085123 / run #267 / PASS
```

Human bootstrap plan:

```text
0 add / 0 change / 4 destroy
```

Applied exactly:

```text
aws_iam_policy.github_actions_agentcore_deploy
aws_iam_role.github_actions_agentcore_replay
aws_iam_role_policy.github_actions_agentcore_replay
aws_iam_role_policy_attachment.github_actions_agentcore_deploy
```

Apply result:

```text
0 added / 0 changed / 4 destroyed
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

The service-linked role remains protected because safe account-level deletion has not been proven. It is not equivalent to standing GitHub experiment authority.

Gate 14.4 evidence:

```text
docs/adr/0055-remove-standing-agentcore-experiment-iam.md
labs/phase-14-gate-14-4-agentcore-iam-cleanup.md
labs/evidence/phase-14-gate-14-4-agentcore-iam-cleanup-predeploy-v1.json
labs/evidence/phase-14-gate-14-4-agentcore-iam-cleanup-postapply-v1.json
```

## Final Phase 14 retained state

```text
Phase 11 direct Bedrock reasoning reference:  RETAIN / DEFAULT
AgentCore implementation/evidence:           RETAIN
AgentCore managed Runtime as default:         DO NOT RETAIN
AgentCore standing Runtime resources:         NONE RETAINED
AgentCore standing experiment GitHub IAM:     REMOVED
Gate 14.2 PUBLIC network exception:           NOT RETAINED
Runtime Identity service-linked role:         RETAINED pending separate safety proof
```

The historical AgentCore workflow/code remains reproducible lab material, but it is intentionally non-operational without a future evidence-backed re-bootstrap of minimum authority.

## Phase 14 non-claims

Phase 14 does not establish:

```text
AgentCore as the default/production runtime
PUBLIC as a production network decision
production SLOs
production security approval
runtime deployment == runtime exposure
runtime telemetry == business truth
runtime authentication == capability authorization
AgentCore hosting == business authorization
```

No AgentCore Memory, Gateway/Policy, Browser, Code Interpreter, MCP/A2A hosting, or capability execution was retained as production architecture.

## Deferred Governed LLM Gateway integration

PR #89 remains open/draft and is separate cross-project work for the Governed LLM Gateway. It remains untouched by Phase 14 and must be re-evaluated independently before any merge.

Preserved branch/head:

```text
feat/governed-gateway-semantic-planner
3781831795d500b05fa4bc602d50f376b4b1539f
```

## Next authorized phase

Phase 15 — A2A is next.

Its first gate must begin from a concrete interoperability problem and preserve the existing deterministic authority model. A2A must not be introduced merely because Phase 15 exists on the roadmap, and it must not assume AgentCore as the hosting substrate.

The first Phase 15 issue should answer, before implementation:

```text
Which agent/service boundary actually requires A2A interoperability?
What identity and message contract is needed?
What remains proposal/admission authority versus capability authorization?
What failure, replay, provenance, observability, and cost evidence is required?
```
