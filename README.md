<div align="center">

🇺🇸 **English** &nbsp;|&nbsp; 🇧🇷 [Português](README.pt-br.md)

# OpsLens

### Verifiable Software Supply Chain & GenAI Architecture on AWS

**Threat Intelligence · Repository Intelligence · Deterministic Risk · Bedrock RAG · Hybrid Retrieval · Agentic AI · MCP · AgentCore · A2A · Inspector · Evaluation · Security Hardening · Cost Engineering**

</div>

OpsLens is an open-source AWS architecture lab and software-supply-chain intelligence platform built around one principle:

> **Agents reason. Code verifies evidence.**

It answers a practical question: given the software actually used by a repository, which vulnerabilities affect it, what exact evidence proves that, what should be prioritized, and what verified guidance can help act on those findings?

The platform deliberately separates probabilistic reasoning from deterministic authority for package/version matching, vulnerability correlation, risk policy, semantic-query admission, SQL compilation, evidence admission, tool authorization, result admission, and cost/resource limits.

> **Repository Risk != Runtime Exposure.**

## Current status

**Phases 0–18 are complete.** Phase 18 was protected-squash-merged through PR #290 at `feca774535b7d83f57c26f4e9fe7da71ce268f0f`.

**Phase 19 — Bounded Public Runtime & Productization** is in progress. Gate 19.1 is complete through PR #292. Gate 19.2 is complete through protected PR #347 at `71eda2650889d3047259d37be226862ed2a09092`. Gate 19.3 is complete through protected PR #349 at `18d31c03d27448c88a6ffcba16683f3875a5ba15`. Gate 19.4 is complete through protected PR #351 at `a5067e05fda74aad4d95d7f1a875110fb676304a`. Gate 19.5 is now freezing deterministic async Lambda deployment artifacts and the human-only immutable publication boundary in issue #352 / PR #353; it authorizes no runtime deployment.

```text
19.1  Public Runtime Hypothesis & Launch Contract       COMPLETE
      workload: public-analysis-workload:v1
      historical decision: DEFERRED_PENDING_MEASUREMENT
      leading hypothesis at that time: ASYNC_SUBMIT_STATUS_RESULT
19.2  Representative Workload Measurement              COMPLETE
      measured end-to-end: 17,748 ms
      measured Bedrock-facing stages: 13,098 ms / 73.80% of E2E
      selected interaction pattern: ASYNC_SUBMIT_STATUS_RESULT
      protected merge: PR #347 / 71eda2650889d3047259d37be226862ed2a09092
19.3  Concrete Async Topology Contract                  COMPLETE
      protected merge: PR #349 / 18d31c03d27448c88a6ffcba16683f3875a5ba15
      selected design topology: HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
      deployment authorized: NO
19.4  Disabled Async Runtime Implementation             COMPLETE
      protected merge: PR #351 / a5067e05fda74aad4d95d7f1a875110fb676304a
      runtime materialized by default: false
      execute-api endpoint enabled: NO
      submit/worker enabled: NO
      deployment authorized: NO
19.5  Immutable Async Deployment Artifacts              IN PROGRESS
      issue: #352 / PR: #353
      publication authority: HUMAN_ONLY_CREATE_ONLY
      artifact VersionId before publication: UNMEASURED
      runtime deployment authorized: NO
```

Gate 19.2 does not claim that the successful run timed out. The measured baseline completed below 30 seconds. The async decision is based on provider-latency coupling, retry safety, backpressure, and failure isolation; explicitly derived retry scenarios remain separate from measured evidence.

Gate 19.3 selected the design topology: API Gateway HTTP API + API Lambda + SQS + Lambda worker + DynamoDB, with a DLQ and explicit idempotency/state/retry authority. Gate 19.4 implemented that design **in repository code and Terraform only**, retaining `public_async_runtime_materialized=false`, the execute-api endpoint disabled, submit/worker switches disabled, the SQS event-source mapping disabled, worker reserved concurrency at zero, and no custom public domain. Gate 19.5 now produces separate deterministic API/worker ZIPs with exact SHA-256 and Lambda `source_code_hash` values and freezes content-addressed S3 keys before any human publication. No `terraform apply`, runtime AWS/IAM mutation, public endpoint enablement, or provider-heavy public execution is authorized.

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.md), [Portfolio Evidence](docs/portfolio-evidence.md), [AIP-C01 Learning Map](docs/aip-c01-learning-map.md), the [Gate 19.2 closeout](labs/phase-19-gate-19-2-closeout.md), the [Gate 19.3 topology contract](labs/phase-19-gate-19-3-async-topology-contract.md), the [Gate 19.4 disabled runtime implementation](labs/phase-19-gate-19-4-disabled-async-runtime.md), the [Gate 19.5 publication runbook](labs/phase-19-gate-19-5-immutable-artifact-publication-runbook.md), and the [ADR index](docs/adr/README.md).

## Architecture at a glance

