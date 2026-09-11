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

**Phase 19 — Bounded Public Runtime & Productization** is in progress. Gate 19.1 is complete and protected-squash-merged through PR #292 at `ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1`. Gate 19.2 has completed its human-operated representative live measurement and now has an evidence-backed interaction-pattern decision pending protected closeout merge.

```text
19.1  Public Runtime Hypothesis & Launch Contract       COMPLETE
      workload: public-analysis-workload:v1
      original runtime decision: DEFERRED_PENDING_MEASUREMENT
      leading hypothesis: ASYNC_SUBMIT_STATUS_RESULT
      AWS/IAM/public endpoint mutations: 0
19.2  Representative Workload Measurement              CLOSEOUT IN REVIEW
      measured end-to-end: 17,748 ms
      measured Bedrock-facing stages: 13,098 ms / 73.80% of E2E
      selected interaction pattern: ASYNC_SUBMIT_STATUS_RESULT
      concrete AWS topology selected: NO
```

Gate 19.2 does not claim that the successful run timed out. The measured baseline completed below 30 seconds. The async decision is instead based on provider-latency coupling, retry safety, backpressure, and failure isolation; explicitly derived retry scenarios are kept separate from measured evidence.

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.md), [Portfolio Evidence](docs/portfolio-evidence.md), [AIP-C01 Learning Map](docs/aip-c01-learning-map.md), the [Gate 19.2 closeout](labs/phase-19-gate-19-2-closeout.md), the [Gate 19.2 human live-measurement runbook](labs/phase-19-gate-19-2-human-live-measurement-runbook.md), and the [ADR index](docs/adr/README.md).

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

The retained public-analysis code is currently an **application boundary**, not a deployed HTTP service:

```text
untrusted JSON
 -> strict request admission
 -> validated GitHub coordinates
 -> immutable repository evidence
 -> bounded metadata-only semantic planning
 -> deterministic hybrid route admission
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

Gate 19.2 now has one complete non-public representative execution with deterministic admission, provider accounting, persisted evidence, and offline review. The run reused deterministic repository/risk authority, preloaded admitted threat evidence, measured GitHub transport, bounded Bedrock Knowledge Base retrieval, bounded synthesis, exact result admission, and atomic evidence persistence. CI and ChatGPT did not execute the live provider path.

The selected interaction pattern is now `ASYNC_SUBMIT_STATUS_RESULT`. This is **not** yet a concrete AWS deployment decision: no public endpoint, queue, worker, result store, new AWS resource, or IAM authority is authorized by Gate 19.2. The next Phase 19 boundary is to freeze the smallest concrete async ingress/job/result topology and least-privilege runtime authority before any deployment.

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

The Phase 18 machine-readable evidence chain begins at `labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json` and ends at `labs/evidence/phase-18-closeout-v1.json`. The historical closeout record intentionally preserves its pre-merge state; current-facing documentation reflects the completed protected merge.

Gate 19.2 persisted the canonical live artifact at `labs/evidence/phase-19-gate-19-2-live-measurement-v1.json`, independently hashed as `04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114`, plus the machine-readable closeout record at `labs/evidence/phase-19-gate-19-2-closeout-v1.json`.

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

These are **configured limits, not measured utilization**. Gate 19.2 now contributes whole-workload measurement evidence, but it does not convert configured limits into observed usage or treat `UNMEASURED` values as zero. In particular, Gate 19.2 keeps Athena request-time metrics `NOT_APPLICABLE` for the retained direct structured-evidence path and keeps `throttle_count` `UNMEASURED` even though the numeric counter is zero.

## Retained experimentation boundaries

Phase 11 direct Bedrock reasoning remains the default/reference reasoning architecture. Phase 12 keeps deterministic specialization/handoff but rejects the additional two-model default because the measured topology added overhead without quality lift. MCP and A2A remain bounded interoperability layers rather than public runtimes. AgentCore remains an optional lab target with no standing experiment IAM/runtime. Inspector remains an independent read-only runtime-evidence boundary; its zero-record experiment is not repository-risk authority.

Security Hardening retains full-SHA GitHub Actions, protected-main security invariants, separated privileged identities, Dependency Review, CodeQL, eight adversarial cases across seven threat classes, content-minimized telemetry for 12 Powertools Lambda handlers, and a Terraform-owned pause for exactly three recurring ingestion schedules.

## What is deliberately not claimed

OpsLens does not currently claim a public HTTP production runtime, public MCP/A2A runtime, AgentCore as the default production runtime, production SLOs from bounded experiments, production TCO/monthly run rate, zero runtime exposure from a zero-record Inspector read, configured limits as utilization, a global platform kill switch, or a certification readiness score/pass probability.

Phase 19 now has an evidence-backed async **interaction-pattern** decision. It still does not claim that API Gateway, Lambda, SQS, DynamoDB, Step Functions, ECS/Fargate, AgentCore, or another concrete AWS topology has been selected or deployed.

## AIP-C01 learning laboratory

OpsLens is also used as hands-on preparation for **AWS Certified Generative AI Developer - Professional (AIP-C01)**. Phase 19 adds practical architecture reasoning around enterprise integration, synchronous versus asynchronous APIs, IAM responsibility boundaries, abuse controls, monitoring, performance, cost, and troubleshooting without converting exam breadth into product requirements.

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
public HTTP runtime:  NONE
```

## Documentation

Start with [docs/README.md](docs/README.md). The strongest portfolio entry points are [Architecture](docs/architecture.md), [Portfolio Evidence](docs/portfolio-evidence.md), [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), the [Phase 18 closeout](labs/phase-18-closeout.md), the [Gate 19.1 launch contract](labs/phase-19-gate-19-1-public-runtime-hypothesis.md), the [Gate 19.2 closeout](labs/phase-19-gate-19-2-closeout.md), and the [ADR index](docs/adr/README.md).

---

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work and is not a Phase 19 dependency unless explicitly re-evaluated later.
