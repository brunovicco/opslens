# Phase 2.4F — GHSA Cross-source Deterministic Evidence Contract

_Date started: 2026-08-30_

_Status: SELECTED FOR IMPLEMENTATION_

## Purpose

Freeze the deterministic cross-source analytical contract that closes the GHSA milestone and satisfies the remaining Phase 2 threat-intelligence evidence requirements before historical EPSS expansion.

The governing invariant remains:

> **Agents reason. Code verifies evidence.**

This increment does not introduce an LLM, agent, text-to-SQL path, package-version applicability engine, or new AWS runtime.

The target user question is:

> Given a CVE identifier and explicit source-time coordinates, what deterministic evidence does OpsLens currently have from NVD, CISA KEV, FIRST EPSS, and GitHub Security Advisories?

## Existing analytical surfaces

Phase 2.4F reuses only the already deployed analytical tables:

```text
opslens_dev.nvd_cve_versions
opslens_dev.kev_entries
opslens_dev.epss_scores
opslens_dev.ghsa_advisory_versions
```

No new Glue table, Lambda, queue, scheduler, crawler, database, or S3 projection is required to prove the cross-source bundle.

## Why explicit temporal coordinates are mandatory

EPSS and KEV use injected `snapshot_date` partition projection. Their existing contracts intentionally require a concrete snapshot date and reject the notion of an implicit analytical `latest`.

Therefore the cross-source bundle must carry:

```text
cve_id

EPSS:
  epss_snapshot_date

KEV:
  kev_snapshot_date

NVD:
  explicit analytical authority coordinates used for the proof
  (source_kind_partition + projection_date set)

GHSA:
  exact historical advisory-version relation
```

A bundle is reproducible only when these coordinates are reported with the evidence.

The Phase 2 exit phrase `current EPSS` means:

```text
an EPSS snapshot independently established as the latest available
at the time of the proof,
then queried by its explicit snapshot_date
```

It does not authorize a query that silently guesses the latest partition.

The same rule is used for KEV membership: the proof first establishes the most recent available KEV snapshot and then queries that explicit partition.

## CVE input contract

Input CVE identifiers must use the canonical form:

```text
CVE-YYYY-NNNN...
```

The proof must fail before query execution when the supplied identifier does not match the accepted CVE syntax.

No fuzzy matching, substring matching, semantic search, or model interpretation is permitted for the join key.

## Source-specific evidence semantics

### NVD

NVD answers:

```text
Did an authoritative projected NVD observation for this CVE exist
within the explicit authority coordinates used by the proof?
```

Evidence may include:

```text
cve_id
observed_cve_version_id
observation_id
source_kind
source_batch_id
source_observed_at
published_at
last_modified_at
vuln_status
is_rejected
cwe_ids
cvss_metrics
```

OpsLens must not collapse multiple NVD CVSS observations into one invented universal score.

If multiple authoritative NVD observations for the same CVE are present in the explicit analytical scope, the cross-source proof must preserve the set or apply an independently justified observation-order rule. It must not use `MAX(last_modified_at)` alone as a hidden current-state authority.

### CISA KEV

KEV answers:

```text
Was this CVE present in the explicitly selected KEV snapshot?
```

The deterministic membership result is:

```text
is_kev = true  -> one matching row exists in the selected snapshot
is_kev = false -> no matching row exists in the selected snapshot
```

Evidence may include:

```text
snapshot_date
cve
vendor_project
product
vulnerability_name
date_added
required_action
due_date
known_ransomware_campaign_use
catalog_version
catalog_date_released
source_sha256
retrieved_at
```

Absence means only `not present in this selected KEV snapshot`; it must not be generalized into `not exploited`.

### FIRST EPSS

EPSS answers:

```text
What exploitation-probability evidence exists for this CVE
in the explicitly selected EPSS snapshot?
```

Evidence may include:

```text
snapshot_date
cve
epss
percentile
model_version
score_timestamp
source_sha256
```

If no row exists, the result is `EPSS evidence absent for this snapshot`; no default score of zero is fabricated.

### GitHub Security Advisories

GHSA answers:

```text
Which exact observed GitHub advisory content versions reference this CVE?
```

Evidence may include:

```text
ghsa_id
observed_advisory_version_id
source_advisory_sha256
cve_id
severity
published_at
updated_at
is_withdrawn
identifiers
cvss_metrics
vulnerabilities
```

GHSA remains a historical exact-content relation. Phase 2.4F does not fabricate a `current` advisory version from `MAX(updated_at)`.

For each nested vulnerability entry, the bundle may expose source evidence:

```text
ecosystem
package_name
vulnerable_version_range
first_patched_version
vulnerable_functions
```

This is published advisory evidence only.

## Explicit Phase 3 boundary

Phase 2.4F may state:

```text
GitHub published vulnerable_version_range = "..."
GitHub published first_patched_version = "..." or NULL
```

It must not state:

```text
installed version X is vulnerable
installed version X is fixed
repository Y is exploitable
```

Evaluating a concrete package version against ecosystem-specific range syntax belongs to the deterministic Phase 3 Vulnerability Correlation Engine.

No range parser or applicability decision is introduced in Phase 2.4F.

## Cross-source bundle shape

The logical proof result is one CVE-centered bundle with independent source sections:

```text
CrossSourceCveEvidenceV1

cve_id
proof_coordinates
  epss_snapshot_date
  kev_snapshot_date
  nvd_authority_coordinates
  athena_workgroup
  athena_engine_version

nvd
  exists
  observations[]

kev
  snapshot_date
  is_kev
  entry | null

epss
  snapshot_date
  evidence_present
  score | null

ghsa
  advisory_version_count
  advisory_versions[]
    package_evidence[]

query_evidence
  query_execution_id
  data_scanned_in_bytes
  total_execution_time_in_millis
```

