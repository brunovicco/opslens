# Phase 2.4D — GHSA Silver Runtime Closeout

_Date completed: 2026-08-30_

_Status: COMPLETE_

## Purpose

Close Phase 2.4D by proving the deterministic transformation of one exact GHSA Bronze COMPLETE attempt into immutable advisory-content Silver evidence in the real `dev` AWS environment.

The governing invariant remains:

> **Agents reason. Code verifies evidence.**

No LLM participates in advisory identity, CVE alias consistency, CVSS normalization, package/range preservation, Parquet generation, object identity, completion, or replay decisions.

## Final architecture boundary

The deployed Phase 2.4D path is:

```text
exact GHSA Bronze COMPLETE
  Key + VersionId
        |
        v
GHSA Silver Lambda
  exact manifest read
  exact page reads
  source revalidation
  attempt_id recomputation
  deterministic record composition
        |
        v
one immutable Parquet object
per observed_advisory_version_id
        |
        v
Silver COMPLETE manifest
  exact occurrence -> exact content object bindings
```

The identity boundary is explicit:

```text
observed_advisory_version_id
    exact advisory source-content identity

sync_id
    logical synchronization-window identity

attempt_id
    exact physical Bronze attempt identity

attempt_occurrence_id
    exact source position inside one attempt
```

Repeated observation of identical advisory content does not create another authoritative advisory content version.

## Authoritative Silver physical grain

The authoritative dataset remains:

```text
dataset:        ghsa_advisory_versions
schema_version: 1
physical grain: one row per exact observed_advisory_version_id
```

Each content object is stored under the deterministic content identity:

```text
silver/ghsa/advisory_versions/
  schema_version=1/
    ghsa_id=<GHSA-ID>/
      source_advisory_sha256=<sha256>/
        record.parquet
```

Attempt completion is stored separately:

```text
silver/ghsa/completions/
  schema_version=1/
    sync_id=<sync-id>/
      attempt_id=<attempt-id>/
        manifest.json
```

This prevents physical source occurrence metadata from redefining advisory content identity.

## Immutable persistence semantics

Silver content objects and COMPLETE manifests use create-only persistence.

The runtime behavior is:

```text
PutObject If-None-Match: *
        |
        +--> created
        |
        +--> existing object
                |
                v
          HeadObject -> VersionId
                |
                v
          GetObject(exact VersionId)
                |
                v
          exact byte verification
                |
                +--> exact match -> replay-safe success
                +--> mismatch    -> fail closed
```

A COMPLETE manifest is published only after every authoritative content object has been created or exactly verified.

## Exact Bronze reader boundary

The Silver runtime never discovers Bronze through listing or mutable latest-object semantics.

Invocation accepts only:

```json
{
  "schema_version": "1",
  "manifest_key": "<exact Bronze COMPLETE key>",
  "manifest_version_id": "<exact Bronze COMPLETE VersionId>"
}
```

The runtime then:

1. reads the exact Bronze manifest version;
2. validates canonical COMPLETE bytes and contract fields;
3. reads every declared page using its exact VersionId;
4. verifies size and SHA-256;
5. revalidates persisted page bytes against the GHSA source parser;
6. reconstructs the bounded pagination chain;
7. recomputes `attempt_id` from the exact page evidence;
8. composes deterministic Silver records.

The invocation carries no source window, mode, page inventory, advisory identifiers, or derived attempt identity that could compete with the Bronze COMPLETE manifest as authority.

## CVSS runtime refinement discovered by real evidence

The first real Bronze-to-Silver invocation reached transformation code correctly but failed on a valid source shape:

```text
InvalidGhsaAdvisoryCollectionsError
cvss_severities.cvss_v4.vector_string must be a non-empty string
```

The real reviewed GHSA batch demonstrated that a known CVSS family may be present as an unavailable placeholder, including an empty or nullable vector.

The Silver contract was refined without changing schema v1:

```text
usable known vector + numeric score
    -> typed cvss_metrics entry

known family present but vector unavailable
    -> no fabricated typed metric
    -> exact source object preserved in cvss_severities_json

malformed non-null vector or incompatible score
    -> fail closed
```

The regression suite now covers empty and nullable placeholders plus malformed known-family shapes.

The final real batch contained:

```text
cvss_v4_placeholder_rows=7
```

All seven preserved the source JSON while emitting no invented typed CVSS v4 observation.

## Runtime artifact evidence

The initial deterministic runtime artifact was:

```text
sha256=5740e5b4d7348392a00bada4136622719c0e5c1dee11eef8b2fff19ff45aca54
s3_key=lambda/ghsa-silver/5740e5b4d7348392a00bada4136622719c0e5c1dee11eef8b2fff19ff45aca54.zip
s3_version_id=Y6qI2gg6o9n.Aexh1CGjcENp.dya2hHo
```

