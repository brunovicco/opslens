# Phase 19 Gate 19.8 — Request-time threat evidence authority

Issue: #374  
Source protected main: `8700478c7fca230e5984c3ce034194ea3bd337e4`

## Problem

Gate 19.7 materialized the asynchronous public-runtime topology, but intentionally left it disabled. The materialized worker has deterministic queue/job authority, yet its provider-heavy executor is deliberately not composed.

The retained Gate 19.2 live workload cannot simply be installed as that executor. It is a representative experiment bound to one frozen repository and preloaded threat evidence. An arbitrary admitted public repository needs a request-time structured threat-evidence boundary before the existing Phase 3/4 correlation logic can run safely.

Therefore Gate 19.8 addresses the next missing authority, not runtime enablement.

## Bounded architecture

```text
PublicRepositoryEvidenceExecution
        |
        | deterministic normalized dependency evidence
        v
PublicThreatEvidenceScope
        |
        | package/version/purl + source record indexes
        | exact source execution binding
        v
PublicThreatEvidenceRequest
        |
        | snapshot policy: latest_complete
        v
PublicThreatEvidenceAuthority  <--- provider-neutral port only
        |
        | exact selected source-local identities
        v
PublicRepositoryThreatEvidence
        |
        +-- GHSA package occurrences within admitted package scope
        +-- NVD observed CVE versions bound to scoped GHSA CVEs
        +-- exact complete KEV snapshot + hash
        +-- exact complete EPSS snapshot + hash
        |
        v
retained deterministic Phase 3/4 correlation and enrichment
```

No LLM owns package identity, source selection, vulnerability applicability, snapshot provenance, or source truth.

## Scope semantics

The request scope is derived only from the already-admitted `PublicRepositoryEvidenceExecution` normalization inventory.

For each canonical package-version identity it preserves:

```text
package_name
version
purl
source_record_indexes[]
```

The physical lookup surface can use the unique `query_package_names`, but exact package/version/purl evidence remains in the scope. This permits lookup deduplication without losing the installed dependency evidence that Phase 3 later evaluates.

If a canonical-PyPI source record failed Phase 3 normalization, Gate 19.8 fails closed instead of silently analyzing only the subset that normalized successfully.

## Provenance semantics

`latest_complete` is a selection policy, not provenance. Once an authority executes that policy, the returned evidence must expose exact selected source-local identities:

```text
GHSA: observed_advisory_version_id
NVD:  observed_cve_version_id
KEV:  snapshot_date + source SHA-256
EPSS: snapshot_date + source SHA-256
```

The contract intentionally does not invent physical S3 keys, object VersionIds, Athena query IDs, or projection coordinates. Those belong to the later concrete provider adapter and must be measured/admitted there.

Missing evidence is not converted into benign evidence.

## Evidence admission

The offline contract rejects at least these contradictions before deterministic correlation:

- a GHSA occurrence whose canonical package is outside the admitted dependency scope;
- malformed GHSA source hashes or a version identity that contradicts its source hash;
- duplicate GHSA source occurrences;
- an NVD record whose CVE is unrelated to the admitted scoped GHSA evidence;
- multiple selected NVD observed versions for the same CVE;
- evidence returned for a different content-addressed request;
- incomplete PyPI normalization upstream.

Complete KEV and EPSS snapshots remain snapshot authorities. Their exact date/hash is carried forward rather than treating an absent CVE row as globally benign evidence.

## Physical structured-source adapter decision

Decision:

```text
DEFERRED_PENDING_BOUNDED_RUNTIME_ADAPTER_EVIDENCE
```

Existing candidate surfaces are real but not yet sufficient to select a runtime adapter:

1. Glue/Athena already exposes structured threat tables.
2. Exact S3 authority readers already exist for the frozen Gate 19.2 proof path.
3. The current worker IAM does not grant Athena, Glue, or threat-data S3 read authority.
4. The representative live measurement deliberately preloaded threat evidence, so Athena request count/bytes were `NOT_APPLICABLE`; it provides no request-time structured-source latency or cost measurement.
5. GHSA Silver currently needs a bounded package lookup/index/query path for arbitrary repositories; the frozen exact-object locator path is not a general package discovery mechanism.

Selecting Athena or direct S3 now would therefore be architecture by preference rather than evidence.

The next provider-backed gate must compare the smallest bounded alternatives, define exact query/read semantics and IAM, and measure latency/cost before any worker composition or enablement is considered.

## Authority impact

Gate 19.8 performs only source, tests, documentation, and offline verification.

```text
Terraform provider/backend operations: 0
AWS mutations:                          0
IAM mutations:                          0
Lambda artifact publications:           0
runtime enablements:                    0
provider live executions:               0
third-party repository code executions: 0
PR #89 modifications:                   0
```

The deployed runtime remains:

```text
materialized: true
execute-api endpoint: disabled
submit: disabled
API reserved concurrency: 0
worker: disabled
worker reserved concurrency: 0
event-source mapping: disabled
provider-heavy executor: uncomposed
custom domain: absent
```

## AIP-C01 learning value

This gate exercises a Professional-level boundary between model reasoning and deterministic application authority: structured data admission, source attribution, fail-closed validation, bounded integration contracts, least-privilege planning, and separating configuration from observed runtime evidence.

It deliberately does not add an AWS service merely for certification coverage.

## Exit evidence

Machine-readable authority record:

`labs/evidence/phase-19-gate-19-8-threat-evidence-authority-v1.json`

Offline verifier:

`python scripts/verify_phase19_gate19_8_threat_evidence_authority.py`

The verifier must pass without AWS credentials or provider calls while the async worker remains fail-closed and uncomposed.
