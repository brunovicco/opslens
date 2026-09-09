# Phase 16 — Gate 16.4: Temporary Inspector Read Role and Measured Rerun

_Date: 2026-09-09_

## Status

**COMPLETE — MINIMUM READ BOUNDARY WORKED; CURRENT DEV ACCOUNT RETURNED ZERO COVERAGE AND ZERO FINDINGS.**

```text
issue:                       #245
implementation PR:           #246
implementation merge:        bc3c79b4168ffbaa1374b50e60bb8a6d416a14c2
workflow:                    Inspector Read-Only Discovery
run:                         34414116549 / #2
job:                         102675000098
workflow conclusion:         SUCCESS
experiment result:           SUCCESS
```

## Bootstrap result

The human bootstrap plane applied the exact Gate 16.3 IAM contract after reviewing a saved Terraform plan:

```text
plan:   2 add / 0 change / 0 destroy
apply:  2 added / 0 changed / 0 destroyed
```

Created exactly:

```text
aws_iam_role.github_actions_inspector_discovery
aws_iam_role_policy.github_actions_inspector_discovery
```

The resulting principal was:

```text
role:                       OpsLensInspectorDiscoveryRole
policy:                     OpsLensInspectorDiscoveryReadOnly
OIDC audience:              sts.amazonaws.com
OIDC subject:               repo:brunovicco@38844444/opslens@1333092779:ref:refs/heads/main
allowed actions:            inspector2:ListCoverage
                            inspector2:ListFindings
resource:                   *
region condition:           aws:RequestedRegion == us-east-1
role max session duration:  3600 seconds
workflow requested session: 900 seconds
```

`OpsLensGitHubDeployRole` was not modified.

## Measured discovery

GitHub OIDC successfully assumed the dedicated temporary role. The bounded client then called only the two previously authorized Inspector read APIs.

```text
client elapsed:              465.877452 ms
ListCoverage:                SUCCESS
coverage pages:              1
coverage records:            0
coverage SDK retries:        0
ListFindings:                SUCCESS
finding pages:               1
finding records:             0
finding SDK retries:         0
coverage resource types:     none observed
finding resource types:      none observed
finding types:               none observed
scan status counts:          none observed
AWS mutations:               0
new IAM during discovery:    0
model invocations:           0
capability executions:       0
```

Both empty business-content pages produced the same deterministic canonical hash:

```text
4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
```

Actions artifact:

```text
artifact id:      10128371987
artifact name:    phase-16-gate-16-4-inspector-readonly-34414116549
size:             579 bytes
digest:           sha256:a6f917e62124b4c604891e1a83db9874e3ef34696110dfaead1af16d45a03365
retention:        14 days
```

## Interpretation

The rerun answers the IAM question positively:

```text
dedicated minimum read identity
 -> sufficient to call ListCoverage
 -> sufficient to call ListFindings
```

It does **not** establish useful runtime evidence for the current dev account:

```text
runtime coverage records: 0
Inspector findings:       0
```

That zero result is intentionally narrow evidence. It does not prove that Amazon Inspector is disabled, unsupported, or without value in another deployment. It also does not authorize changing Inspector configuration merely to create demo data.

The authority boundary remains:

```text
Inspector API success != runtime evidence presence
zero Inspector records != proof of service disablement
Inspector evidence != repository evidence
runtime evidence correlation != capability authorization
```

## Retention consequence

Gate 16.4 completed the only experiment authorized for the temporary role. Therefore the role has no remaining standing purpose.

```text
Inspector read-only adapter/contract:        RETAIN
measured zero-evidence result:               RETAIN
standing Inspector discovery IAM:            REMOVE
OpsLensGitHubDeployRole Inspector access:     NONE
Inspector activation/config change:          DO NOT CREATE IN PHASE 16
repository/runtime automatic correlation:    DO NOT CREATE
runtime-risk composite scoring:              DO NOT CREATE
model synthesis over Inspector evidence:     DO NOT CREATE
```

The next step is mandatory teardown, not another read experiment.

## Next gate

Phase 16 Gate 16.5 removes the temporary role/policy from Terraform desired state, protected-merges that cleanup, then requires a human bootstrap destroy plan/apply, post-apply convergence, and independent role absence verification before Phase 16 closes.

## Evidence

```text
labs/evidence/phase-16-gate-16-4-inspector-readonly-rerun-v1.json
GitHub Actions run 34414116549
GitHub Actions artifact 10128371987
```

PR #89 / `feat/governed-gateway-semantic-planner` remains untouched.
