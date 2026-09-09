# Phase 17 Gate 17.1 — Cross-cutting threat model and control-gap inventory

## Objective

Review the retained OpsLens platform as an attacker and operator would before changing runtime behavior or adding AWS services.

This gate separates:

```text
PROVEN_CONTROL
GAP
DEFERRED
NOT_APPLICABLE
```

and preserves missing evidence as missing evidence rather than silently promoting it to a vulnerability or a control.

## Source checkpoint

The review is bound to Phase 16 closeout `main`:

```text
f6fc614fbeaf7b3f294d7dba10c31e6f0e96313c
```

Issue:

```text
#250 — Phase 17 Gate 17.1 — build cross-cutting threat model and control-gap inventory
```

Canonical machine-readable evidence:

```text
labs/evidence/phase-17-gate-17-1-threat-model-v1.json
```

## Method

The review sampled repository implementation, infrastructure-as-code, workflow definitions, prior ADRs/lab evidence, current GitHub ruleset configuration, and current external guidance where it changes interpretation.

For every material claim the review distinguished:

```text
retained runtime behavior
historical experiment automation
business/evidence authority
protocol/framework acceptance
cloud authentication
capability authorization
missing repository-local evidence
```

The review deliberately did not infer platform/account settings that are not represented in observable repository or GitHub ruleset evidence.

## Review domains

```text
identity / IAM / GitHub OIDC trust
CI/CD workflow permissions and action pinning
artifact / release / dependency integrity
third-party repository acquisition and parser abuse
semantic planning / prompt injection
retrieved-content instruction resistance
agent proposal / deterministic authorization / execution binding
MCP raw admission / capability bridge / result projection
A2A raw admission / reference identity / task-result admission
AgentCore optional runtime and historical workflow assumptions
Amazon Inspector runtime-evidence boundary
secrets / credentials / sensitive-data handling
telemetry content minimization and leakage
failure recovery / rollback / kill switch
rate limiting / quotas / denial-of-wallet exposure
security-documentation drift
```

## High-priority gaps

### SEC17-CICD-001 — main merge authority does not require CI

The active `Protect main` ruleset proves several strong repository controls:

```text
PR required
review-thread resolution required
squash-only merge
linear history
deletion protection
non-fast-forward protection
no bypass actors
```

The same ruleset has no `required_status_checks` rule.

OpsLens already relies operationally on exact-head CI before merge, so the gap is not missing CI execution; it is missing enforcement that the CI must succeed before `main` accepts the PR.

### SEC17-IAM-002 — plan-only EPSS workflows receive write-capable authority

Both historical EPSS planning workflows configure `OpsLensEpssHistoryCoordinatorRole` before selecting the read-only plan path or mutating execution path.

The coordinator role can perform bounded S3 writes and invoke the historical transformer Lambda. The full backfill also requests a 21,600-second session for both planning and execution.

This violates the narrow security expectation:

```text
plan-only path -> no write/invoke authority
long STS session -> actual bounded execution only
```

### SEC17-IAM-003 — historical AgentCore workflow is not inert

AgentCore-specific standing experiment IAM was removed in Phase 14. However, the retained historical runtime workflow still assumes `OpsLensGitHubDeployRole` and can perform mutations already available to that shared deployment role before later AgentCore-specific authorization is needed.

Therefore historical reproducibility alone does not prove zero mutation authority.

## Medium-priority gaps

### SEC17-CICD-003 — persisted checkout credentials

`actions/checkout` is commit-SHA pinned, but existing workflow checkouts generally do not set:

```yaml
persist-credentials: false
```

The GitHub token permissions are already mostly `contents: read`, which limits impact, but ambient credentials remain unnecessary in jobs that do not perform authenticated git operations after checkout.

### SEC17-SUPPLY-001 — no repository-local continuous dependency security automation observed

The repository has a locked dependency graph and deterministic Lambda packaging, but Gate 17.1 did not observe:

```text
.github/dependabot.yml
dependency-review-action
CodeQL workflow
active pip-audit workflow
```

Historical `pip-audit` evidence is not current continuous coverage. Platform security settings outside repository content were not observable and are not claimed absent.

## Low-priority gap

### SEC17-DOC-001 — architecture header drift

`docs/architecture.md` and `docs/architecture.pt-br.md` still present Phase 9 as the accumulated baseline and Phase 10 as next.

