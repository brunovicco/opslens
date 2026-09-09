# ADR 0058 — Use the Official A2A SDK Only as an Isolated Conformance Oracle

- Status: Accepted
- Date: 2026-09-09
- Phase: 15 — A2A
- Gate: 15.3 — Official SDK Conformance

## Context

Gate 15.2 retained a strict OpsLens-owned offline A2A reference adapter:

```text
a2a-reference-interoperability:v1
```

It proved that one pre-admitted `SpecialistAgentTask` can be represented by a content-addressed reference, projected through the selected A2A `1.0` JSON-RPC `SendMessage` profile, and re-admitted as bounded Message or terminal Task metadata while keeping model invocation, capability execution, AWS/IAM mutation, network runtime, and business-result transport at zero.

That experiment still had one evidence limitation: both protocol sides were implemented by OpsLens code.

Gate 15.3 therefore asks only:

> Does the official Python A2A implementation independently accept and preserve the frozen Gate 15.2 happy-path protocol semantics?

This is a protocol-conformance question, not an authorization question and not a reason to deploy an A2A service.

## Official implementation frozen for the gate

```text
repository:     a2aproject/a2a-python
release:        v1.1.4
package:        a2a-sdk
version:        1.1.4
source commit:  2d4d3048b245d2af854bad804f0e722ea9febc08
```

The official SDK exports A2A v1 protobuf types including `AgentCard`, `SendMessageRequest`, and `SendMessageResponse`. Its JSON-RPC client transport serializes `SendMessageRequest` through protobuf JSON conversion, emits method `SendMessage`, and parses the result into `SendMessageResponse`.

## Dependency-distribution evidence

The first Gate 15.3 CI attempt used:

```text
uv run --with a2a-sdk==1.1.4 ...
```

The CI default package-index resolver reported no satisfiable `a2a-sdk==1.1.4` distribution. The conformance script did not execute.

This is not protocol incompatibility. It is dependency-distribution evidence.

OpsLens therefore does not silently downgrade the oracle and does not add the SDK to project dependencies merely to make the test pass.

The retained acquisition method is the exact official source commit corresponding to `v1.1.4`:

```text
uv run \
  --with 'a2a-sdk @ git+https://github.com/a2aproject/a2a-python.git@2d4d3048b245d2af854bad804f0e722ea9febc08' \
  ...
```

This fetch/build activity belongs to CI dependency setup. It is explicitly distinct from A2A protocol/runtime network traffic.

## Decision

Use the official A2A Python SDK **only as an isolated, exact-source CI conformance oracle** for the frozen Gate 15.2 happy-path profile.

Do not add `a2a-sdk` to OpsLens `pyproject.toml` or `uv.lock`.

Do not accept SDK objects directly as business/domain authority.

Keep:

```text
OpsLens raw duplicate-key validation:     AUTHORITATIVE
OpsLens exact-shape admission:            AUTHORITATIVE
OpsLens content-addressed identity:        AUTHORITATIVE
OpsLens replay refusal:                    AUTHORITATIVE
OpsLens result admission:                  AUTHORITATIVE
official SDK parsing/round-trip:           PROTOCOL ORACLE ONLY
official JSON-RPC construction:            PROTOCOL ORACLE ONLY
```

Permanent boundary:

```text
A2A SDK acceptance != OpsLens admission authority
```

## Conformance surface

The oracle validates only the already-frozen happy path:

```text
AgentCard
 -> exactly one supportedInterface
 -> protocolBinding = JSONRPC
 -> protocolVersion = 1.0

SendMessageRequest
 -> ROLE_USER
 -> one data Part
 -> handoff_id
 -> reference_sha256
 -> specialist_task_id

JSON-RPC request
 -> jsonrpc = 2.0
 -> method = SendMessage
 -> string request id preserved

SendMessageResponse
 -> direct Message result
 -> terminal Task result
```

The comparison is semantic rather than byte-for-byte. Serializer ordering, omitted defaults, or other non-authoritative representation details may differ if the frozen meaning is preserved.

