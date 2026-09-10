# ADR 0067 — Bounded adversarial authority regression suite

- Status: Accepted
- Date: 2026-09-10
- Phase: 17 — Security Hardening
- Gate: 17.4 — Adversarial input, prompt-injection, and tool-abuse testing
- Issue: #263
- PR: #264

## Context

Phases 9–15 introduced multiple fail-closed boundaries around untrusted public request data, retrieved content, model proposals, capability authorization, typed execution, MCP, and A2A. Gate 17.1 recorded those controls as existing evidence, while Gates 17.2 and 17.3 hardened the surrounding CI/supply-chain control plane.

Those historical unit tests prove individual contracts, but Phase 17 still needs one explicit attacker-oriented regression surface that asks a cross-cutting question:

> Can untrusted text, protocol payloads, model-style proposals, malformed result evidence, or amplification attempts cross the authority boundaries that OpsLens claims to retain?

Gate 17.4 must answer that without creating a new public runtime, invoking a model, adding tools, widening IAM, or executing third-party repository code.

## Decision

### 1. Add one dedicated offline adversarial regression suite

Retain:

```text
tests/security_hardening/test_adversarial_boundaries.py
```

The first suite contains eight deterministic cases across seven threat classes:

```text
ADV17-PUBLIC-001  unknown instruction field is rejected before network/provider work
ADV17-PROMPT-001  direct/indirect injection remains question/evidence data
ADV17-TOOL-001    task text cannot expand the capability allowlist
ADV17-TOOL-002    specialist handoff cannot reintroduce absent capabilities
ADV17-RESULT-001  forged result binding cannot become execution evidence
ADV17-MCP-001     dynamic/cross-capability MCP tool requests fail closed
ADV17-A2A-001     A2A reference payload cannot smuggle capability/tool arguments
ADV17-COST-001    input/call/retry/fallback budgets cannot be expanded
```

Every case executes the real retained domain/application boundary directly. The suite does not simulate a fictional WAF, policy engine, or network runtime.

### 2. Prefer boundary tests over live adversarial model calls

The current risks being tested are deterministic authority violations. Therefore the first Gate 17.4 evaluation intentionally performs:

```text
model invocations:      0
capability executions:  0
AWS calls:              0
network calls:          0
third-party repo code:  0
```

A live model red-team run would measure model behavior but would not replace deterministic authorization/admission proof. It is not required to establish whether caller-controlled text can directly change code-owned authority.

### 3. Keep prompt-injection resistance structural

The knowledge-synthesis adversarial case injects hostile instructions into both the user question and retrieved evidence. The retained prompt contract must keep:

```text
trusted instructions
!= user question
!= retrieved evidence
```

The test does not claim that any model is universally injection-proof. It proves that the application does not serialize retrieved/user text into the trusted instruction field.

### 4. Keep tool and protocol abuse below execution authority

The suite attacks both pre-execution and interoperability boundaries:

- model-style capability proposals outside the admitted allowlist are denied;
- multi-agent specialization cannot widen the source-task capability set;
- MCP tool names cannot create dynamic tools or reinterpret a typed invocation;
- A2A reference data cannot add capability names or tool arguments;
- forged result hashes cannot become admitted execution evidence.

These preserve:

```text
model proposal != capability authorization
MCP transport/tool name != capability authority
A2A message/reference != business authority
transport success != result admission
```

### 5. Freeze amplification budgets in the same attacker-oriented surface

The suite also asserts retained hard limits:

```text
single-agent executions per call: 1
execution retries:                 0
adaptive execution fallbacks:     0
synthesis model calls:             1
single-agent task UTF-8 bytes:     2048
```

Attempts to enlarge task input or synthesis call count fail at deterministic construction time.

### 6. Run the suite in a dedicated least-privilege CI workflow

Retain:

```text
.github/workflows/adversarial-security-ci.yml
workflow: Adversarial Security CI
job/check: Adversarial authority boundaries
permissions: contents: read
```

The workflow uses the locked development environment and exact-SHA-pinned setup actions. It has no `id-token: write`, AWS credential step, `security-events: write`, repository write permission, or runtime deployment behavior.

The repository-wide `Security Hardening CI` verifier freezes this non-cloud authority boundary so later edits cannot silently turn adversarial testing into a privileged workflow.

## First measured result

Initial implementation head:

```text
d392e0ed610a24dd9ccedd5baf056863bbad4dc4
```

Measured run:

```text
workflow:      Adversarial Security CI
run:           34425331159 / #1
job:           102709241947
Ruff:          PASS
Pyright:       PASS / 0 errors
pytest:        PASS / 8 passed in 2.01s
GITHUB_TOKEN:  contents: read (+ platform metadata read)
```

Adjacent Gate 17 controls on the same head also succeeded:

```text
Repository security invariants  34425331118 / #21  SUCCESS
Dependency Review               34425331165 / #6   SUCCESS
CodeQL / Python                 34425331130 / #8   SUCCESS
```

No adversarial case exposed a business-logic gap requiring implementation remediation in this first slice. This means the tested retained boundaries behaved as specified; it does **not** prove universal safety.

## Permanent authority separations

```text
untrusted text != instruction authority
retrieved content != system/developer authority
model proposal != capability authorization
malformed tool request != best-effort execution
failed/forged capability result != admissible business result
MCP transport success != capability admission
A2A transport success != business/evidence truth
contradictory metadata != tolerated ambiguity
adversarial test success != proof of universal safety
```

## Alternatives rejected

### Ask an LLM to jailbreak OpsLens and treat a clean response as security proof

Rejected. A sampled model response is probabilistic evidence and cannot establish deterministic business authorization boundaries.

### Add generic prompt sanitization that removes suspicious words

Rejected. Keyword filtering is brittle and would confuse content classification with authority. The retained design keeps untrusted text structurally separated and verifies machine-readable outputs/authorization deterministically.

### Give the adversarial workflow AWS or deployment credentials for realism

Rejected. The tested contracts are repository-local and pre-runtime. Cloud authority would add attack surface without improving the evidence question.

### Rewrite existing business contracts before testing them

Rejected. Gate 17 is evidence-driven. The first suite passed against the retained implementation, so no speculative redesign is justified.

## Consequences

Positive:

- cross-cutting attacker-oriented regression evidence is now explicit;
- prompt/tool/protocol/result/cost boundaries are tested together against real code;
- the suite is deterministic, fast, offline, and suitable for recurring CI;
- no model or cloud cost is introduced;
- existing architecture remains simpler because no speculative remediation was required.

Trade-offs:

- eight cases are a bounded regression set, not a complete red-team program;
- structural prompt separation cannot guarantee the behavior of every future model;
- path-filtered adversarial CI is additive; `Repository security invariants` remains the universal protected-main check;
- future new capabilities/protocols must add their own adversarial cases deliberately.

## Cloud/runtime impact

```text
AWS mutations:          0
new IAM permissions:    0
new AWS services:       0
model invocations:      0
capability executions:  0
public runtime changes: 0
Inspector activation:   0
PR #89 changes:         0
```

## Evidence

```text
labs/phase-17-gate-17-4-adversarial-boundaries.md
labs/evidence/phase-17-gate-17-4-adversarial-boundaries-v1.json
Adversarial Security CI run 34425331159
```

Final exact PR-head CI is required after policy/evidence/document synchronization before Gate 17.4 can close.
