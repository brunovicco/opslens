# Phase 16 Gate 16.2 — Bounded Read-Only Amazon Inspector Discovery

## Status

```text
COMPLETE / BLOCKED_BY_EXISTING_IAM
```

The experiment itself completed successfully. The measured AWS result was a fail-closed authorization boundary: the already-existing GitHub deployment role could assume through OIDC, but Amazon Inspector rejected `ListCoverage` with `AccessDeniedException`.

This is valid terminal evidence for Gate 16.2. No IAM or Inspector state was changed.

## Question

Can the existing OpsLens AWS credentials expose useful Amazon Inspector coverage/finding evidence without changing AWS state or widening IAM?

Measured answer:

```text
NO — BLOCKED_BY_EXISTING_IAM
```

## Frozen authority boundary

Gate 16.1 authorized only:

```text
inspector2:ListCoverage
inspector2:ListFindings
```

and explicitly prohibited automatic IAM widening or Inspector activation/configuration changes.

The runtime path remained:

```text
existing OpsLensGitHubDeployRole
 -> OIDC assumption
 -> inspector2 ListCoverage
 -> AccessDeniedException
 -> STOP
```

`ListFindings` was deliberately not attempted after the required `ListCoverage` admission failed. This prevents partial discovery from being presented as complete evidence and preserves fail-closed behavior.

## Measured run

```text
workflow:               Inspector Read-Only Discovery
run:                    34411934819 / #1
job:                    102668116801
main SHA:               d5ba77cc98df84488928e49ea5e429234e46bc9a
region:                 us-east-1
existing AWS role:      OpsLensGitHubDeployRole
workflow conclusion:    success
experiment result:      BLOCKED_BY_EXISTING_IAM
client elapsed:         103.252301 ms
```

### Coverage

```text
attempted:              true
outcome:                ACCESS_DENIED
AWS error code:         AccessDeniedException
pages:                  0
records:                0
SDK retries:            0
```

### Findings

```text
attempted:              false
outcome:                NOT_ATTEMPTED
pages:                  0
records:                0
SDK retries:            0
```

No resource, finding, finding-type, or scan-status counts were available because the first required read was denied.

## Zero-authority / zero-mutation evidence

```text
AWS mutation count:             0
new IAM count:                  0
Inspector activation/change:    0
model invocations:              0
capability executions:          0
repository/runtime correlation: 0
```

The key security distinction is:

```text
AWS authentication succeeded != Inspector read authorization succeeded
```

OIDC successfully authenticated and assumed the existing deployment role. That identity still lacked authority for the selected Inspector read API. Gate 16.2 correctly treated the denial as evidence rather than escalating privileges.

## Artifact integrity

The workflow preserved the content-minimized JSON output as GitHub Actions artifact:

```text
artifact ID:        10127569570
artifact name:      phase-16-gate-16-2-inspector-readonly-34411934819
size:               586 bytes
SHA-256:            8814b313261e2ac2cde2894e7ea428e437aaa66cd0d2f47e7187759565d6738e
retention:          14 days
```

The immutable repository evidence is:

```text
labs/evidence/phase-16-gate-16-2-inspector-readonly-discovery-v1.json
```

## Interpretation

Gate 16.2 does **not** prove that Amazon Inspector has no useful evidence in the account. It proves only that the current `OpsLensGitHubDeployRole` cannot read the first required Inspector discovery surface.

It also does not authorize changing the role. The access denial answers the discovery question while preserving least privilege.

The next decision must therefore be explicit and separate:

```text
Gate 16.3 — Minimum Inspector Read-Only IAM Boundary Decision
```

Gate 16.3 should decide whether runtime-evidence value justifies a narrowly scoped read identity and, if so, whether that authority belongs in a dedicated Inspector discovery role rather than being silently added to the general deployment role.

Until that decision is accepted:

```text
Inspector IAM mutation:          NOT AUTHORIZED
Inspector activation/change:     NOT AUTHORIZED
repository/runtime correlation:  NOT AUTHORIZED
runtime-risk scoring:            NOT AUTHORIZED
```

## AIP-C01 learning note

This gate demonstrates an important production pattern for generative-AI platforms on AWS: authentication, authorization, and business/evidence authority are independent layers.

A successful OIDC role assumption proves identity establishment. It does not prove permission to invoke a downstream AWS API, and permission to read an AWS API would still not make the returned data model/business authority. Each boundary must be admitted separately and fail closed.

## Deferred work

OpsLens PR #89 / `feat/governed-gateway-semantic-planner` remains unrelated and untouched.
