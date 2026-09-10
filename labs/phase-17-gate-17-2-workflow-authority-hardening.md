# Phase 17 Gate 17.2 — CI/CD and workflow authority hardening

## Scope

Gate 17.2 implements only the CI/CD and workflow-authority slice authorized by Gate 17.1.

```text
issue:                         #252
PR:                            #255
source main:                   8e0bfef5d53b1791af4ea876ddde5b451ed85553
implementation validation:    dd2b5cea01009d8acbfe73f135fc5a7c8380aba7
AWS mutations:                 0
new IAM permissions:           0
new AWS services:              0
PR #89 changes:                0
```

## 1. Universal merge-security evidence

`Security Hardening CI` now runs for every pull request and exposes exactly one stable job/check name intended for protected-main enforcement:

```text
Repository security invariants
```

Implementation validation:

```text
workflow run:  34420383193 / #12
head SHA:      dd2b5cea01009d8acbfe73f135fc5a7c8380aba7
conclusion:    SUCCESS
```

The active `Protect main` ruleset did not yet require this context when Gate 17.2 implementation was built. Adding it is deliberately deferred to a human/platform-administration step after protected merge.

## 2. Repository-wide workflow policy

`scripts/verify_workflow_security.py` checks all current workflow YAML files and fails closed on:

```text
external action without full 40-hex SHA
checkout without persist-credentials:false
pull_request_target
workflow_run
write-all
contents: write
retired AgentCore cloud/mutation fragments
EPSS plan/execute role-binding drift
GitHub OIDC aud/sub drift
```

The verifier reports all observed drift in one run so a failure is diagnosable without repeatedly weakening the policy.

## 3. Checkout credential hardening

Every current `actions/checkout` use explicitly disables credential persistence:

```yaml
with:
  persist-credentials: false
```

This reduces the lifetime/surface of the GitHub credential made available to a job and removes authority that current workflows do not need after source checkout.

## 4. EPSS authority split

### Plan-only

Both historical EPSS canary and full-backfill plan paths use:

```text
OpsLensEpssHistoryEvidenceRole
```

The role already exists and is read-only over the bounded EPSS evidence prefixes required by planning.

### Execute

Only `inputs.execute == true` receives:

```text
OpsLensEpssHistoryCoordinatorRole
```

The coordinator can perform the exact bounded S3/Lambda operations required by the historical execution contract.

### Session duration

```text
canary plan:           no coordinator session
canary execute:        coordinator / default bounded session
full backfill plan:    no coordinator session
full backfill execute: coordinator / 21600 seconds
```

The six-hour session exists only where the measured operation may actually need six hours.

## 5. AgentCore historical workflow retirement

The old Phase 14 mutating workflow is no longer a dormant path to `OpsLensGitHubDeployRole`.

Current historical guard:

```text
manual dispatch only
contents: read
no OIDC token permission
no AWS credential action
no shared deploy role
no Terraform apply
no AgentCore runtime invocation
always exits non-zero with AGENTCORE_RUNTIME_EXPERIMENT_RETIRED
```

A future experiment requires a fresh architecture/network/IAM decision and a dedicated principal.

## 6. What this gate does not prove

Gate 17.2 does not claim:

- that all dependency vulnerabilities are continuously detected;
- that CodeQL or dependency review is enabled;
- that every GitHub repository/account security setting is observable from code;
- that CI currently blocks merges before the ruleset is changed;
- that AgentCore can never be reintroduced;
- that read-only AWS credentials are equivalent to zero AWS authority.

These distinctions keep missing evidence separate from actual implementation gaps.

## 7. Human/platform boundary after merge

After Gate 17.2 is merged and the exact final PR head is green, update active ruleset `Protect main` (id `20873628`) to require:

```text
Repository security invariants
```

Then independently verify that the ruleset reports this required status context. Until that proof exists:

```text
Security Hardening CI success = evidence
Security Hardening CI success != enforced merge gate
```

## AIP-C01 learning checkpoint

This gate illustrates least privilege as a runtime/control-plane property rather than only an IAM document property: identities are selected at the branch where authority is actually needed, long sessions are constrained to the long-running execution branch, historical automation loses inherited authority after its experiment closes, and CI evidence is distinguished from enforcement. The same reasoning applies to agent tools and model execution: authentication and availability do not grant business authority.
