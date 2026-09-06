# ADR 0023 — Bounded Bedrock knowledge synthesis

Status: Accepted for Phase 7 Gate 7.6c

Date: 2026-09-06

## Context

Gate 7.4 separated raw Knowledge Base retrieval from generation. Gate 7.5 then
measured retrieval independently and showed that vector similarity is evidence,
not calibrated confidence or authority. Both out-of-authority negative cases
returned non-empty nearest-neighbor results with scores overlapping legitimate
positive evidence.

Gate 7.6a therefore introduced deterministic context assembly over only
already-admitted retrieval evidence. Gate 7.6b then froze a provider-independent
synthesis request/output contract with deterministic pre-model authority admission,
explicit `insufficient_evidence` abstention, exact output parsing, one model call,
and a hard 4,000-character application answer bound.

The remaining Gate 7.6c decision is the concrete Amazon Bedrock inference boundary.
It must preserve those application authorities instead of moving them into the
model or provider API.

## Decision

Use Amazon Bedrock **Converse**, non-streaming, through the `bedrock-runtime`
endpoint for the first knowledge-synthesis provider adapter.

Freeze the first synthesis configuration as:

```text
Region:                  us-east-1
provider:                Anthropic
model:                   Claude Haiku 4.5
inference profile:       US Geographic, system-defined
model/profile ID:        us.anthropic.claude-haiku-4-5-20251001-v1:0
API:                     Converse
streaming:               no
tools:                   none
temperature:             0.0
provider maxTokens:      2,048
application model calls: 1
application answer cap:  4,000 characters
```

Gate 7.6c remains **offline**. It constructs and tests the exact request shape but
does not invoke Bedrock, add IAM permissions, or create AWS resources.

## Why Converse

Converse is selected because OpsLens already uses and has real evidence for this
Bedrock runtime surface in Phase 6, and it provides the controls needed here without
adding agent/tool orchestration authority.

The request keeps three trust domains structurally separate:

```text
system
 -> frozen trusted OpsLens synthesis instructions

user content block 1
 -> user question, explicitly untrusted data

user content block 2
 -> source-verified retrieved evidence, explicitly untrusted data
```

Retrieved text is allowed to influence an explanation as evidence. It is not
allowed to redefine system instructions, invoke tools, change IAM/policy, or become
structured vulnerability authority.

## Structured output

Use Bedrock native structured output through:

```text
outputConfig.textFormat.type = json_schema
```

The v1 schema permits exactly:

```json
{
  "decision": "answer | insufficient_evidence",
  "answer": "string | null"
}
```

with `additionalProperties: false`.

This provider schema narrows the generation surface but is **not** the final
application authority. OpsLens still parses the response deterministically and
enforces the semantic pairing:

```text
answer                -> non-blank bounded answer text
insufficient_evidence -> answer must be null
```

Current Bedrock structured-output documentation supports basic JSON types,
`enum`, `anyOf`, and `additionalProperties: false`, but does not support string
`minLength`/`maxLength`. Therefore the 4,000-character answer limit remains an
application parser invariant rather than a provider-schema claim.

Bedrock may spend additional latency compiling a new schema grammar on first use;
AWS documents a 24-hour cache for successfully compiled identical grammars. This
must be considered when interpreting the first real Gate 7.6 invocation latency.

Anthropic native citations are not enabled because Bedrock documents them as
incompatible with structured output. OpsLens Gate 7.7 will project and evaluate
citations deterministically from admitted retrieval evidence instead.

## Model and inference-profile choice

Select the existing US Geographic Claude Haiku 4.5 inference profile rather than
introducing a second model for the first synthesis slice.

Reasons:

- the exact profile has already been exercised successfully by OpsLens Phase 6;
- current Bedrock documentation lists Claude Haiku 4.5 as active and compatible
  with Converse and structured outputs;
- the model card lists the exact US Geo ID used by the repository;
- from `us-east-1`, the US Geo profile keeps routing inside the documented US
  destination set rather than opening the broader Global routing boundary;
- a lightweight model is sufficient for one bounded evidence-to-explanation step.

This is a Phase 7 baseline, not a permanent vendor commitment. Availability,
lifecycle, pricing, and destination Regions must be revalidated before significant
future changes.

## Provider token bound

Set provider `maxTokens` to `2,048`.

This does not replace the stronger application answer limit. It is a second,
provider-level denial-of-wallet/output-growth bound.

A smaller `1,024` token cap was considered, but it could become the accidental
limiting factor for a valid 4,000-character multilingual or code-heavy answer.
`2,048` remains far below the model's documented maximum output while preserving a
small and explicit call budget.

## IAM boundary

Converse requires `bedrock:InvokeModel`.

Because this gate is non-streaming, `bedrock:InvokeModelWithResponseStream` is not
required. The synthesis path has no tool authority and requires no Knowledge Base
write, ingestion, S3 write, vector write/delete, PassRole, or infrastructure
provisioning permission.

