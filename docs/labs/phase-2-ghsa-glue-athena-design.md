# Phase 2.4E — GHSA Glue / Athena Analytics Design

_Date started: 2026-08-30_

_Status: SELECTED FOR IMPLEMENTATION_

## Purpose

Freeze the permanent GHSA analytical boundary before adding AWS Glue resources or running Athena queries.

Phase 2.4D established an authoritative immutable Silver dataset with one Parquet row per exact advisory content version and a separate COMPLETE namespace for attempt provenance.

The governing invariant remains:

> **Agents reason. Code verifies evidence.**

No LLM participates in analytical authority, advisory identity, CVE alias evidence, CVSS evidence, package/fix evidence, or SQL result validation.

## Existing authority boundary

Phase 2.4D stores authoritative advisory content under:

```text
silver/ghsa/advisory_versions/
  schema_version=1/
    ghsa_id=<GHSA-ID>/
      source_advisory_sha256=<sha256>/
        record.parquet
```

Attempt provenance is stored separately:

```text
silver/ghsa/completions/
  schema_version=1/
    sync_id=<sync-id>/
      attempt_id=<attempt-id>/
        manifest.json
```

Therefore the proposed Athena table root contains only schema-compatible Parquet content objects. COMPLETE JSON is not mixed below the table location.

The authoritative row identity remains:

```text
observed_advisory_version_id
```

Repeated physical observation of identical advisory content does not produce another content object.

## Decision: query authoritative Silver directly

Create one permanent AWS Glue external table directly over the authoritative GHSA Silver content root:

```text
Database: opslens_dev
Table:    ghsa_advisory_versions
Location: s3://<data-bucket>/silver/ghsa/advisory_versions/schema_version=1/
Format:   Parquet
```

No additional analytics copy/projector is introduced in Phase 2.4E.

### Why GHSA differs from NVD analytics

The NVD authority chain is:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

Its permanent analytics projector exists because a Silver object is not automatically authoritative; committed watermark evidence decides eligibility.

GHSA has no equivalent promotion/watermark boundary in the current contract. Phase 2.4D already makes the content namespace authoritative and deduplicated by exact advisory source content.

Adding another GHSA Lambda merely to copy identical Parquet bytes would introduce:

```text
another runtime identity
another deployment artifact
another retry/failure boundary
another S3 namespace
another set of VersionIds
another source-vs-projection lineage contract
additional storage and requests
```

without solving an authority problem that currently exists.

The selected design therefore keeps:

```text
Silver authority == analytical source bytes
```

while Glue remains metadata-only and Athena remains read-only downstream analytics.

## No crawler

The application already owns the exact Arrow/Parquet schema.

Create the Glue table explicitly in Terraform. Do not introduce a Glue crawler to infer schema that OpsLens already defines deterministically.

This follows the existing EPSS, KEV, and NVD catalog pattern.

## No GHSA partitions in v1

The physical content layout contains high-cardinality identity directories:

```text
ghsa_id=<GHSA-ID>/
source_advisory_sha256=<64-hex>/
```

Those directories are storage identity, not selected analytical partition dimensions.

Do not register them as Glue partition keys and do not use partition projection for them.

Reasons:

- `ghsa_id` cardinality grows with every advisory;
- `source_advisory_sha256` cardinality grows with every exact content version;
- queries commonly span many advisories/CVEs rather than a caller-supplied content hash;
- both values already exist in each authoritative Parquet row;
- partition metadata/projection would duplicate content identity without improving the initial query contract.

The v1 table therefore has zero partition keys and uses the static Silver schema-version root as its `LOCATION`.

Athena recursively discovers Parquet objects below that root. The nested object hierarchy may add S3 listing overhead as the dataset grows; that is accepted for the current bounded development scale and must be measured before introducing a compaction/projection layer.

A future derived compaction layer is allowed only after evidence demonstrates that small-file/listing overhead is materially harmful. It must remain downstream-only and must not replace Silver authority.

## Glue schema mapping

The application-owned Arrow v1 schema maps to Athena/Hive DDL types as follows:

```text
schema_version                 smallint
ghsa_id                        string
observed_advisory_version_id   string
source_advisory_sha256         string
cve_id                         string
advisory_type                  string
severity                       string
url                            string
html_url                       string
repository_advisory_url        string
source_code_location           string
summary                        string
description                    string
published_at                   timestamp
updated_at                     timestamp
github_reviewed_at             timestamp
nvd_published_at               timestamp
withdrawn_at                   timestamp
is_withdrawn                   boolean
identifiers                    array<struct<type:string,value:string>>
references                     array<string>
cwes                           array<struct<cwe_id:string,name:string>>
cvss_metrics                   array<struct<family:string,vector_string:string,score:double>>
cvss_severities_json           string
vulnerability_entry_count      int
vulnerabilities                array<struct<
                                  source_index:int,
                                  vulnerability_entry_id:string,
                                  source_entry_sha256:string,
                                  ecosystem:string,
                                  package_name:string,
                                  vulnerable_version_range:string,
                                  first_patched_version:string,
                                  vulnerable_functions:array<string>,
                                  source_entry_json:string
                                >>
```

Nullable Arrow fields remain nullable data values; Glue does not encode Arrow nullability as a separate table-column property.

No source field is renamed for analytics in v1.

## Historical relation, not a fabricated current-state relation

`ghsa_advisory_versions` contains exact historical content versions.

It does **not** claim:

```text
one row per current GHSA
```

The Phase 2.4B identity contract intentionally does not trust `updated_at` as content identity. Therefore Phase 2.4E must not silently implement:

```sql
MAX(updated_at)
```

