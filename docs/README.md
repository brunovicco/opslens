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
Phase 16 Runtime Exposure with Inspector        COMPLETE
Phase 17 Security Hardening                     NEXT
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

Canonical closeout:

- [`adr/0059-phase15-a2a-closeout.md`](adr/0059-phase15-a2a-closeout.md)
- [`../labs/phase-15-closeout.md`](../labs/phase-15-closeout.md)
- [`../labs/evidence/phase-15-closeout-v1.json`](../labs/evidence/phase-15-closeout-v1.json)

## Phase 16 — Runtime Exposure with Amazon Inspector — complete

Phase 16 retained Amazon Inspector only as an **independent read-only runtime-evidence boundary**.

Gate sequence:

```text
16.1 capability fit                 COMPLETE / READ-ONLY ONLY
16.2 existing-role discovery       COMPLETE / BLOCKED_BY_EXISTING_IAM
16.3 minimum IAM decision          COMPLETE / DEDICATED TEMP ROLE
16.4 measured dedicated rerun      COMPLETE / SUCCESS / ZERO RECORDS
16.5 mandatory temporary teardown  COMPLETE / ROLE ABSENT / CONVERGED
```

Measured successful rerun:

```text
run:                    34414116549 / #2
job:                    102675000098
ListCoverage:           SUCCESS / 1 page / 0 records / 0 retries
ListFindings:           SUCCESS / 1 page / 0 records / 0 retries
client elapsed:         465.877452 ms
AWS mutations:          0
model invocations:      0
capability executions:  0
artifact:               10128371987
artifact SHA-256:       a6f917e62124b4c604891e1a83db9874e3ef34696110dfaead1af16d45a03365
```

Mandatory IAM cleanup:

```text
plan:                    0 add / 0 change / 2 destroy
apply:                   0 added / 0 changed / 2 destroyed
post-apply plan:         No changes
temporary role:          ABSENT / NoSuchEntity
shared deploy role:      PRESENT
standing Inspector IAM:  NONE
```

The zero-record result is evidence about the current dev account/region/time, not proof that Amazon Inspector is globally disabled or without value.

Final retention:

```text
Inspector read-only domain/adapter contract:   RETAIN
historical discovery workflow:                 RETAIN / DISABLED BY DEFAULT
measured zero-record evidence:                 RETAIN
standing Inspector discovery IAM:              NONE
Inspector activation/configuration:             NOT CREATED
hybrid runtime_exposure routing:                NOT CREATED
repository/runtime automatic correlation:       NOT CREATED
runtime-risk composite scoring:                 NOT CREATED
model synthesis over Inspector evidence:        NOT CREATED
```

References:

- [`adr/0060-bounded-amazon-inspector-runtime-evidence-fit.md`](adr/0060-bounded-amazon-inspector-runtime-evidence-fit.md)
- [`adr/0061-dedicated-temporary-inspector-discovery-role.md`](adr/0061-dedicated-temporary-inspector-discovery-role.md)
- [`adr/0062-retain-inspector-read-contract-without-standing-iam-or-scan-activation.md`](adr/0062-retain-inspector-read-contract-without-standing-iam-or-scan-activation.md)
- [`adr/0063-phase16-runtime-exposure-closeout.md`](adr/0063-phase16-runtime-exposure-closeout.md)
- [`../labs/phase-16-closeout.md`](../labs/phase-16-closeout.md)
- [`../labs/evidence/phase-16-closeout-v1.json`](../labs/evidence/phase-16-closeout-v1.json)
- [`../labs/evidence/phase-16-gate-16-5-inspector-iam-cleanup-postapply-v1.json`](../labs/evidence/phase-16-gate-16-5-inspector-iam-cleanup-postapply-v1.json)

## Next — Phase 17 Security Hardening

Phase 17 begins with a cross-cutting threat-model and control-gap inventory. The first gate should map existing controls and residual risks before authorizing implementation changes or new AWS services.
