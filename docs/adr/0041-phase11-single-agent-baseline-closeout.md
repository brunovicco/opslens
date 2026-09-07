# ADR 0041 — Close Phase 11 at the bounded single-agent baseline

- Status: Accepted
- Date: 2026-09-07
- Phase: 11 — Single-Agent Baseline
- Gate: 11.6 — Phase 11 Closeout

## Context

Phase 11 introduced agentic reasoning only after OpsLens had already frozen deterministic authority for structured security facts, semantic retrieval, hybrid evidence, public repository admission, operational evidence, capability authorization, typed capability execution, and deterministic evaluation.

The completed Phase 11 sequence is:

```text
Gate 11.1 — Capability Authorization Contract                COMPLETE / MERGED
Gate 11.2 — Typed Capability Bindings + Offline Executor      COMPLETE / MERGED
Gate 11.3 — Frozen Single-Agent Evaluation Fixture            COMPLETE / MERGED
Gate 11.4 — First Bounded Model Reasoning Baseline            COMPLETE / MERGED
Gate 11.5 — Measured Optimization Decision                    COMPLETE / MERGED — NO-CHANGE
Gate 11.6 — Phase 11 Closeout                                 THIS DECISION
```

The real Gate 11.4 replay used Amazon Bedrock Converse with the fixed `us.anthropic.claude-haiku-4-5-20251001-v1:0` inference profile and the frozen six-case reasoning corpus. It produced:

```text
proposal quality:             6/6
bounds compliance:            6/6
SDK retries:                  0
capability executions:        0
input/output/total tokens:    3291 / 104 / 3395
provider latency median:      809.5 ms
client elapsed median:        977.5 ms
derived six-case cost:        USD 0.0041921
```

The historical evidence is preserved at:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Gate 11.5 reviewed that evidence and found no material measured quality, reliability, token, latency, or cost gap that justified a bounded optimization experiment. The resulting `NO-CHANGE / NO-EXPERIMENT` decision is itself part of the Phase 11 engineering evidence.

## Decision

Close Phase 11 at the bounded single-agent baseline and freeze the following contracts as the reference architecture for subsequent agentic work:

```text
single-agent-authority:v1
single-agent-execution:v1
single-agent-evaluation:v1
single-agent-reasoning:v1
single-agent-reasoning-evaluation:v1
```

The permanent reasoning authority path remains:

```text
SingleAgentTask
 -> code-owned allowed capabilities
 -> one bounded model reasoning invocation
 -> transient untrusted {decision, capability}
 -> deterministic parser
 -> AgentActionProposal
 -> deterministic authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
```

The Gate 11.4 model-quality baseline deliberately ends at `STOP` before capability execution. This is not an implementation gap: it isolates model proposal quality from capability execution quality and preserves Gate 11.2 as the independent typed execution/result-admission authority.

A valid model proposal does not grant execution authority.

## Frozen authority boundary

Deterministic code continues to own:

- package/version semantics and vulnerability applicability;
- CVE/GHSA/NVD reconciliation and KEV/EPSS/CVSS/Risk Policy facts;
- `SemanticQuery` validation and SQL compilation;
- retrieval/evidence admission and hybrid route/completeness;
- canonical evidence and citation identity;
- public request/repository evidence admission;
- capability allowlists and capability authorization;
- exact typed capability invocation admission;
- downstream result binding and execution evidence identity;
- reasoning-output admission;
- evaluation expectations, metrics, bounds, and report identity;
- provider/model selection and retry/fallback policy;
- runtime-exposure authority.

LLMs may classify, plan, propose, synthesize, explain, select already-admitted citation IDs, and propose one already-permitted capability. They do not acquire deterministic truth, authorization, executable-argument authority, arbitrary tool authority, SQL authority, evaluation authority, or runtime-exposure authority.

The following distinctions are permanent:

```text
agent action proposal != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
structured model output != trusted proposal
evaluation evidence != operational telemetry
model selection != capability authority
```

## Evidence admission

