# Phase 11 Gate 11.3 — Offline Single-Agent Evaluation

## Objective

Create a reproducible offline baseline for the already-frozen Gate 11.1 authorization and Gate
11.2 typed execution contracts before introducing any real reasoning model or runtime.

## Contract

```text
single-agent-evaluation:v1
```

Frozen upstream contracts remain unchanged:

```text
single-agent-authority:v1
single-agent-execution:v1
operational-telemetry:v1
```

## Architecture

```text
strict golden JSON fixture
 -> typed content-addressed AgentEvaluationDataset
 -> SingleAgentTask + untrusted AgentActionProposal
 -> authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
 -> optional typed AgentCapabilityInvocation
 -> execute_authorized_capability(...), at most once
 -> stable observation
 -> deterministic decomposed metrics
 -> content-addressed AgentEvaluationReport
```

No evaluation branch can authorize a capability on behalf of Gate 11.1 or repair a rejected Gate
11.2 result binding.

## Golden cases

The first corpus contains six small cases:

| Case | Authorization | Execution | Expected stable result |
|---|---|---|---|
| `authorized-structured-no-execution` | allowed | no | authorized |
| `explicit-abstention` | abstain | no | abstained |
| `unauthorized-capability` | denied | no | `capability_authorization` |
| `structured-execution-admitted` | allowed | one attempt | admitted |
| `structured-executor-failure` | allowed | one attempt | `executor_failure` |
| `structured-result-contract-failure` | allowed | one attempt | `result_contract` |

The execution cases use the existing typed `StructuredSecurityQueryInvocation` and
`StructuredSecurityQueryResultBinding`. They do not add a generic tool registry or an arbitrary
argument surface.

## Metrics

Gate 11.3 computes exact integer dimensions:

```text
total_cases
passed_cases
authorization_matches
capability_matches
execution_matches
failure_category_matches
bounds_compliant_cases
```

The case result preserves the observed capability and stable failure category, so a failed metric
cannot be "corrected" by reinterpretation during reporting.

## Security properties

- fixture schema drift fails closed;
- proposal data remains untrusted;
- only the existing deterministic authorization function grants capability authority;
- only typed Gate 11.2 invocation/result bindings can become execution evidence;
- executor exception messages are not admitted into evaluation evidence;
- the evaluator performs no retries or adaptive fallback;
- one case performs at most one capability execution attempt;
- report serialization omits raw task text and arbitrary executor/provider content.

## Runtime and cost boundary

For this gate:

```text
real reasoning model calls: 0
real AWS calls:             0
new AWS resources:          0
new IAM roles/policies:     0
AgentCore runtime:          0
MCP:                        0
A2A:                        0
gateway integration:        0
```

Therefore no AWS inference cost is measured or claimed for Gate 11.3. "No call" is recorded as
absence of runtime usage, not fabricated measured cost of zero.

## Validation commands

```bash
uv lock --check
uv run ruff check src/opslens/agent_baseline tests/unit/agent_baseline
uv run pyright src/opslens/agent_baseline tests/unit/agent_baseline
uv run pytest tests/unit/agent_baseline
```

The PR CI result is the authoritative validation evidence for the exact merged candidate SHA.

## Failure lab

The `structured-executor-failure` case raises an executor exception containing synthetic sensitive
text. Gate 11.2 converts it to `executor_failure`, and Gate 11.3 persists only that stable category.
The report test verifies that the original exception text is absent.

The `structured-result-contract-failure` case returns a valid typed result bound to a different
invocation. Gate 11.2 rejects it as `result_contract`; Gate 11.3 scores that rejection exactly
without admitting the mismatched result as evidence.

## Exit boundary

Gate 11.3 stops after deterministic offline evaluation. It does not prove real model reasoning
quality, provider latency, token use, or runtime cost. Those measurements require an explicitly
authorized later gate after this baseline is merged and preserved.
