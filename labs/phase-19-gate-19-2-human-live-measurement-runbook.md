# Phase 19 Gate 19.2 — Human Live Measurement Runbook

_Date: 2026-09-10_

## Purpose

Execute the smallest **non-public** representative workload measurement required by Gate 19.2 without creating or modifying public runtime infrastructure, AWS resources, IAM policy, or third-party repository state.

This runbook is an execution boundary, not runtime-selection authority. The retained decision remains:

```text
DEFERRED_PENDING_MEASUREMENT
```

The retained leading hypothesis remains:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

until a successful representative measurement artifact exists and is reviewed.

## Permanent safety rules

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

The operator MUST NOT run dependency installation, build, test, package, hook, workflow, or arbitrary repository code from the target repository. The only third-party repository content admitted by the workload is the inert `uv.lock` file obtained through the retained fixed-host GitHub adapter and bound to an exact commit.

## Frozen representative input

The previous Requests anchor was rejected during read-only pre-live discovery because its GHSA advisory was not materialized in the current analytical GHSA state. Gate 19.2 therefore freezes the following reproducible input instead:

```text
repository:      openedx/mockprock
commit/ref:      18c954d8604df4740c829ba17fa2f3640b92b900
evidence file:  uv.lock
dependency:     webob==1.8.10
GHSA anchor:    GHSA-6hx8-3wjj-gr8g
CVE anchor:     CVE-2026-54770
affected range: < 1.8.11
patched from:   1.8.11
```

Read-only cross-source discovery established the following pre-live source facts for that exact CVE:

```text
GHSA advisory versions: 1
GHSA package entries:    1
NVD present:             yes
NVD observations:        1
KEV snapshot:            2026-09-10
KEV membership:          absent in the selected complete snapshot
EPSS snapshot:           2026-09-10
EPSS score:              0.00339
EPSS percentile:         0.26988
source overlap:          GHSA + NVD + EPSS = 3
```

The cross-source builder validated `selection_expectations_match=true`. These facts are pre-live evidence coordinates, not proof of repository runtime exposure. In particular, KEV absence means only **not present in the selected KEV snapshot**; it is not a zero-risk assertion.

The immutable `uv.lock` evidence is read only. Do not clone and execute the target repository, install its dependencies, run its tests, or interpret dependency presence as runtime reachability.

## Existing AWS boundary

The live workload may reuse only already-retained resources and authority. It must not create or mutate infrastructure.

Known retained Bedrock Knowledge Base:

```text
region:            us-east-1
knowledge base id: BTVJ2PBR2A
```

Use the already-approved Bedrock synthesis model/inference profile configured by the retained synthesis path. Do not broaden model or resource permissions for this experiment.

## Pre-flight verification

Start from protected `main` containing the merged Gate 19.2 measurement implementation and threat-evidence admission boundary.

```bash
git switch main
git fetch origin
git pull --ff-only

git status --short
git rev-parse HEAD

uv lock --check
uv sync --frozen

uv run ruff check src/opslens/public_analysis tests/unit/public_analysis scripts/verify_phase19_gate19_2_measurement_contract.py
uv run pyright src/opslens/public_analysis tests/unit/public_analysis scripts/verify_phase19_gate19_2_measurement_contract.py
uv run pytest tests/unit/public_analysis
PYTHONPATH=src uv run python scripts/verify_phase19_gate19_2_measurement_contract.py
```

Abort if any command fails or if the working tree contains unexpected changes.

## Credential and authority check

Use an existing operator profile/session that already has the minimum retained read/invoke permissions required by the current experiment. Do not modify IAM as part of this run.

At minimum, the live path may require existing authority for:

```text
bedrock:Retrieve
bedrock:InvokeModel
```

plus any already-retained read-only source access needed to materialize authoritative GHSA/NVD/KEV/EPSS evidence. If the existing identity cannot perform the run, **stop**. Lack of permission is evidence; it is not authorization to add permission.

Verify identity before execution:

```bash
aws sts get-caller-identity --profile <existing-profile>
```

## Threat-evidence materialization boundary

Before the end-to-end run, materialize the exact typed inputs required by `RepresentativeRepositoryThreatEvidence`:

```text
GhsaPyPIVulnerabilityEvidence tuple
NvdCveCoreRecord tuple
KevCatalogSnapshot
EpssSnapshot | HistoricalEpssSnapshot
```

Then pass the untrusted `CrossSourceCveEvidenceV1` projection plus those complete typed inputs through `admit_representative_threat_evidence`.

Requirements:

- evidence must come through retained source/transform contracts;
- the GHSA occurrence must bind `webob` to `GHSA-6hx8-3wjj-gr8g` / `CVE-2026-54770`;
- the analytical vulnerable range must remain `< 1.8.11` with `range_evaluation_performed=false`;
- installed-version applicability remains owned by the retained correlation layer;
- NVD authority must preserve the exact `ObservedCveVersion` identity rather than reconstructing it from a partial analytical row;
- KEV absence must be revalidated against one complete immutable KEV snapshot;
- EPSS score evidence must be revalidated against one complete current or historical EPSS snapshot;
- unavailable evidence remains unavailable/unsupported according to the retained contracts;
- do not convert a missing source into a fabricated zero or negative finding.

