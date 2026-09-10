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

Phases 0–17 are complete. **Phase 18 — Evaluation, Cost & Portfolio Readiness is complete pending the Gate 18.5 protected closeout merge.** Gates 18.1–18.4 are complete; Gate 18.5 freezes the evidence-backed closeout without adding another benchmark or runtime surface.

```text
18.1  Cross-phase Evidence Inventory            COMPLETE
18.2  Consolidated Evaluation & Reliability     COMPLETE
18.3  Cost Accounting & Budget Envelopes        COMPLETE
18.4  Portfolio Evidence + AIP-C01 Mapping       COMPLETE
18.5  Phase 18 evidence-backed closeout          IN PROGRESS
```

See [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.md), [Portfolio Evidence](docs/portfolio-evidence.md), [AIP-C01 Learning Map](docs/aip-c01-learning-map.md), and the [ADR index](docs/adr/README.md).

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

## Retained measured evidence

The current portfolio projection is deliberately evidence-bound rather than promotional. Examples include:

| Experiment | Evidence |
| --- | --- |
| Phase 7 grounding review | 11/13 claims supported; derived supportedness ratio `0.8461538461538461` |
| Phase 11 retained reasoning reference | 6/6 cases; 3,395 tokens; 809.5 ms provider-latency median; derived USD `0.0041921` |
| Phase 12 bounded two-model comparison | 6/6 cases but 5,982 tokens, 1,694 ms derived provider-latency median, derived USD `0.0074338`; not retained as default |
| Phase 14 AgentCore experiment | 6/6 replay; derived total USD `0.006572445136128483`; retained only as optional lab target |
| Phase 16 Inspector read experiment | successful bounded read with zero returned records; **not** interpreted as zero runtime exposure |
| Phase 17 recovery | exact three-scheduler pause/resume cycle with final Terraform convergence |

The machine-readable evidence chain begins at `labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json`, ends at `labs/evidence/phase-18-closeout-v1.json`, and is deterministically revalidated in CI.

## Cost and resource envelopes

Gate 18.3 separates observed/derived cost evidence from configured limits and forbids unsafe aggregation across unrelated experiments.

```text
semantic planner max output          256 tokens
single-agent max output               96 tokens
multi-agent triage max output         64 tokens
knowledge synthesis max output      2048 tokens
Athena scan cutoff/query         10485760 bytes
Scheduler maximum event age         3600 seconds
Scheduler maximum retry attempts        2
```

These are **configured limits, not measured utilization**. OpsLens does not manufacture a production TCO or monthly run rate from bounded lab measurements.

## Retained experimentation boundaries

Phase 11 direct Bedrock reasoning remains the default/reference reasoning architecture. Phase 12 keeps deterministic specialization/handoff but rejects the additional two-model default because the measured topology added overhead without quality lift. MCP and A2A remain bounded interoperability layers rather than public runtimes. AgentCore remains an optional lab target with no standing experiment IAM/runtime. Inspector remains an independent read-only runtime-evidence boundary; its zero-record experiment is not repository-risk authority.

Security Hardening retains full-SHA GitHub Actions, protected-main security invariants, separated privileged identities, Dependency Review, CodeQL, eight adversarial cases across seven threat classes, content-minimized telemetry for 12 Powertools Lambda handlers, and a Terraform-owned pause for exactly three recurring ingestion schedules.

## What is deliberately not claimed

OpsLens does not currently claim a public HTTP production runtime, public MCP/A2A runtime, AgentCore as the default production runtime, production SLOs from bounded experiments, production TCO/monthly run rate, zero runtime exposure from a zero-record Inspector read, configured limits as utilization, a global platform kill switch, or a certification readiness score/pass probability.

## AIP-C01 learning laboratory

OpsLens is also used as hands-on preparation for **AWS Certified Generative AI Developer - Professional (AIP-C01)**. The repository map classifies each current exam task as `EVIDENCED`, `PARTIAL`, or `STUDY_ONLY` and keeps exam-service breadth separate from product requirements.

A service is not added merely because it appears in the exam guide. Exam coverage is not a certification guarantee. See [docs/aip-c01-learning-map.md](docs/aip-c01-learning-map.md).

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
```

## Documentation

Start with [docs/README.md](docs/README.md). The strongest portfolio entry points are [Architecture](docs/architecture.md), [Portfolio Evidence](docs/portfolio-evidence.md), [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), the [Phase 18 closeout](labs/phase-18-closeout.md), and the [ADR index](docs/adr/README.md).

---

The next implementation phase is intentionally not pre-authorized by Phase 18. PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred Governed LLM Gateway work unless explicitly re-evaluated and resumed.