Each source remains independently attributable. A missing source observation must not erase or alter evidence from another source.

## No lossy four-way SQL join

The cross-source proof must not use one naïve inner join such as:

```sql
NVD
JOIN KEV
JOIN EPSS
JOIN GHSA
```

because absent KEV, EPSS, or GHSA evidence would incorrectly remove a valid NVD CVE from the result, while one-to-many GHSA package evidence could multiply unrelated NVD/EPSS/KEV fields.

The selected pattern is:

```text
1 CVE input
  -> independent source CTEs/subqueries
  -> source-local cardinality validation
  -> one deterministic bundle/result projection
```

When nested one-to-many evidence is required, it remains nested/aggregated by its source identity rather than being flattened into a misleading Cartesian product.

## Phase 2.4F proof strategy

The implementation sequence is:

```text
2.4F-1  freeze cross-source evidence semantics                COMPLETE by this document
2.4F-2  discover and freeze current proof coordinates         NEXT
2.4F-3  select one deterministic CVE with useful overlap
2.4F-4  execute bounded Athena cross-source evidence query
2.4F-5  independently verify source-local result invariants
2.4F-6  prove GHSA package/fix evidence without range evaluation
2.4F-7  record cost/query evidence and reconcile Phase 2.4 closeout
```

## 2.4F-2 coordinate discovery requirements

Before the cross-source query is written, the proof must discover from real AWS state:

```text
latest available EPSS snapshot_date
latest available KEV snapshot_date
available authoritative NVD projection coordinates
GHSA table availability
Athena workgroup configuration/cutoff
```

The discovery must be read-only.

The result must be printed and retained as proof input. Do not hard-code dates from old lab documents merely because they were previously validated.

## Deterministic CVE selection

The proof CVE must be selected from the real analytical data, not chosen from memory.

Preferred selection criteria:

```text
NVD evidence present
EPSS evidence present in the selected current snapshot
GHSA advisory evidence present
KEV membership present if at least one such overlap exists
GHSA package evidence present if possible
```

If no CVE exists across all four sources, that is a valid empirical result. The selection algorithm then chooses the highest available overlap deterministically and records which source is absent.

A deterministic tie-break such as lexical `cve_id ASC` is allowed after overlap cardinality is computed.

## Cost boundary

Reuse the existing Athena workgroup:

```text
opslens-dev
```

The current repository contract enforces a 10 MiB per-query bytes-scanned cutoff.

Phase 2.4F must not raise that cutoff to make a query pass.

Cross-source SQL should remain column-bounded, CVE-bounded, and partition-bounded where the table design supports partitions.

If a candidate query exceeds the cutoff, redesign the query rather than expanding the guardrail.

## Security boundary

Phase 2.4F is analytical and read-only.

It does not require:

```text
new runtime IAM
new deployment IAM
new S3 write access
new Glue mutation
new scheduler permissions
new secrets
```

Human proof execution continues through temporary AWS IAM Identity Center credentials and the existing `opslens-bootstrap` profile.

## Failure semantics

```text
invalid CVE input
    -> reject before Athena query

missing explicit EPSS/KEV snapshot coordinate
    -> fail closed

selected snapshot does not exist
    -> fail closed

NVD evidence absent
    -> report nvd.exists=false

KEV row absent
    -> report is_kev=false for that snapshot

EPSS row absent
    -> report evidence_present=false, never fabricate epss=0

GHSA rows absent
    -> advisory_version_count=0

ambiguous one-to-many evidence
    -> preserve collection; do not collapse silently

Athena cutoff exceeded
    -> redesign query; do not increase cutoff automatically
```

## Exit evidence required

Phase 2.4F passes only when a real AWS proof demonstrates a CVE-centered deterministic bundle that can answer, with explicit source coordinates:

```text
CVE exists in NVD evidence?
KEV membership for selected current snapshot?
EPSS score/percentile for selected current snapshot?
NVD CVSS/severity evidence?
Which observed GHSA advisories reference the CVE?
Which GHSA package/range evidence exists?
Is first_patched_version present where GitHub supplied it?
```

The proof must also retain:

```text
Athena QueryExecutionId
DataScannedInBytes
execution timing
selected temporal coordinates
source-local row/cardinality checks
```

## Gates established by this contract

```text
GHSA_CROSS_SOURCE_EXPLICIT_TIME_COORDINATES_GATE=PASS
GHSA_CROSS_SOURCE_NO_IMPLICIT_LATEST_GATE=PASS
GHSA_CROSS_SOURCE_NO_LOSSY_JOIN_GATE=PASS
GHSA_CROSS_SOURCE_SOURCE_LOCAL_AUTHORITY_GATE=PASS
GHSA_CROSS_SOURCE_PHASE3_RANGE_BOUNDARY_GATE=PASS
GHSA_CROSS_SOURCE_NO_NEW_RUNTIME_GATE=PASS
GHSA_2_4F_1_GATE=PASS
```

Phase 2.4F remains open until the real read-only AWS proof and closeout pass.

## References

- `docs/labs/phase-1-epss-athena-query.md`
- `docs/labs/phase-2-kev-athena-query.md`
- `docs/labs/phase-2-nvd-versioned-silver-contract.md`
- `docs/labs/phase-2-nvd-glue-athena-permanent-athena-proof.md`
- `docs/labs/phase-2-ghsa-advisory-silver-contract.md`
- `docs/labs/phase-2-ghsa-glue-athena-closeout.md`
- `infra/environments/dev/analytics_glue.tf`
- `infra/environments/dev/analytics_ghsa_glue.tf`
