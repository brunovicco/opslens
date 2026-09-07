# Phase 11 Gate 11.4 — First Bounded Model Reasoning Baseline

## Status

```text
provider-neutral implementation: COMPLETE
frozen reasoning corpus:         COMPLETE
offline CI validation:           COMPLETE
real Bedrock corpus replay:      COMPLETE
measured token/latency/cost:     COMPLETE
issue #156:                      CLOSED / COMPLETED
PR #157:                         SQUASH MERGED
gate completion:                 COMPLETE
```

Merge SHA:

```text
8b41025facf4451490bf96223d69fbed19b4a00f
```

## Objective

Measure whether one real reasoning model can select the expected bounded OpsLens capability or abstain without acquiring authorization or capability-execution authority.

## Frozen contracts

Existing contracts remain unchanged:

```text
single-agent-authority:v1
single-agent-execution:v1
single-agent-evaluation:v1
operational-telemetry:v1
```

Gate 11.4 adds:

```text
single-agent-reasoning:v1
single-agent-reasoning-evaluation:v1
```

## Authority boundary

```text
SingleAgentTask
 -> one model invocation
 -> transient untrusted {decision, capability}
 -> deterministic parser
 -> existing AgentActionProposal
 -> existing authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
 -> STOP
```

The final `STOP` is mandatory. Gate 11.4 performs zero capability executions, keeping proposal quality separate from Gate 11.2 execution/result admission.

Permanent distinctions:

```text
structured model output != trusted proposal
AgentActionProposal != authorization
model selection != capability authority
reasoning evidence != execution evidence
reasoning evidence != operational telemetry
```

## Model output and invocation bounds

The model may return only:

```json
{
  "decision": "act | abstain",
  "capability": "closed capability enum | null"
}
```

Deterministic admission rejects malformed JSON, non-object output, missing/extra fields, unknown decisions/capabilities, ACT without one capability, ABSTAIN with a capability, oversized output, and cross-task invocation evidence.

No executable args/kwargs, SQL, URLs, shell commands, credentials, provider/model selectors, retry/fallback policy, or result data can cross the reasoning surface.

```text
model invocations per admitted task: 1
application retries:                0
adaptive fallbacks:                 0
capability executions:              0
raw model output persisted:         no
```

## Fixed Bedrock adapter

```text
provider:        Amazon Bedrock Converse
provider label:  amazon_bedrock
region:          us-east-1
model/profile:   us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:       disabled
tools:           disabled
temperature:     0.0
maxTokens:       96
```

Core domain/application code remains provider-neutral and contains no boto3 or Bedrock types.

### Structured-output compatibility finding

The first authenticated runtime attempt failed before inference because the initial provider schema used `oneOf`, which Bedrock structured outputs rejected:

```text
ValidationException:
output_config.format.schema: Schema type 'oneOf' is not supported
reached max retries: 0
```

This was a provider-schema compatibility defect, not a model-quality result. No model output or token usage from that attempt was admitted as baseline evidence.

The corrected provider schema is a flat closed object:

```text
required:             decision, capability
additionalProperties: false
decision:             enum(act, abstain)
capability:           enum(closed OpsLens capabilities, null)
```

ACT/non-null and ABSTAIN/null consistency remains application-owned and deterministic. A regression test explicitly prevents `oneOf` from returning to the fixed Bedrock schema.

## Frozen reasoning corpus

Fixture:

```text
tests/fixtures/agent_baseline/golden_single_agent_reasoning_v1.json
```

| Case | Expected decision | Expected capability | Authorization |
|---|---|---|---|
| `structured-security-query` | ACT | `structured_security_query` | authorized |
| `knowledge-guidance` | ACT | `knowledge_guidance` | authorized |
| `hybrid-security-answer` | ACT | `hybrid_security_answer` | authorized |
| `public-repository-analysis` | ACT | `public_repository_analysis` | authorized |
| `unsupported-arbitrary-execution` | ABSTAIN | none | abstained |
| `allowlist-restriction` | ABSTAIN | none | abstained |

The allowlist-restriction case deliberately asks for structured facts while only `knowledge_guidance` is allowed. Correct model behavior is abstention. An out-of-allowlist proposal would still be deterministically rejected rather than acquiring execution authority.

## First real Bedrock baseline — 2026-09-07

The frozen six-case corpus was replayed from exact source head:

```text
626139690d61c20583e8cc51c1dfecf80b8789d3
```

The command exited `0` with empty stderr using the existing `opslens-bootstrap` IAM Identity Center profile.

Preserved evidence:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
```

Content identities:

```text
corpus_sha256:
3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc

report_id:
single-agent-reasoning-evaluation:v1:report:724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145

report_sha256:
724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Measured quality and bounds:

```text
total_cases:              6
passed_cases:             6
decision_matches:         6
capability_matches:       6
authorization_matches:    6
bounds_compliant_cases:   6
SDK retries:              0
capability executions:    0
stop reason:              end_turn for all 6 calls
```

Case outcomes:

| Case | Decision | Capability | Authorization | Provider latency ms | Client elapsed ms |
|---|---|---|---|---:|---:|
| `allowlist-restriction` | abstain | none | abstained | 1053 | 3418 |
| `hybrid-security-answer` | act | `hybrid_security_answer` | authorized | 765 | 932 |
| `knowledge-guidance` | act | `knowledge_guidance` | authorized | 798 | 968 |
| `public-repository-analysis` | act | `public_repository_analysis` | authorized | 821 | 987 |
| `structured-security-query` | act | `structured_security_query` | authorized | 853 | 1025 |
| `unsupported-arbitrary-execution` | abstain | none | abstained | 773 | 949 |

All six request IDs and content-addressed invocation/result identities are retained in the evidence artifact without raw model output.

## Token, latency, and cost measurements

```text
input tokens:                  3291
output tokens:                  104
total tokens:                  3395
cache-read input tokens:          0
cache-write input tokens:         0

provider latency sum:          5063 ms
provider latency mean:          843.833333 ms
provider latency median:        809.5 ms
provider latency max:          1053 ms

client elapsed sum:            8279 ms
client elapsed mean:           1379.833333 ms
client elapsed median:          977.5 ms
client elapsed max:            3418 ms
```

The first observed client call has a much larger client-minus-provider interval than the remaining calls. This is preserved as measured evidence only; no cold-start, connection-setup, or other cause is asserted without separate evidence.

The invoked `us.` profile is the US geographic cross-Region Claude Haiku 4.5 profile. Contemporaneously checked rates on 2026-09-07 were:

```text
input:  USD 1.10 / 1M tokens
output: USD 5.50 / 1M tokens
```

Derived baseline inference cost:

```text
input  = 3291 / 1,000,000 * USD 1.10 = USD 0.0036201
output =  104 / 1,000,000 * USD 5.50 = USD 0.0005720
----------------------------------------------------------
total                                  USD 0.0041921
```

This is a token-price derivation from observed usage, not an AWS invoice reconciliation. No cache charge is added because both observed cache token counters are zero.

Pricing references recorded in the immutable evidence artifact and reviewed during the experiment:

- Amazon Bedrock Claude Haiku 4.5 model card;
- AWS machine-learning example using Claude Haiku 4.5 at the same US rates;
- Anthropic AWS Bedrock list prices dated 2026-05-27.

## Final exact-head CI and merge

```text
PR #157 final validated head: 2ec5b3804fa8c6454e1ea7d824b82d2db9113f91
Single-Agent CI:             34170308179 / run #37 / PASS
job:                         101889202476
PR merge test commit:        bd3802bf4003e5a447e5e104caad0a86cf8388ec
uv lock --check:             PASS
entrypoint smoke:            PASS
Ruff:                        PASS
Pyright strict:              0 errors / 0 warnings / 0 informations
pytest:                      56 passed in 0.43s
PR #157 merge SHA:           8b41025facf4451490bf96223d69fbed19b4a00f
issue #156:                  CLOSED / COMPLETED
```

## AWS / IAM / integration boundary

```text
new AWS resources:              0
new IAM roles/policies:         0
AgentCore:                      0
MCP:                            0
A2A:                            0
public agent runtime:           0
runtime-exposure authority:     0
Governed LLM Gateway changes:   0
```

The real replay used an already-authorized human IAM Identity Center profile. No credentials are stored in the repository. The long-lived OpsLens PR #89 remains deferred, draft, and outside Gate 11.4.

## Gate 11.5 input

```text
proposal quality:          6/6
bounds compliance:         6/6
provider retries:          0
capability executions:     0
six-case token cost:       USD 0.0041921
provider latency median:   809.5 ms
client elapsed median:     977.5 ms
```

Gate 11.5 must decide whether any bounded optimization experiment is justified by these measurements. It must not optimize merely because an optimization gate exists.

## Exit boundary

```text
offline engineering gate: PASS
real-model evidence gate: PASS
quality baseline:         6/6 PASS
cost derivation:          COMPLETE
exact-head CI:            PASS
protected squash merge:   COMPLETE
Gate 11.4:                COMPLETE
Gate 11.5:                NEXT
```
