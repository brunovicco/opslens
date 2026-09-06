# Phase 7 — Gate 7.8: Knowledge Retrieval Architecture Closeout

_Date: 2026-09-06_

## Status

**COMPLETE — documentation/architecture closeout pending final PR CI and squash merge.**

Gate 7.8 starts from the exact merged Gate 7.7 baseline:

```text
928f9b6173fba67778c3ee9f104aa250d108cf50
```

Tracking issue:

```text
#101 — Phase 7 Gate 7.8 — close out Bedrock knowledge retrieval architecture
```

Working branch:

```text
docs/phase7-closeout
```

## Goal

Close Phase 7 without silently optimizing the measured Gate 7.7 result.

Gate 7.8 consolidates what the completed retrieval/synthesis/citation work proved about authority, failures, IAM, cost, observability, evaluation, documentation, and the entry boundary for Phase 8.

No provider/model replay or prompt tuning is part of this gate.

## Repository documentation review

The closeout included an explicit README/documentation review before Phase 8.

Findings before correction:

```text
README.md
 -> status stopped at Phase 5
 -> Phase 6 still described as next
 -> repository structure omitted semantic_query / knowledge_retrieval
 -> quality-gate inventory omitted Semantic Query / Knowledge Retrieval

README.pt-br.md
 -> same Phase 5 / Phase 6 staleness

docs/README.md
 -> described architecture only through Gate 7.3
 -> still said Gate 7.3 merge pending and Gate 7.4 next

docs/architecture.pt-br.md
 -> baseline still described Phase 5 complete / Phase 6 next

docs/current-state.md
 -> Gate 7.7 complete but still treated PR #100 as pending

docs/roadmap.md
 -> Gate 7.8 still next

docs/architecture.md
 -> already current through Gate 7.7, but Gate 7.8 still next
```

Corrections made in this closeout:

```text
README.md / README.pt-br.md
 -> Phase 0–7 complete / Phase 8 next
 -> current structured + semantic system shape
 -> measured retrieval and groundedness baselines
 -> current AWS/Bedrock architecture
 -> current repository structure and CI slices

docs/README.md
 -> current document index and Phase 7 evidence map

docs/current-state.md
 -> Phase 7 complete and Gate 7.8 closeout decisions

docs/roadmap.md
 -> Phase 7 complete and explicit Phase 8 gates

docs/architecture.md / architecture.pt-br.md
 -> synchronized Phase 7 closeout baseline

docs/adr/README.md
 -> ADR 0024 indexed
```

Historical lab files remain historical evidence and are not rewritten merely to make old checkpoints appear current.

## Preserved Phase 7 baseline

### Retrieval evaluation

Frozen dataset:

```text
knowledge-retrieval-golden:v1
10 cases
8 positive
2 negative/out-of-authority
```

Measured baseline:

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Both negative cases returned non-empty nearest-neighbor results. Vector score/existence therefore does not become routing or answerability authority.

### Groundedness evaluation

Frozen dataset:

```text
knowledge-grounding-golden:v1
4 cases
3 expected answers
1 expected abstention
```

Measured baseline:

```text
decision accuracy:                 1.0
citation target precision:         0.2857142857142857
citation target recall:            0.5
claim supportedness rate:          0.8461538461538461
unsupported claim rate:            0.15384615384615385
citation correctness rate:         0.8461538461538461
abstention precision:              1.0
abstention recall:                 1.0
```

The isolation case is intentionally preserved as a failure example:

```text
correct target retrieved at rank 1 / C1
model cited adjacent C2 for both claims
strict exact-chunk support: unsupported for both pairs
```

This is a citation-attribution/groundedness failure rather than retrieval unavailability.

The exact TLS-cipher case correctly returned `insufficient_evidence` despite non-empty vector retrieval.

## Failure taxonomy

Gate 7.8 freezes a stage-oriented diagnostic taxonomy:

