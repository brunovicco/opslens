# Phase 11 Gate 11.4 — First Bounded Model Reasoning Baseline

## Status

```text
provider-neutral implementation: COMPLETE
frozen reasoning corpus:         COMPLETE
offline CI validation:           COMPLETE
real Bedrock corpus replay:      COMPLETE
measured token/latency/cost:     COMPLETE
gate completion:                 READY FOR FINAL EXACT-HEAD CI
```

Gate 11.4 now has the first preserved real-model baseline required by issue #156. The remaining merge
boundary is repository process only: exact-head CI, review, ready-for-review transition, and protected
squash merge.

## Objective

Measure whether one real reasoning model can select the expected bounded OpsLens capability or
abstain without acquiring authorization or capability-execution authority.

## Frozen contracts

Existing contracts remain unchanged:

```text
single-agent-authority:v1
single-agent-execution:v1
single-agent-evaluation:v1
operational-telemetry:v1
```

Gate 11.4 introduces:

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

The final `STOP` is mandatory for this baseline. Gate 11.4 performs zero capability executions so
proposal quality remains separable from the Gate 11.2 executor/result-admission boundary.

Permanent distinctions:

```text
structured model output != trusted proposal
AgentActionProposal != authorization
model selection != capability authority
reasoning evidence != execution evidence
reasoning evidence != operational telemetry
```

## Reasoning output contract

The model may return only:

```json
{
  "decision": "act | abstain",
  "capability": "closed capability enum | null"
}
```

Deterministic admission rejects invalid JSON, non-object output, missing or extra fields, unknown
decisions/capabilities, ACT without one capability, ABSTAIN with a capability, output larger than
512 UTF-8 bytes, and invocation evidence bound to another task.

No executable args/kwargs, SQL, URL, shell command, credentials, provider/model selector,
retry/fallback policy, or result data can cross this reasoning proposal surface.

## Invocation bounds

```text
model invocations per admitted task: 1
application retries:                0
adaptive fallbacks:                 0
capability executions:              0
```

The provider SDK is configured with `total_max_attempts=1`. Observed SDK retry metadata must be zero
for a case to satisfy the evaluation bound.

## First provider adapter

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

The provider adapter depends on an injected narrow Converse client Protocol. Domain/application code
contains no boto3 or Bedrock types. Provider/model/Region selection remains code-owned.

## Bedrock structured-output compatibility finding

The first authenticated real attempt reached Bedrock Converse but failed before inference because the
initial provider schema used `oneOf`, which the Bedrock structured-output subset rejected:

```text
ValidationException:
output_config.format.schema: Schema type 'oneOf' is not supported
reached max retries: 0
```

This was a provider-schema compatibility defect, not a model-quality result. No model output or token
usage from that failed attempt was admitted as baseline evidence.

The corrected Bedrock schema is a flat closed object:

```text
required:             decision, capability
additionalProperties: false
decision:             enum(act, abstain)
capability:           enum(closed OpsLens capabilities, null)
```

The ACT/capability and ABSTAIN/null cross-field relation remains application-owned and deterministic.
A provider-valid structured response is still an untrusted proposal. A regression test explicitly
forbids `oneOf` from the fixed Bedrock schema.

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

The allowlist-restriction case deliberately asks for structured facts while only
`knowledge_guidance` is allowed. Correct model behavior is abstention. An out-of-allowlist proposal
would still be deterministically rejected rather than acquiring execution authority.

## Deterministic metrics

```text
total_cases
passed_cases
decision_matches
capability_matches
authorization_matches
bounds_compliant_cases
```

A case passes only when all decomposed dimensions match. There is no LLM judge and no opaque
correctness score.

## Offline failure lab

Regression tests prove:

