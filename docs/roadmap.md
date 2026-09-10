# OpsLens — Incremental Roadmap

_Last updated: 2026-09-10_

The roadmap is evidence-gated. A later phase does not invalidate earlier authority boundaries, and certification topics do not automatically become product requirements.

## Completed phases

```text
Phase 0   AWS Foundation                                      COMPLETE
Phase 1   EPSS Vertical Slice                                 COMPLETE
Phase 2   Threat Intelligence Data Lake                       COMPLETE
Phase 3   Vulnerability Correlation Engine                    COMPLETE
Phase 4   Repository Intelligence                             COMPLETE
Phase 5   Risk Prioritization Engine                          COMPLETE
Phase 6   Semantic Query Layer                                COMPLETE
Phase 7   Knowledge Retrieval with Bedrock                    COMPLETE
Phase 8   Hybrid Retrieval                                    COMPLETE
Phase 9   Public Analyze Your Repository application boundary COMPLETE
Phase 10  Observability & Operational Excellence              COMPLETE
Phase 11  Single-Agent Baseline                               COMPLETE
Phase 12  Multi-Agent Architecture                            COMPLETE
Phase 13  MCP                                                 COMPLETE
Phase 14  Amazon Bedrock AgentCore                            COMPLETE
Phase 15  A2A                                                 COMPLETE
Phase 16  Runtime Exposure with Amazon Inspector              COMPLETE
Phase 17  Security Hardening                                  COMPLETE
```

## Phase 18 — Evaluation, Cost & Portfolio Readiness

**Status: IN PROGRESS**

### Gate 18.1 — Cross-phase Evidence Inventory — COMPLETE

Retained result: 27 metrics, 8 source artifacts, 20 comparability groups, and 11 explicit non-comparability assertions.

### Gate 18.2 — Consolidated Evaluation & Reliability View — COMPLETE

Retained result: 5 sections, 27 metrics, 4 negative/rejected-default decision signals, 3 `UNMEASURED`, and 1 `NOT_APPLICABLE`.

### Gate 18.3 — Cost Accounting & Budget Envelopes — COMPLETE

Retained result: 16 entries, 7 cost observations, 2 resource observations, 7 configured limits, 3 `UNMEASURED`, 1 `NOT_APPLICABLE`, and no production TCO.

### Gate 18.4 — Portfolio Evidence Pack & AIP-C01 Synchronization — IN PROGRESS

Create a portfolio projection that remains mechanically traceable to Gates 18.2/18.3 and a repository-local AIP-C01 learning map.

Exit criteria:

- 11 selected headline numeric claims stay bound to Gate 18.2 classification/value/unit/scope;
- 7 configured budget claims stay bound to Gate 18.3 classification/value/unit;
- all four Gate 18.2 negative/rejected-default signals remain visible;
- portfolio documentation states explicitly what is not claimed;
- all 20 current AIP-C01 tasks are mapped as `EVIDENCED`, `PARTIAL`, or `STUDY_ONLY`;
- `EVIDENCED`/`PARTIAL` mappings require existing repository evidence;
- no certification-readiness/composite score is created;
- no AWS/IAM/model/tool mutation or pricing refresh is introduced;
- exact-head CI passes before protected squash merge.

### Candidate Gate 18.5 — Phase 18 closeout

After Gate 18.4, perform a narrow evidence-backed Phase 18 closeout. Do not add new benchmarks merely for presentation. Close only if the portfolio, evaluation, cost, and learning-map surfaces agree with the retained architecture and no unresolved evidence gap justifies another technical experiment.

## Beyond Phase 18

Do not pre-authorize the next implementation phase. Choose it from observed product/evidence gaps after the Phase 18 closeout. The deferred Governed LLM Gateway integration represented by PR #89 remains separate unless explicitly resumed and re-evaluated against the current OpsLens architecture.
