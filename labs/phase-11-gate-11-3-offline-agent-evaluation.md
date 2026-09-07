# Phase 11 Gate 11.3 — Offline Single-Agent Evaluation

## Status

```text
COMPLETE / MERGED
```

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

## Exact merged evidence

```text
issue #153:              CLOSED / COMPLETED
PR #154 final head:      2dcc7abfc559a8a0b053278a68c926b5dc38d694
Single-Agent CI:         34163023511 / run #14 / PASS
job:                     101868535029
PR merge test commit:    96628ebc2bb5acffa6e27446de28e1073e9d6100
uv lock --check:         PASS
Ruff:                    PASS
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  37 passed in 0.54s
PR #154 merge SHA:       b1b2f4e45005f1d55a017f4761f3b7e061f8a070
post-merge workflow:     NONE — Single-Agent CI has no push trigger
```

The exact-head PR CI remains the authoritative executable evidence. The merge was protected with
`expected_head_sha=2dcc7abfc559a8a0b053278a68c926b5dc38d694`.

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

The merged gate preserves:

```text
agent proposal != authorization != execution result != evaluation score
authorization evidence != execution evidence != evaluation evidence != operational telemetry
```

## Next gate

```text
Gate 11.4 — First Bounded Model Reasoning Baseline — NEXT
```

Gate 11.4 is the first gate permitted to add a real reasoning-model call. It must consume the
frozen Gate 11.1–11.3 boundaries rather than broaden them. The model may only produce an untrusted
bounded proposal; deterministic code retains capability authorization, typed execution admission,
result binding, metric computation, and report identity.

PR #89 remains deferred and untouched.
