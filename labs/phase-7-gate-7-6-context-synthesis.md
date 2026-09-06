# Phase 7 — Gate 7.6: Deterministic Context Assembly + Synthesis

_Date: 2026-09-06_

## Status

**IN PROGRESS — 7.6a, 7.6b, AND 7.6c COMPLETE OFFLINE / 7.6d PROVIDER ADAPTER NEXT.**

Gate 7.5 was squash-merged to `main` at:

```text
b30af10a568cefa7175c253120499939f9ca18d8
```

Gate 7.6 remains on draft PR #99. No real synthesis invocation has occurred yet.

## Permanent boundary

> Retrieval candidates are evidence. Deterministic code decides what evidence may enter synthesis context and whether a model call is allowed.

This extends the project rule:

> **Agents reason. Code verifies evidence.**

Retrieved text remains untrusted instruction content even after its source identity, hash, bytes, and canonical provenance have been admitted.

## Gate 7.5 evidence that constrains this design

Frozen real baseline:

```text
10 real Retrieve calls
8 positive cases
2 negative/out-of-authority cases
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
```

Both negative cases returned nine nearest-neighbor candidates, with rank-1 scores near `0.689`. Those values overlap scores observed for legitimate positive evidence.

Therefore Gate 7.6 does **not** use provider relevance score as confidence probability, authority decision, route decision, or context-admission threshold. No global score threshold is derived from the frozen Gate 7.5 test set.

## 7.6a — Deterministic context assembly — COMPLETE

Provider-independent flow:

```text
RetrievalEvidence
 -> deterministic contiguous rank-prefix assembly
 -> whole ContextEvidenceBlock[]
 -> AssembledContext
```

Frozen limits:

```text
default max chunks:      5
hard max chunks:         10
max admitted text bytes: 16,384 UTF-8 bytes
```

Selection rules:

- only already-admitted `RetrievedChunk` evidence is eligible;
- whole chunks only; no source-text truncation;
- preserve one contiguous retrieval-rank prefix from rank 1;
- stop at the first non-fitting chunk;
- never backfill with a smaller lower-ranked chunk;
- empty retrieval fails closed;
- a rank-1 chunk that cannot fit fails closed;
- provider `relevance_score` is not projected into synthesis context;
- `context_sha256` binds query identity, limits, provenance/content hashes, ranks, counts, and stop reason.

The byte ceiling is an application denial-of-wallet/input-growth bound, not a token estimate or provider context-window claim.

## 7.6b — Synthesis request/output + abstention contract — COMPLETE

Gate 7.6b freezes the provider-independent model boundary before any provider call.

```text
AssembledContext
 + exact original question
 + deterministic authority decision
 + SynthesisLimits
 -> SynthesisRequest
 -> SynthesisPromptEnvelope
 -> future provider call
 -> exact JSON output parser
 -> SynthesisResult
```

### Authority vs model decision

The deterministic pre-model authority decision is:

```text
SUPPORTED
UNSUPPORTED
```

`UNSUPPORTED` fails before a `SynthesisRequest` exists. The model cannot grant itself authority.

For an already-supported request, the model may propose only:

```text
ANSWER
INSUFFICIENT_EVIDENCE
```

This distinction matters:

```text
unsupported authority
 -> deterministic routing/admission fact
 -> no model call

insufficient evidence
 -> legitimate model abstention inside an already-authorized explanatory domain
```

The model cannot return `unsupported_authority` and thereby redefine routing policy.

### Frozen v1 application bounds

```text
question:            <= 1,000 characters
model calls:         exactly 1 maximum
answer:              <= 4,000 characters
raw response parser: <= 65,536 characters
```

The larger raw-response transport cap is not a larger answer entitlement. JSON escaping can make a wire payload longer than the decoded answer, so the parser uses a separate defensive transport ceiling while still enforcing the 4,000-character answer invariant after JSON decoding.

### Prompt trust envelope

The provider-independent envelope keeps three logical trust classes separate:

```text
trusted system instructions
untrusted user question
untrusted but source-verified retrieved evidence
```

The frozen trusted instructions explicitly tell the future model to treat commands, role changes, policy changes, tool requests, and attempts to ignore prior instructions found in retrieved text as evidence data rather than control instructions.

The envelope is content-addressed through:

```text
request_sha256
evidence_sha256
prompt_sha256
```

Canonical evidence serialization and all fingerprints fail closed on tampering.

### Output contract

Accepted model JSON is exactly one of:

```json
{"decision":"answer","answer":"..."}
```

or:

```json
{"decision":"insufficient_evidence","answer":null}
```

Markdown fences, extra keys, blank answer text, malformed JSON, invalid decisions, and answer text attached to `insufficient_evidence` are rejected.

## 7.6c — Bedrock model/API selection — COMPLETE OFFLINE

ADR 0023 freezes the first provider boundary as:

```text
Region:                  us-east-1
endpoint:                bedrock-runtime
API:                     Converse
streaming:               no
provider:                Anthropic
model:                   Claude Haiku 4.5
US Geo profile ID:       us.anthropic.claude-haiku-4-5-20251001-v1:0
temperature:             0.0
provider maxTokens:      2,048
tools:                   none
application model calls: 1
```

The exact US Geographic inference profile is reused from the real Phase 6 Bedrock planner rather than introducing model diversity without a measured requirement.