The CVSS runtime refinement produced the final validated artifact:

```text
sha256=242e6fe88efd09514fe70e4b1dd3ec3a4335884b6a80d4f8b943c5fa3f0ae27e
source_code_hash=JC5v6I79CVFP5w5LHdPsOkM1iEtqgNT4uUPF+j8K4n4=
s3_key=lambda/ghsa-silver/242e6fe88efd09514fe70e4b1dd3ec3a4335884b6a80d4f8b943c5fa3f0ae27e.zip
s3_version_id=Bb6ludDG1hI4ztxoK2xxQa9zxmLfqwde
compressed_bytes=67408251
uncompressed_bytes=184445789
```

The Linux/Python 3.13 artifact was built twice with the same SHA-256 before publication.

Because the compressed artifact exceeds the Lambda direct-upload boundary, deployment uses the existing versioned deployment-artifacts S3 bucket.

## Terraform-managed dev runtime

The minimum Phase 2.4D runtime manages:

```text
aws_iam_role.ghsa_silver_lambda
aws_iam_role_policy.ghsa_silver_lambda_runtime
aws_cloudwatch_log_group.ghsa_silver
aws_lambda_function.ghsa_silver
```

The initial reviewed plan and apply proved:

```text
Plan: 4 to add, 0 to change, 0 to destroy.
Apply complete! Resources: 4 added, 0 changed, 0 destroyed.
```

The CVSS artifact repin later proved:

```text
Plan: 0 to add, 1 to change, 0 to destroy.
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

The repin changed only:

```text
s3_key
s3_object_version
source_code_hash
```

No IAM, memory, timeout, environment, or adjacent infrastructure changed.

## Deployed Lambda configuration

The final live function is:

```text
FunctionName=opslens-dev-ghsa-silver
Runtime=python3.13
Handler=opslens.transformation.ghsa.lambda_handler.lambda_handler
Architectures=[x86_64]
MemorySize=3008
Timeout=900
EphemeralStorage=512 MiB
CodeSha256=JC5v6I79CVFP5w5LHdPsOkM1iEtqgNT4uUPF+j8K4n4=
State=Active
LastUpdateStatus=Successful
TracingConfig.Mode=Active
LoggingConfig.LogFormat=JSON
LogGroup=/aws/lambda/opslens-dev-ghsa-silver
```

The only application environment value is the non-secret GHSA data bucket name.

## IAM boundary

The runtime uses a dedicated execution role.

Bronze read authority is limited to exact-version object retrieval under:

```text
bronze/ghsa/advisories/*
```

Silver write/replay authority is limited to:

```text
silver/ghsa/advisory_versions/*
silver/ghsa/completions/*
```

The role intentionally has no `s3:ListBucket` permission.

CloudWatch Logs and X-Ray permissions are scoped to the runtime observability responsibility. The function has no GitHub credential access because Silver transforms persisted Bronze evidence and does not call the external GHSA source.

## Real Bronze input evidence

The live proof reused the exact immutable Bronze attempt already proven by Phase 2.4C:

```text
mode=published
sync_id=1670a1e4730ba3e5a8214b7278d68b43fd8c929a069bae27099abd370cf9193e
attempt_id=e013864e669cc3b4f92766a94e9f487960bd4b3bf40247d523b8415a0d8aaa40
manifest_version_id=IHt7S5Uvj21ABxWfPAPsXbnQhQW3ErRH
page_count=1
total_items=10
```

No new Bronze ingestion was created to make the Silver proof pass.

## First successful real Silver materialization

After deploying the CVSS refinement, the exact same Bronze COMPLETE produced:

```text
status=complete
sync_id=1670a1e4730ba3e5a8214b7278d68b43fd8c929a069bae27099abd370cf9193e
attempt_id=e013864e669cc3b4f92766a94e9f487960bd4b3bf40247d523b8415a0d8aaa40
logical_record_set_sha256=b5d50ba85f23bd70e6b0db9d3570007d19ba73b524ee00b98021d17ed3e1fc38
row_count=10
content_object_count=10
```

The Silver COMPLETE evidence is:

```text
key=silver/ghsa/completions/schema_version=1/sync_id=1670a1e4730ba3e5a8214b7278d68b43fd8c929a069bae27099abd370cf9193e/attempt_id=e013864e669cc3b4f92766a94e9f487960bd4b3bf40247d523b8415a0d8aaa40/manifest.json
version_id=vqewf1VGfD1tzgMeF0DpBppgiDpV0KTV
sha256=45533f87c843f2a149eb7becca72a5d7e4e1ad51c80dba9c57db730437518f92
```

## Exact content verification

The COMPLETE was independently read using its exact VersionId and its SHA-256 matched.

Every one of the ten declared content objects was then independently read by exact S3 VersionId.

The proof validated for all ten objects:

```text
Parquet SHA-256
size_bytes
physical row_count=1
ghsa_id
observed_advisory_version_id
source_advisory_sha256
```

Final evidence:

```text
exact_content_objects=10
single_row_parquet_objects=10
unique_observed_advisory_versions=10
cvss_v4_placeholder_rows=7
```

## Deterministic replay proof

Before replay, the proof inventoried only the eleven exact Silver keys involved in the attempt:

```text
10 authoritative content objects
1 COMPLETE manifest
```

Inventory before replay:

```text
tracked_keys=11
version_count_before=11
delete_markers_before=0
```

A second synchronous Lambda invocation using the same exact Bronze manifest key and VersionId returned the same:

```text
sync_id
attempt_id
Bronze manifest key + VersionId
logical_record_set_sha256
Silver COMPLETE key + VersionId + SHA-256
row_count=10
content_object_count=10
```

The Lambda request identifier differed, as expected for a separate invocation.

Inventory after replay:

```text
version_count_after=11
new_s3_versions=0
new_delete_markers=0
```

Therefore the replay reused all existing immutable Silver evidence and created no duplicate S3 versions.

## Validation gates

Source and static gates:

```text
GHSA_BRONZE_MANIFEST_AUTHORIZATION_GATE=PASS
GHSA_EXACT_VERSION_S3_READ_GATE=PASS
GHSA_SILVER_RUNTIME_PREPARATION_CORE_GATE=PASS
GHSA_BRONZE_ATTEMPT_RECOMPUTATION_GATE=PASS
GHSA_EXACT_BRONZE_TO_SILVER_PREPARATION_GATE=PASS
GHSA_2_4D_2_GATE=PASS

GHSA_SILVER_CONTENT_KEY_IDENTITY_GATE=PASS
GHSA_SILVER_COMPLETION_KEY_IDENTITY_GATE=PASS
GHSA_SILVER_SINGLE_ROW_CONTENT_GRAIN_GATE=PASS
GHSA_SILVER_LOGICAL_ATTEMPT_MATERIALIZATION_GATE=PASS
GHSA_SILVER_ONE_CONTENT_ONE_PARQUET_GATE=PASS
GHSA_SILVER_CONTENT_ARTIFACT_DETERMINISM_GATE=PASS

GHSA_SILVER_DEV_IAM_GATE=PASS
GHSA_SILVER_DEV_OBSERVABILITY_GATE=PASS
GHSA_SILVER_TERRAFORM_STATIC_GATE=PASS
GHSA_SILVER_ARTIFACT_S3_VERSION_GATE=PASS
GHSA_SILVER_LIVE_TERRAFORM_PLAN_GATE=PASS
GHSA_SILVER_LIVE_TERRAFORM_APPLY_GATE=PASS
GHSA_2_4D_5_GATE=PASS
```

Final runtime proof:

```text
GHSA_SILVER_EXACT_COMPLETE_GATE=PASS
GHSA_SILVER_EXACT_CONTENT_GATE=PASS
GHSA_SILVER_REAL_CVSS_PLACEHOLDER_GATE=PASS
GHSA_SILVER_DETERMINISTIC_REPLAY_GATE=PASS
GHSA_SILVER_NO_DUPLICATE_S3_VERSION_GATE=PASS
GHSA_2_4D_6_GATE=PASS
GHSA_2_4D_GATE=PASS
```

## Phase boundary

Phase 2.4D is complete.

The next GHSA milestone is Phase 2.4E — Glue/Athena Analytics. Phase 2.4E may expose deterministic query surfaces over the authoritative GHSA advisory-version dataset, but it must not evaluate whether a concrete installed package version is affected by `vulnerable_version_range`.

Installed-version applicability remains Phase 3 deterministic correlation work.

Phase 2 remains open after Phase 2.4D. Historical EPSS expansion and remaining Phase 2 exit criteria must still pass or be explicitly deferred before Phase 3 begins.

## References

- `docs/adr/0005-ghsa-source-and-synchronization-strategy.md`
- `docs/adr/0006-ghsa-silver-content-versioning-and-physical-shape.md`
- `docs/adr/0007-ghsa-runtime-credential-and-retry-strategy.md`
- `docs/labs/phase-2-ghsa-advisory-silver-contract.md`
- `docs/labs/phase-2-ghsa-bronze-contract.md`
- `docs/labs/phase-2-ghsa-manual-dev-runtime.md`
- `docs/labs/phase-2-ghsa-runtime-composition.md`
