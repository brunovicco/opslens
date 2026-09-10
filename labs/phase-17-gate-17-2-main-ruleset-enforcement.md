# Phase 17 Gate 17.2 — main ruleset enforcement verification

## Purpose

Preserve independent evidence that the human/platform administration boundary required by Gate 17.2 was completed after PR #255 merged.

## Verified source state

```text
main SHA:                  ca73643254a3464c5e61f1b458fe301022e4dd7f
ruleset:                   Protect main
ruleset id:                20873628
enforcement:               active
target:                    default branch
required status context:   Repository security invariants
integration id:            15368
bypass actors:             0
current user bypass:       never
```

The previously retained protections also remain present:

```text
deletion protection
non-fast-forward protection
pull request required
squash-only merge method
review-thread resolution required
linear history required
```

## Gate conclusion

Gate 17.2 is now complete. The repository-local security workflow existed and was green before the platform change; the active `Protect main` ruleset now requires the exact stable context that Gate 17.2 froze.

This closes the previously explicit distinction:

```text
CI evidence != enforced merge gate until the ruleset requires the context
```

The required context remains a control-plane merge prerequisite only. It does not become business authority, model authority, AWS authority, or runtime evidence truth.

## Cloud/runtime impact

```text
AWS mutations:          0
new IAM permissions:    0
new AWS services:       0
model invocations:      0
capability executions:  0
PR #89 changes:         0
```

## Next gate

Proceed to Gate 17.3 — dependency and code-scanning hardening, tracked in #256. That gate must remain repository-native and must not widen AWS/runtime authority.

Canonical evidence:

```text
labs/evidence/phase-17-gate-17-2-main-ruleset-enforcement-v1.json
```