The exact serialized/materialized evidence used for the run should be retained under `labs/evidence/` with hashes or source identifiers sufficient to reproduce the input without storing unnecessary source payloads.

## Representative workload execution

Execute exactly one success-path run of `public-analysis-workload:v1` through the composed Gate 19.2 path:

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

The runtime wiring must use:

- retained `GitHubRestSnapshotSource` with `MeasuredGitHubHttpsConnectionFactory`;
- retained deterministic repository-analysis and Risk Policy v1 functions;
- retained Bedrock Knowledge Base direct Retrieve adapter for semantic evidence;
- retained bounded Bedrock hybrid synthesis adapter;
- deterministic final result admission;
- a real monotonic clock for stage/end-to-end duration;
- explicit provider measurement coverage.

Do not expose an HTTP endpoint for this run. Execute locally/non-publicly under the operator identity.

## Required observations

The live measurement artifact must record these dimensions exactly:

```text
end_to_end_duration_ms
stage_duration_ms
github_http_request_count
athena_query_count
athena_bytes_scanned
bedrock_retrieve_count
bedrock_retrieve_client_elapsed_ms
bedrock_model_call_count
bedrock_input_tokens
bedrock_output_tokens
bedrock_model_client_elapsed_ms
bedrock_model_latency_ms
retry_count
throttle_count
serialized_result_bytes
```

Evidence semantics are separate from numeric values. A numeric zero is not enough to establish that a metric was measured.

For the retained direct structured-evidence projection in this workload:

```text
athena_query_count:   NOT_APPLICABLE
athena_bytes_scanned: NOT_APPLICABLE
```

Do not report those as `MEASURED=0`. The read-only Athena queries used earlier to discover and materialize the pre-admitted threat bundle are preparation evidence; they are not request-time structured-evidence queries in this representative workload.

`throttle_count` remains `UNMEASURED` unless the concrete live adapter instrumentation used by the entire provider path can prove the observation. Do not infer throttling from elapsed time, retry count, or provider success.

Bedrock latency values must come from retained invocation evidence:

- Retrieve client elapsed time from `BedrockRetrieveInvocationEvidence.client_elapsed_ms`;
- model client elapsed time from `BedrockHybridSynthesisInvocationEvidence.client_elapsed_ms`;
- model provider latency from `BedrockHybridSynthesisInvocationEvidence.bedrock_latency_ms`.

## Failure-path validation

After the success-path measurement, validate at least one deterministic fail-closed path without mutating infrastructure. Prefer an input/admission failure that occurs before paid provider execution, such as malformed public request JSON or an invalid repository/ref contract.

The failure-path run must demonstrate that:

- invalid input does not become a partial success;
- no final admitted result is emitted;
- missing measurements are not backfilled as zero;
- the failure does not authorize fallback execution against another repository, model, KB, or runtime.

## Evidence artifact

Write the successful live observation to a new immutable evidence artifact, for example:

```text
labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
```

The artifact should include at least:

```text
artifact/version identity
exact OpsLens commit SHA
run id and UTC timestamp
frozen repository + exact commit
source evidence identifiers/hashes
Bedrock KB id
model/inference-profile identity
ordered stage durations
provider numeric totals
provider measurement classifications
serialized_result_bytes
final result SHA-256
success/failure outcome
public endpoint count = 0
new AWS resource count = 0
new IAM role/policy count = 0
third-party repository code executions = 0
```

Do not put secrets, credentials, authorization headers, full prompt contents, or unnecessary retrieved source text in the artifact.

## Runtime decision after measurement

Only after the live artifact exists and passes deterministic verification may Gate 19.2 evaluate:

```text
SYNC
ASYNC
DEFERRED_PENDING_MEASUREMENT
```

The decision must be derived from the measured workload characteristics and retained service limits, not from the prior `ASYNC_SUBMIT_STATUS_RESULT` hypothesis.

If the evidence is incomplete, inconsistent, or still materially `UNMEASURED`, retain:

```text
DEFERRED_PENDING_MEASUREMENT
```

## Stop conditions

Stop the run immediately if any of the following occurs:

- a required permission is absent;
- an operation would create or mutate AWS/IAM/public runtime resources;
- a target repository path other than retained inert evidence would need to be executed;
- provider identity, exact repository commit, or source evidence cannot be established;
- measurement instrumentation cannot distinguish `UNMEASURED` from a real observed zero;
- the workload would require touching PR #89;
- any deterministic admission or provenance contract fails.

A stopped run is preferable to manufacturing measurement authority.