```text
1. route / authority failure
2. provider retrieval failure
3. retrieval evidence-admission failure
4. retrieval relevance / coverage failure
5. context-assembly failure
6. synthesis transport failure
7. synthesis output-admission failure
8. answerability / decision failure
9. citation-authority failure
10. citation-attribution failure
11. semantic groundedness failure
```

### Why the separation matters

A single “RAG failed” label destroys useful evidence.

Examples:

```text
Retrieve succeeds + relevant target missing
 -> retrieval relevance / coverage failure

Retrieve succeeds + target present + model cites wrong chunk
 -> citation-attribution failure

valid citation ID + cited evidence does not support claim
 -> semantic groundedness failure

five neighbors retrieved + model correctly abstains
 -> not a retrieval failure
```

This separation is retained for Phase 8 evaluation and future observability.

## Future least-privilege runtime IAM

No deployed application compute principal exists at Phase 7 closeout.

Therefore Gate 7.8 creates **no IAM role and no permission attachment**. It records the future runtime policy shape in ADR 0024.

### Direct retrieval

Future application runtime requires:

```text
Action:
  bedrock:Retrieve

Resource:
  arn:aws:bedrock:us-east-1:487757851499:knowledge-base/BTVJ2PBR2A
```

The already-proven path does not justify `RetrieveAndGenerate`, Knowledge Base administration, ingestion management, or direct S3 Vectors access.

### Non-streaming synthesis

The Phase 7 application uses non-streaming `Converse`, which is authorized by `bedrock:InvokeModel`.

Selected Geographic inference profile:

```text
us.anthropic.claude-haiku-4-5-20251001-v1:0
```

For a source request from `us-east-1`, current AWS documentation lists the following destination Regions for this US Geographic profile:

```text
us-east-1
us-east-2
us-west-2
```

A future runtime role therefore needs access to the exact inference-profile ARN plus the exact foundation-model ARN in those source/destination Regions. Foundation-model statements should be restricted by the exact `bedrock:InferenceProfileArn` condition.

Streaming permission is deliberately absent.

The policy must be revalidated against current AWS documentation immediately before deployment because model/profile routing can change.

## Cost-accounting map

Phase 7 does not collapse distinct cost drivers into an invented single number.

| Stage | Cost driver | Phase 7 evidence |
| --- | --- | --- |
| Corpus ingestion | embedding model usage | AWS bill/provider side; not reconstructed from runtime query evidence |
| Vector persistence | S3 Vectors storage/write | infrastructure/billing evidence |
| Query | query embedding | exact billable token/unit count not exposed by real runtime artifact |
| Vector query | request | directly computable from published per-request rate |
| Vector query | data processed | exact billable bytes not exposed by runtime artifact |
| Vector query | data returned | exact billable bill units not exposed by runtime artifact |
| Synthesis | model input tokens | directly observed |
| Synthesis | model output tokens | directly observed |

Gate 7.7 first four-case directly computable components:

```text
model input:             $0.0129074
model output:            $0.0035475
model subtotal:          $0.0164549
4 S3 Vectors requests:   $0.0000100
computable total:        $0.0164649
```

This remains explicitly **not the complete AWS bill**.

## Observability map

### Already captured in bounded lab/runtime evidence

```text
provider request IDs
retrieval result count/rank/score
canonical source/document/chunk identities
content/provenance hashes
context/catalog/request/result hashes
model/profile ID
input/output/total/cache tokens
Bedrock latency
client elapsed time
SDK retry count
stop reason
answer/abstention decision
claim/citation mappings
human support-judgment hashes
```

### Not yet claimed

```text
production SLOs
continuous deployed RAG metrics
end-user distributed trace correlation
production alert thresholds
high-volume percentile distributions
high-volume route/groundedness error rates
complete per-request AWS bill attribution
```

These require a deployed application runtime and measured workload. Small laboratory samples are not promoted into production SLOs.

## Quality and regression evidence inventory

Phase 7 now has distinct quality layers:

```text
unit/contract quality
 -> Ruff
 -> Pyright strict
 -> pytest

retrieval quality
 -> frozen knowledge-retrieval-golden:v1

provider/runtime integration
 -> real bounded Retrieve
 -> real bounded Converse
 -> request IDs / latency / retries / token evidence

groundedness quality
 -> frozen knowledge-grounding-golden:v1
 -> human-reviewed pair-level support labels
 -> deterministic metrics

infrastructure quality
 -> Terraform validation / TFLint / Checkov where AWS resources change
```

The closeout itself introduces documentation/ADR changes only and requires the existing repository CI to remain green before merge.

## Phase 8 entry criteria

Phase 8 may begin only with these boundaries frozen:

```text
1. structured vulnerability/risk truth remains deterministic authority
2. semantic retrieval remains explanatory/remediation evidence
3. route eligibility is explicit and typed
4. STRUCTURED / SEMANTIC / HYBRID / UNSUPPORTED outcomes are distinguishable
5. combined evidence preserves provenance by evidence class
6. missing required evidence produces explicit partial/unsupported behavior
7. Gate 7.7 first-run baseline remains immutable
8. prompt/reranker/search changes are separately versioned and reevaluated
9. quality, latency, cost, failures, and observability remain separately measurable
10. no AWS service is added merely for certification coverage
```

Phase 8 starts offline-first with a routing/authority contract. It must not begin by concatenating Athena rows with vector chunks.

## Deferred optimization backlog

The following are intentionally deferred until a measured Phase 8 hypothesis justifies them:

```text
larger retrieval candidate budget
metadata-filter changes
reranking
keyword + vector hybrid search
OpenSearch Serverless
alternative vector store
alternative embedding model
a revised synthesis/citation prompt
runtime cache
similarity-score thresholding
```

The Gate 7.7 weakness is a baseline, not permission for post-hoc tuning.

## AWS changes in Gate 7.8

```text
real AWS calls:        0
new AWS resources:    0
new IAM roles:        0
new IAM permissions:  0
new model calls:      0
```

This is intentional. The gate closes architecture and evidence before the next implementation phase.

## AIP-C01 learning notes

Gate 7.8 reinforces several exam-relevant architecture distinctions without adding AWS services solely for certification:

```text
Knowledge Base service role != application runtime identity
Retrieve != RetrieveAndGenerate
Converse non-streaming -> bedrock:InvokeModel authorization
Geographic inference profiles have source/destination IAM implications
vector similarity != confidence / authority
retrieval quality != groundedness quality
model token evidence != complete end-to-end AWS cost
laboratory telemetry != production observability/SLOs
```

## Current official AWS references checked

- Amazon Bedrock Knowledge Base permissions:
  https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-prereq-permissions-general.html
- Geographic cross-Region inference:
  https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html
- Claude Haiku 4.5 model card:
  https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html
- Amazon Bedrock inference APIs / IAM:
  https://docs.aws.amazon.com/bedrock/latest/userguide/inference.html
- Amazon S3 pricing / S3 Vectors:
  https://aws.amazon.com/s3/pricing/
- Amazon Bedrock pricing:
  https://aws.amazon.com/bedrock/pricing/

## Exit checklist

```text
[x] Gate 7.7 measured weakness preserved without tuning
[x] failure taxonomy consolidated
[x] future least-privilege runtime IAM documented
[x] cost-accounting boundary documented
[x] observability boundary documented
[x] README EN reviewed and synchronized
[x] README PT-BR reviewed and synchronized
[x] docs index reviewed and synchronized
[x] architecture EN/PT-BR synchronized
[x] current state synchronized
[x] roadmap synchronized and Phase 8 gates frozen
[x] ADR index synchronized
[x] no AWS/IAM/model changes introduced
[ ] final closeout PR CI green
[ ] squash merge
```

After the final two items, Phase 7 is closed and Phase 8 Gate 8.1 becomes authorized.
