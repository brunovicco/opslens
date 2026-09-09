# ADR 0062 — Retain the Inspector read contract without standing IAM or scan activation

- Status: Accepted
- Date: 2026-09-09

## Context

Phase 16 separates repository risk from runtime exposure and treats Amazon Inspector as an independent evidence authority.

Gate 16.2 first attempted `ListCoverage` and `ListFindings` through the existing `OpsLensGitHubDeployRole`. Authentication succeeded, but the first Inspector read was denied. Gate 16.3 therefore rejected widening the shared deployment role and accepted a dedicated temporary read-only identity for exactly one experiment.

Gate 16.4 implemented and human-applied that temporary identity, then ran one main-only discovery using:

```text
OpsLensInspectorDiscoveryRole
 -> inspector2:ListCoverage
 -> inspector2:ListFindings
 -> Resource = "*"
 -> aws:RequestedRegion == us-east-1
```

The workflow requested a 900-second role session. Both Inspector calls succeeded with zero SDK retries and zero AWS mutation, model invocation, or capability execution.

Measured result:

```text
ListCoverage: SUCCESS / 1 page / 0 records
ListFindings: SUCCESS / 1 page / 0 records
```

No coverage resource type, finding resource type, finding type, or scan status was observed.

## Decision

Retain the bounded Inspector read-only adapter, evidence contract, test coverage, and measured evidence, but do not retain standing Inspector discovery IAM after the completed experiment.

Do not activate or reconfigure Amazon Inspector in Phase 16 merely to populate the dev account with evidence.

Do not introduce repository/runtime automatic correlation, runtime-risk composite scoring, model synthesis over Inspector evidence, or agent capability execution when the current account produced no Inspector evidence to correlate.

The temporary IAM role and policy must be removed after the measured experiment and independently verified absent.

## Rationale

The experiment established two different facts that must not be conflated:

```text
minimum IAM boundary works
!=
current account contains useful Inspector evidence
```

The dedicated role proved that the selected read APIs can be called without widening the general deployment role. The zero-record result then showed that the current dev account does not presently provide useful coverage/finding evidence through those calls.

Creating scan configuration, enabling service coverage, or changing runtime resources solely to manufacture portfolio data would cross the boundary frozen by Gate 16.1. It would turn an evidence-discovery phase into infrastructure modification without an operational requirement.

The reusable engineering value is therefore in the source-authority separation, deterministic adapter, fail-closed behavior, content-minimized evidence, IAM isolation, and measured lifecycle—not in forcing non-empty findings.

## Retained state

```text
Inspector read-only adapter/contract:        RETAIN
content-minimized deterministic evidence:    RETAIN
Gate 16.2 AccessDenied evidence:             RETAIN
Gate 16.4 successful zero-record evidence:   RETAIN
standing Inspector discovery IAM:            DO NOT RETAIN / REMOVE
OpsLensGitHubDeployRole Inspector access:     NONE
Inspector activation/configuration change:   DO NOT CREATE IN PHASE 16
repository/runtime automatic correlation:    DO NOT CREATE
runtime-risk composite scoring:              DO NOT CREATE
model synthesis over Inspector evidence:     DO NOT CREATE
```

## Interpretation boundaries

```text
Inspector API success != runtime evidence presence
zero coverage != proof Inspector is disabled
zero findings != proof no runtime vulnerability exists
Inspector finding != repository finding
Inspector resource presence != network exposure
Inspector PACKAGE_VULNERABILITY != NETWORK_REACHABILITY
Inspector evidence != model authority
runtime evidence correlation != capability authorization
```

The measured zero result is scoped to the exact account, region, time, APIs, and role session used by Gate 16.4.

## Cleanup requirement

The temporary role existed only for one bounded experiment. After this decision:

1. remove its Terraform desired state;
2. protected-merge the cleanup;
3. human-plan the bootstrap change from merged `main`;
4. require only the temporary role/policy destruction;
5. apply the saved plan;
6. require a fresh convergent post-apply plan;
7. independently prove `OpsLensInspectorDiscoveryRole` is absent;
8. independently preserve that `OpsLensGitHubDeployRole` remains present without Inspector permissions.

Until teardown is verified, Phase 16 is not closed.

## Consequences

Positive:

- shared deployment authority remains free of Inspector permissions;
- experimental IAM does not become standing ambient authority;
- Phase 16 preserves a reusable read/evidence implementation without making unsupported production-runtime claims;
- empty discovery is treated as evidence rather than as pressure to mutate AWS configuration;
- the project retains a clear re-entry path if a future concrete runtime use case justifies Inspector evidence.

Trade-off:

- OpsLens does not demonstrate non-empty Inspector findings in the current dev account;
- the retained discovery workflow becomes intentionally non-operational after IAM teardown until a future evidence-backed re-entry recreates minimum authority.

## Evidence

```text
labs/phase-16-gate-16-4-inspector-readonly-rerun.md
labs/evidence/phase-16-gate-16-4-inspector-readonly-rerun-v1.json
GitHub Actions run 34414116549
GitHub Actions artifact 10128371987
```

PR #89 is outside this decision and remains untouched.
