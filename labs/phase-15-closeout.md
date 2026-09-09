# Phase 15 — A2A Closeout

_Date: 2026-09-09_

## Status

**COMPLETE — RETAIN BOUNDED OFFLINE INTEROPERABILITY; DO NOT CREATE A NETWORK A2A RUNTIME WITHOUT A CONCRETE CONSUMER.**

```text
issue:          #235
source main:    f28a761bd666538cdfe24a53ee4e336b15b36398
phase:          Phase 15 — A2A
A2A release:    1.0.0
binding:        JSONRPC
operation:      SendMessage
```

## Phase question

Phase 15 asked whether A2A provides useful interoperability without moving OpsLens authority into protocol metadata, remote peer claims, task state, or transport success.

The answer is yes at a bounded offline reference-only boundary. The current architecture does not justify a public/network peer runtime.

## Evidence chain

### Gate 15.1 — capability fit

```text
independently deployed retained peer: NO
current handoff requires A2A:         NO
bounded protocol-fit hypothesis:      YES
decision:                             GO OFFLINE ONLY
```

The protocol baseline was corrected before implementation to A2A `1.0.0`, with `JSONRPC` explicitly selected as the first OpsLens binding rather than treated as the only A2A binding.

### Gate 15.2 — bounded offline adapter

Retained path:

```text
pre-admitted SpecialistAgentTask
 -> content-addressed A2AReference
 -> code-owned local registry
 -> strict raw A2A 1.0 JSON-RPC SendMessage projection
 -> exact-shape / duplicate-key validation
 -> code-owned reference resolution
 -> bounded Message or terminal completed Task metadata
 -> deterministic OpsLens admission
 -> STOP
```

Measured evidence:

```text
Agent Card bytes:          582
protocol requests:         2
peer handler attempts:     2
request bytes total:       1308
response bytes total:      989
client elapsed sum:        0.353039 ms
handler elapsed sum:       0.239397 ms
retries:                   0
model invocations:         0
capability executions:     0
new AWS resources:         0
new IAM roles/policies:    0
incremental AWS cost:      USD 0.00
```

The timings are local-process measurements only and are not production/network latency evidence.

### Gate 15.3 — independent official SDK conformance

Oracle:

```text
distribution:  a2a-sdk
version:       1.1.4
release tag:   v1.1.4
source commit: 2d4d3048b245d2af854bad804f0e722ea9febc08
acquisition:   exact GitHub source commit in CI setup only
```

Successful exact-head validation before merge:

```text
implementation head: bcf1ee4e7fa6ff948041696f6df4d735ef8b6cb5
A2A CI:             34408271518 / #16 — SUCCESS
Multi-Agent CI:     34408271444 / #48 — SUCCESS
AgentCore CI:       34408271466 / #75 — SUCCESS
merge:              f28a761bd666538cdfe24a53ee4e336b15b36398
```

Conformance result:

```text
AgentCard parse:                         PASS
AgentCard semantic round-trip:           PASS
SendMessageRequest parse:                PASS
SendMessageRequest semantic round-trip:  PASS
JSON-RPC 2.0 SendMessage construction:   PASS
Message response parse/round-trip:       PASS
Task response parse/round-trip:          PASS
project a2a-sdk dependency:              0
protocol network requests:               0
model invocations:                       0
capability executions:                   0
new AWS resources:                       0
new IAM roles/policies:                  0
incremental AWS cost:                    USD 0.00
```

The package-index resolution failure from the first attempt is preserved as distribution evidence. Gate 15.3 did not downgrade the SDK; it froze the exact official source commit instead.

## Final retention decision

Retain:

```text
A2AReference content-addressed identity
strict raw JSON admission
reference-only SendMessage profile
bounded Message / terminal Task metadata admission
local replay refusal
A2A fixtures / CI
exact-source official SDK conformance oracle
immutable Phase 15 evidence
```

Do not retain/create:

```text
network/public A2A runtime
standing cloud resources
A2A-specific IAM
protocol-derived capability authority
business-result transport authority
SDK runtime/project dependency
AgentCore hosting for A2A
MCP runtime promotion
```

## Permanent authority boundaries

```text
A2A message != capability authorization
A2A peer identity != business authority
A2A AgentCard skill != OpsLens capability authorization
A2A task state != business/evidence truth
A2A transport success != business/evidence truth
A2A artifact != admitted OpsLens evidence
A2A handoff proposal != handoff admission
A2A context/task identity != OpsLens source-task identity
A2A authentication != capability authorization
A2A protocol binding != business authority
A2A generated id != OpsLens content identity
A2A SDK acceptance != OpsLens admission authority
```

## Closeout conclusion

```text
Phase 15 A2A: COMPLETE
```

The retained architecture proves protocol compatibility without inventing a distributed runtime.

The next planned phase in the existing roadmap is:

```text
Phase 16 — Runtime Exposure with Amazon Inspector
```

No Phase 16 AWS mutation is authorized by this closeout alone.

## Evidence

```text
docs/adr/0059-phase15-a2a-closeout.md
labs/evidence/phase-15-closeout-v1.json
```

PR #89 / `feat/governed-gateway-semantic-planner` remains untouched.
