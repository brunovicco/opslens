# ADR 0015 — Enrich Repository Findings with Exact NVD and CVSS Evidence

- Status: Accepted
- Date: 2026-09-03
- Phase: 4 — Repository Intelligence
- Gate: 4.8 — CVE/NVD + CVSS enrichment

## Context

Gate 4.7 emits deterministic repository-risk findings only after a normalized locked PyPI package version matches an exact GHSA vulnerable range through the Phase 3 correlation authority.

That finding intentionally proves only repository applicability. It does not yet attach the GitHub CVE assertion, the independently observed NVD CVE version, or NVD CVSS evidence required by the Phase 4 exit criteria.

The completed Phase 2 and Phase 3 surfaces already provide the required deterministic authorities:

- `GhsaPyPIVulnerabilityEvidence` preserves an exact GHSA vulnerability occurrence and GitHub's CVE assertion when present;
- `reconcile_github_cve_with_nvd` creates a source-preserving GHSA/CVE/NVD alias edge without discovery or source merging;
- `NvdCveCoreRecord` binds a CVE to one exact `ObservedCveVersion` and its canonical source JSON SHA-256;
- `NvdCvssMetricsTransformer` deterministically normalizes every supported CVSS metric family present in that exact NVD source object.

The repository layer must reuse these authorities rather than inventing a second CVE, CVSS, or source-selection rule.

## Decision

### 1. Base repository findings are immutable applicability truth

Gate 4.8 does not recompute, upgrade, downgrade, rank, or otherwise change the `affected` decision emitted by Gate 4.7.

The new evidence record references the existing content-addressed `repository-finding:v1` identity and adds independent threat-intelligence evidence around it.

`Repository Risk != Runtime Exposure` remains unchanged.

### 2. GHSA source evidence must rebind exactly to the affected finding

The enrichment application receives exact `GhsaPyPIVulnerabilityEvidence` records only to recover GitHub's CVE assertion and identifier provenance that were not embedded in the Gate 4.7 finding.

Before reconciliation, the source occurrence must match the affected assessment on all source-local coordinates used by the finding contract, including:

- GHSA id;
- observed advisory version id;
- advisory SHA-256;
- vulnerability entry id;
- source index;
- entry SHA-256;
- ecosystem;
- package name;
- vulnerable range;
- first patched version.

A missing, duplicate, or mismatched GHSA occurrence fails closed.

### 3. CVE alias truth remains owned by the Phase 3 adapter

Gate 4.8 calls `reconcile_github_cve_with_nvd` and preserves its states exactly:

- `no_github_cve`;
- `github_asserted_only`;
- `nvd_observed`;
- `nvd_rejected`.

`nvd=None` continues to mean only that no matching NVD evidence was supplied to this enrichment call. It must never be interpreted as proof that NVD has no record.

### 4. NVD input contains at most one exact observed version per CVE

Gate 4.8 does not choose a "latest" NVD observation and does not apply a hidden temporal policy.

The caller may supply zero or one `NvdCveCoreRecord` for a CVE. Supplying multiple observed versions for the same CVE is ambiguous and fails closed.

Historical/current NVD observation selection belongs upstream to the evidence retrieval layer.

### 5. CVSS is re-derived from the exact NVD source content

Gate 4.8 does not accept detached CVSS values.

When an exact NVD observation is linked, the application parses the already validated `ObservedCveVersion.canonical_json` and runs `NvdCvssMetricsTransformer` against that exact source object.

This guarantees that CVE identity, NVD source SHA-256, vulnerability status, and normalized CVSS observations all refer to the same immutable NVD content version.

The repository evidence model verifies that supplied normalized CVSS evidence still equals a fresh deterministic transformation of that source content.

### 6. Preserve all supported CVSS observations; do not select a preferred score

Gate 4.8 preserves every normalized NVD CVSS metric emitted by the existing Phase 2 transformer, including:

- family and version;
- source;
- Primary/Secondary type;
- vector string;
- base score;
- base severity when present;
- exploitability score when present;
- impact score when present;
- canonical source metric JSON.

Unsupported future `cvssMetricV*` families remain explicit in `unsupported_cvss_families`.

No "highest", "best", "primary", or merged CVSS value is selected in Phase 4. Selection or weighting would be risk-policy behavior and belongs to Phase 5.

### 7. Enrichment is independently content-addressed

Each enriched record commits to:

- base repository finding id and SHA-256;
- GHSA/CVE/NVD alias state and provenance;
- exact NVD observed-version identity when supplied;
- NVD source SHA-256, source identifier, status, and timestamps;
- all normalized CVSS evidence and unsupported family names.

The base Gate 4.7 finding id is not changed.

### 8. Work is bounded and fails closed

The enrichment accepts at most 50,000 supplied NVD observations per call.

The existing 50,000 GHSA occurrence bound remains the maximum rehydration surface. Duplicate NVD CVE identities, duplicate GHSA occurrence identities, malformed source binding, detached CVSS evidence, and bound violations fail closed rather than truncating.

## Alternatives considered

### Copy `github_cve_id` into the Gate 4.7 finding

Rejected for this gate. It would mutate the already released content-addressed finding schema and change finding ids even though applicability truth has not changed.

### Accept precomputed CVSS alongside NVD core evidence

Rejected. `NvdCvssMetrics` has no independent CVE/version identity. Accepting it detached would permit accidental cross-version evidence mixing.

### Select one CVSS metric for convenience

Rejected. NVD can publish multiple families and sources. Selecting one is policy, not evidence normalization.

### Automatically select the newest NVD observation for a CVE

Rejected. It introduces an implicit temporal rule and makes historical reproducibility dependent on call-time state.

## Security and operational impact

- Third-party repository code is still never executed.
- No LLM is involved.
- No new AWS service is required.
- No new IAM permissions are required.
- Incremental AWS cost: $0 for this pure deterministic domain/application gate.
- Existing Phase 2 and Phase 3 source authorities remain unchanged.

## AIP-C01 learning relevance

This gate reinforces:

- deterministic evidence grounding before model reasoning;
- separation of source authority from downstream interpretation;
- reproducible and auditable AI/security data pipelines;
- fail-closed validation;
- keeping risk policy separate from raw evidence construction.

## Next gates

After this gate is validated independently:

1. attach CISA KEV evidence by exact CVE identity and explicit snapshot semantics;
2. attach EPSS evidence by exact CVE identity and explicit score snapshot semantics;
3. close the Phase 4 exit criteria before introducing Phase 5 Risk Policy v1.
