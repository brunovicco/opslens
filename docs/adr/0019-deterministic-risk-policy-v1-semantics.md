# ADR 0019 — Deterministic Risk Policy v1 semantics

- Status: Accepted
- Date: 2026-09-03
- Phase: 5 — Risk Prioritization Engine
- Gate: 5.1

## Context

Phase 4 closes with a deterministic `RepositoryAnalysisResult` over already-established repository and threat-intelligence evidence:

1. immutable repository snapshot and inert dependency evidence;
2. deterministic PyPI package/version identity and GHSA vulnerable-range applicability;
3. CVE/GHSA/NVD reconciliation;
4. all preserved supported NVD CVSS observations;
5. complete-snapshot CISA KEV membership;
6. exact-snapshot FIRST EPSS evidence;
7. fixed-version evidence when GHSA publishes it.

Phase 4 deliberately does not rank findings, select a preferred CVSS observation, define EPSS thresholds, weight KEV, or calculate a risk score.

Phase 5 must now prioritize already-proven affected findings without weakening the permanent boundary:

> Agents reason. Code verifies evidence.

The policy also must preserve:

> Repository Risk != Runtime Exposure.

The first policy should be small enough to explain, reproduce, test factor by factor, and defend without hiding arbitrary weights behind a composite numeric score.

## External semantics reviewed

The policy semantics were checked against the current authoritative descriptions of the underlying signals:

- CISA describes the KEV catalog as the authoritative source of vulnerabilities known to have been exploited in the wild and recommends using it as an input to vulnerability-management prioritization: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- FIRST describes EPSS as a calibrated probability of exploitation within the next 30 days and explicitly warns against interpreting it as a binary safe/unsafe threshold: https://www.first.org/epss/how-it-works
- NVD describes CVSS as a qualitative measure of severity and explicitly states that CVSS is not a measure of risk: https://nvd.nist.gov/general/FAQ-Sections/CVE-FAQs

Therefore OpsLens treats KEV, EPSS, and CVSS as different evidence dimensions rather than interchangeable scores.

## Decision

Phase 5 v1 will use a **rule-first deterministic prioritization policy**.

It will not use an additive or weighted risk formula such as `CVSS * weight + EPSS * weight + KEV * weight`.

The policy authority is versioned as:

```text
opslens-risk-policy-v1
```

Any future change to ranking precedence, EPSS threshold semantics, CVSS selection semantics, missing-evidence behavior, or authoritative factor effects requires a new policy version.

Documentation-only wording changes do not require a new policy version if decision semantics are unchanged.

## Input boundary

Risk Policy v1 consumes only Phase 4 `RepositoryAnalysisFinding` evidence derived from a validated `RepositoryAnalysisResult`.

The policy must not accept caller-supplied replacements for:

- affected status;
- dependency/package identity;
- GHSA/CVE identity;
- KEV state;
- EPSS state or score;
- CVSS metrics;
- fixed version;
- evidence identities.

The policy does not re-evaluate package applicability.

Every input finding is already deterministically `affected` according to Phase 3/4 semantics.

## Output contract

One policy evaluation produces a deterministic risk decision with at least:

```text
policy_version
finding_id
decision_status
priority_tier
factor_evidence
factor_effects
review_reasons
priority_sort_coordinates
decision_id
```

`decision_status` is one of:

```text
prioritized
review_required
```

`priority_tier` is present only for `prioritized` decisions and is one of:

```text
urgent
elevated
standard
```

A `review_required` result is not silently converted to the lowest priority.

## Authoritative factor semantics

### 1. Affected status

Phase 5 does not score applicability.

The input finding already proves that the installed package/version is affected by the exact GHSA vulnerable range. Applicability remains a prerequisite, not a weighted factor.

### 2. CISA KEV

KEV has the strongest v1 escalation semantics because it represents source evidence of exploitation in the wild.

Rules:

```text
KEV present
 -> decision_status = prioritized
 -> priority_tier = urgent

KEV absent
 -> continue to EPSS policy

KEV cve_unavailable
 -> decision_status = review_required
 -> no automatic priority tier
```

`KEV absent` is not equivalent to "not exploited". It means only that the CVE was absent from the complete KEV snapshot used by Phase 4.

### 3. FIRST EPSS

EPSS is treated as temporal exploitation-probability evidence, not severity and not a safety verdict.

For findings with `KEV absent`:

