# ADR 0064 — Prioritize security hardening from a cross-cutting evidence inventory

- Status: Accepted
- Date: 2026-09-09
- Phase: 17 — Security Hardening
- Gate: 17.1 — Cross-cutting threat model and control-gap inventory
- Issue: #250

## Context

Phase 16 closed with the retained platform spanning AWS ingestion and analytics, deterministic repository/vulnerability/risk authority, bounded Bedrock reasoning and retrieval, content-minimized operational telemetry, typed agent capability authorization/execution, bounded offline MCP/A2A interoperability, optional historical AgentCore lab material, and a read-only Amazon Inspector evidence contract with no standing Inspector experiment IAM.

Security Hardening must not treat the existence of many controls as proof that the system is secure, nor treat every missing enterprise control as a present vulnerability. The first Phase 17 task is therefore to distinguish:

```text
proven control
actual residual gap
deferred control
not-applicable threat
missing evidence
```

before authorizing implementation work.

The canonical Gate 17.1 inventory is:

```text
labs/evidence/phase-17-gate-17-1-threat-model-v1.json
```

It is bound to Phase 16 closeout `main` SHA:

```text
f6fc614fbeaf7b3f294d7dba10c31e6f0e96313c
```

## Decision

Use the Gate 17.1 inventory as the authority for Phase 17 prioritization and authorize exactly one next repository slice:

```text
Gate 17.2 — CI/CD and workflow authority hardening
```

Gate 17.2 may harden only the repository/workflow boundaries evidenced by Gate 17.1. It does not authorize new AWS services, AWS IAM mutation, public runtime deployment, Inspector reactivation, dependency-platform rollout in the same slice, or changes to PR #89.

## Highest-priority observed gaps

### Main protection does not require CI

The active `Protect main` ruleset requires pull requests, squash-only merge, linear history, review-thread resolution, deletion protection, and non-fast-forward protection, with no bypass actors. It does **not** require any status check.

This is a real control-plane gap because OpsLens engineering decisions already rely on exact-head CI evidence before protected merge, while GitHub enforcement does not currently encode that invariant.

Gate 17.2 must define the exact required status contexts. Enabling those required checks remains a human/platform administration boundary.

### EPSS plan-only workflows assume write-capable authority

The historical EPSS canary/backfill workflows default to plan-only behavior but configure `OpsLensEpssHistoryCoordinatorRole` before branching on `execute`.

That role can write the bounded historical Bronze object and invoke the historical transformer Lambda. The full backfill also requests a 21,600-second STS session before knowing whether execution is requested.

Therefore:

```text
plan-only intent != write authority requirement
```

Gate 17.2 must remove write/invoke authority from plan-only paths and reserve any long session for the actual bounded execution path.

### Historical AgentCore workflow is not fully non-operational

Phase 14 removed standing AgentCore-specific experiment IAM, but the retained historical workflow can still assume `OpsLensGitHubDeployRole` and perform mutations that the shared deployment role already permits before any later AgentCore-specific authorization failure.

Therefore:

```text
historical workflow != inert workflow
removed feature-specific IAM != zero remaining mutation authority
```

Gate 17.2 must disable this historical mutating path by default and require any future AgentCore re-entry to recreate a dedicated minimum principal under a new explicit decision.

## Medium-priority observed gaps

Gate 17.1 also records:

- `actions/checkout` uses its default persisted credential behavior where no post-checkout authenticated git requirement has been proven;
- repository-local continuous dependency update/review/vulnerability-scanning configuration was not observed.

The checkout credential issue belongs in Gate 17.2. Dependency security is intentionally separated into a later gate so CI/workflow authority is hardened before new automation is added.

## Proven controls retained as non-gaps

Gate 17.1 verified that the following controls already exist and should not be rebuilt without new evidence:

- GitHub Actions AWS OIDC trust is constrained to `sts.amazonaws.com` and the immutable numeric repository/main subject;
- sampled external GitHub Actions are pinned to full commit SHAs;
- `pull_request_target` and `workflow_run` are not currently used;
- public repository request admission is bounded and rejects duplicate keys, unsupported fields, non-GitHub targets, URL ambiguity, and oversized payloads;
- public GitHub acquisition is fixed-host, GET-only, bounded, non-redirecting, and immutable-commit bound;
- semantic planning is proposal-only and cannot broaden deterministic evidence scope;
- retrieved content remains untrusted instruction data;
- agent action proposals require deterministic task/capability authorization before execution;
- capability execution uses a closed typed executor set and validates typed downstream results;
- MCP performs raw exact-key-set admission before permissive framework coercion;
- A2A performs raw JSON duplicate-key/exact-key admission and treats protocol identifiers/artifacts as correlation rather than business authority;
- operational telemetry is content-minimized;
- bounded model/token limits exist at model-call boundaries;
- AWS automation uses OIDC rather than repository-stored long-lived AWS access keys;
- no public HTTP runtime is currently retained, so WAF/client-rate-limit/tenant-isolation controls are not current deployment claims.

## Documentation drift

`docs/architecture.md` and `docs/architecture.pt-br.md` still carry a Phase 9/Phase 10 header despite later phases being authoritative in `docs/current-state.md`, `docs/roadmap.md`, ADRs, and gate evidence.

This is a low-priority documentation gap, not proof of a runtime vulnerability. It must be synchronized without changing runtime authority, either during the Phase 17 documentation pass or before Phase 17 closeout.

## Dependency-security sequencing

Gate 17.1 found no repository-local `.github/dependabot.yml`, dependency-review workflow, CodeQL workflow, or active `pip-audit` workflow. Historical `pip-audit` evidence does not prove current continuous coverage.

This does not authorize enabling all security products at once. A later Gate 17.3 should evaluate each control against the repository's actual language, dependency, licensing, signal, and maintenance needs after workflow authority has been hardened.

## Gate 17.2 authorized repository scope

```text
freeze repository-wide external-action full-SHA invariant
reject privileged pull_request_target/workflow_run triggers unless separately authorized
set checkout persist-credentials:false where authenticated git is unnecessary
make EPSS history plan-only paths use read-only/no-write credentials
limit 21600-second EPSS coordinator session to actual execution only
disable historical AgentCore mutating workflow by default until dedicated minimum authority is recreated
define exact required CI status contexts for main
```

Human/platform boundary:

```text
changing the GitHub ruleset required status checks
```

Not authorized:

```text
AWS IAM mutation
new AWS service
new public runtime
Inspector activation/reactivation
dependency-platform enablement in Gate 17.2
PR #89 modification
```

## Consequences

Security work now follows observed authority gaps rather than generic checklists. This preserves the core design principle:

> **Agents reason. Code verifies evidence.**

It also adds a Phase 17 security corollary:

```text
security control name != proven enforcement
historical workflow != inert workflow
plan-only operation != write-authority requirement
CI evidence != enforced merge gate
```

## AWS / runtime impact

Gate 17.1 performs no AWS mutation, creates no IAM authority, invokes no model, executes no agent capability, and deploys no runtime.

## References

- `labs/evidence/phase-17-gate-17-1-threat-model-v1.json`
- `labs/phase-17-gate-17-1-threat-model.md`
- `docs/adr/0063-phase16-runtime-exposure-closeout.md`
- GitHub Actions security guidance: <https://docs.github.com/en/actions/reference/security/secure-use>
- AWS IAM OIDC role guidance: <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html>
- AWS Well-Architected Generative AI Lens security guidance: <https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensec05-bp01.html>
- OWASP GenAI Security Project: <https://genai.owasp.org/initiatives/top-10-for-llm-and-genai/>
