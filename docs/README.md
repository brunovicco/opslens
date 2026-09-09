# OpsLens Documentation

OpsLens documentation is organized around current architecture, implementation state, incremental roadmap, ADRs, gate laboratories, and immutable evaluation/runtime evidence.

## Primary documents

- [`architecture.md`](architecture.md) — accumulated architecture baseline.
- [`architecture.pt-br.md`](architecture.pt-br.md) — Portuguese architecture baseline.
- [`current-state.md`](current-state.md) — authoritative implementation checkpoint.
- [`roadmap.md`](roadmap.md) — incremental phase/gate plan and completion status.
- [`adr/`](adr/) — accepted architecture decisions.
- [`../labs/`](../labs/) — gate laboratories and immutable evidence references.

## Current implementation checkpoint

```text
Phase 0  AWS Foundation                         COMPLETE
Phase 1  EPSS Vertical Slice                    COMPLETE
Phase 2  Threat Intelligence Data Lake          COMPLETE
Phase 3  Vulnerability Correlation Engine       COMPLETE
Phase 4  Repository Intelligence                COMPLETE
Phase 5  Risk Prioritization Engine             COMPLETE
Phase 6  Semantic Query Layer                   COMPLETE
Phase 7  Knowledge Retrieval with Bedrock       COMPLETE
Phase 8  Hybrid Retrieval                       COMPLETE
Phase 9  Public Analyze Your Repository         COMPLETE
Phase 10 Observability & Operational Excellence COMPLETE
Phase 11 Single-Agent Baseline                  COMPLETE
Phase 12 Multi-Agent Architecture               COMPLETE
Phase 13 MCP                                    COMPLETE
Phase 14 Amazon Bedrock AgentCore               COMPLETE
Phase 15 A2A                                    COMPLETE
Phase 16 Runtime Exposure with Inspector        IN PROGRESS
  Gate 16.1 capability fit                     COMPLETE / GO READ-ONLY ONLY
  Gate 16.2 existing-role discovery            COMPLETE / BLOCKED_BY_EXISTING_IAM
  Gate 16.3 minimum read IAM                   COMPLETE / DEDICATED TEMP ROLE
  Gate 16.4 temporary role + rerun             COMPLETE / SUCCESS / ZERO RECORDS
  Gate 16.5 temporary IAM teardown             HUMAN DESTROY PENDING
Phase 17 Security Hardening                     PLANNED
Phase 18 Evaluation, Cost & Portfolio           PLANNED
```

## Permanent authority separations

```text
agent proposal != authorization
handoff proposal != handoff admission
handoff admission != capability authorization
AuthorizedAgentAction != capability invocation
capability invocation != execution result
MCP call admission != capability execution
MCP result projection != public runtime exposure
AgentCore hosting != business authorization
runtime deployment != runtime-exposure truth
A2A message != capability authorization
A2A transport success != business/evidence truth
A2A SDK acceptance != OpsLens admission authority
AWS authentication != Inspector read authorization
Inspector API success != runtime evidence presence
Inspector coverage != vulnerability finding
Inspector finding != repository finding
Inspector package match != deployed application ownership
Inspector resource presence != network exposure
Inspector PACKAGE_VULNERABILITY != NETWORK_REACHABILITY
Inspector score != Risk Policy v1
Inspector EPSS != OpsLens source-authority replacement
Inspector finding status != business remediation state
Inspector evidence != model authority
runtime evidence correlation != capability authorization
Repository Risk != Runtime Exposure
```

## Retained measured reasoning reference

Phase 11 remains the default/reference reasoning architecture:

```text
quality:                    6/6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
derived six-case cost:      USD 0.0041921
```

## Retained interoperability/runtime decisions

### Phase 13 — MCP

MCP remains a bounded offline interoperability layer over existing typed capability authority. A public/network MCP runtime is not retained.

### Phase 14 — AgentCore

AgentCore remains an optional lab target, not the default OpsLens reasoning runtime. Standing experiment-specific GitHub IAM was removed after the measured experiment.