```text
EPSS score_present and score >= 0.70
 -> priority_tier = elevated

EPSS score_present and score < 0.70
 -> priority_tier = standard

EPSS score_absent
 -> decision_status = review_required

EPSS cve_unavailable
 -> decision_status = review_required
```

The `0.70` boundary is an explicit **OpsLens Risk Policy v1 product threshold**, not a threshold recommended by FIRST.

It is intentionally frozen in the policy version so repeated evidence produces repeated decisions. Changing the threshold requires a new policy version.

The exact EPSS snapshot remains part of the decision evidence. OpsLens never substitutes a missing score with `0.0`.

EPSS percentile is not used in v1 ranking because it is another representation of the same underlying EPSS observation and would double-count one signal.

### 4. CVSS

CVSS is a severity signal and does not establish risk by itself.

CVSS does **not** change the v1 priority tier. It is used only as a deterministic tie-break coordinate inside an already-established tier when one metric can be selected without ambiguity.

Risk Policy v1 selects one CVSS tie-break observation with this precedence:

1. prefer `Primary` metrics when at least one exists; otherwise use `Secondary` metrics;
2. within the selected metric type, prefer the newest supported family in this order:

```text
V40 > V31 > V30 > V2
```

3. if exactly one metric remains at the selected type/family, use its base score as the CVSS tie-break coordinate;
4. if multiple metrics remain at the same selected type/family, mark CVSS selection as `ambiguous` and do not use CVSS to break the tie;
5. if no supported metric exists, mark CVSS selection as `unavailable` and do not invent a score.

The policy never selects the numerically highest CVSS observation merely because it is highest.

All original Phase 4 CVSS observations remain preserved as evidence regardless of whether one is selected for the v1 tie-break.

Missing or ambiguous CVSS alone does not force `review_required` when KEV/EPSS evidence is sufficient for automatic prioritization.

### 5. Fixed-version evidence

`fixed_version` is treated as **actionability/remediation evidence**, not a risk-severity factor.

In v1 it does not:

- change the priority tier;
- change the risk sort order;
- imply that an unfixed vulnerability is less important;
- imply that a fixed version makes the currently installed vulnerable version safe.

The decision records whether fixed-version evidence is available so later remediation phases can use it without changing vulnerability truth.

### 6. Evidence completeness

Missing evidence is never normalized to a benign numeric default.

Risk Policy v1 distinguishes:

```text
known negative evidence
unknown/unavailable evidence
ambiguous evidence
```

Automatic prioritization requires enough exploitation evidence to apply the rules above.

Specifically:

- `KEV present` is sufficient for `urgent` even when EPSS or CVSS is unavailable;
- `KEV absent` requires `EPSS score_present` for automatic prioritization;
- `KEV cve_unavailable`, `EPSS score_absent`, or `EPSS cve_unavailable` in a non-KEV path produces `review_required`;
- CVSS unavailable/ambiguous is recorded as incomplete evidence but does not by itself force manual review;
- fixed-version absence is evidence absence, not a review failure.

## Deterministic ordering

Only `prioritized` findings receive automatic risk ordering.

The repository-level sort is lexicographic, not a weighted sum:

```text
1. priority tier: urgent > elevated > standard
2. EPSS availability, then EPSS score descending when present
3. selected CVSS availability, then selected CVSS base score descending when present
4. analysis_finding_id ascending as the final stable tie-break
```

Missing EPSS or CVSS is never converted to zero for this ordering. Availability is represented as a separate coordinate.

For `urgent` KEV findings, EPSS may legitimately be unavailable; that finding remains urgent because observed exploitation evidence supersedes the predictive EPSS requirement in v1.

`review_required` findings are not mixed into the automatic risk order. Consumers must surface them explicitly as requiring review rather than implying they are low priority.

## No numeric risk score in v1

Risk Policy v1 does not emit an authoritative composite numeric risk score.

Reasons:

1. KEV, EPSS, and CVSS represent different concepts;
2. arbitrary additive weights would create false precision;
3. rule precedence is easier to explain and test;
4. future runtime-exposure evidence will add another independent dimension;
5. a numeric score can be introduced later only if a concrete product/evaluation need justifies and validates it.

A repository-level ordinal rank may be derived from the deterministic sort order, but it is not a universal risk score.

## Factor explanation contract

Every decision must expose factor-level reason codes rather than only the final tier.

