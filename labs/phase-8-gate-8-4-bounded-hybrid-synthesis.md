# Phase 8 Gate 8.4 — First Bounded Hybrid Synthesis

_Date: 2026-09-06_

## Objective

Execute the first model-assisted Phase 8 synthesis only after deterministic route and evidence admission, while preserving structured truth, semantic citation provenance, explicit abstention/rejection, and the frozen Gate 8.3 benchmark.

## Starting point

```text
main:   57d052d4bf768c0a1692631ffe1d1e553594fc74
issue:  #114
branch: feat/phase8-bounded-hybrid-synthesis
PR:     #115
```

Frozen input:

```text
dataset_id: hybrid-evaluation-golden:v1
sha256:
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

The fixture is consumed unchanged.

## Authority-preserving execution

```text
EvidenceNeed proposal
 -> deterministic Gate 8.1 routing
 -> deterministic Gate 8.2 ALL_REQUIRED envelope admission
 -> route-aware Gate 8.4 execution
```

Execution policy:

```text
STRUCTURED
 -> deterministic F1/F2/... fact projection
 -> 0 model calls

SEMANTIC
 -> deterministic S1/S2/... semantic citation projection
 -> <= 1 bounded Converse call

HYBRID
 -> deterministic F projections
 + deterministic S projections
 -> <= 1 bounded Converse call

UNSUPPORTED
 -> abstain
 -> 0 model calls

incomplete evidence
 -> reject_before_synthesis
 -> 0 model calls
```

The model never owns the structured values. Its only positive authority is bounded explanatory synthesis over admitted semantic evidence, with optional references to already-admitted structured `F` handles.

## Provider-independent synthesis contract

```text
contract: hybrid-synthesis:v1
```

Hard bounds:

```text
max model calls per eligible case: 1
max explanatory chars:             4000
max claims:                         16
max structured facts:              64
max semantic chunks:               10
max canonical evidence JSON:       24 KiB
```

A model answer is admitted only when it is exact JSON with:

```text
decision: answer | insufficient_evidence
claims[]:
  text
  semantic_citation_ids[]
  structured_fact_ids[]
```

Every answer claim requires at least one allowlisted semantic `S` citation. Unknown `S`/`F` IDs, extra keys, malformed JSON, excessive output, invalid route references, provider failure, or non-`end_turn` stop reason fail closed.

## Prompt injection boundary

Trusted instructions are separated from:

- user question;
- structured fields;
- semantic chunk text.

All evidence and question content is untrusted data. Retrieved instructions cannot change policy, request tools, request SQL, broaden evidence authority, or turn similarity rank into truth.

## Bedrock runtime profile

Gate 8.4 reuses the Phase 7 bounded synthesis transport profile:

```text
region:      us-east-1
model:       us.anthropic.claude-haiku-4-5-20251001-v1:0
Converse:    non-streaming
tools:       none
temperature: 0.0
maxTokens:   2048
```

No AWS infrastructure or IAM change is introduced by this gate.

## Frozen metric semantics

The Gate 8.3 metric dimensions remain independent.

### `route_accuracy`

Reuses the deterministic Gate 8.3 offline metric. Gate 8.4 does not redefine routing quality.

### `structured_fact_correctness`

Scored only on expected-answer cases with frozen structured targets. Every target must be present unchanged in deterministic `F` projection.

### `semantic_groundedness`

Scored on completed model-required cases. A case passes only when the model answers and every explanatory claim cites only fixture-adjudicated supporting chunk IDs.

### `citation_correctness`

Scored independently from groundedness. The union of selected canonical chunk IDs must exactly equal the frozen expected citation target set.

### `abstention`

Scored over cases expected not to answer. `abstain` and `reject_before_synthesis` remain distinct expected system behaviors.

### `latency`

Arithmetic mean of client elapsed milliseconds over successful model-required calls only. Zero-call routes are not inserted as fake zero-latency model observations.

### `cost`

Remains `UNMEASURED` in Gate 8.4 until a deterministic versioned pricing contract exists. Token usage is recorded, but an unstated current price is not turned into authoritative cost.

There is no composite score.

## Semantic-noise proof

The frozen noise case contains:

```text
S1 / rank 1 -> admitted clean-environment neighbor -> NOT support target
S2 / rank 2 -> transitive lockfile review       -> expected support/citation target
```

A model that cites `S1` merely because it is rank one degrades both semantic groundedness and citation correctness while route accuracy, structured fact correctness, and abstention remain independent.

## Offline fake-client validation

Unit tests exercise:

- structured route with zero model calls;
- semantic route with one model call;
- true hybrid route with one model call;
- unsupported route with zero model calls;
- incomplete structured evidence rejected before synthesis;
- semantic-noise case selecting `S2` rather than rank-one `S1`;
- malformed output, unknown references, stop-reason failure, and provider failure;
- metrics remaining independent;
- cost remaining explicitly unmeasured.

CI evidence will be recorded here after the final executable head is green.

## First real runtime command

Run only after the final executable PR head is green. The command uses the normal botocore credential chain and therefore honors an already-authorized `AWS_PROFILE` if one is set in the shell.

```bash
PYTHONPATH=src uv run python -m opslens.hybrid_retrieval.cli.run_bedrock_hybrid_synthesis_evaluation \
  --region us-east-1 \
  > /tmp/opslens-gate84-hybrid-synthesis.json \
  2> /tmp/opslens-gate84-hybrid-synthesis.stderr

exit_code=$?

echo "exit_code=$exit_code"
echo
echo "STDERR:"
cat /tmp/opslens-gate84-hybrid-synthesis.stderr
echo
echo "JSON bytes:"
wc -c /tmp/opslens-gate84-hybrid-synthesis.json
```

Expected application-call budget for a complete run:

```text
6 fixture cases
3 Bedrock Converse calls maximum
0 calls for STRUCTURED
0 calls for UNSUPPORTED
0 calls for incomplete evidence
1 call for each SEMANTIC/HYBRID eligible case
```

Do not rerun adaptively to improve the first baseline. If the command exits non-zero, preserve both output files and review the partial evidence first.

## Real baseline status

```text
PENDING — must be executed with the existing authorized local AWS credentials after final CI.
```

The gate is not complete and PR #115 must remain draft until this first runtime evidence is reviewed.

## Architecture record

See:

```text
docs/adr/0028-bounded-route-aware-hybrid-synthesis.md
```

## AIP-C01 learning points

This gate exercises several certification-relevant distinctions:

- model invocation should be downstream of deterministic authorization and evidence admission;
- structured factual authority can bypass LLM synthesis entirely;
- retrieved context must be treated as untrusted data;
- structured output constrains syntax but does not establish semantic truth;
- citation allowlists and canonical provenance are application responsibilities;
- retrieval rank is not groundedness;
- evaluation dimensions should remain independently observable;
- token/runtime evidence is not automatically cost without a pricing contract;
- Bedrock transport selection does not imply that Bedrock owns business-policy authority.

## Next step

Complete CI on the exact executable PR head, execute the one first real Bedrock baseline, record the immutable observations without changing the frozen fixture, and only then decide whether Gate 8.4 satisfies its exit criteria.

Gate 8.5 optimization is explicitly out of scope until this baseline exists.
