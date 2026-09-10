# ADR 0065 — CI/CD and workflow authority hardening

- Status: Accepted
- Date: 2026-09-09
- Phase: 17 — Security Hardening
- Gate: 17.2 — CI/CD and workflow authority hardening
- Issue: #252
- PR: #255

## Context

Gate 17.1 established that most OpsLens business and model boundaries were already fail-closed, but it also found concrete control-plane authority gaps in GitHub Actions and protected-main enforcement.

The highest-priority findings were:

```text
SEC17-CICD-001  protected main had no required CI status context
SEC17-IAM-002   EPSS plan-only workflows assumed write/invoke-capable authority
SEC17-IAM-003   a historical AgentCore experiment could still use the shared deploy role
SEC17-CICD-003  checkout credentials persisted where authenticated git was unnecessary
```

The objective of Gate 17.2 is to remove those authority mismatches without adding AWS permissions, services, runtime behavior, or dependency-scanning scope.

## Decision

### 1. One universal repository security context

`Security Hardening CI` runs on every pull request without path filtering. Its stable job/check context is:

```text
Repository security invariants
```

The workflow has only `contents: read` and performs repository-local verification. This is the single context authorized for later protected-main required-status enforcement.

The GitHub ruleset change itself remains a human/platform administration boundary. CI success is evidence; it is not merge enforcement until the ruleset requires the context.

### 2. Repository-wide workflow verifier

`scripts/verify_workflow_security.py` is the deterministic policy authority for the first workflow-security baseline. It fails closed if it observes:

- an external GitHub Action not pinned to a full 40-hex commit SHA;
- `actions/checkout` without explicit `persist-credentials: false`;
- `pull_request_target` or `workflow_run` triggers;
- `write-all` or `contents: write` workflow authority;
- reactivation of the retired AgentCore experiment's cloud/mutation path;
- drift in the EPSS plan/execute identity separation;
- drift in retained GitHub OIDC audience or immutable main-branch subject conditions.

This verifier does not claim that a syntactically valid workflow is secure in every dimension. It freezes the evidence-backed Gate 17.2 invariants only.

### 3. Checkout credentials are not retained

Every current `actions/checkout` use explicitly sets:

```yaml
with:
  persist-credentials: false
```

No current workflow requires authenticated Git mutation after checkout. A future exception requires a separate evidence-backed decision.

### 4. EPSS plan and execution identities are separated

Plan-only historical EPSS paths still require bounded AWS reads because the plan resolves existing S3 evidence. They now use the already-existing read-only role:

```text
OpsLensEpssHistoryEvidenceRole
```

Actual mutation/execution paths use the existing bounded coordinator role only when `inputs.execute == true`:

```text
OpsLensEpssHistoryCoordinatorRole
```

The 21,600-second STS session is retained only for the real 1,939-snapshot full-backfill execution path. It is not requested for plan-only execution or the seven-snapshot canary.

No IAM policy or role is created, deleted, or widened by Gate 17.2.

### 5. Historical AgentCore mutation automation is retired

The Phase 14 experiment workflow remains as historical/re-entry evidence but is intentionally inert. It has:

```text
contents: read
no id-token: write
no AWS credential configuration
no OpsLensGitHubDeployRole reference
no Terraform apply
no AgentCore invocation
no artifact upload
```

A future AgentCore experiment must first define a new architecture/network decision and a dedicated minimum principal. Historical experiment code is not authority to reuse the shared deploy role.

## Authority model

Gate 17.2 adds these permanent control-plane separations:

```text
CI evidence != enforced merge gate
plan-only intent != write authority
historical workflow != current execution authority
repository checkout != persisted Git credential requirement
OIDC authentication != authorization to reuse a shared deployment role
```

## Alternatives rejected

### Require every existing CI workflow as a protected-main check

Rejected. Many existing workflows are path-filtered, so making them individually mandatory can create missing-check/deadlock behavior on unrelated pull requests. One always-running security context provides a stable enforcement target while specialized workflows remain additive quality gates.

### Keep one write-capable EPSS identity because execution is manually confirmed

Rejected. Manual confirmation does not justify granting mutation authority to plan-only runs. Authority must follow the actual branch of execution.

### Keep the old AgentCore workflow because its experiment-specific IAM is gone

Rejected. The historical workflow still referenced a broader shared deployment principal. Removal of one experiment role does not make unrelated standing authority safe to inherit.

### Add Dependabot, CodeQL, or new AWS security services in this gate

Rejected. Gate 17.2 fixes previously evidenced workflow-authority gaps only. Dependency/code-scanning hardening remains a separate later decision.

## Consequences

Positive:

- one stable, always-running security status context exists for protected-main enforcement;
- workflow security invariants are repository-wide and deterministic;
- plan-only EPSS work no longer receives write/invoke authority;
- long-lived coordinator credentials exist only on the long execution branch;
- historical AgentCore automation cannot silently regain shared deployment authority;
- checkout tokens are not persisted into local Git configuration;
- no AWS mutation or IAM widening is required.

Trade-offs:

- the universal verifier becomes an important control-plane component and must stay intentionally small and reviewable;
- future workflows must satisfy the frozen policy or explicitly change it through architecture evidence;
- protected-main enforcement is incomplete until a human adds `Repository security invariants` to the active ruleset.

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
labs/phase-17-gate-17-2-workflow-authority-hardening.md
labs/evidence/phase-17-gate-17-2-workflow-authority-hardening-v1.json
Security Hardening CI run 34420383193
```

The implementation-validation run succeeded on exact implementation head `dd2b5cea01009d8acbfe73f135fc5a7c8380aba7`. Final PR-head CI is still required after documentation/evidence synchronization.