Candidate stable reason-code vocabulary for implementation includes:

```text
kev_known_exploited
kev_not_listed_in_complete_snapshot
kev_cve_unavailable
epss_at_or_above_v1_threshold
epss_below_v1_threshold
epss_score_absent
epss_cve_unavailable
cvss_selected_for_tie_break
cvss_ambiguous_for_tie_break
cvss_unavailable_for_tie_break
fixed_version_available
fixed_version_unavailable
```

The exact typed names may be adjusted mechanically during Gate 5.2, but their semantics must remain consistent with this ADR.

## Content-addressed decision identity

Each implemented risk decision must receive a deterministic content-addressed identity:

```text
risk-decision:v1@sha256:<digest>
```

The canonical decision evidence must commit to at least:

- `policy_version`;
- authoritative Phase 4 finding identity/evidence hash;
- KEV state and relevant source evidence identity;
- EPSS state, exact snapshot coordinates, and score when present;
- CVSS selection state and selected metric evidence when applicable;
- fixed-version availability evidence;
- decision status;
- priority tier when present;
- stable reason codes;
- authoritative policy constants that affect the decision.

Changing temporal threat-intelligence evidence or policy semantics must therefore change the decision identity.

## Explicit v1 non-goals

Risk Policy v1 does not use or infer:

- direct vs transitive dependency status unless later evidence establishes it;
- runtime deployment or package activation;
- Amazon Inspector evidence;
- environmental CVSS customization;
- business criticality of an asset;
- internet exposure;
- exploit-chain reachability;
- compensating controls;
- remediation cost;
- LLM judgment;
- a universal numeric risk score.

These signals must not be fabricated as zero-valued factors.

## Failure behavior

The policy must fail closed on malformed or internally inconsistent Phase 4 evidence.

Evidence that is valid but insufficient for automatic ranking produces `review_required`; it does not raise a policy error merely because a source lacks a score.

An implementation error, impossible state, provenance mismatch, or unsupported policy input must remain distinct from a legitimate `review_required` decision.

## Consequences

### Positive

- Same evidence and same policy version produce the same decision.
- Known exploitation receives explicit precedence without blending KEV into an opaque score.
- EPSS remains temporal probability evidence and is not interpreted as a safety threshold.
- CVSS remains severity evidence and does not masquerade as risk.
- Missing evidence cannot silently lower priority.
- Fixed-version evidence remains available for remediation without distorting risk.
- Factor-level explanations can be tested independently.
- Future runtime-exposure evidence can be added without redefining current source authority.

### Trade-offs

- The v1 tier model is deliberately coarse.
- The `0.70` EPSS threshold is a policy choice and will need evaluation against historical cases.
- Findings without usable EPSS evidence on the non-KEV path require review rather than automatic ranking.
- CVSS affects order only within a tier, so a severe low-EPSS vulnerability may remain in the `standard` tier; this is intentional in v1 and must be evaluated rather than silently compensated with weights.

## Rejected alternatives

### Weighted additive risk score

Rejected for v1 because it combines non-equivalent evidence into a number whose weights would be arbitrary before an evaluation corpus exists.

### Use CVSS as the primary risk score

Rejected because CVSS measures severity, not risk, and does not incorporate observed/predicted exploitation evidence.

### Treat missing EPSS as zero

Rejected because absent source evidence is not evidence of zero exploitation probability.

### Treat KEV absence as proof of no exploitation

Rejected because KEV absence is only absence from the selected complete catalog snapshot.

### Pick the highest CVSS score across all source observations

Rejected because that would introduce a hidden source-selection policy and can overstate one observation merely because it is numerically larger.

### Make fixed-version availability increase or decrease risk

Rejected because fix availability is remediation/actionability evidence rather than proof of vulnerability severity or exploitation likelihood.

### Use an LLM to rank findings

Rejected because prioritization over these structured factors is deterministic policy logic and must be reproducible, testable, and auditable.

## Security, cost, IAM, and infrastructure

Gate 5.1 is an architecture contract only.

The intended Phase 5 implementation remains pure deterministic domain/application logic unless a later concrete requirement proves otherwise.

- New AWS services: none.
- New IAM permissions: none.
- Incremental AWS infrastructure cost: $0.
- LLM dependency: none.
- Third-party repository code execution: none.

No persistence, cache, API, UI, Bedrock, Lambda, DynamoDB, or other service is justified by this gate alone.
