# Phase 7 — Gate 7.6: Deterministic Context Assembly + Synthesis

_Date: 2026-09-06_

## Status

**IN PROGRESS — 7.6a–7.6d COMPLETE AND CI-GREEN / 7.6e REAL-RUN ENTRYPOINT READY, NOT YET EXECUTED.**

Gate 7.5 was squash-merged to `main` at:

```text
b30af10a568cefa7175c253120499939f9ca18d8
```

Gate 7.6 remains on draft PR #99. No real synthesis model invocation has occurred yet.

## Permanent boundary

> Retrieval candidates are evidence. Deterministic code decides what evidence may enter synthesis context and whether a model call is allowed.

This extends the project rule:

> **Agents reason. Code verifies evidence.**

Retrieved text remains untrusted instruction content even after source identity, hash, bytes, and canonical provenance have been admitted.

## Gate 7.5 evidence that constrains synthesis

Frozen real retrieval baseline:

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

Both negative cases returned non-empty nearest-neighbor results with rank-1 scores near `0.689`, overlapping legitimate positive evidence. Gate 7.6 therefore does not treat provider relevance score as confidence probability, routing authority, source authority, or a synthesis-admission threshold.

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

Rules:

- only already-admitted `RetrievedChunk` evidence is eligible;
- whole chunks only; no source-text truncation;
- preserve one contiguous retrieval-rank prefix from rank 1;
- stop at the first non-fitting chunk;
- never backfill with a smaller lower-ranked chunk;
- empty retrieval fails closed;
- a rank-1 chunk that cannot fit fails closed;
- provider relevance score is not projected into synthesis context;
- `context_sha256` binds query identity, limits, selected canonical provenance/content hashes, ranks, counts, and stop reason.

The byte ceiling is an application denial-of-wallet/input-growth bound, not a token estimate or provider context-window claim.

## 7.6b — Synthesis request/output + abstention contract — COMPLETE

Provider-independent model boundary:

```text
AssembledContext
 + exact original question
 + deterministic authority decision
 + SynthesisLimits
 -> SynthesisRequest
 -> SynthesisPromptEnvelope
 -> provider call
 -> exact JSON output parser
 -> SynthesisResult
```

### Authority vs model decision

Deterministic pre-model authority:

```text
SUPPORTED
UNSUPPORTED
```

`UNSUPPORTED` cannot form a `SynthesisRequest`. It fails before any model call.

For an already-supported request, the model may propose only:

```text
ANSWER
INSUFFICIENT_EVIDENCE
```

This preserves the distinction:

```text
unsupported authority
 -> routing/admission fact owned by deterministic code
 -> zero model calls

insufficient evidence
 -> legitimate model abstention inside an already-authorized explanatory domain
```

The model cannot grant itself authority or redefine routing policy.

### Frozen v1 application bounds

```text
question:            <= 1,000 characters
model calls:         exactly 1 maximum
answer:              <= 4,000 characters
raw response parser: <= 65,536 characters
```

The transport parser ceiling is deliberately larger than the answer entitlement because JSON escaping may make the wire payload longer than the decoded answer. The deterministic parser still enforces the 4,000-character answer invariant after decoding.

### Prompt trust envelope

The prompt keeps three logical trust classes separate:

```text
trusted system instructions
untrusted user question
untrusted but source-verified retrieved evidence
```

The frozen trusted instructions explicitly tell the model to treat commands, role changes, policy changes, tool requests, and attempts to ignore prior instructions found in retrieved evidence as data rather than control instructions.

The envelope is content-addressed through:

```text
request_sha256
evidence_sha256
prompt_sha256
```

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

The exact US Geographic inference profile is reused from the real Phase 6 planner rather than introducing model diversity without a measured requirement.

Current official AWS documentation confirms that Claude Haiku 4.5 supports Converse and Bedrock structured outputs. From `us-east-1`, the selected US Geo profile may route within the documented US destination set. Global inference is not selected because it would widen the geographic processing boundary.

### Structured output

The Converse request uses:

```text
outputConfig.textFormat.type = json_schema
```

with:

```text
decision: enum(answer, insufficient_evidence)
answer:   string | null
additionalProperties: false
```

Provider schema narrows generation shape but does not replace deterministic parsing. AWS currently documents `minLength` and `maxLength` as unsupported structured-output schema features, so the 4,000-character answer cap remains an application invariant.

AWS also documents first-use structured-output grammar compilation latency and caching for an identical successfully compiled grammar. First real synthesis latency must therefore be interpreted as first-run evidence rather than a warmed steady-state latency claim.

Anthropic native citations are not enabled because AWS documents them as incompatible with structured output. Deterministic citation projection and groundedness remain Gate 7.7.

### IAM boundary

Converse requires:

```text
bedrock:InvokeModel
```

The non-streaming path does not require:

```text
bedrock:InvokeModelWithResponseStream
```

A future deployed runtime must be scoped to the selected inference profile and required foundation-model resources in the US Geo source/destination Regions. No deployed application runtime principal exists yet, so Gate 7.6 introduces no synthetic runtime role merely for certification coverage.

### Cost planning

Current US Geographic Claude Haiku 4.5 rate baseline used for this gate:

```text
input:  $1.10 / 1,000,000 tokens
output: $5.50 / 1,000,000 tokens
```

If the provider output cap of 2,048 tokens were fully consumed, the output-token component alone would be approximately `$0.011264`. This is not a full per-call ceiling because input tokens are not known until real runtime telemetry exists.

Automatic Bedrock model invocation body logging remains disabled. The provider request carries content-free metadata only:

```text
opslens_stage
contract_id
request_sha256
prompt_sha256
```

