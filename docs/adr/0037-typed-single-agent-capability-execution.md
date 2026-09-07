# ADR 0037 — Typed Single-Agent Capability Execution

- Status: Accepted
- Date: 2026-09-07
- Phase: 11 — Single-Agent Baseline
- Gate: 11.2

## Context

Gate 11.1 froze `single-agent-authority:v1` and established that an agent proposal is not capability authorization and capability authorization is not execution.

The next architectural question is deliberately narrower than a full agent loop:

> How can an already-authorized action enter one existing OpsLens capability without turning model output, framework dispatch, or a generic tool registry into execution authority?

The unsafe shortcut would be:

```text
AuthorizedAgentAction
 -> generic tool name + arbitrary args
 -> framework dispatch
 -> downstream result
```

That would reintroduce authority through arguments even though the capability name itself had been authorized. It would also allow existing deterministic OpsLens contracts to be bypassed by a new agent-specific execution surface.

## Decision

Freeze a separate provider-neutral execution contract:

```text
single-agent-execution:v1
```

The Gate 11.1 contract remains unchanged:

```text
single-agent-authority:v1
```

The execution flow is:

```text
AuthorizedAgentAction
 -> exact typed capability invocation
 -> deterministic capability/action match
 -> explicit capability-specific executor port
 -> at most one execution attempt
 -> typed downstream result admission
 -> content-addressed AgentCapabilityExecution
 -> STOP
```

The permanent distinctions are:

```text
agent action proposal != capability authorization != execution result
AuthorizedAgentAction != capability invocation
capability invocation != execution result
```

## Exact typed bindings

Gate 11.2 exposes only four bindings to already-governed OpsLens contracts:

```text
structured_security_query
 -> SemanticQuery
 -> StructuredSecurityQueryResultBinding(AthenaQueryResult)

knowledge_guidance
 -> SynthesisRequest
 -> SynthesisResult

hybrid_security_answer
 -> HybridSynthesisRequest
 -> HybridSynthesisResult

public_repository_analysis
 -> PublicAnalysisRequest
 -> PublicAnalysisAdmissionHandoff
```

Each invocation class embeds the exact `AuthorizedAgentAction` plus one typed downstream request value. There is no generic `tool_name`, argument dictionary, arbitrary kwargs bag, URL, SQL string, shell command, browser operation, provider selection, model selection, credential, retry policy, or fallback policy.

## Argument authority

Gate 11.2 does not give the agent or a future model authority to author executable arguments.

The executable input for each capability must already satisfy the downstream deterministic contract:

- `SemanticQuery` owns the structured query surface and still contains no arbitrary SQL;
- `SynthesisRequest` must already have passed knowledge-retrieval authority admission;
- `HybridSynthesisRequest` must already be bound to a complete admitted hybrid evidence envelope;
- `PublicAnalysisRequest` must already be a content-addressed admitted public repository request.

The invocation layer binds those exact values to the authorized action. It does not reinterpret them.

## Invocation identity

Each typed invocation is content-addressed over:

```text
single-agent-execution:v1
authorized action_id
fixed capability
exact typed input identity
```

Input identity is capability-specific:

```text
structured -> canonical SemanticQuery semantics
knowledge  -> SynthesisRequest.request_sha256
hybrid     -> HybridSynthesisRequest.request_sha256
public     -> PublicAnalysisRequest.request_id + request_sha256
```

Changing the authorized action or executable input changes the invocation identity.

A capability mismatch between the `AuthorizedAgentAction` and the typed invocation fails before an executor call.

## Structured query/result binding

`AthenaQueryResult` is valid structured execution evidence but does not itself carry the exact `SemanticQuery` identity that produced it.

Gate 11.2 therefore introduces:

```text
StructuredSecurityQueryResultBinding
```

which content-addresses:

```text
single-agent-execution:v1
invocation_sha256
exact AthenaQueryResult evidence
```

This prevents an Athena result produced for one structured invocation from being rebound to another invocation.

The model never authors or validates this binding.

## Knowledge and hybrid result admission

Knowledge and hybrid synthesis results already carry deterministic request identities.

Execution admission therefore requires:

```text
SynthesisResult.request_sha256
 == KnowledgeGuidanceInvocation.request.request_sha256
```

and:

```text
HybridSynthesisResult.request_sha256
 == HybridSecurityAnswerInvocation.request.request_sha256
```

A typed result from another request is rejected after the one executor attempt and cannot become `AgentCapabilityExecution` evidence.

## Public-analysis result admission

A successful public capability result must be one admitted `PublicAnalysisAdmissionHandoff` whose source execution remains bound to the exact public request in the invocation.

Gate 11.2 verifies both:

```text
request_id
request_sha256
```

before creating agent execution evidence.

This preserves the existing Phase 9 source, routing, and handoff authority rather than creating a parallel agent-specific public-analysis authority.

## Executor ports

The application layer defines four explicit protocols:

```text
StructuredSecurityQueryExecutor
KnowledgeGuidanceExecutor
HybridSecurityAnswerExecutor
PublicRepositoryAnalysisExecutor
```

They are grouped in a closed `AgentCapabilityExecutors` value only for explicit dependency injection. This is not a dynamic registry and cannot dispatch an arbitrary caller-provided tool string.

The dispatcher accepts only the closed `AgentCapabilityInvocation` union.

## Execution limits

V1 freezes:

```text
MAX_AGENT_EXECUTIONS_PER_CALL = 1
MAX_AGENT_EXECUTION_RETRIES = 0
MAX_AGENT_EXECUTION_ADAPTIVE_FALLBACKS = 0
```

