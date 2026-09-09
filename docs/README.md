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
  Gate 16.1 Inspector capability fit            COMPLETE / GO READ-ONLY ONLY
  Gate 16.2 read-only Inspector discovery       COMPLETE / BLOCKED_BY_EXISTING_IAM
  Gate 16.3 minimum Inspector read IAM          NEXT / DECISION ONLY
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

### Gate 16.1 — capability fit / authority

Phase 16 starts from the invariant:

> **Repository Risk != Runtime Exposure.**

The first capability-fit decision treats Amazon Inspector as an independent runtime evidence authority rather than an extension of repository-risk truth.

Selected first read APIs:

```text
ListCoverage
ListFindings
```

Current Inspector finding dimensions relevant to OpsLens:

```text
NETWORK_REACHABILITY
PACKAGE_VULNERABILITY
CODE_VULNERABILITY
```

The current upstream contract is explicitly preserved:

```text
NETWORK_REACHABILITY is EC2-only.
```

Therefore Phase 16 keeps four evidence dimensions separate:

```text
runtime_coverage
runtime_vulnerability
network_reachability
code_vulnerability
```

References:

- [`adr/0060-bounded-amazon-inspector-runtime-evidence-fit.md`](adr/0060-bounded-amazon-inspector-runtime-evidence-fit.md)
- [`../labs/phase-16-gate-16-1-inspector-runtime-evidence-fit.md`](../labs/phase-16-gate-16-1-inspector-runtime-evidence-fit.md)
- [`../labs/evidence/phase-16-gate-16-1-inspector-runtime-evidence-fit-v1.json`](../labs/evidence/phase-16-gate-16-1-inspector-runtime-evidence-fit-v1.json)

### Gate 16.2 — bounded read-only discovery — complete

The implementation was merged before the live experiment. The main-only workflow then used the existing `OpsLensGitHubDeployRole` without changing IAM or Inspector configuration.

Measured result:

```text
workflow:                 Inspector Read-Only Discovery
run:                      34411934819 / #1
job:                      102668116801
main SHA:                 d5ba77cc98df84488928e49ea5e429234e46bc9a
workflow conclusion:      success
experiment result:        BLOCKED_BY_EXISTING_IAM
ListCoverage:             ACCESS_DENIED / AccessDeniedException
ListFindings:             NOT_ATTEMPTED after fail-closed stop
client elapsed:           103.252301 ms
SDK retries:              0
AWS mutations:            0
new IAM:                  0
model invocations:        0
capability executions:    0
```

Authentication succeeded through GitHub OIDC, but Inspector read authorization did not. This is valid terminal evidence for Gate 16.2 and does not authorize automatic privilege expansion.

References:

- [`../labs/phase-16-gate-16-2-inspector-readonly-discovery.md`](../labs/phase-16-gate-16-2-inspector-readonly-discovery.md)
- [`../labs/evidence/phase-16-gate-16-2-inspector-readonly-discovery-v1.json`](../labs/evidence/phase-16-gate-16-2-inspector-readonly-discovery-v1.json)
- GitHub Actions run `34411934819`
- artifact `10127569570`, SHA-256 `8814b313261e2ac2cde2894e7ea428e437aaa66cd0d2f47e7187759565d6738e`

### Next gate — Gate 16.3

Evaluate the minimum Inspector read-only IAM boundary as a decision-only gate. Compare widening the existing deployment role, introducing a dedicated read-only discovery identity, and stopping Phase 16 without additional IAM.

No IAM mutation, Inspector activation/configuration change, hybrid routing integration, repository/runtime automatic correlation, or runtime-risk composite scoring is authorized until that decision is separately accepted.