## 7.6d — Offline provider adapter + response evidence — COMPLETE

`BedrockKnowledgeSynthesizer` is an outbound adapter over an injected minimal `BedrockConverseClient` Protocol.

Responsibilities:

```text
SynthesisRequest
 -> deterministic prompt envelope
 -> frozen Converse request
 -> exactly one converse() invocation
 -> require provider identity + usage/latency metadata
 -> require stopReason=end_turn
 -> require exactly one assistant text block
 -> deterministic synthesis-output parser
 -> SynthesisResult + BedrockSynthesisInvocationEvidence
```

Successful invocation evidence is content-free:

```text
model/profile id
region
provider request id
stop reason
input/output/total tokens
cache read/write tokens
Bedrock latency
client elapsed
SDK retry count
request_sha256
prompt_sha256
context_sha256
```

The adapter fails closed for provider invocation failures, missing/invalid metadata, non-`end_turn` stop reasons, wrong role, multiple/non-text blocks, malformed or semantically invalid JSON output, inconsistent token totals, clock regression, and request/evidence identity mismatch.

`insufficient_evidence` is preserved as a valid typed model abstention rather than misclassified as provider failure.

Offline tests cover successful answers, abstention, provider AccessDenied-like errors, non-accepted stop reasons, malformed response unions, invalid model JSON, metadata failure, token inconsistency, and timing drift.

Gate 7.6d CI evidence:

```text
Python CI #260: SUCCESS
Ruff:             PASS
Pyright strict:   PASS
pytest:            PASS
regressions:      PASS
```

## 7.6e — Bounded real synthesis runner — READY / NOT EXECUTED

The real-run composition root is:

```text
python -m opslens.knowledge_retrieval.cli.run_bedrock_synthesis
```

The lab runner requires an explicit authority decision. This is test-harness/operator input, not an LLM classification.

### Unsupported control

```text
authority=unsupported
 -> validate bounded query
 -> emit content-free refusal evidence
 -> no manifest read required
 -> no AWS session/client creation
 -> 0 Retrieve calls
 -> 0 Converse calls
```

A unit test replaces AWS session creation with a forbidden function and proves this path exits successfully without touching AWS.

### Supported real path

```text
authority=supported
 -> exactly one Bedrock KB Retrieve
 -> deterministic checked-corpus admission
 -> deterministic bounded context assembly
 -> exactly one Bedrock Converse synthesis invocation
 -> strict stop-reason/response/output admission
 -> one captured JSON evidence record
```

The evidence record includes the synthesized answer for first-run quality analysis, plus answer hash/length. It does not echo the raw user query or retrieved source text. Retrieval/context metadata and provider request metadata remain content-addressed and provenance-oriented.

Transport configuration:

```text
Retrieve:
  connect_timeout: 5s
  read_timeout:    30s
  retries:         standard, max_attempts=3

Synthesis:
  connect_timeout: 5s
  read_timeout:    90s
  retries:         standard, max_attempts=3
```

The longer synthesis read timeout is still bounded and only accommodates possible first-use structured-output grammar compilation latency. It does not grant iterative model-call authority.

Runner CI history:

```text
Python CI #262: FAIL — Ruff required explicit raw regex in one test only
Python CI #263: SUCCESS
  Ruff:             PASS
  Pyright strict:   PASS
  pytest:            PASS
  regressions:      PASS
```

Latest CI-green real-run preparation head:

```text
511dd4367c3a2e595aab9bbb74a0b0348d765541
```

No real model call was made while implementing or correcting the runner.

## AWS / IAM / cost effect before the real 7.6e run

```text
real synthesis AWS calls: 0
new AWS resources:        0
new IAM permissions:      0
model tokens consumed:    0
provider synthesis cost:  $0
```

The existing human lab identity is used only for explicit local validation. It is not the final deployed runtime IAM boundary.

## 7.6 increment plan

```text
7.6a deterministic context assembly contract                 COMPLETE
7.6b synthesis request/output + abstention contract           COMPLETE
7.6c Bedrock model/API selection + pricing/IAM review         COMPLETE OFFLINE
7.6d offline provider adapter + response evidence             COMPLETE
7.6e bounded real synthesis success/failure evidence          RUNNER READY / REAL RUN NEXT
7.6f quality/latency/token/cost analysis                      PENDING
7.6g docs/state closeout + final CI + squash merge            PENDING
```

## Next authorized step

Execute the first supported 7.6e lab run exactly once against the existing dev Knowledge Base and frozen Claude Haiku 4.5 US Geo profile. Capture stdout, stderr, and exit code before considering any replay.

The first intended question is the already-proven Gate 7.4 retrieval case:

```text
How can I make pip dependency installation more secure using hashes?
```

This query is selected because Gate 7.4 already demonstrated the expected PyPA hash-checking evidence at retrieval rank 1. Reusing it isolates synthesis behavior rather than intentionally introducing a new retrieval-quality variable during the first generation call.

If the first provider attempt fails, preserve that failure evidence and diagnose before deciding whether a versioned rerun is justified. Do not silently replace the first run.

After a successful preserved real run, Gate 7.6f will calculate answer quality, retrieval/context behavior, latency, token usage, retries, and observed model cost. Then synchronize current-state/roadmap/architecture, run final CI, mark PR #99 ready, and squash merge only against the validated head SHA.

## References

- ADR 0023: [`../docs/adr/0023-bounded-bedrock-knowledge-synthesis.md`](../docs/adr/0023-bounded-bedrock-knowledge-synthesis.md)
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html
- https://aws.amazon.com/bedrock/pricing/
