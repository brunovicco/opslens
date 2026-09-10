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
Phase 18  Evaluation, Cost & Portfolio Readiness              COMPLETE PENDING GATE 18.5 MERGE
```

### Retained Phase 17 security lineage

**Gate 17.1** established the cross-cutting evidence-first threat/control-gap inventory. **Gate 17.2** hardened CI/CD and workflow authority and introduced the retained `Repository security invariants` protected-main context. Later Phase 17 gates added bounded dependency/code scanning, adversarial regression, telemetry hardening, operational recovery, architecture synchronization, and closeout without weakening those earlier controls.

## Phase 18 — Evaluation, Cost & Portfolio Readiness

**Status: COMPLETE PENDING GATE 18.5 PROTECTED MERGE**

### Gate 18.1 — Cross-phase Evidence Inventory — COMPLETE

Retained result: 27 metrics, 8 source artifacts, 20 comparability groups, and 11 explicit non-comparability assertions.

### Gate 18.2 — Consolidated Evaluation & Reliability View — COMPLETE

Retained result: 5 sections, 27 metrics, 4 negative/rejected-default decision signals, 3 `UNMEASURED`, and 1 `NOT_APPLICABLE`.

### Gate 18.3 — Cost Accounting & Budget Envelopes — COMPLETE

Retained result: 16 entries, 7 cost observations, 2 resource observations, 7 configured limits, 3 `UNMEASURED`, 1 `NOT_APPLICABLE`, and no production TCO.

### Gate 18.4 — Portfolio Evidence Pack & AIP-C01 Synchronization — COMPLETE

Retained result:

```text
headline metric claims:   11
configured limit claims:   7
decision signals:          4
AIP-C01 tasks:             20
EVIDENCED tasks:           14
PARTIAL tasks:              6
STUDY_ONLY tasks:           0
```

The task map also preserves explicit study-only topics. Those topics are study scope only and do not imply product implementation or service adoption.

Gate 18.4 was protected-squash-merged through PR #288 as `4a8e5d3d98504451cef26df4e9f274f2f9fd8dd0` after exact-head Security Hardening, Dependency Review, Evaluation Readiness, AgentCore, and CodeQL checks succeeded.

### Gate 18.5 — Phase 18 closeout — IN PROGRESS

Close Phase 18 without adding a new experiment. The closeout must:

- preserve the Gate 18.1 evidence-classification and comparability rules;
- preserve Gate 18.2 independent evaluation dimensions and all four negative/rejected-default signals;
- preserve Gate 18.3 cost/resource accounting without unsupported cross-workload aggregation or production TCO;
- preserve Gate 18.4 portfolio and AIP-C01 projections as evidence views rather than new authority;
- synchronize repository-facing documentation with the retained architecture;
- re-run the existing read-only Phase 18 validation chain on the exact closeout head;
- add no AWS/IAM/model/capability authority and no benchmark replay;
- leave the next implementation phase intentionally un-authorized.

## Beyond Phase 18

Do not pre-authorize a Phase 19 implementation theme. Select the next phase from observed product/evidence gaps after this closeout. A future choice may be productization, deployment, additional measured evaluation, or a separately re-evaluated Governed LLM Gateway integration, but none is authorized by Phase 18 itself.

PR #89 / `feat/governed-gateway-semantic-planner` remains separate deferred work unless explicitly resumed against the then-current OpsLens architecture.