- arbitrary extra model fields such as tool args fail closed;
- unknown capabilities fail closed;
- ACT/ABSTAIN contradictions fail closed;
- cross-task provider evidence fails closed;
- an out-of-allowlist proposal remains a rejected proposal rather than authority;
- Bedrock multiple-content responses fail closed;
- inconsistent token accounting fails closed;
- provider failures are wrapped with stable outward text and one attempt;
- raw model text is absent from admitted reasoning/result-report evidence;
- unsupported Bedrock `oneOf` cannot return to the fixed provider schema;
- one deliberately wrong allowlist-case fake proposal exposes a `5/6` quality result while retaining
  `6/6` invocation-bound compliance.

## Pre-baseline exact-head validation

The provider-schema remediation was validated at exact head:

```text
head:                    626139690d61c20583e8cc51c1dfecf80b8789d3
Single-Agent CI:         34169804186 / run #33 / PASS
job:                     101887815839
PR merge test commit:    098d0d282a08d3a7c63acb4d926e2b5b92224bd4
uv lock --check:         PASS
entrypoint smoke:        PASS
Ruff:                    PASS
Pyright strict:          0 errors / 0 warnings / 0 informations
pytest:                  56 passed in 0.45s
```

That CI proves the implementation and provider-schema shape, not real model quality.

## First real Bedrock baseline — 2026-09-07

The operator replayed the frozen six-case corpus from exact source head
`626139690d61c20583e8cc51c1dfecf80b8789d3` using the existing `opslens-bootstrap` IAM Identity
Center profile. The command exited `0` with empty stderr.

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

All six Bedrock request IDs and content-addressed invocation/result identities are retained in the
evidence artifact without raw model output.

## Token and latency measurements

Aggregated real observations:

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

The first observed client call has a much larger client-minus-provider interval than the remaining
five calls. This is retained as measured evidence only; Gate 11.4 does not label it a cold start,
connection setup, or another cause without separate evidence.

## Experiment-time cost derivation

The invoked identifier starts with `us.`, which AWS documents as the US geographic cross-Region
inference profile for Claude Haiku 4.5. The contemporaneously checked standard US geographic
cross-Region rates are:

```text
input:  USD 1.10 / 1M tokens
output: USD 5.50 / 1M tokens
```

Pricing references checked on 2026-09-07:

- Amazon Bedrock Claude Haiku 4.5 model card:
  https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html
- AWS machine-learning example using Claude Haiku 4.5 at the same US rates:
  https://aws.amazon.com/blogs/machine-learning/live-meeting-assistant-with-amazon-transcribe-amazon-bedrock-and-strands-agents/
- Anthropic 2026-05-27 list prices for AWS Bedrock:
  https://www-cdn.anthropic.com/files/4zrzovbb/website/3684c2faafb97418665782cea0001f439f74b1d2.pdf

Derived baseline inference cost:

```text
input  = 3291 / 1,000,000 * USD 1.10 = USD 0.0036201
output =  104 / 1,000,000 * USD 5.50 = USD 0.0005720
----------------------------------------------------------
total                                  USD 0.0041921
```

This is a token-price derivation from observed usage, not an AWS invoice reconciliation. No cache
charge is added because both observed cache token counters are zero.

## AWS / IAM / integration boundary

This gate adds:

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

The real replay used an already-authorized human IAM Identity Center profile. No credentials are
stored in the repository.

The long-lived OpsLens PR #89 remains deferred, draft, and outside Gate 11.4.

## Gate 11.5 input

The first baseline gives Gate 11.5 a measured decision surface rather than an assumed optimization
need:

```text
proposal quality:          6/6
bounds compliance:         6/6
provider retries:          0
capability executions:     0
six-case token cost:       USD 0.0041921
provider latency median:   809.5 ms
client elapsed median:     977.5 ms
```

Gate 11.5 must decide whether any bounded optimization experiment is justified by these measurements.
It must not optimize merely because an optimization gate exists.

## Exit boundary

Evidence state after the first real replay:

```text
offline engineering gate: PASS
real-model evidence gate: PASS
quality baseline:         6/6 PASS
cost derivation:          COMPLETE
Gate 11.4:                READY FOR FINAL EXACT-HEAD CI
```

Gate 11.4 can be marked complete only after this evidence/documentation head receives exact-head CI
and PR #157 completes the normal review and protected squash-merge process.