One call to `execute_authorized_capability(...)` may attempt exactly one capability executor call.

There is no retry, alternate capability, provider fallback, hidden framework retry, or recursive agent loop in this gate.

## Failure semantics

Execution failures are projected into a bounded content-free taxonomy:

```text
executor_failure
result_contract
```

Arbitrary downstream exception text is not part of the admitted execution error and is not retained as execution evidence.

A downstream exception is surfaced as `executor_failure` after the single attempt. A wrong result type or downstream identity mismatch is surfaced as `result_contract`.

Neither failure causes another capability to execute.

## Execution evidence

Successful execution creates content-addressed `AgentCapabilityExecution` evidence over:

```text
action_id
capability
invocation_id
downstream_result_sha256
single-agent-execution:v1
```

This proves which authorized action entered which typed invocation and which admitted downstream result identity was accepted.

It does not claim that the agent owns the downstream truth semantics.

## Deterministic authority preservation

Gate 11.2 adds execution binding authority but does not move existing authorities into the agent layer.

Deterministic code still owns:

- package/version and vulnerability applicability;
- Risk Policy facts;
- `SemanticQuery` validation and SQL compilation;
- Athena result contract admission;
- knowledge evidence and synthesis request admission;
- hybrid routing, evidence completeness, citations, and synthesis output admission;
- public request/source/route/handoff admission;
- capability authorization;
- typed capability invocation/result binding;
- execution identity and execution limits.

A future agent may reason about which already-authorized capability to use. It does not obtain any of these authorities.

## Observability decision

Gate 11.2 does not add agent execution stages to `operational-telemetry:v1`.

The Phase 10 five-stage public-analysis telemetry contract remains frozen. Agent execution has different semantics and cardinality requirements. If agent execution telemetry is introduced later, it must use a separately versioned contract and preserve Phase 10 content-minimization, bounded-failure, and low-cardinality principles.

```text
telemetry evidence != business truth
telemetry evidence != execution authority
```

## AWS and IAM boundary

Gate 11.2 is an offline/provider-neutral execution-boundary gate:

```text
real reasoning model calls:   0
real AWS calls:               0
new AWS resources:            0
new IAM roles/policies:       0
public runtime:               0
AgentCore runtime:            0
MCP:                          0
A2A:                          0
runtime-exposure authority:   0
```

The tests use injected in-memory fakes and existing domain contracts. A protocol named after an existing AWS-backed capability does not prove that AWS was called in this gate.

Least-privilege runtime IAM remains deferred until a concrete deployed runtime and concrete adapters require it.

## Cost boundary

No real provider, AWS, or model execution occurs in Gate 11.2, so runtime cost is not measured.

```text
unmeasured future execution cost != zero future execution cost
```

A later real single-agent baseline must separately measure reasoning calls, capability calls, latency, failures/retries, and provider/runtime cost.

## Consequences

### Positive

- authorization cannot silently become generic tool execution;
- executable inputs remain typed by existing OpsLens contracts;
- model-authored arbitrary arguments remain impossible in v1;
- downstream result rebinding is rejected deterministically;
- all four capability paths have explicit ports and result-admission rules;
- one-attempt execution behavior is regression-testable offline;
- execution evidence is content-addressed and independent of framework/provider choice.

### Trade-offs

- callers must construct already-admitted typed capability inputs before execution;
- the executor dispatcher is intentionally explicit rather than dynamically extensible;
- adding a capability requires an explicit invocation/result contract and code change;
- no multi-step autonomy exists yet.

These constraints are intentional because the baseline is optimizing for auditable authority, not maximum autonomy.

## Rejected alternatives

### Generic tool registry with arbitrary kwargs

Rejected because it would create a second execution authority surface outside existing OpsLens contracts.

### Let the model author typed invocation arguments

Rejected in Gate 11.2. Typed Python objects alone do not make model-authored arguments authoritative. Argument construction and admission must remain deterministic until a later gate explicitly evaluates a bounded proposal-to-input mapping.

### Reuse a single generic executor protocol

Rejected because capability-specific ports make the dependency and result contract explicit and prevent best-effort dynamic dispatch.

### Retry another capability after executor failure

Rejected because it would turn failure handling into implicit route/execution authority and make the one-step baseline harder to evaluate.

### Add agent steps to `operational-telemetry:v1`

Rejected because Phase 10 operational stages and agent execution stages are semantically different evidence contracts.

## AIP-C01 learning notes

This gate demonstrates professional agentic-system design principles relevant to AWS Certified Generative AI Developer – Professional preparation:

- authorization and invocation should be separate from model reasoning;
- structured model output is not equivalent to execution authority;
- tool/capability arguments need deterministic admission, not only schema validation;
- least privilege starts with a narrow application capability surface before IAM is granted;
- explicit request/result identity prevents evidence from being rebound across executions;
- bounded retries and fallback semantics are part of the security and evaluation contract;
- managed agent runtimes should implement an already-defined authority model rather than define it implicitly;
- offline deterministic tests should prove execution boundaries before adding model/runtime nondeterminism.

## Deferred integration

OpsLens PR #89 remains open/draft as deferred consumer-side work for Phase 14 — Case 3 of the separate Governed LLM Gateway project. Gate 11.2 does not merge, rebase, or otherwise alter that integration.

## Next

Gate 11.3 may freeze a deterministic single-agent evaluation dataset over the Gate 11.1 authority contract and Gate 11.2 execution contract.

It must establish measurable cases and independent metrics before Gate 11.4 introduces the first real bounded model-reasoning baseline.
