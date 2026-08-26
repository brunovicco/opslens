# Phase 2.3G — NVD Glue and Athena Design Spike

## Status

IN PROGRESS — design and AWS compatibility proof required before deployment.

## Objective

Phase 2.3G exposes committed NVD Silver evidence through AWS Glue Data Catalog and Amazon Athena without weakening the evidence-first runtime proven in Phase 2.3F.

The analytical path must preserve the authority boundary:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
```

A Silver artifact is not analytically authoritative merely because it exists. Incremental observations become eligible only after the authoritative watermark commit proves the exact Bronze COMPLETE, Silver COMPLETE, and Silver Parquet evidence.

## Existing Silver contract

The frozen NVD Silver v1 dataset is:

```text
dataset:        nvd_cve_versions
schema_version: 1
format:         Parquet / Snappy
```

The physical schema already preserves vulnerability identity, observed content identity, immutable Bronze provenance, CVE lifecycle fields, descriptions, tags, CWE evidence, references, all supported CVSS observations, and canonical configuration JSON.

Canonical Silver keys are batch-scoped.

Bootstrap:

```text
silver/nvd/cve/
  schema_version=1/
  source_kind=bootstrap/
  feed_year=<year>/
  feed_revision=<revision>/
    part-00000.parquet
    manifest.json
```

Incremental:

```text
silver/nvd/cve/
  schema_version=1/
  source_kind=incremental/
  update_id=<sha256>/
    part-00000.parquet
    manifest.json