```text
NVD / CISA KEV / FIRST EPSS / GitHub Advisories
        |
        v
source-preserving threat evidence
        |
public repository -> immutable snapshot -> inert uv.lock
        |
        v
deterministic PyPI + PEP 440 correlation
        |
NVD/CVSS + KEV + EPSS enrichment
        |
RepositoryAnalysisResult -> deterministic Risk Policy v1

Natural-language fact question
        |
        v
bounded Bedrock proposal -> deterministic SemanticQuery admission
        |
        v
typed SQL compiler -> bounded read-only Athena

Official knowledge sources
        |
        v
canonical corpus -> Bedrock Knowledge Base -> S3 Vectors
        |
        v
bounded Retrieve -> checked evidence -> bounded synthesis + citations

Structured + semantic evidence
        |
        v
deterministic route/composition -> bounded agent reasoning
        |
        v
typed capability authorization -> execution/result admission
```

No unrestricted text-to-SQL authority is granted to an LLM. Retrieved content is evidence, not instruction authority. Tool/protocol success is not business truth.

## Public product boundary

Protected `main` still has **no deployed public HTTP runtime**. Gate 19.4 is now protected code/Terraform implementation only; Gate 19.5 deals with immutable deployment-artifact provenance and does not materialize runtime resources.

The retained public-analysis authority begins with:

```text
untrusted JSON
 -> strict request admission
 -> validated GitHub coordinates
 -> immutable repository evidence
 -> deterministic threat/risk authority
 -> bounded semantic evidence
 -> bounded model reasoning
 -> deterministic result admission
```

Gate 19.2 exercised this complete non-public representative execution with deterministic admission, provider accounting, persisted evidence, and offline review. CI and ChatGPT did not execute the live provider path.

Gate 19.3 froze, and Gate 19.4 now implements behind disabled defaults, the following asynchronous control shape:

```text
POST /v1/analyses
  -> API Gateway HTTP API
  -> deterministic API Lambda
  -> DynamoDB job/idempotency authority
  -> SQS standard job queue
  -> Lambda worker
  -> admitted result back to DynamoDB

GET /v1/analyses/{job_id}
GET /v1/analyses/{job_id}/result
```

The job record, not queue delivery, owns business execution truth. The queue carries only deterministic `job_id` transport identity. Duplicate delivery is admitted through conditional DynamoDB state/attempt authority. The worker remains provider-disabled until a later gate explicitly admits and composes the provider-heavy executor.

Gate 19.5 adds a second provenance boundary before any exact deployment plan:

```text
role-specific source + locked dependency hashes
 -> deterministic ZIP bytes
 -> SHA-256 + Lambda source_code_hash
 -> content-addressed S3 key
 -> HUMAN-ONLY create-only publication
 -> exact immutable S3 VersionId
 -> Gate 19.6 exact Terraform plan input
```

`artifact hash != S3 VersionId`, and publication success does not mean deployment authorization.

## Retained measured evidence

The portfolio projection remains evidence-bound rather than promotional. Examples include:

| Experiment | Evidence |
| --- | --- |
| Phase 7 grounding review | 11/13 claims supported; derived supportedness ratio `0.8461538461538461` |
| Phase 11 retained reasoning reference | 6/6 cases; 3,395 tokens; 809.5 ms provider-latency median; derived USD `0.0041921` |
| Phase 12 bounded two-model comparison | 6/6 cases but 5,982 tokens, 1,694 ms derived provider-latency median, derived USD `0.0074338`; not retained as default |
| Phase 14 AgentCore experiment | 6/6 replay; derived total USD `0.006572445136128483`; retained only as optional lab target |
| Phase 16 Inspector read experiment | successful bounded read with zero returned records; **not** interpreted as zero runtime exposure |
| Phase 17 recovery | exact three-scheduler pause/resume cycle with final Terraform convergence |
| Phase 19 Gate 19.2 representative workload | 17,748 ms end-to-end; 4 GitHub requests; 1 Bedrock Retrieve at 4,148 ms client elapsed; 1 model call at 8,901 ms client elapsed / 7,772 ms provider latency; 5,936 input + 408 output tokens; 5,285-byte admitted result |

The Phase 18 machine-readable evidence chain begins at `labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json` and ends at `labs/evidence/phase-18-closeout-v1.json`. Historical artifacts remain immutable evidence even when current-facing documentation advances.

Gate 19.2 persisted the canonical live artifact at `labs/evidence/phase-19-gate-19-2-live-measurement-v1.json`, independently hashed as `04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114`, plus the machine-readable closeout record at `labs/evidence/phase-19-gate-19-2-closeout-v1.json`.

Gate 19.3 adds the design-only contract at `labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json`; it records zero deployment/AWS/IAM/provider mutations. Gate 19.4 adds implementation/readiness evidence at `labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json` plus an offline verifier. Gate 19.5 adds the canonical pre-publication manifest at `labs/evidence/phase-19-gate-19-5-prepublication-v1.json`; before human publication its S3 `VersionId` fields intentionally remain `UNMEASURED / PENDING_HUMAN_PUBLICATION`.

Current deterministic Gate 19.5 package identities are:

```text
API SHA-256:     99477676dcc41345c63ed28c81bb41c7f9f47bcf5b072254bc1ef0e2cfcd876e
API source hash: mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24=
API ZIP bytes:   17271715

Worker SHA-256:     0d04b472476ad7825b5190352da1642db9a7d42d1ce349d21a39fac8f6ecbdc9
Worker source hash: DQS0ckdq14JbUZA1LaFkLbmn1C0c40nSGjn6yPbsvck=
Worker ZIP bytes:   1036437
```

These are artifact identities, not runtime utilization or deployment evidence.

## Cost and resource envelopes

OpsLens separates measured/derived cost evidence from configured limits and forbids unsafe aggregation across unrelated experiments.

```text
semantic planner max output          256 tokens
single-agent max output               96 tokens
multi-agent triage max output         64 tokens
knowledge synthesis max output      2048 tokens
Athena scan cutoff/query         10485760 bytes
Scheduler maximum event age         3600 seconds
Scheduler maximum retry attempts        2
```

These are **configured limits, not measured utilization**. Gate 19.2 contributes whole-workload measurement evidence, but it does not convert configured limits into observed usage or treat `UNMEASURED` values as zero. In particular, request-time Athena metrics remain `NOT_APPLICABLE` for the retained direct structured-evidence path and `throttle_count` remains `UNMEASURED` even though its numeric counter is zero.

Gate 19.4 adds disabled-runtime design limits such as API reserved concurrency `2`, worker reserved concurrency `0`, API timeout `15 s`, worker timeout `60 s`, queue visibility `120 s`, redrive receive count `4`, worker max attempts `3`, and HTTP API burst/rate limits `10/5`. Every one of these values is `CONFIGURED_LIMIT`, not measured utilization.

## Retained experimentation boundaries

Phase 11 direct Bedrock reasoning remains the default/reference reasoning architecture. Phase 12 keeps deterministic specialization/handoff but rejects the additional two-model default because the measured topology added overhead without quality lift. MCP and A2A remain bounded interoperability layers rather than public runtimes. AgentCore remains an optional lab target with no standing experiment IAM/runtime. Inspector remains an independent read-only runtime-evidence boundary; its zero-record experiment is not repository-risk authority.

Security Hardening retains full-SHA GitHub Actions, protected-main security invariants, separated privileged identities, Dependency Review, CodeQL, eight adversarial cases across seven threat classes, content-minimized telemetry for 12 Powertools Lambda handlers, and a Terraform-owned pause for exactly three recurring ingestion schedules.

## What is deliberately not claimed

OpsLens does not currently claim a deployed public HTTP production runtime, public MCP/A2A runtime, AgentCore as the default production runtime, production SLOs from bounded experiments, production TCO/monthly run rate, zero runtime exposure from a zero-record Inspector read, configured limits as utilization, a global platform kill switch, or a certification readiness score/pass probability.

Phase 19 now has an evidence-backed async interaction-pattern decision, a protected concrete topology contract, a protected disabled code/Terraform implementation, and deterministic deployment-artifact identities in progress. Neither the Terraform definitions from Gate 19.4 nor the Gate 19.5 ZIP identities mean that API Gateway, Lambda, SQS, DynamoDB, IAM roles/policies, or any other public-runtime AWS resource has been created or enabled.

The retained deployment sequence is:

```text
Gate 19.5  deterministic build + human create-only immutable artifact publication
Gate 19.6  exact Terraform plan + offline admission/review
later gate human-authorized Terraform apply / controlled enablement, if admitted
```

## AIP-C01 learning laboratory

OpsLens is also used as hands-on preparation for **AWS Certified Generative AI Developer - Professional (AIP-C01)**. Phase 19 adds practical architecture reasoning around enterprise integration, synchronous versus asynchronous APIs, IAM responsibility boundaries, deployment provenance, abuse controls, monitoring, performance, cost, and troubleshooting without converting exam breadth into product requirements.

```text
AIP-C01 topic != product requirement
```

## AWS baseline

```text
environment:          dev
region:               us-east-1
vector store:         Amazon S3 Vectors
embedding model:      amazon.titan-embed-text-v2:0
embedding dimensions: 1024
chunking:             NONE
canonical chunks:     9
synthesis API:        Amazon Bedrock Converse
reasoning profile:    us.anthropic.claude-haiku-4-5-20251001-v1:0
public HTTP runtime:  NONE DEPLOYED
```

## Documentation

Start with [docs/README.md](docs/README.md). The strongest portfolio entry points are [Architecture](docs/architecture.md), [Portfolio Evidence](docs/portfolio-evidence.md), [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), the [Phase 18 closeout](labs/phase-18-closeout.md), the [Gate 19.1 launch contract](labs/phase-19-gate-19-1-public-runtime-hypothesis.md), the [Gate 19.2 closeout](labs/phase-19-gate-19-2-closeout.md), the [Gate 19.3 topology contract](labs/phase-19-gate-19-3-async-topology-contract.md), the [Gate 19.4 disabled runtime implementation](labs/phase-19-gate-19-4-disabled-async-runtime.md), the [Gate 19.5 publication runbook](labs/phase-19-gate-19-5-immutable-artifact-publication-runbook.md), and the [ADR index](docs/adr/README.md).

---

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency unless explicitly re-evaluated later.
