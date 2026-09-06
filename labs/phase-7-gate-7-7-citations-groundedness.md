# Phase 7 — Gate 7.7: Deterministic Citations + Groundedness Evaluation

_Date: 2026-09-06_

## Status

**COMPLETE — implementation, preserved first real run, human-reviewed groundedness evidence, deterministic metrics, and closeout evidence are complete.**

Gate 7.7 is implemented on PR #100 from the Gate 7.6 merge:

```text
cc8097b3e2e9b048ca069e961736788de0a79f0d
```

The first real Gate 7.7 run was executed exactly once from validated head:

```text
507fe04f963c7eeb49748eb950101ea2fc55e14f
```

No prompt replay or post-observation fixture tuning was performed.

## Permanent boundary

> **Models may select among already-admitted citation IDs. They may not create citation authority.**

This extends:

> **Agents reason. Code verifies evidence.**

and preserves:

> **Structured facts use structured retrieval.**

A valid citation identifier proves that the reference resolves to admitted evidence. It does **not** prove that the evidence semantically supports the associated claim.

## Gate shape

```text
frozen knowledge question
 -> bounded direct Retrieve
 -> deterministic checked-corpus admission
 -> deterministic bounded context
 -> deterministic C1..Cn catalog
 -> one bounded grounded Converse call
 -> strict structured-output admission
 -> model-proposed claims + allowlisted citation IDs
 -> explicit human-reviewed claim/citation support judgments
 -> deterministic grounding metrics
```

Canonical URI, source ID, document ID, chunk ID, and hashes are projected from deterministic evidence. They are never accepted from model output.

## 7.7a — Deterministic citation catalog — COMPLETE

```text
AssembledContext
 -> exact selected ContextEvidenceBlock[]
 -> C1..Cn in retrieval-rank order
 -> ProjectedCitation[]
 -> CitationCatalog
```

Rules:

- only chunks admitted into `AssembledContext` can become citation authority;
- excluded retrieval suffixes cannot be cited;
- provider relevance score is not citation authority;
- every projected citation retains canonical source/document/chunk identity and content hashes;
- each citation and catalog is content-addressed;
- source text is not duplicated into operational citation identity.

## 7.7b — Structured claim/citation contract — COMPLETE

Frozen provider-independent model proposal:

```json
{
  "decision": "answer",
  "claims": [
    {"text": "...", "citation_ids": ["C1"]}
  ]
}
```

or:

```json
{"decision": "insufficient_evidence", "claims": []}
```

Application authority:

- deterministic code assigns claim indices;
- every answer claim requires at least one catalog citation;
- unknown or duplicate citation IDs fail closed;
- model-authored URLs/source IDs/document IDs/chunk IDs/hashes are rejected;
- final rendering contains only admitted cited claims;
- insufficient evidence contains no claims;
- maximum 16 claims;
- maximum 1,000 characters per claim;
- rendered answer remains under the Gate 7.6 hard 4,000-character entitlement;
- raw provider response remains bounded to 65,536 characters.

## 7.7c — Frozen evaluation contract — COMPLETE

Dataset:

```text
knowledge-grounding-golden:v1
4 cases
3 expected answer cases
1 expected insufficient-evidence case
judgment authority: human_reviewed_claim_citation_pairs_v1
```

Cases were frozen before the grounded provider run:

```text
grounding-hash-verification-01
grounding-transitive-review-01
grounding-isolation-01
grounding-insufficient-pip-tls-cipher-01
```

Metric dimensions remain separate:

```text
citation target precision / recall
claim supportedness
unsupported claim rate
claim/citation pair correctness
answer / abstention decision accuracy
abstention precision / recall
```

Semantic support cannot be inferred from retrieval score, citation syntax, source reputation, or lexical overlap. Pair-level support requires explicit review evidence.

## 7.7d — Bounded grounded Bedrock integration — COMPLETE

Provider boundary reuses Gate 7.6:

```text
Region:                 us-east-1
API:                    bedrock-runtime / Converse
model/profile:          us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:              no
temperature:            0.0
provider maxTokens:     2,048
tools:                  none
structured output:      JSON Schema
```

The adapter permits exactly one grounded Converse attempt per application attempt, requires `stopReason=end_turn`, exactly one assistant text block, valid provider telemetry, and deterministic grounded-output admission.

Retrieved/source content remains untrusted user-role data even after provenance admission.

## 7.7e — First real four-case evaluation — COMPLETE

Runtime command completed once with:

```text
exit_code:                     0
stderr:                        empty
application case attempts:     4 / 4
application complete:          true
planned top_k:                 5
real Retrieve attempts:        4
real grounded Converse calls:  4
SDK retries:                   0 on every Retrieve and Converse call
stop reason:                   end_turn on every Converse call
```

### Runtime observations

| Case | Retrieve ms | Bedrock ms | Client synthesis ms | Input tokens | Output tokens | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| hash verification | 1457 | 5740 | 6409 | 3158 | 297 | answer |
| transitive review | 571 | 4374 | 4586 | 2422 | 197 | answer |
| isolation | 568 | 2480 | 2704 | 3167 | 137 | answer |
| exact TLS cipher | 564 | 992 | 1274 | 2987 | 14 | insufficient_evidence |

Aggregate runtime evidence:

```text
retrieval latency min / mean / max: 564 / 790.0 / 1457 ms
Bedrock latency min / mean / max:   992 / 3396.5 / 5740 ms
client synthesis min / mean / max:  1274 / 3743.25 / 6409 ms
input tokens:                       11,734
output tokens:                      645
total tokens:                       12,379
cache read tokens:                  0
cache write tokens:                 0
```

This four-case sample is lab evidence, not an SLO or production latency distribution.

## Human-reviewed semantic support

The preserved metadata-only review artifact is:

```text
labs/evidence/phase-7-gate-7-7-first-run-review-v1.json
```

It stores claim hashes, citation IDs, canonical chunk mappings, content-addressed human judgments, result/catalog/request hashes, and run identity. It does not duplicate model claim text or source bodies.

Review used the exact frozen source pins in the canonical manifest.

### Hash verification

Six emitted claims used `C1` for the frozen PyPA `Hash-checking Mode` chunk except one lockfile-consistency claim using the admitted uv lockfile-checking chunk. All six claim/citation pairs were supported by the exact pinned evidence.

Frozen expected target was the PyPA hash chunk. The model selected two unique citation targets, one of which matched the frozen expected target:

```text
citation target precision: 0.5
citation target recall:    1.0
claim supportedness:       1.0
```

### Transitive review

Five emitted claims were individually supported by the cited OWASP, pip constraint-file, or uv lockfile evidence.

The frozen expected evidence targets were the pip transitive/constraint chunk and the uv diff-review chunk. The model selected four unique targets but selected only the pip expected target, not the expected uv diff-review target:

```text
citation target precision: 0.25
citation target recall:    0.5
claim supportedness:       1.0
```

This demonstrates that a semantically supported answer can still have weak alignment with a pre-frozen preferred evidence target set.

### Isolation — important failure signal

Retrieval succeeded: the exact frozen OWASP isolation chunk was rank 1 and became `C1`.

However, both generated claims cited only `C2`, the adjacent OWASP post-change testing-outcomes chunk. Under strict exact-chunk review, both claim/citation pairs were marked unsupported because the claims included the isolated/testing-environment premise while their only cited chunk did not establish that premise. The premise lives in `C1`.

```text
retrieval of required target:      successful, rank 1
model-selected citation target:    C2 instead of expected C1
citation target precision:         0.0
citation target recall:            0.0
supported claims:                  0 / 2
```

This is a citation-attribution/grounding failure, not a retrieval-availability failure. The baseline is preserved rather than repaired post hoc.

