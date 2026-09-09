# Phase 15 — Gate 15.3: Offline Official A2A SDK Conformance

_Date: 2026-09-09_

## Status

**COMPLETE — FROZEN A2A 1.0 HAPPY-PATH PROFILE ACCEPTED BY THE OFFICIAL PYTHON SDK; SDK REMAINS AN ISOLATED ORACLE ONLY.**

```text
issue:               #233
PR:                  #234
source main:         a60ea13008d841222af0f6486ca9ed69dd6f8426
successful head:     5639aa1984295a62714c56271f44111aa0e311ff
SDK:                 a2a-sdk 1.1.4
release tag:         v1.1.4
source commit:       2d4d3048b245d2af854bad804f0e722ea9febc08
protocol traffic:    none
```

## Evidence gap addressed

Gate 15.2 proved a strict local A2A profile, but both sides were OpsLens-owned code.

Gate 15.3 adds one independent oracle without changing authority:

```text
OpsLens-owned frozen serialized protocol evidence
 -> official A2A SDK proto parser / protobuf JSON round-trip
 -> official JSON-RPC request library
 -> semantic comparison only
 -> evidence
```

The official SDK never receives authority to construct or admit an OpsLens specialist task, capability, execution request, or business result.

## Frozen profile under test

```text
contract:          a2a-reference-interoperability:v1
A2A release:       1.0.0
protocol version:  1.0
binding:           JSONRPC
JSON-RPC:          2.0
operation:         SendMessage
```

Reference data remains exactly:

```text
handoff_id
reference_sha256
specialist_task_id
```

## Official SDK source provenance

The gate freezes:

```text
repository:     a2aproject/a2a-python
release tag:    v1.1.4
source commit:  2d4d3048b245d2af854bad804f0e722ea9febc08
package name:   a2a-sdk
version:        1.1.4
```

The official implementation exposes protobuf-backed A2A types and its JSON-RPC transport uses protobuf JSON conversion for `SendMessageRequest` / `SendMessageResponse` around method `SendMessage`.

## First attempt — package-index resolution failure

Initial head:

```text
c19970e1c9c2767be7f5b9baebee7d5a914ca944
```

CI:

```text
run: 34407729623 / #9
job: 102654625012
```

Everything before the SDK probe passed, including:

```text
project lockfile:                    PASS
project dependency sync:             PASS
a2a-sdk absent from pyproject:       PASS
a2a-sdk absent from project uv.lock: PASS
Gate 15.2 fixture/evidence:           PASS
Gate 15.2 regression experiment:     PASS
```

The SDK probe did not execute because the default resolver returned:

```text
No solution found when resolving --with dependencies
there is no version of a2a-sdk==1.1.4
```

Interpretation:

```text
default package-index resolution unavailable
!=
A2A protocol incompatibility
```

No SDK downgrade was authorized.

An intermediate run #10 at `1eac72ef16505b146d1e53f4bedd7a69f8bb4c64` repeated the same resolver path before the workflow itself was switched to exact Git source acquisition. It produced no additional protocol evidence.

## Exact-source acquisition decision

The retry uses the exact commit pointed to by official tag `v1.1.4`:

```text
uv run \
  --with 'a2a-sdk @ git+https://github.com/a2aproject/a2a-python.git@2d4d3048b245d2af854bad804f0e722ea9febc08' \
  python scripts/run_a2a_sdk_conformance.py
```

This produces a temporary isolated dependency environment only.

```text
OpsLens pyproject change: 0
OpsLens uv.lock change:   0
runtime dependency change: 0
```

The Git fetch/build is CI setup traffic. It must not be mislabeled as A2A protocol/runtime traffic.

## Successful conformance run

```text
head:     5639aa1984295a62714c56271f44111aa0e311ff
workflow: A2A CI
run:      34407951331 / #11
job:      102655344898
result:   SUCCESS
```

Quality/regression checks:

```text
uv lock --check:                    PASS
uv sync --frozen:                   PASS
project SDK dependency absence:     PASS
Gate 15.2 fixture/evidence:          PASS
Gate 15.2 regression experiment:    PASS
official SDK source conformance:    PASS
Ruff:                                PASS
Pyright:                             PASS — 0 errors / 0 warnings
pytest A2A slice:                    PASS — 25 passed in 0.08s
```

## Agent Card conformance

The OpsLens Agent Card was parsed as the official SDK `AgentCard` type and round-tripped through protobuf JSON conversion.

Measured result:

```text
parse:                         PASS
semantic round-trip:           PASS
supportedInterface count:      1
protocolBinding:               JSONRPC
protocolVersion:               1.0
omitted default-false fields:  []
```

No material semantic difference was observed for the frozen Agent Card profile.

## SendMessage request conformance

The OpsLens JSON-RPC `params` object was parsed as official `SendMessageRequest` and semantically round-tripped.

Measured result:

```text
parse:                    PASS
semantic round-trip:      PASS
role:                     ROLE_USER
reference fields:         handoff_id / reference_sha256 / specialist_task_id
JSON-RPC construction:    PASS
jsonrpc:                  2.0
method:                   SendMessage
string request id:        preserved
```

The independent JSON-RPC library used by the official SDK accepts the selected request semantics.

## Response conformance

Both frozen Gate 15.2 result variants were parsed through official `SendMessageResponse`:

```text
direct Message result:
  parse:               PASS
  semantic round-trip: PASS

terminal Task result:
  parse:               PASS
  semantic round-trip: PASS
```

The check is semantic, not byte-for-byte. No material semantic differences were observed in this selected surface.

## Measured process evidence

```text
SDK conformance process elapsed: 255.964758 ms
A2A protocol network requests:   0
model invocations:               0
capability executions:           0
new AWS resources:               0
new IAM roles/policies:          0
business-result transport:       0
incremental AWS cost:            USD 0.00
```

The elapsed value does not include a remote A2A exchange because none exists. It is not production latency evidence.

## Authority boundary

```text
A2A SDK acceptance != OpsLens admission authority
A2A protocol binding != business authority
A2A generated id != OpsLens content identity
A2A message != capability authorization
A2A task state != business/evidence truth
A2A transport success != business/evidence truth
```

Retained authority remains:

```text
raw duplicate-key validation -> OpsLens code
exact-shape admission        -> OpsLens code
reference identity           -> OpsLens code
reference resolution         -> OpsLens code
replay refusal               -> OpsLens code
result admission             -> OpsLens code
SDK parse/round-trip         -> protocol evidence only
```

## Result

The remaining Gate 15.2 conformance gap is closed for the selected happy path:

```text
OpsLens local profile works:              PASS
official SDK accepts Agent Card:          PASS
official SDK accepts SendMessage params:  PASS
official SDK accepts Message result:      PASS
official SDK accepts Task result:         PASS
project dependency expansion:             0
runtime authority expansion:              0
```

This does not create a need for a network deployment.

## Retention recommendation

Retain:

```text
Gate 15.2 offline A2A reference adapter
strict raw/domain admission
exact-source official SDK CI conformance recipe
Gate 15.3 evidence
```

Do not add:

```text
a2a-sdk project/runtime dependency
public A2A endpoint
standing A2A cloud resources
A2A-specific IAM
remote peer merely for protocol demonstration
```

## Next authorized gate

Gate 15.4 only — **Phase 15 retention and closeout**.

The decision question should be:

> Given that the strict offline reference boundary works and independently conforms to the official SDK, what should OpsLens retain now that no concrete independent peer requires a deployed A2A runtime?

A valid closeout is expected to preserve the reusable boundary/evidence while deferring network deployment until a real consumer requirement exists.

## Evidence

```text
docs/adr/0058-official-a2a-sdk-as-ci-conformance-oracle.md
labs/evidence/phase-15-gate-15-3-official-sdk-conformance-v1.json
```

## PR #89

Unrelated Governed LLM Gateway work remains untouched:

```text
PR:     #89
branch: feat/governed-gateway-semantic-planner
```
