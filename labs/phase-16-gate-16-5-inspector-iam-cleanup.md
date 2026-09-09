# Phase 16 Gate 16.5 — Temporary Amazon Inspector IAM Teardown

_Date: 2026-09-09_

## Status

**COMPLETE — TEMPORARY DISCOVERY IAM REMOVED AND TERRAFORM CONVERGED.**

Gate 16.4 proved the dedicated read boundary with one measured `ListCoverage` / `ListFindings` experiment. ADR 0061 required that identity to be removed immediately after the bounded run unless a later retention decision explicitly justified standing authority. No such justification was observed.

## Source state

The cleanup desired state was protected-merged on:

```text
main SHA: 28f0194dc932569a40fc6b54e1cd8cd81aa690b2
PR:       #248
issue:    #247
```

The repository no longer contains:

```text
infra/bootstrap/github_inspector_discovery_role.tf
```

Runtime Exposure CI also requires that retained bootstrap Terraform contain neither `inspector2:` actions nor `OpsLensInspectorDiscoveryRole`.

## Human bootstrap cleanup

The reviewed plan was exactly:

```text
Plan: 0 to add, 0 to change, 2 to destroy.
```

Destroyed only:

```text
aws_iam_role_policy.github_actions_inspector_discovery
aws_iam_role.github_actions_inspector_discovery
```

No create, update, replacement, or unrelated destroy was present.

Apply result:

```text
Apply complete! Resources: 0 added, 0 changed, 2 destroyed.
```

## Terraform convergence

A fresh post-apply bootstrap plan returned:

```text
No changes. Your infrastructure matches the configuration.
```

This proves that the Terraform-managed bootstrap plane converged after teardown rather than merely accepting a successful delete operation.

## Independent IAM verification

The temporary role was queried independently after apply:

```text
OpsLensInspectorDiscoveryRole
 -> ABSENT
 -> NoSuchEntity
```

The shared deployment identity remained present:

```text
role:   OpsLensGitHubDeployRole
roleId: AROAXDEFCFNVTM36UV7S2
arn:    arn:aws:iam::487757851499:role/OpsLensGitHubDeployRole
```

Neither the Gate 16.4 create plan nor the Gate 16.5 destroy plan modified the shared role. The retained OpsLens bootstrap Terraform contains no `inspector2:` authority. The earlier Gate 16.2 shared-role experiment had also measured `AccessDeniedException` for `ListCoverage` before the temporary role was introduced.

The closeout claim is therefore deliberately scoped to the OpsLens-managed control plane:

```text
no standing Inspector authority in retained OpsLens Terraform
!=
claim that arbitrary out-of-band IAM state can never exist
```

## Retention outcome

```text
Inspector read-only adapter/contract:        RETAIN
Gate 16.4 zero-record evidence:              RETAIN
standing Inspector discovery IAM:            REMOVED
OpsLensGitHubDeployRole Inspector authority: NONE IN RETAINED OPSLENS TERRAFORM
Inspector activation/configuration:          DO NOT CREATE IN PHASE 16
repository/runtime automatic correlation:    DO NOT CREATE
runtime-risk composite scoring:              DO NOT CREATE
model synthesis over Inspector evidence:     DO NOT CREATE
```

The successful reads returned zero coverage and zero findings for the current dev account. That is valid current-account evidence; it is not interpreted as proof that Inspector is globally disabled, unsupported, or without future value.

## Preserved authority boundaries

```text
Repository Risk != Runtime Exposure
AWS authentication != Inspector read authorization
Inspector API success != runtime evidence presence
Inspector coverage != vulnerability finding
Inspector finding != repository finding
Inspector resource presence != network exposure
Inspector evidence != model authority
runtime evidence correlation != capability authorization
```

No Inspector activation, ECR/EC2/Lambda scan-mode change, EventBridge integration, repository/runtime correlation, model invocation, or agent capability execution occurred during teardown.

## Evidence

```text
labs/evidence/phase-16-gate-16-5-inspector-iam-cleanup-postapply-v1.json
```

The supplied human-bootstrap terminal transcript has SHA-256:

```text
404e2b11d4839eb4cfc7d388ccd06f4acd8f60d09e587779d0634cfa58d93ab9
```

## Exit checklist

```text
[x] temporary IAM removed from Terraform desired state
[x] exact-head Runtime Exposure / Terraform / AgentCore CI green before cleanup merge
[x] protected cleanup merge
[x] human plan = 0 add / 0 change / 2 destroy
[x] only temporary role/policy destroyed
[x] apply = 0 added / 0 changed / 2 destroyed
[x] fresh post-apply plan = No changes
[x] temporary role independently returns NoSuchEntity
[x] shared OpsLensGitHubDeployRole remains present
[x] no Inspector authority retained in OpsLens bootstrap Terraform
[x] no Inspector activation/configuration changes
[x] PR #89 untouched
```
