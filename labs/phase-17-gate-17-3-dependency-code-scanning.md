# Phase 17 Gate 17.3 — dependency and code-scanning hardening

## Goal

Close the Gate 17.1 continuous dependency/code-security gap with the smallest repository-native scanner surface that preserves Gate 17.2 workflow authority.

## Source state

```text
source main SHA:    c39984fe2f9832710350ae5939e34898661bb337
issue:              #256
language:           Python
lock evidence:      uv.lock retained
AWS mutation:       not authorized
PR #89:             out of scope
```

Gate 17.2 is already enforced by the active `Protect main` ruleset through the stable required status context:

```text
Repository security invariants
```

## Selected controls

### Dependency Review

```text
scope:               pull requests
source:              actions/dependency-review-action
release:             v5.0.0
exact SHA:           a1d282b36b6f3519aa1f3fc636f609c47dddb294
failure threshold:   HIGH
workflow permission: contents: read
OIDC/AWS authority:  none
```

The action is intended to detect newly introduced vulnerable dependencies in the pull-request dependency diff. Its result is an engineering merge signal only.

### CodeQL

```text
scope:               Python
source:              github/codeql-action
release line:        v4.38.0
exact SHA:           b96794f015dfd88f77b49b1c93e0fa7110f94c63
triggers:            pull_request / main push / weekly / manual
permissions:         contents: read + security-events: write
OIDC/AWS authority:  none
```

`security-events: write` is admitted only for the CodeQL workflow so the official action can publish code-scanning results. It does not imply repository-content write authority and does not create AWS authority.

## Repository policy integration

Gate 17.2 already made the repository workflow verifier mandatory for protected main. Gate 17.3 extends that verifier so the scanner definitions themselves are continuously checked for:

```text
full action SHA pins
checkout persist-credentials:false
expected scanner triggers
expected minimum permissions
no id-token:write
no AWS credential configuration
no role-to-assume
no unrelated repository write permission
```

## Authority separations

```text
dependency finding != vulnerability applicability authority
code-scanning alert != runtime exploitability truth
security scan success != absence of vulnerabilities
scanner output != model authority
GitHub security permission != AWS authority
```

A scanner can produce a useful finding without changing OpsLens repository-risk truth, and a clean scanner run cannot prove the absence of every vulnerability.

## Deferred controls

```text
Dependabot version-update automation: DEFER
additional continuous pip-audit:      DEFER
broad dependency upgrades:            NOT AUTHORIZED
```

The purpose of this gate is to establish two attributable signals before adding update-policy or duplicate-audit complexity.

## Exit criteria

Gate 17.3 closes only after an exact PR head proves:

```text
Repository security invariants: PASS
Dependency Review:              understood PASS/failure state
CodeQL / Python:                understood PASS/failure state
AWS/IAM mutations:              0
PR #89 changes:                 0
protected squash merge:         complete
```

If a scanner is blocked by GitHub platform configuration, the result must be recorded as a platform boundary rather than worked around by widening permissions.

Canonical evidence:

```text
labs/evidence/phase-17-gate-17-3-dependency-code-scanning-v1.json
```