as an authoritative current-state selector.

Two distinct content versions may theoretically share a source timestamp, and a deterministic hash tie-break would be reproducible but would not prove which source state was observed later.

Until an explicit current-state observation-order contract is frozen, queries must describe their semantics as one of:

```text
exact observed advisory content versions
any observed advisory version matching evidence
all observed package/fix evidence
```

No table or view named `current`, `latest`, or equivalent is authorized by this design increment.

If the Phase 2 exit reconciliation later requires a current-state relation, it must be derived from explicit observation provenance rather than inferred from timestamp ordering alone.

## Initial deterministic Athena query contract

Phase 2.4E will prove at minimum the following analytical capabilities over the authoritative historical relation.

### Query A — dataset identity and cardinality

Prove that Athena can read the exact Silver schema and expected row/cardinality evidence.

Expected current proof dataset:

```text
10 exact observed advisory content versions
```

### Query B — CVE alias / advisory evidence

Given a CVE identifier, return exact observed advisory versions whose canonical `cve_id` references that CVE.

The query must return at minimum:

```text
ghsa_id
observed_advisory_version_id
cve_id
severity
published_at
updated_at
is_withdrawn
```

This answers:

> Which observed GitHub advisory content versions reference this CVE?

It does not silently claim that the returned version is the latest/current advisory state.

### Query C — package/range/fix evidence

Use `UNNEST(vulnerabilities)` to expose exact nested source evidence:

```text
ghsa_id
observed_advisory_version_id
cve_id
ecosystem
package_name
vulnerable_version_range
first_patched_version
```

This answers whether GitHub supplied a first patched version in an observed advisory version.

It must not evaluate whether a concrete installed version satisfies the vulnerable range.

### Query D — CVSS evidence

Use `UNNEST(cvss_metrics)` to expose typed usable CVSS observations while retaining `cvss_severities_json` as exact source evidence for unavailable/additive structures.

At minimum expose:

```text
ghsa_id
observed_advisory_version_id
family
vector_string
score
```

### Query E — exact content identity lookup

Lookup one exact `observed_advisory_version_id` and verify row values against the corresponding exact Parquet object from Phase 2.4D.

This is the primary local-PyArrow/Athena equivalence proof.

## Existing Athena workgroup

Reuse:

```text
workgroup: opslens-dev
bytes_scanned_cutoff_per_query: 10,485,760 bytes
result encryption: SSE_S3
```

Do not increase the cutoff to make GHSA queries pass.

The first GHSA dataset is small enough that the existing cost boundary should be sufficient. If a query exceeds the cutoff, redesign the query/storage access pattern rather than automatically raising the limit.

## IAM and runtime impact

This design adds no GHSA analytical runtime identity.

No new Lambda, SQS queue, EventBridge rule, S3 notification, or Glue runtime partition writer is required.

Terraform/deployment needs only the authority required to create/update the explicit Glue catalog table under the existing `opslens_dev` database, following the established catalog deployment boundary.

Athena queries continue to run under the human/deployment analytical access already used for Phase 2 evidence proofs.

## Cost and operational impact

New steady-state services/resources:

```text
1 Glue catalog table metadata object
0 Lambda runtimes
0 queues
0 scheduled jobs
0 crawlers
0 duplicated Parquet storage
```

Athena charges remain query-driven and are bounded by the existing workgroup cutoff.

Potential future cost/performance concern:

```text
one-row Parquet small files + nested S3 identity hierarchy
```

This is observable technical debt, not a reason to introduce speculative infrastructure before scale evidence exists.

## Explicit Phase 3 boundary

Phase 2.4E may query and unnest:

```text
package ecosystem
package name
vulnerable version range expression
first patched version
CVE aliases
CVSS evidence
```

It must not decide:

```text
installed package version X is affected
installed package version X is fixed
repository dependency Y is exploitable
```

Those are deterministic Phase 3 correlation decisions.

## Implementation sequence

```text
2.4E-1  freeze direct-Silver analytics contract                 COMPLETE by this document
2.4E-2  add explicit Glue ghsa_advisory_versions table
2.4E-3  static Terraform/schema validation
2.4E-4  live Terraform plan/apply
2.4E-5  deterministic Athena query + PyArrow equivalence proof
2.4E-6  cost/cardinality/nested-evidence proof
2.4E-7  closeout and handoff to 2.4F
```

## Gates

This design increment establishes:

```text
GHSA_ANALYTICS_AUTHORITY_SOURCE_GATE=PASS
GHSA_ANALYTICS_NO_PROJECTOR_GATE=PASS
GHSA_ANALYTICS_EXPLICIT_SCHEMA_GATE=PASS
GHSA_ANALYTICS_NO_CURRENT_STATE_INFERENCE_GATE=PASS
GHSA_2_4E_1_GATE=PASS
```

Phase 2.4E overall remains open until the real Glue/Athena proof passes.

## References

- `docs/labs/phase-2-ghsa-advisory-silver-contract.md`
- `docs/labs/phase-2-ghsa-silver-runtime-closeout.md`
- `docs/labs/phase-2-nvd-glue-athena-permanent-path-design.md`
- `src/opslens/transformation/ghsa/serialization/schema.py`
- AWS Athena — Specify a table location in Amazon S3:
  https://docs.aws.amazon.com/athena/latest/ug/tables-location-format.html
- AWS Athena — Data types:
  https://docs.aws.amazon.com/athena/latest/ug/data-types.html
- AWS Athena — Optimize data / avoid additional storage hierarchies:
  https://docs.aws.amazon.com/athena/latest/ug/performance-tuning-data-optimization-techniques.html
