# Phase 19 — Gate 19.13 Portfolio / README / Architecture Polish

## Source checkpoint

```text
protected main: 4d001ba33e157c48891ccff3d5189263877f22b1
Gate 19.12 PR: #383 / merged
Gate 19.12 issue: #382 / closed completed
post-merge CodeQL: 34719883927 / run #430 / success
Gate 19.13 issue: #384
```

## Decision

Gate 19.13 polishes the public V1 presentation without adding business, provider, runtime, or model authority.

```text
POLISH_PUBLIC_V1_PRESENTATION_WITHOUT_NEW_AUTHORITY
portfolio claim != new evidence authority
```

OpsLens V1 remains a demonstration and architecture lab, not a production SaaS.

## Reviewer-first public entry points

The English and Portuguese root READMEs now put the reproducible V1 path before historical phase detail:

```bash
uv sync --frozen
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
uv run python scripts/demo_opslens_web.py
```

The browser reviewer opens:

```text
http://127.0.0.1:8765/
```

Both READMEs retain historical decision markers required to preserve the evidence trail rather than rewriting earlier Phase 19 decisions.

## Final V1 architecture presentation

`docs/architecture.md` and `docs/architecture.pt-br.md` are synchronized through Gate 19.12 and include GitHub-rendered Mermaid diagrams for:

- the final evidence/authority architecture;
- the retained async AWS topology.

The architecture explicitly separates deterministic authority from bounded probabilistic reasoning.

| Concern | Deterministic authority | Model / agent role |
| --- | --- | --- |
| Package/version applicability | authoritative | explain only |
| Threat provenance and correlation | authoritative | summarize admitted evidence |
| Risk score/tier | authoritative | explain, never override |
| Semantic query / SQL | typed admission/compilation | bounded proposal |
| Retrieval/citations | evidence admission | bounded synthesis |
| Capability/tool execution | authorization + limits | request/propose |
| Missing evidence | fail closed | no repair into benign truth |
| Visual projection | retained result remains truth | model disabled in V1 |

```text
Agents reason. Code verifies evidence.
model proposal != authorization
visual projection != business authority
```

## Measured evidence presentation

The public-facing material retains the Phase 19 representative-workload measurements as bounded evidence:

```text
end-to-end duration: 17748 ms MEASURED
serialized result: 5285 bytes
github physical HTTP requests: 4 MEASURED
bedrock Retrieve: 1 call / 4148 ms client elapsed MEASURED
bedrock model: 1 call / 5936 input / 408 output tokens MEASURED
model client elapsed: 8901 ms MEASURED
provider latency: 7772 ms MEASURED
retry count: 0 MEASURED
throttle count: UNMEASURED
```

The presentation keeps the evidence classes explicit:

```text
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
lab metric != production SLO
cost evidence != production TCO
```

No production extrapolation is introduced.

## Security and failure presentation

The architecture and portfolio views now make failure behavior visible rather than presenting only successful paths.

Key retained controls include:

```text
READ, NEVER EXECUTE third-party repository code.
strict repository/source identity admission
immutable repository and dependency evidence
fail-closed package/version normalization
scoped threat evidence
no unrestricted text-to-SQL
deterministic capability authorization
bounded execution/cost budgets
content-minimized telemetry
Dependency Review + CodeQL
least-privilege IAM evidence
HUMAN protected-merge boundaries
```

The three demo scenarios demonstrate material success, complete-evidence no-finding, and incomplete-evidence rejection.

```text
missing evidence != benign evidence
```

## Walkthrough and capture guidance

Gate 19.13 adds:

```text
docs/demo/WALKTHROUGH.md
docs/demo/PORTFOLIO_CAPTURE.md
```

The walkthrough provides a three-to-five-minute interview/architecture-review sequence. The capture guide provides reproducible terminal/browser capture steps and explicitly limits claims and sensitive information.

Binary screenshots and recordings are optional presentation artifacts, not gate truth. The reproducible deterministic demo and checked-in procedure remain the source of presentation evidence.

## Retained runtime evidence

The async AWS topology remains architecture evidence only:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
managed resources materialized: 21
public endpoint enabled: NO
submit enabled: NO
worker enabled: NO
event-source mapping enabled: NO
provider-heavy public executions: 0
```

```text
materialized != enabled
demonstration readiness != production readiness
```

Gate 19.13 performs no AWS, IAM, Terraform, or runtime operation.

## Verification contract

The offline Gate 19.13 verifier checks:

- exact Gate 19.12 source checkpoint and post-merge CodeQL identity;
- English/Portuguese README demo commands and historical markers;
- final architecture diagram and authority separation;
- measured-evidence non-extrapolation markers;
- security/failure semantics;
- walkthrough and portfolio capture guidance;
- synchronized current-state, roadmap, and V1 checklist;
- zero authority impact.

The verifier performs no network/provider/model access.

## Authority impact

```text
Terraform/provider operations:          0
AWS mutations:                          0
IAM mutations:                          0
artifact publications:                  0
runtime enablements:                    0
provider live executions:               0
model invocations:                      0
third-party repository code executions: 0
PR #89 modifications:                   0
```

## Exit criteria

Gate 19.13 reaches the HUMAN protected-merge boundary when:

1. public English/Portuguese entry points are synchronized and reviewer-first;
2. final architecture and authority boundaries are understandable from GitHub;
3. measured evidence is presented without production extrapolation;
4. security/failure behavior is visible;
5. the walkthrough and reproducible capture guide exist;
6. exact-head CI/security/CodeQL are green;
7. no external authority has been exercised.

Protected merge remains HUMAN-only. Gate 19.14 owns final clean-environment verification, Phase 19 closeout evidence/status, and release readiness. The `v1.0.0` tag/release remains HUMAN-authorized artifact publication.