## Measured conformance result

Successful Gate 15.3 head:

```text
5639aa1984295a62714c56271f44111aa0e311ff
```

CI:

```text
workflow: A2A CI
run:      34407951331 / run #11 / SUCCESS
job:      102655344898
```

Results:

```text
Agent Card parse:                   PASS
Agent Card semantic round-trip:     PASS
supportedInterface count:           1
protocolBinding:                     JSONRPC
protocolVersion:                     1.0
omitted default-false fields:        []

SendMessageRequest parse:            PASS
SendMessageRequest round-trip:       PASS
ROLE_USER preserved:                 PASS
reference fields preserved:          PASS
JSON-RPC construction:               PASS
JSON-RPC 2.0 preserved:              PASS
method SendMessage preserved:        PASS
string request id preserved:         PASS

Message SendMessageResponse parse:   PASS
Message semantic round-trip:         PASS
Task SendMessageResponse parse:      PASS
Task semantic round-trip:            PASS
```

Measured conformance-process elapsed time:

```text
255.964758 ms
```

This elapsed value excludes any A2A peer/network call because none occurred. It is local CI conformance-process evidence, not a runtime SLO.

## Impact

```text
A2A protocol network requests:       0
CI source dependency acquisition:    YES — setup only
OpsLens runtime dependency changes:  0
OpsLens lockfile changes:             0
model invocations:                   0
capability executions:               0
new AWS resources:                   0
new IAM roles/policies:              0
business-result transport:           0
incremental AWS cost:                USD 0.00
```

## What this proves

Gate 15.3 supports these claims:

1. the official SDK v1.1.4 accepts the frozen OpsLens Agent Card profile;
2. the official SDK preserves the selected JSON-RPC `1.0` interface semantics;
3. the official SDK accepts and round-trips the reference-only `SendMessageRequest` semantics;
4. the official JSON-RPC dependency accepts the selected method/version/request-id shape;
5. the official SDK accepts both bounded Message and terminal Task response variants;
6. this independent check can remain isolated from OpsLens project dependencies and runtime authority.

## What this does not prove

```text
production network interoperability
real remote peer value
production TLS/authentication
network latency / SLOs
multi-turn semantics
streaming
push notifications
extended Agent Card authentication
business-result transport
exactly-once distributed execution
A2A capability authorization
A2A as retained production network architecture
AgentCore hosting for A2A
MCP public runtime
```

## Network consequence

Passing SDK conformance does **not** create a reason to deploy a second agent service.

The architecture still has no retained independent agent peer that requires a network protocol.

Therefore:

```text
protocol conformance PASS
!=
network deployment justified
```

A future real peer experiment requires a concrete independent consumer/service requirement and its own transport, authentication, failure, cost, IAM, and observability decision.

## Retention outcome

```text
Gate 15.2 offline reference adapter:       RETAIN
strict OpsLens raw/domain admission:       RETAIN
official SDK exact-source CI oracle:       RETAIN
project a2a-sdk dependency:                DO NOT ADD
public/network A2A runtime:                DO NOT CREATE NOW
```

## Next authorized gate

Authorize Gate 15.4 only:

> Make the Phase 15 A2A retention/closeout decision from Gates 15.1–15.3, without manufacturing a network peer solely to exercise more protocol surface.

The closeout should decide whether to retain the offline reference boundary and SDK conformance recipe while deferring network deployment until a concrete independent peer exists.

## Evidence

```text
labs/evidence/phase-15-gate-15-3-official-sdk-conformance-v1.json
labs/phase-15-gate-15-3-official-sdk-conformance.md
```

## Production engineering / AIP-C01 learning connection

This gate reinforces production engineering discipline relevant to GenAI systems on AWS: independently validate interoperability contracts, isolate third-party dependencies from runtime authority, pin exact source provenance when distribution channels lag, keep transport/protocol success separate from business authorization, and avoid deploying infrastructure merely because a protocol implementation passes conformance.
