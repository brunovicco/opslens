# Phase 17 Gate 17.3 — dependency and code-scanning hardening closeout

## Final retained state

Gate 17.3 is retained around two bounded GitHub-native engineering signals:

```text
Dependency Review:  RETAIN
Python CodeQL:      RETAIN
AWS authority:      NONE ADDED
business authority: UNCHANGED
```

The implementation was squash-merged through PR #261 at:

```text
b3f4a11df1a826c850cc16f1a4e0dd44efb3edd3
```

Final exact PR-head validation on `f9ee70d772d28987c45008b723e3efc07b65680e`:

```text
Repository security invariants
  run:        34424002745 / #19
  job:        102705238305
  conclusion: SUCCESS

Dependency Review
  run:        34424002767 / #4
  job:        102705238338
  conclusion: SUCCESS

CodeQL / Python
  run:        34424003077 / #4
  job:        102705239118
  conclusion: SUCCESS
```

## Platform prerequisite evidence

The first Dependency Review execution failed because the repository Dependency graph was disabled:

```text
run:        34423137362 / #1
attempt:    1
job:        102702675325
conclusion: FAILURE
```

The job had only repository read authority. No permission widening was justified or performed.

A human enabled the repository Dependency graph, then the exact same run was retried:

```text
attempt:    2
job:        102704585117
conclusion: SUCCESS
```

Retained separation:

```text
scanner platform prerequisite != scanner permission requirement
```

## Security meaning

The scanners are engineering evidence sources only:

```text
dependency finding != vulnerability applicability authority
code-scanning alert != runtime exploitability truth
security scan success != absence of vulnerabilities
scanner output != model authority
GitHub security permission != AWS authority
```

OpsLens deterministic vulnerability applicability, Risk Policy v1, runtime-exposure evidence, model boundaries, and capability authorization remain unchanged.

## Retained scanner contracts

### Dependency Review

```text
action:              actions/dependency-review-action
release:             v5.0.0
exact SHA:           a1d282b36b6f3519aa1f3fc636f609c47dddb294
trigger:             pull_request
fail-on-severity:    high
permission:          contents: read
OIDC/AWS authority:  none
```

### CodeQL

```text
action:              github/codeql-action
release line:        v4.38.0
exact SHA:           b96794f015dfd88f77b49b1c93e0fa7110f94c63
language:            python
triggers:            pull_request / main push / weekly / manual
permissions:         contents: read + security-events: write
OIDC/AWS authority:  none
```

## Deferred

```text
Dependabot version-update automation: DEFER
additional continuous pip-audit:      DEFER
broad dependency upgrades:            NOT AUTHORIZED
```

## Impact

```text
AWS mutations:          0
new IAM permissions:    0
new AWS services:       0
model invocations:      0
capability executions:  0
public runtime changes: 0
PR #89 changes:         0
```

Canonical evidence:

```text
labs/evidence/phase-17-gate-17-3-dependency-code-scanning-v1.json
labs/evidence/phase-17-gate-17-3-closeout-v1.json
```