```

The Parquet object and the Silver COMPLETE JSON manifest intentionally share the same batch directory.

## Athena addressability problem

A normal Athena external table `LOCATION` represents an S3 folder, not one exact object. Athena reads the files under that location.

AWS documentation:

- <https://docs.aws.amazon.com/athena/latest/ug/tables-location-format.html>
- <https://docs.aws.amazon.com/athena/latest/ug/performance-tuning-data-optimization-techniques.html>

Therefore a Glue Parquet table must not point directly at the existing NVD Silver batch/root prefixes. Doing so would expose both:

```text
part-00000.parquet
manifest.json
```

to the Parquet reader.

This is rejected as an unsafe analytical contract.

## Constraints

Phase 2.3G must not solve analytics by silently changing previously proven evidence contracts.

Rejected shortcuts:

```text
Direct Athena LOCATION on silver/nvd/cve/*
    rejected: mixed Parquet + JSON objects

Rename or move existing Silver v1 objects
    rejected: changes frozen deterministic keys and persisted evidence

Copy every Silver Parquet into a second analytical dataset by default
    rejected: unnecessary data duplication until measured need exists

Glue crawler
    rejected: schema is already explicit and deterministic

Iceberg
    rejected: no demonstrated update/delete/table-maintenance requirement

Unrestricted text-to-SQL
    rejected: outside Phase 2 and violates the structured-query boundary
```

## Candidate compatibility layer

The bounded candidate for the AWS proof is `SymlinkTextInputFormat`.

AWS explicitly documents symlinks as a compatibility technique when files are not neatly organized for a table or when different schemas share a location. AWS also recommends using it only when better reorganization options are unavailable because the indirection adds S3 round trips.

That trade-off fits the current NVD v1 constraint: the authoritative Silver layout is already deployed and must remain stable.

Candidate analytical index:

```text
S3
analytics/nvd/cve/committed/
    <append-only symlink files>
        |
        +--> s3://.../silver/nvd/cve/.../part-00000.parquet
```

The index contains references only to Parquet objects that have passed the appropriate authority boundary.

The Glue table continues to use the existing explicit NVD Silver v1 columns and Parquet SerDe, while `SymlinkTextInputFormat` controls which physical objects Athena opens.

## Incremental authority source

The authoritative watermark already records the exact committed incremental Silver evidence:

```text
commit_basis.kind = silver_complete_promotion
commit_basis.update_id
commit_basis.silver_manifest.key
commit_basis.silver_manifest.version_id
commit_basis.silver_manifest.sha256
commit_basis.silver_parquet.key
commit_basis.silver_parquet.version_id
commit_basis.silver_parquet.sha256
committed_through_at
```

This means the analytics projection does not need to discover Silver objects with `ListBucket` and must not infer authority from an S3 prefix.

Target incremental flow after the compatibility proof:

```text
Promotion commits watermark
    |
    v
exact watermark ObjectCreated event
    |
    v
NVD Analytics Indexer
    |
    +--> read exact watermark VersionId
    +--> validate canonical committed state
    +--> require silver_complete_promotion basis
    +--> verify exact referenced Silver Parquet evidence
    +--> conditionally create one append-only symlink entry
    |
    v
Athena-visible committed observation corpus
```

The indexer is downstream of authority. It cannot advance the watermark.

## Bootstrap seed

The initial authoritative watermark is a Bootstrap recovery seed and does not contain a Silver Parquet reference.

Therefore Bootstrap analytics must use a one-time explicit seed based on already persisted exact Silver COMPLETE/Parquet evidence. The exact bootstrap key, VersionId, SHA-256, and row count must be re-read and verified before creating that seed.

No bootstrap Parquet location will be guessed from memory or inferred from a prefix listing.

## Why the index should be append-only

A mutable cumulative `symlink.txt` would introduce a new shared-state race and require read-modify-write reconciliation on every authority advance.

The preferred design is one deterministic index object per committed source batch. Duplicate delivery then maps to the same deterministic key and can use conditional creation plus exact replay verification.

Conceptually:

```text
analytics/nvd/cve/committed/
    bootstrap/<deterministic-seed-id>.symlink
    incremental/<update_id>.symlink
```

Each file contains only the corresponding immutable Parquet S3 URI.

Athena can read the collection through the symlink input format without copying the Parquet bytes.

## Analytical semantics

The table is an observation-history table, not a destructive current-state table.

Multiple rows for the same `cve_id` across committed batches are expected and correct.

The physical identities remain distinct:

```text
cve_id
observed_cve_version_id
observation_id
source_batch_id
```

Phase 2.3G must first prove deterministic observation queries. A later application-owned query compiler can derive current-state semantics using explicit ordering/tie-break rules; an LLM will not decide which observation is authoritative.

Initial target questions:

```text
Does CVE X exist in committed NVD evidence?
What committed observations exist for CVE X?
What vulnStatus values were observed?
What CVSS assessments exist for a selected observation?
What CWE IDs and references are attached to the selected observation?
```

## Cost and query limits

The existing Athena workgroup scan cutoff remains authoritative:

```text
10 MiB per query
```

NVD uses Parquet, so Athena can benefit from column pruning and Parquet metadata, but scan size must be measured rather than assumed.

The first AWS proof must record:

```text
bytes scanned
engine execution time
total execution time
result row count
query failure behavior when the scan cutoff is exceeded
```

No scan-limit increase is authorized by this design spike.

## AWS proof sequence

Before Terraform adds a permanent NVD Glue table or runtime indexer, validate the compatibility layer against exact existing evidence.

Required sequence:

```text
1. Resolve exact persisted Bootstrap Silver COMPLETE and Parquet evidence.
2. Resolve the exact committed incremental Silver Parquet from the current watermark.
3. Verify exact object SHA-256 / VersionId evidence.
4. Create a bounded temporary symlink prefix containing only those Parquet URIs.
5. Create a temporary Athena/Glue-compatible table using:
   - SymlinkTextInputFormat
   - ParquetHiveSerDe
   - the exact NVD Silver v1 schema
6. Query both primitive and complex NVD columns.
7. Cross-check Athena rows against the exact Parquet objects with PyArrow.
8. Measure bytes scanned and latency under the existing workgroup cutoff.
9. Delete the temporary table/index evidence after recording results.
```

A failed compatibility proof must not mutate Silver data or the authoritative watermark.

## Proof gates

```text
NVD_2_3G_EXACT_SOURCE_EVIDENCE_GATE
NVD_2_3G_MIXED_PREFIX_REJECTION_GATE
NVD_2_3G_SYMLINK_PARQUET_READ_GATE
NVD_2_3G_SCHEMA_COMPATIBILITY_GATE
NVD_2_3G_COMPLEX_TYPE_GATE
NVD_2_3G_PARQUET_ATHENA_CROSSCHECK_GATE
NVD_2_3G_SCAN_LIMIT_GATE
NVD_2_3G_AUTHORITY_ONLY_GATE
```

Only after these gates pass should the permanent Glue table, exact deployment IAM, and event-driven analytics-index runtime be implemented.

## Out of scope

```text
GitHub Security Advisories
EPSS historical expansion
package-to-vulnerability correlation
repository analysis
RAG / embeddings
Bedrock
agents
MCP
A2A
natural-language SQL
Phase 3
```

## Current decision

```text
Direct Silver LOCATION: REJECTED
Silver v1 layout rewrite: REJECTED
Default Parquet duplication: REJECTED
SymlinkTextInputFormat compatibility proof: SELECTED FOR AWS SPIKE
Permanent Glue/index runtime: DEFERRED UNTIL PROOF
```
