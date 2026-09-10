# Phase 19 Gate 19.2 — Representative Workload Measurement

_Date: 2026-09-10_

## Objective

Close the whole-workload measurements that Gate 19.1 deliberately left `UNMEASURED` before OpsLens selects a public runtime topology.

Gate 19.2 starts from protected `main` at:

```text
ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1
```

That commit is the protected squash merge of PR #292. Gate 19.1 remains the authority for `public-analysis-workload:v1`, the `DEFERRED_PENDING_MEASUREMENT` runtime decision, and the non-authoritative `ASYNC_SUBMIT_STATUS_RESULT` leading hypothesis.

## Current implementation slice

Issue: #295  
Draft PR: #297  
Branch: `feat/phase19-gate19-2-representative-workload-measurement`

The first slice adds a provider-neutral measurement contract and harness rather than a public endpoint or cloud runtime.

Exact representative stages:

```text
public_request_admission
repository_acquisition
dependency_evidence
vulnerability_correlation
risk_prioritization
structured_evidence
semantic_evidence
model_reasoning
result_admission
```

The harness requires this exact order. Missing, duplicated, or reordered stages fail closed.

## Measurement contract

Every successful representative run must record concrete observations for:

```text
end_to_end_duration_ms
stage_duration_ms
github_http_request_count
athena_query_count
athena_bytes_scanned
bedrock_retrieve_count
bedrock_model_call_count
bedrock_input_tokens
bedrock_output_tokens
retry_count
throttle_count
serialized_result_bytes
```

Zero is a valid measured value only when the corresponding stage executed with measurement instrumentation and observed zero. Missing instrumentation must not be projected as measured zero.

The whole-run provider counters must equal the exact sum of the stage observations. The final result size is measured only from non-empty serialized bytes after result admission.

## Retained deterministic composition

Gate 19.2 reuses the existing repository truth chain rather than duplicating it:

```text
PublicRepositoryEvidenceExecution
 -> build_repository_pypi_vulnerability_scan
 -> enrich_repository_findings_with_nvd
 -> enrich_repository_findings_with_kev
 -> enrich_repository_findings_with_epss
 -> build_repository_analysis_result
```

`RepresentativeRepositoryAnalysis` binds those retained outputs back to the exact public repository evidence execution and rejects chain drift.

Risk remains a separate deterministic stage and continues to use the retained Risk Policy v1 entry point:

```text
RepositoryAnalysisResult
 -> prioritize_repository_analysis
 -> RiskPrioritizationResult
```

The measurement layer does not calculate vulnerability applicability or risk priority itself.

## Physical GitHub request measurement

The retained `GitHubRestSnapshotSource` has one logical `get_commit` operation that performs two physical HTTPS requests: ref-to-SHA resolution and exact Git commit-object retrieval. Therefore Gate 19.2 must measure at the transport boundary rather than count application method calls.

`MeasuredGitHubHttpsConnectionFactory` wraps the existing injectable HTTPS connection factory. It:

- counts each delegated physical `request(...)` call;
- observes GitHub 429 and rate-limit-style 403 responses for throttle counting;
- does not alter destination, path, headers, body reads, retry behavior, or typed errors;
- exposes the result only as `ProviderResourceUsage`.

The retained GitHub source still performs no automatic retry. Retry measurement is not inferred from request count.

## Security and authority boundary

```text
public endpoints:       0
new AWS resources:      0
new IAM roles/policies: 0
live AWS/model calls:   0 in this implementation slice
third-party code exec:  0
PR #89 modifications:  0
```

Permanent rules remain:

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
retrieved content != instruction authority
model proposal != authorization
tool/protocol success != business truth
MEASURED != DERIVED
UNMEASURED != zero
configured limit != measured utilization
```

## Validation completed so far

The provider-neutral harness has deterministic unit coverage for:

- complete ordered measurement aggregation;
- reordered-stage rejection;
- negative-counter rejection;
- empty-result rejection;
- monotonic-clock regression rejection.

The retained deterministic repository-analysis composition has an integration-style unit test that builds public repository evidence from inert `uv.lock`, reuses GHSA/NVD/KEV/EPSS processing, produces one `RepositoryAnalysisResult`, and then reuses Risk Policy v1 without moving risk authority into Gate 19.2.

The GitHub transport measurement adapter has offline coverage for physical-call counting and rate-limit observation while preserving the retained fail-closed GitHub source behavior.

## Remaining Gate 19.2 work

The gate is not complete. Remaining work is to compose the measured workload through the retained structured-evidence, semantic-evidence, bounded model-reasoning, and deterministic result-admission boundaries; preserve exact provider accounting for those stages; freeze a reproducible non-public measurement input; and then human-execute the smallest live AWS/model measurement if required.

Only after representative evidence exists may the runtime decision become:

```text
SYNC
ASYNC
DEFERRED_PENDING_MEASUREMENT
```

No public runtime topology is selected by this lab.
