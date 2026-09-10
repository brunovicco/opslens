# Phase 17 — Gate 17.4 Closeout

_Date: 2026-09-10_

## Status

**COMPLETE / IMPLEMENTATION MERGED / DOCUMENTATION SYNC IN THIS CLOSEOUT SLICE.**

Issue: #263  
Implementation PR: #264  
ADR: `docs/adr/0067-bounded-adversarial-authority-regression-suite.md`

## Retained implementation

Gate 17.4 added one explicit attacker-oriented regression layer over already-retained OpsLens authority boundaries.

```text
tests/security_hardening/test_adversarial_boundaries.py
.github/workflows/adversarial-security-ci.yml
```

The suite contains eight deterministic cases across seven threat classes:

```text
ADV17-PUBLIC
ADV17-PROMPT
ADV17-TOOL
ADV17-RESULT
ADV17-MCP
ADV17-A2A
ADV17-COST
```

No first-slice case exposed a business-logic gap requiring remediation.

## Final implementation validation

Exact implementation PR head:

```text
60010d4fcb5d6142c9748bbf764fb074dc3a4dc8
```

Exact-head CI:

```text
Adversarial Security CI          34426092786 / #5  / SUCCESS
Repository security invariants   34426092824 / #25 / SUCCESS
Dependency Review                34426092798 / #10 / SUCCESS
CodeQL / Python                  34426092795 / #12 / SUCCESS
```

Protected squash merge:

```text
PR #264 -> cfad2680ca9e1977c754977ea58f9ab8865601dd
```

The merge commit was verified on authoritative `main`.

## Retention decision

```text
adversarial boundary regression suite:        RETAIN
Adversarial Security CI:                      RETAIN
least-privilege workflow verifier coverage:   RETAIN
live model jailbreak as authority proof:      DO NOT USE
new AWS/model/tool authority from Gate 17.4:  NOT AUTHORIZED
business-logic redesign:                      NOT REQUIRED BY OBSERVED EVIDENCE
```

## What the gate proved

The tested implementation preserved the following authority separations:

```text
untrusted text != instruction authority
retrieved content != system/developer authority
model proposal != capability authorization
malformed tool request != best-effort execution
failed/forged capability result != admissible business result
MCP transport success != capability admission
A2A transport success != business/evidence truth
contradictory metadata != tolerated ambiguity
```

The prompt-injection test is intentionally structural. Hostile user/retrieved text remains outside the frozen trusted instruction field. This is application-boundary evidence, not a universal guarantee about every current or future model.

## Cost/amplification result

The retained code-owned budgets remain bounded:

```text
single-agent task UTF-8 bytes:     2048
single-agent executions per call: 1
execution retries:                 0
adaptive execution fallbacks:     0
synthesis model calls:             1
```

No cloud or model execution was needed to test these boundaries.

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

## Canonical evidence

```text
docs/adr/0067-bounded-adversarial-authority-regression-suite.md
labs/phase-17-gate-17-4-adversarial-boundaries.md
labs/evidence/phase-17-gate-17-4-adversarial-boundaries-v1.json
labs/phase-17-gate-17-4-closeout.md
labs/evidence/phase-17-gate-17-4-closeout-v1.json
```

## Next

Proceed to **Gate 17.5 — sensitive-data / logging / telemetry hardening**.

That gate should inspect retained observability and failure logging for secrets, user/source text, provider payloads, protocol data, and high-cardinality identifiers before authorizing new telemetry functionality.

The next slice remains evidence-driven: a logging or data-handling control should be changed only when a concrete retained path shows an exposure or ambiguity.

PR #89 / `feat/governed-gateway-semantic-planner` remains out of scope and untouched.