Current official AWS documentation confirms that Claude Haiku 4.5 supports Converse and Bedrock structured outputs. From `us-east-1`, the selected US Geo profile may route within the documented US destination set. Global inference is not selected because it would widen the geographic processing boundary.

### Structured output

The pure Converse request uses:

```text
outputConfig.textFormat.type = json_schema
```

with a simple schema containing:

```text
decision: enum(answer, insufficient_evidence)
answer:   string | null
additionalProperties: false
```

The provider schema narrows generation shape but does not replace the deterministic parser.

AWS currently documents `minLength` and `maxLength` as unsupported structured-output schema features, so the 4,000-character answer cap remains an application invariant rather than a provider-schema claim.

AWS also documents that a new structured-output grammar can take additional time to compile on first use and that a successfully compiled identical grammar is cached for 24 hours. The first real synthesis latency therefore must be interpreted with that possible first-use effect visible.

Anthropic native citations are intentionally not enabled because AWS documents them as incompatible with structured output. Deterministic citation projection and groundedness remain Gate 7.7.

### IAM boundary

Converse requires:

```text
bedrock:InvokeModel
```

This non-streaming path does not need:

```text
bedrock:InvokeModelWithResponseStream
```

A future deployed runtime must be scoped to the selected inference profile and required Claude Haiku 4.5 foundation-model resources in the US Geo source/destination Regions. Cross-Region routing means IAM/SCP restrictions across those required Regions can cause invocation failure.

No deployed application runtime principal exists yet, so Gate 7.6c adds no IAM permission and invents no runtime role.

### Cost planning

Current US Geographic Claude Haiku 4.5 rate baseline:

```text
input:  $1.10 / 1,000,000 tokens
output: $5.50 / 1,000,000 tokens
```

If the provider output cap of 2,048 tokens were fully consumed, the output-token component would be approximately:

```text
$0.011264
```

That is not a full per-call ceiling because real input tokens have not yet been measured. Gate 7.6e/7.6f must calculate observed cost from provider usage telemetry.

### Model invocation logging

Automatic Bedrock model invocation body logging remains disabled by decision for this gate. Synthesis prompts contain the user question and retrieved source text, so raw provider logging would introduce a separate retention/access-control boundary.

The request instead carries content-free metadata:

```text
opslens_stage
contract_id
request_sha256
prompt_sha256
```

## Offline provider-request implementation

Gate 7.6c now has a pure request builder that creates the exact non-streaming Converse request without a network call.

Tests prove:

- the selected region/profile/model constants are frozen;
- trusted instructions remain in the `system` field;
- question and admitted evidence remain user-role untrusted data;
- tools and streaming are absent;
- the structured-output schema is exact;
- request metadata contains hashes/contract identity rather than user or source text;
- wrong runtime contract types fail closed.

## CI history

Gate 7.6a:

```text
#243 FAIL — Ruff line length
#244 FAIL — Pyright direct-isinstance diagnostics
#245 SUCCESS
#249 SUCCESS after synchronized docs
```

Gate 7.6b:

```text
#250 SUCCESS — first synthesis contract
#251 FAIL — Pyright nested JSON typing only
#252 SUCCESS — hardened synthesis envelope
```

Gate 7.6c:

```text
#253 FAIL — Ruff test line length
#254 FAIL — Pyright nested request-fixture typing
#255 FAIL — one remaining Pyright list-element narrowing diagnostic
#256 SUCCESS — pure Bedrock request selection is CI-green
```

All failures were local static-quality diagnostics. No AWS call was made while correcting them.

## AWS / IAM / cost effect through 7.6c

```text
real synthesis AWS calls: 0
new AWS resources:        0
new IAM permissions:      0
model tokens consumed:    0
provider synthesis cost:  $0
```

The selected model/API/pricing/IAM boundary is now documented before runtime implementation.

## 7.6 increment plan

```text
7.6a deterministic context assembly contract                 COMPLETE
7.6b synthesis request/output + abstention contract           COMPLETE
7.6c Bedrock model/API selection + pricing/IAM review         COMPLETE OFFLINE
7.6d offline provider adapter + response evidence             NEXT
7.6e bounded real synthesis success/failure evidence          PENDING
7.6f quality/latency/token/cost analysis                      PENDING
7.6g docs/state closeout + final CI + squash merge            PENDING
```

## Next authorized step

Implement **7.6d offline** before invoking Bedrock:

1. inject a minimal Converse client protocol;
2. perform exactly one non-streaming `converse()` call per admitted request;
3. strictly parse the assistant response shape and supported stop reason;
4. pass returned text through the existing deterministic synthesis-output parser;
5. capture content-free runtime evidence: provider request ID, stop reason, token usage, Bedrock latency, client elapsed time, retry count, request/prompt/context hashes;
6. preserve provider failures distinctly from legitimate `insufficient_evidence` abstention;
7. add success and failure unit tests;
8. require CI green before preparing any real AWS validation command.

Do not add broad IAM or make a real synthesis call merely to exercise Bedrock.

## References

- ADR 0023: [`../docs/adr/0023-bounded-bedrock-knowledge-synthesis.md`](../docs/adr/0023-bounded-bedrock-knowledge-synthesis.md)
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html
- https://aws.amazon.com/bedrock/pricing/