### Exact TLS cipher — abstention

Nearest-neighbor retrieval still returned five chunks, but none established the requested exact TLS cipher suite. The model correctly returned:

```text
insufficient_evidence
claims: 0
```

This is evidence that non-empty vector retrieval does not itself imply answerability.

## Frozen groundedness metrics

Human-reviewed support judgments plus deterministic metric code produce:

```text
decision accuracy:                 1.0       (4 / 4)

citation target selected:          7
citation target expected:          4
citation target correct:           2
citation target precision:         0.2857142857142857
citation target recall:            0.5

claims:                            13
supported claims:                  11
unsupported claims:                2
claim supportedness rate:          0.8461538461538461
unsupported claim rate:            0.15384615384615385

claim/citation pairs:              13
supporting pairs:                  11
citation correctness rate:         0.8461538461538461

abstention precision:              1.0
abstention recall:                 1.0
```

Interpretation:

- all four answer/abstention decisions matched the frozen expectations, but `N=4` is too small for broad quality claims;
- syntactic citation coverage was complete by construction, but semantic groundedness was not perfect;
- citation-target alignment was materially weaker than claim supportedness;
- the isolation case proves that retrieving the right evidence is insufficient if the generator cites a neighboring chunk instead;
- no score threshold or post-hoc target relabeling is justified by this run.

## Cost evidence

Using the provider rates frozen for the Gate 7.6/7.7 Haiku 4.5 US Geo boundary:

```text
11,734 input tokens  × $1.10 / 1M = $0.0129074
645 output tokens     × $5.50 / 1M = $0.0035475
model subtotal                         $0.0164549
4 S3 Vectors request components        $0.0000100
                                        ----------
directly computable total              $0.0164649
```

This is not represented as the full AWS bill. Titan query-embedding consumption and S3 Vectors data-processed/data-returned billable units are not exposed by the runtime evidence and are not fabricated.

## CI evidence

Important checkpoints:

```text
#266 SUCCESS — deterministic citation catalog
#268 SUCCESS — grounded claim/citation contract
#274 SUCCESS — frozen evaluation contract
#277 SUCCESS — grounded Bedrock adapter
#279 SUCCESS — real-evaluation harness
#280 SUCCESS — pre-run documentation head
#283 FAIL    — strict Pyright diagnostics in reviewed-evidence projection only
#284 SUCCESS — reviewed evidence + deterministic metrics
```

CI failures listed above were static-quality diagnostics and triggered no AWS calls.

## AWS / IAM effect

```text
new AWS resources:       0
new IAM permissions:     0
real Gate 7.7 Retrieve:  4
real Gate 7.7 Converse:  4
provider retries:        0
```

Gate 7.7 reused the already-authorized Knowledge Base, S3 Vectors path, and Bedrock Runtime profile. No new IAM entitlement was introduced merely for evaluation.

## AIP-C01 learning outcomes

Gate 7.7 demonstrates several certification-relevant distinctions:

- retrieval quality, citation attribution, groundedness, and abstention are separate evaluation dimensions;
- structured outputs reduce output-shape variability but do not prove semantic correctness;
- deterministic provenance and citation allowlists reduce hallucinated-source risk without granting the model source authority;
- nearest-neighbor retrieval can produce plausible evidence for unsupported questions, so answerability requires an independent boundary;
- evaluation evidence should preserve the first observed baseline before optimization;
- model token cost, retrieval request cost, latency, retries, and quality should be measured separately.

## Gate 7.7 conclusion

Gate 7.7 is complete. The system now has a measured citation-aware RAG baseline with an explicit failure signal rather than a cosmetically perfect benchmark.

The next Phase 7 step is **Gate 7.8 — Phase 7 closeout**, focused on failure diagnosis, least-privilege runtime IAM strategy, observability/cost synthesis, architecture consistency, and phase-level evidence before moving to Phase 8 Hybrid Retrieval.
