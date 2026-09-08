# ADR 0043 — Freeze Multi-Agent Comparison Before a Second Model Call

- Status: Accepted
- Date: 2026-09-07
- Phase: 12 — Multi-Agent Architecture
- Gate: 12.2 — Comparative Multi-Agent Evaluation Contract

## Context

Gate 12.1 froze a deterministic `multi-agent-handoff:v1` boundary that can narrow a source task's capability surface from at most four Phase 11 capabilities to at most two specialist capabilities. That gate intentionally made no model call and did not claim multi-agent quality improvement.

The Phase 11 single-agent reference already achieved `6/6` on its frozen acceptance corpus with zero SDK retries and zero capability executions. Introducing a second reasoning model merely because a multi-agent phase exists would add latency, token cost, failure modes, and architecture without a measured target.

A later two-model experiment therefore needs a comparison protocol that exists **before** the experiment. Otherwise metrics, acceptance criteria, or evidence semantics could be selected after observing the result.

## Decision

Freeze a provider-neutral deterministic comparison contract:

```text
multi-agent-comparison:v1
```

Gate 12.2 remains offline. It evaluates a frozen fixture containing synthetic untrusted handoff proposals through the existing deterministic Gate 12.1 admission boundary.

```text
frozen comparison fixture
 -> admitted SingleAgentTask
 -> synthetic untrusted MultiAgentHandoffProposal
 -> deterministic handoff admission
 -> HANDOFF | ABSTAINED | REJECTED
 -> deterministic decomposed case score
 -> content-addressed comparison report
 -> runtime measurements = null / unmeasured
 -> STOP
```

The synthetic proposals are test inputs. Their conformance score is not model quality and must never be presented as a real multi-agent baseline.

## Deterministic scoring dimensions

Each case records independently:

```text
decision exact match
specialization exact match
admission outcome exact match
target capability-scope exact match
non-broadening of source authority
hard-bound compliance
```

The report keeps these dimensions separate and additionally records:

```text
total_cases
passed_cases
handoff_cases
abstention_cases
source capability slots for admitted handoffs
specialist capability slots
capability slots removed
```

A single opaque score is insufficient because it would hide whether failure came from routing, authority admission, scope projection, or bounds.

## Runtime evidence boundary

Gate 12.2 makes no model invocation. These fields remain explicitly unmeasured and are serialized as `null`:

```text
model invocation count
input tokens
output tokens
total tokens
provider latency
client elapsed latency
SDK retries
inference cost
```

They are not set to zero. Zero would falsely look like observed runtime evidence.

The offline evaluator does assert `offline_capability_executions = 0` because its code path never invokes a capability executor. That assertion is limited to the offline evaluation path and is not a production/runtime claim.

## Phase 11 reference binding

The Gate 12.2 dataset and report bind to the exact immutable Phase 11 reference identities:

```text
corpus_sha256:
3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc

report_sha256:
724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Later comparison work cannot silently substitute another single-agent baseline.

## Frozen fixture semantics

The first comparison fixture uses six cases:

```text
broad structured-security request -> EVIDENCE_ANALYSIS -> 4 to 2
broad knowledge-guidance request  -> GUIDANCE_SYNTHESIS -> 4 to 2
broad hybrid request              -> GUIDANCE_SYNTHESIS -> 4 to 2
broad repository request          -> EVIDENCE_ANALYSIS -> 4 to 2
unsupported arbitrary execution   -> ABSTAIN
allowlist conflict                -> ABSTAIN
```

The broad cases make the structural narrowing property measurable without asserting that narrower scope improves answer quality.

## Authority preservation

This decision does not move any authority into a model.

```text
triage proposal != handoff admission
handoff admission != capability authorization
capability authorization != invocation
invocation != execution result
```

The comparison metric implementation is deterministic. An LLM judge is not accepted as metric authority.

## Real experiment entry rule

A later gate may introduce a bounded two-model experiment only after this contract is merged. That experiment must reuse the frozen comparison dimensions and preserve deterministic handoff and capability authorization.

The first real experiment should stop before capability execution so that reasoning quality and coordination overhead can be measured independently of executor behavior.

The topology must be rejected if measured specialization value does not justify additional model calls, latency, token usage, cost, failure surface, or complexity.

## Alternatives rejected

### Add the second model first and decide metrics afterward

Rejected because it permits post-hoc success criteria and weakens evaluation credibility.

### Reuse only the Phase 11 final pass/fail metric

Rejected because multi-agent coordination adds distinct routing, handoff, and capability-surface dimensions that a single aggregate result cannot expose.

### Treat synthetic fixture conformance as multi-agent model quality

Rejected because no model participates in Gate 12.2.

### Record runtime metrics as zero

Rejected because no real runtime measurement exists. Unmeasured values remain null.

### Use an LLM judge for routing or handoff acceptance

Rejected because metric authority must remain deterministic and reproducible.

## Consequences

Positive:

- comparison criteria predate the real experiment;
- Phase 11 reference evidence is immutable and explicitly bound;
- coordination failures remain diagnosable by dimension;
- runtime evidence cannot be fabricated accidentally;
- the project can reject multi-agent complexity based on measured evidence.

Costs:

- an additional evaluation contract and fixture must be maintained;
- synthetic conformance is useful only for contract verification, not model-quality claims;
- a later real experiment is still required to measure tokens, latency, cost, retries, and routing quality.

## AWS / IAM / runtime impact

```text
new AWS resources:          0
new IAM roles/policies:     0
real model calls:           0
capability executions:      0
AgentCore:                  0
MCP:                        0
A2A:                        0
public runtime:             0
runtime-exposure authority: 0
```

## AIP-C01 learning connection

This gate reinforces professional-level evaluation discipline: define objective metrics before experimentation, separate deterministic evaluation authority from generative reasoning, preserve provenance to the exact baseline, distinguish offline test evidence from runtime evidence, and treat cost/latency as measured engineering inputs rather than assumptions.