### Phase 15 — A2A

A2A retains a content-addressed reference-only JSON-RPC `SendMessage` profile plus exact-source official SDK conformance in CI. No public/network A2A runtime, A2A-specific IAM, or SDK runtime dependency is retained.

Canonical Phase 15 closeout:

- [`adr/0059-phase15-a2a-closeout.md`](adr/0059-phase15-a2a-closeout.md)
- [`../labs/phase-15-closeout.md`](../labs/phase-15-closeout.md)
- [`../labs/evidence/phase-15-closeout-v1.json`](../labs/evidence/phase-15-closeout-v1.json)

## Phase 16 — Runtime Exposure with Amazon Inspector — in progress

Phase 16 starts from:

> **Repository Risk != Runtime Exposure.**

Amazon Inspector is treated as an independent runtime-evidence authority. The bounded read surface remains:

```text
ListCoverage
ListFindings
```

### Gate 16.2 — first discovery

The first main-only attempt used the shared deploy role without widening it:

```text
run:              34411934819 / #1
ListCoverage:     ACCESS_DENIED
ListFindings:     NOT_ATTEMPTED / fail-closed
AWS mutations:    0
new IAM:          0
```

That result triggered a separate IAM decision rather than automatic privilege expansion.

### Gate 16.3 — dedicated temporary read role

The accepted experiment identity was limited to the two Inspector list actions, the immutable OpsLens main OIDC subject, `aws:RequestedRegion == us-east-1`, and mandatory teardown after one measured run.

Reference:

- [`adr/0061-dedicated-temporary-inspector-discovery-role.md`](adr/0061-dedicated-temporary-inspector-discovery-role.md)

### Gate 16.4 — measured rerun

Human bootstrap created exactly the temporary role/policy and one main-only rerun succeeded:

```text
run:                      34414116549 / #2
job:                      102675000098
client elapsed:           465.877452 ms
ListCoverage:             SUCCESS / 1 page / 0 records
ListFindings:             SUCCESS / 1 page / 0 records
SDK retries:              0
AWS mutations:            0
new IAM during discovery: 0
model invocations:        0
capability executions:    0
```

The minimum IAM boundary worked, but the current dev account returned no Inspector coverage or finding evidence. The zero result is intentionally narrow: it does not prove Inspector is disabled, unsupported, or without value elsewhere.

Retained decision:

```text
Inspector read-only adapter/contract:        RETAIN
measured zero-evidence result:               RETAIN
standing Inspector discovery IAM:            REMOVE
Inspector activation/configuration change:   DO NOT CREATE IN PHASE 16
repository/runtime automatic correlation:    DO NOT CREATE
runtime-risk composite scoring:              DO NOT CREATE
model synthesis over Inspector evidence:     DO NOT CREATE
```

References:

- [`adr/0062-retain-inspector-read-contract-without-standing-iam-or-scan-activation.md`](adr/0062-retain-inspector-read-contract-without-standing-iam-or-scan-activation.md)
- [`../labs/phase-16-gate-16-4-inspector-readonly-rerun.md`](../labs/phase-16-gate-16-4-inspector-readonly-rerun.md)
- [`../labs/evidence/phase-16-gate-16-4-inspector-readonly-rerun-v1.json`](../labs/evidence/phase-16-gate-16-4-inspector-readonly-rerun-v1.json)
- GitHub Actions run `34414116549`
- artifact `10128371987`, digest `sha256:a6f917e62124b4c604891e1a83db9874e3ef34696110dfaead1af16d45a03365`

### Gate 16.5 — mandatory teardown

The retained repository state removes the temporary Inspector IAM definition. The historical discovery workflow remains for reproducibility but is disabled by default and requires explicit confirmation that a separately authorized temporary role exists.

After protected merge, the human bootstrap plane must prove an exact `0 add / 0 change / 2 destroy` cleanup, apply the reviewed saved plan, require post-apply convergence, and independently verify the temporary role is absent while the shared deployment role remains free of Inspector authority.

Phase 16 closes only after that cleanup evidence is recorded.