`docs/current-state.md`, `docs/roadmap.md`, ADRs, and immutable gate evidence remain authoritative through Phase 16, so this is documentation/control-plane drift rather than a runtime-control failure.

## Proven controls

The review also froze important non-gaps so later security work does not recreate working controls.

### GitHub OIDC

Observed OIDC trust uses:

```text
aud = sts.amazonaws.com
sub = repo:brunovicco@38844444/opslens@1333092779:ref:refs/heads/main
```

for the standing GitHub deployment/evidence identities reviewed.

### Workflow supply chain

Sampled external Actions are full-commit-SHA pinned. No `pull_request_target` or `workflow_run` trigger was found in the retained workflows.

### Public request and repository acquisition

The public analysis request boundary includes strict size, UTF-8, duplicate-key, exact-key-set, host, path, port, query/fragment, and ref validation.

The GitHub acquisition adapter uses a fixed HTTPS API host, GET-only requests, bounded time/response sizes, no redirect behavior, no adaptive transport retries, and exact immutable commit binding before `uv.lock` acquisition.

### Prompt and retrieval trust

Semantic planning receives bounded metadata instead of raw repository content. Retrieved evidence remains untrusted data and is serialized separately from trusted model instructions. Model outputs remain proposals or admitted explanatory claims, never structured vulnerability/risk authority.

### Agent execution

`authorize_agent_action(...)` verifies exact task binding and a code-owned capability allowlist. Execution then uses a closed typed executor set and validates downstream result identity before producing deterministic execution evidence.

### MCP and A2A

MCP retains raw exact-key validation before framework coercion and does not grant generic business-input authority.

A2A retains raw JSON duplicate-key/exact-key admission, reference-only resolution, and strict result admission. A2A protocol/task/artifact identity remains correlation metadata rather than OpsLens business/evidence authority.

### Telemetry and model-cost boundaries

Operational telemetry is content-minimized and uses content-addressed identifiers. Model paths have explicit token budgets and bounded call/retry behavior. No public HTTP runtime exists, so client rate limits, WAF, tenant isolation, and production edge-abuse controls are currently `NOT_APPLICABLE`, not silently assumed implemented.

## Decision

```text
Gate 17.1: COMPLETE when exact-head CI and protected merge succeed
next gate: 17.2 — CI/CD and workflow authority hardening
```

Authorized Gate 17.2 repository scope:

```text
full-SHA external-action invariant
privileged workflow-trigger negative guard
checkout persist-credentials:false where authenticated git is unnecessary
EPSS plan-only no-write/no-invoke authority
21,600-second coordinator session only on real bounded execution
historical AgentCore workflow disabled by default until dedicated minimum authority is recreated
exact required CI status contexts defined for main
```

Human/platform boundary:

```text
change GitHub main ruleset required status checks
```

Not authorized:

```text
AWS IAM mutation
new AWS service
public runtime
Inspector reactivation
dependency-platform enablement in Gate 17.2
PR #89 modification
```

## Security invariants added by this gate

```text
security control name != proven enforcement
historical workflow != inert workflow
plan-only intent != write-authority requirement
CI evidence != enforced merge gate
missing repository evidence != proof of disabled platform control
```

## Cost and mutation evidence

```text
AWS mutations:          0
new IAM:                0
model invocations:      0
capability executions:  0
new AWS services:       0
PR #89 changes:         0
```

## AIP-C01 learning checkpoint

This gate reinforces a professional security posture for GenAI systems: model/agent controls are only one part of the attack surface. CI identity, workflow authority, artifact provenance, deterministic authorization, prompt/retrieval trust separation, credential lifetime, and operational boundaries all participate in the system's effective security posture.

The key architectural lesson is that least privilege must apply to **each execution path**, not merely to named roles or nominal workflow intent.

## References

- `docs/adr/0064-evidence-first-security-hardening-priorities.md`
- `labs/evidence/phase-17-gate-17-1-threat-model-v1.json`
- GitHub Actions secure use: <https://docs.github.com/en/actions/reference/security/secure-use>
- actions/checkout input defaults: <https://github.com/actions/checkout/blob/main/action.yml>
- AWS IAM OIDC guidance: <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html>
- AWS Generative AI Lens security guidance: <https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec05-bp01.html>
- OWASP GenAI Security Project: <https://genai.owasp.org/initiatives/top-10-for-llm-and-genai/>
