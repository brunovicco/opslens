# Phase 17 — Gate 17.4: Adversarial Authority Boundaries

_Date: 2026-09-10_

## Status

**IMPLEMENTATION COMPLETE / FINAL PR-HEAD VALIDATION PENDING.**

Issue: #263  
PR: #264  
ADR: `docs/adr/0067-bounded-adversarial-authority-regression-suite.md`

## Goal

Attack retained application, model-adjacent, execution, MCP, and A2A authority boundaries without creating new cloud/runtime authority.

The evaluation is intentionally adversarial but offline. It asks whether caller-controlled text, protocol payloads, model-style proposals, result tampering, or cost-amplification attempts can cross deterministic boundaries already claimed by OpsLens.

## Evaluation design

```text
untrusted/adversarial input
 -> real retained admission/authorization boundary
 -> deterministic expected disposition
 -> no fallback authority
 -> no network/model/AWS execution
 -> immutable evidence
```

This gate does not use a synthetic security layer. Each case calls retained production domain/application code directly.

## Cases

| ID | Boundary | Attack | Expected | Result |
| --- | --- | --- | --- | --- |
| `ADV17-PUBLIC-001` | public request admission | unknown field attempts to inject instructions/tool authority | `REJECT` | `REJECT` |
| `ADV17-PROMPT-001` | synthesis prompt envelope | direct + retrieved-content prompt injection | bounded accepted data | bounded accepted data |
| `ADV17-TOOL-001` | single-agent authorization | capability outside admitted allowlist | `REJECT` | `REJECT` |
| `ADV17-TOOL-002` | multi-agent handoff | specialization tries to recover absent authority | `REJECT` | `REJECT` |
| `ADV17-RESULT-001` | result admission | forged content-addressed result binding | `REJECT` | `REJECT` |
| `ADV17-MCP-001` | MCP admission | dynamic/cross-capability tool request | `REJECT` | `REJECT` |
| `ADV17-A2A-001` | A2A reference admission | capability/tool args smuggled in reference payload | `REJECT` | `REJECT` |
| `ADV17-COST-001` | cost/amplification limits | expand bytes/calls/retries/fallbacks | `REJECT` | `REJECT` |

## Prompt-injection boundary

The prompt case intentionally places hostile instructions in two untrusted channels:

```text
user question
retrieved evidence text
```

The real `SynthesisPromptEnvelope` must preserve:

```text
TRUSTED_SYNTHESIS_INSTRUCTIONS_V1
!= question
!= evidence_json
```

The assertion is structural. It does **not** claim that a future model cannot ever be socially engineered by adversarial content. It proves that application serialization does not promote user/retrieved text into the trusted instruction field.

## Capability/tool boundary

The suite verifies both single-agent and multi-agent authority.

```text
model-style proposal
 -> authorize_agent_action(...)
 -> capability must already exist in task.allowed_capabilities
```

and:

```text
source task authority
 -> specialization capability set
 -> deterministic intersection
 -> empty intersection => reject
```

Task text cannot create a new capability and a handoff cannot reintroduce authority that the source task never had.

## MCP boundary

The attack surface stays reference/typed-invocation based.

```text
raw/dynamic tool name
 -> closed McpToolName parser
 -> unknown tool => reject

existing typed invocation
 + mismatched MCP tool
 -> capability mismatch
 -> reject
```

MCP interoperability therefore remains downstream of existing business authorization rather than becoming a dynamic tool-authority plane.

## A2A boundary

The retained A2A profile is still reference-only.

An attacker attempts to add capability/tool arguments to the JSON-RPC reference payload. Exact-key admission rejects the message before the reference can be treated as a valid OpsLens handoff.

```text
A2A transport payload
!= source-task authority
!= capability authorization
!= business result
```

## Result-admission boundary

A forged structured result digest is rejected by the retained content-addressed result-binding contract. Transport/executor completion alone cannot create admissible evidence.

## Cost-amplification boundary

The same attacker-oriented suite freezes retained bounds:

```text
single-agent task UTF-8 bytes:     2048
single-agent executions per call: 1
execution retries:                 0
adaptive execution fallbacks:     0
synthesis model calls:             1
```

Attempts to increase those limits through untrusted inputs or constructed objects are rejected before runtime amplification can occur.

## CI authority

Dedicated workflow:

```text
.github/workflows/adversarial-security-ci.yml
name: Adversarial Security CI
job/check: Adversarial authority boundaries
```

Authority:

```text
contents: read
persist-credentials: false
id-token: write:                 NO
AWS credential configuration:   NO
security-events: write:          NO
repository write permission:     NO
runtime deployment:              NO
```

`Security Hardening CI` additionally verifies this workflow cannot silently acquire OIDC/AWS/write authority later.

## First measured result

Initial implementation head:

```text
d392e0ed610a24dd9ccedd5baf056863bbad4dc4
```

```text
Adversarial Security CI
run:       34425331159 / #1
job:       102709241947
Ruff:      PASS
Pyright:   PASS / 0 errors
pytest:    PASS / 8 passed in 2.01s
```

Adjacent controls on that implementation also succeeded:

```text
Repository security invariants  34425331118 / #21  SUCCESS
Dependency Review               34425331165 / #6   SUCCESS
CodeQL / Python                 34425331130 / #8   SUCCESS
```

## Policy-frozen checkpoint

After adding repository-wide verification for the new adversarial workflow and ADR 0067, head:

```text
b6477efda1e6e9694c68005f0cf547d7c37c72f2
```

also produced:

```text
Adversarial Security CI          34425544809 / #3   SUCCESS
Repository security invariants   34425544821 / #23  SUCCESS
Dependency Review                34425544847 / #8   SUCCESS
CodeQL / Python                  34425544941 / #10  SUCCESS
```

## Interpretation

No first-slice adversarial case exposed a business-logic gap that justified remediation or authority expansion.

That is a positive regression result, but the claim remains deliberately narrow:

```text
8 tested boundary attacks behaved as specified
!= universal model safety
!= universal application security
!= absence of future vulnerabilities
```

The strongest architectural outcome is that no speculative prompt sanitizer, generic policy engine, new model guardrail service, AWS service, IAM grant, or dynamic tool layer was required.

## Cloud/runtime impact

```text
AWS mutations:          0
new IAM permissions:    0
new AWS services:       0
network calls:          0
model invocations:      0
capability executions:  0
public runtime changes: 0
Inspector activation:   0
PR #89 changes:         0
```

## Retention decision

```text
adversarial boundary suite:                 RETAIN
Adversarial Security CI:                    RETAIN
least-privilege workflow invariant:         RETAIN
live model jailbreak as authority proof:    DO NOT USE
new AWS/model/tool authority from Gate17.4: NOT AUTHORIZED
```

## Evidence

```text
labs/evidence/phase-17-gate-17-4-adversarial-boundaries-v1.json
docs/adr/0067-bounded-adversarial-authority-regression-suite.md
```

## Remaining closeout steps

Before Gate 17.4 is marked complete:

1. inspect exact-head CI after this evidence/document slice;
2. ensure no unresolved review threads;
3. mark PR #264 ready;
4. protected-squash merge PR #264;
5. create the documentation closeout slice that synchronizes `docs/current-state.md`, `docs/roadmap.md`, and `docs/README.md`;
6. close issue #263 only after the closeout slice is merged.

PR #89 / `feat/governed-gateway-semantic-planner` remains explicitly out of scope.