Raw model output is transient. Arbitrary provider text, exception messages, prompts, and model-generated prose are not admitted into canonical reasoning/evaluation evidence merely because a provider returned them.

Admitted invocation evidence remains content-minimized and provider-neutral. Historical Gate 11.4 evidence is immutable and must not be overwritten by later experiments.

## Optimization decision

Gate 11.5 established that an optimization gate does not imply an optimization must be performed.

No prompt compression, model/profile switch, prompt caching, retry/fallback expansion, connection warm-up experiment, or capability expansion is authorized without a future measured target and predeclared success threshold.

This avoids introducing complexity that cannot be justified by the observed baseline.

## AWS / IAM / runtime boundary

Phase 11 created no new deployed agent runtime and does not authorize new runtime infrastructure through this closeout.

```text
new AWS resources in Gate 11.6:    0
new IAM roles/policies:             0
AgentCore runtime:                  0
MCP runtime:                        0
A2A runtime:                        0
public agent runtime:               0
runtime-exposure authority:         0
Governed LLM Gateway integration:   0
```

The real Gate 11.4 replay used an already-authorized local AWS Identity Center profile. No credentials are stored in the repository.

## What Phase 11 proves

Phase 11 proves that OpsLens can place one real model reasoning step behind deterministic capability authority while preserving bounded execution, content-addressed evidence, deterministic evaluation, measured runtime evidence, and fail-closed proposal admission.

It proves an acceptance-corpus result for the frozen six-case corpus. It does not prove universal model correctness.

## What Phase 11 does not prove

```text
multi-agent quality or coordination
public/deployed agent runtime
production request volume
production p95/p99 or SLO compliance
AgentCore runtime behavior
MCP interoperability
A2A interoperability
runtime exposure / Amazon Inspector evidence
universal model correctness
production cost/request
AWS billing reconciliation
```

These are future claims that require their own concrete evidence.

## Phase 12 entry criteria

Phase 12 — Multi-Agent Architecture — becomes the next planned phase after this closeout merges.

Multi-agent complexity is not automatically justified by roadmap sequence. Any specialization must:

1. have one explicit bounded responsibility;
2. preserve all deterministic authority boundaries frozen through Phase 11;
3. avoid generic tool/argument authority;
4. define bounded handoff semantics and failure behavior before implementation;
5. compare measured results against the frozen Phase 11 single-agent reference before claiming improvement;
6. avoid AgentCore, MCP, or A2A adoption unless a later gate independently justifies those technologies.

A multi-agent topology that cannot demonstrate measurable value over the single-agent reference should not be retained.

## Deferred cross-project integration

OpsLens PR #89 remains deferred consumer-side work for Phase 14 — Case 3 of the separate `brunovicco/governed-llm-gateway` project. Phase 11 closeout does not make that PR mergeable and does not modify its branch.

## Consequences

### Positive

- Phase 11 ends with a reproducible real-model baseline rather than an architectural claim.
- Authorization and execution authority remain outside the model.
- Evaluation remains deterministic and decomposed.
- A measured `NO-CHANGE` decision prevents speculative optimization.
- Phase 12 inherits an explicit single-agent reference for comparative evaluation.
- No new AWS/IAM/runtime surface is added merely to close the phase.

### Trade-offs

- The first real model-quality corpus contains six cases and therefore has intentionally limited coverage.
- The model-quality replay does not exercise capability execution.
- Production latency, reliability, request-volume, and cost distributions remain unknown.
- Multi-agent benefits remain unproven until Phase 12 performs comparative evaluation.

## AIP-C01 learning relevance

This closeout reinforces certification-relevant principles through implementation evidence:

- separate generative reasoning from deterministic authorization;
- use structured outputs as untrusted proposals, not authority;
- retain provider-neutral application contracts with AWS-specific adapters;
- measure tokens, latency, retries, and cost from real inference evidence;
- evaluate before optimizing;
- preserve least privilege by refusing infrastructure/IAM expansion without a concrete runtime need;
- use deterministic evaluation where the expected outcome is structurally verifiable;
- treat managed agent services as architectural options, not mandatory certification checkboxes.