The selected system-defined US Geo inference profile is a cross-Region inference
boundary. A future deployed runtime policy must permit `bedrock:InvokeModel` only
for the selected inference profile and the required foundation-model resources in
the documented source/destination Regions. AWS documents that blocking any required
destination Region through IAM/SCP can make cross-Region inference fail.

OpsLens still has no deployed application runtime principal for this path, so Gate
7.6c does **not** invent or widen one. The real Gate 7.6 validation can use the
existing human IAM Identity Center development identity as operator evidence; the
final runtime identity remains a separate least-privilege attachment decision.

## Observability and sensitive-content boundary

The pure request includes content-free Bedrock `requestMetadata`:

```text
opslens_stage
contract_id
request_sha256
prompt_sha256
```

The provider adapter must additionally capture bounded operational evidence from
the Converse response/client path, including provider request ID, stop reason,
input/output/total tokens, Bedrock-reported latency, client elapsed time, and retry
count.

Automatic model invocation logging is not enabled by this ADR. Prompts contain the
user question and retrieved source text, so provider-side body logging would create
a separate data-retention and access-control decision. Content-free hashes and
bounded runtime metadata are sufficient for the first synthesis evidence slice.

## Cost boundary

At the current US/EU/Australia geographic rate for Claude Haiku 4.5, the model
pricing baseline is:

```text
input:  $1.10 / 1,000,000 tokens
output: $5.50 / 1,000,000 tokens
```

At the hard provider output cap of `2,048` tokens, the maximum output-token price
component for one fully saturated call would be approximately:

```text
2,048 / 1,000,000 * $5.50 = $0.011264
```

That is **not** a complete per-call cost ceiling because input tokens are not known
until the actual prompt is measured. Gate 7.6e/7.6f must use real Bedrock usage
evidence instead of fabricating input-token counts.

## Alternatives considered

### RetrieveAndGenerate

Rejected. It would couple retrieval and generation again, weakening the independent
retrieval quality, failure, latency, and cost evidence established by Gates 7.4 and
7.5.

### InvokeModel

Not selected for this slice. It could work, but Converse already provides the
provider-neutral message surface, structured output, usage, and latency semantics
used elsewhere in OpsLens. A second request protocol has no demonstrated benefit.

### ConverseStream

Rejected. The output is a small machine-readable object. Streaming would add
state, parsing, and `bedrock:InvokeModelWithResponseStream` authority without a
measured product requirement.

### Global cross-Region inference

Not selected. Global routing expands the geographic processing boundary. The US
Geo profile is already proven in OpsLens and has a stable documented US destination
set for the current source Region.

### Amazon Nova 2 Lite

Not selected for the first strict synthesis baseline. Reusing the already-proven
Claude Haiku 4.5 profile gives a smaller architecture delta and a direct structured-
output fit. Model diversity can be evaluated later against measured quality/cost
requirements rather than added for certification coverage.

### Bedrock Guardrails

Deferred. Guardrails may become a useful additional safety control, but they do not
replace deterministic authority routing, source admission, prompt-injection trust
boundaries, or output validation. Adding a guardrail requires its own policy and
evaluation evidence.

### Anthropic native citations

Not selected because Bedrock structured outputs and Anthropic citations are
currently incompatible. Citation projection and groundedness remain Gate 7.7
application responsibilities.

## Failure semantics for the next increment

Gate 7.6d must fail closed on at least:

```text
provider exception
malformed Converse response
non-assistant response
missing or multiple output text blocks
unsupported stop reason
max-token truncation
content/guardrail intervention
structured JSON outside the frozen synthesis contract
application output-bound violation
```

Provider/runtime failures must remain distinct from the legitimate model decision
`insufficient_evidence`.

## AIP-C01 learning map

This decision exercises several certification domains without making certification
the architecture driver:

```text
Domain 1 -> model/API selection, structured model input/output, FM integration
Domain 2 -> Bedrock Converse integration and deterministic application contract
Domain 3 -> IAM least privilege, prompt-injection trust boundary, authority separation
Domain 4 -> token bounds, cross-Region choice, latency and cost planning
Domain 5 -> structured-output validation, failure categorization, troubleshooting evidence
```

## References

- https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html
- https://aws.amazon.com/bedrock/pricing/

## Consequences

Positive:

- generation remains downstream of deterministic retrieval/context authority;
- the first provider request is small, explicit, structured, and single-call;
- prompt injection has a visible trust boundary;
- model output cannot claim structured authority or unsupported routing decisions;
- IAM, token, cost, and geographic boundaries are explicit before a real call;
- Phase 6 operational evidence is reused instead of introducing unnecessary model
  diversity.

Trade-offs:

- US Geo inference can route outside `us-east-1` within the documented US set;
- structured-output first-use grammar compilation can distort initial latency;
- provider JSON Schema cannot encode the application character cap;
- model invocation logging is deliberately deferred, so troubleshooting relies on
  application-level metadata rather than raw provider prompt/response retention;
- final runtime IAM cannot be completed until a deployed runtime principal exists.
