# Phase 19 Gate 19.2 — Human Live Measurement Runbook

_Date: 2026-09-11_

## Purpose

Execute exactly one **non-public** representative Gate 19.2 workload under an existing operator identity, record measured GitHub/Bedrock resource evidence, and persist one bounded immutable artifact without creating or mutating public runtime infrastructure, AWS resources, IAM policy, or third-party repository state.

This runbook crosses a human execution boundary. It does **not** authorize CI, ChatGPT, or an automated workflow to invoke live GitHub/AWS/Bedrock providers.

The retained runtime decision remains:

```text
DEFERRED_PENDING_MEASUREMENT
```

until a successful live artifact exists and is reviewed.

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
NOT_APPLICABLE != zero
configured limit != measured utilization
```

The operator MUST NOT clone-and-build, install dependencies, run tests, execute hooks, run workflows, execute Dockerfiles, or run arbitrary code from the target repository. The representative workload reads only retained inert repository evidence through the fixed-host GitHub adapter.

## Frozen representative anchor

```text
repository:      openedx/mockprock
repository URL:  https://github.com/openedx/mockprock
commit/ref:      18c954d8604df4740c829ba17fa2f3640b92b900
evidence file:  uv.lock
dependency:     webob==1.8.10
GHSA anchor:    GHSA-6hx8-3wjj-gr8g
CVE anchor:     CVE-2026-54770
affected range: < 1.8.11
patched from:   1.8.11
```

Frozen threat coordinates:

```text
NVD observations: 1
KEV snapshot:     2026-09-10
KEV membership:   absent in that complete snapshot
EPSS snapshot:    2026-09-10
EPSS score:       0.00339
EPSS percentile:  0.26988
```

KEV absence does not mean zero risk. Low EPSS does not mean zero risk. Repository dependency evidence does not establish runtime exposure.

## Retained live provider coordinates

The driver reuses only existing resources:

```text
region:             us-east-1
knowledge base id:  BTVJ2PBR2A
data source id:     IEL1LBE026
source/data bucket: opslens-dev-data-487757851499-us-east-1
synthesis model:    us.anthropic.claude-haiku-4-5-20251001-v1:0
```

These coordinates were already established by the retained Phase 7/8 Bedrock path. Do not create a new Knowledge Base, vector index, model deployment, IAM role, policy, endpoint, bucket, or data source for this experiment.

## Driver boundary

The human-run entrypoint is:

```text
scripts/run_phase19_gate19_2_live_measurement.py
```

Its checked implementation lives under `opslens.public_analysis.cli.run_live_measurement`; the script is only a thin operator wrapper.

Before the measured workload starts, the driver:

1. validates the frozen repository/model coordinates and output path;
2. loads the local cross-source evidence bundle and immutable locator manifest;
3. loads the checked canonical retrieval manifest/catalog;
4. performs the retained exact-version S3 threat-authority materialization with explicit byte limits;
5. validates CVE/GHSA and KEV/EPSS snapshot identity;
6. projects only bounded source hashes into final artifact metadata;
7. constructs Bedrock and GitHub adapters without executing the measured workload yet.

Those exact-version S3 `GetObject(VersionId=...)` reads are **pre-measurement preparation**. They are not inserted into any request-time workload stage because S3 request count/latency is outside the frozen Gate 19.2 measurement contract.

The measured path then calls `execute_representative_workload(...)` exactly once using:

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

The live composition reuses:

- `MeasuredGitHubHttpsConnectionFactory` around the retained fixed-host GitHub source;
- `PreloadedRepresentativeThreatEvidenceLoader` for already-admitted threat evidence;
- direct bounded Bedrock Knowledge Base `Retrieve` plus canonical retrieval-catalog admission;
- retained bounded hybrid Bedrock synthesis;
- the real monotonic measurement clock;
- the frozen provider measurement classifications.

No public endpoint is involved.

## Pre-flight verification

Run from the exact reviewed commit that will be recorded in the evidence artifact:

```bash
git status --short
git rev-parse HEAD

uv lock --check
uv sync --frozen

uv run ruff check src/opslens/public_analysis tests/unit/public_analysis
uv run pyright src/opslens/public_analysis tests/unit/public_analysis
uv run pytest tests/unit/public_analysis
PYTHONPATH=src uv run python scripts/verify_phase19_gate19_2_measurement_contract.py
```

Abort if any check fails or if the working tree has unexpected changes.

Verify the existing AWS identity without changing IAM:

```bash
aws sts get-caller-identity --profile <existing-profile>
```

The existing identity must already have the retained read/invoke permissions required for exact S3 authority reads, Bedrock `Retrieve`, and model invocation. Missing permission is a stop condition, not authorization to expand IAM.

## Required local inputs

Prepare paths to the exact reviewed files used by the pre-measurement threat-evidence preparation:

```bash
export OPSLENS_BUNDLE=<path-to-cross-source-cve-evidence-v1.json>
export OPSLENS_LOCATOR_MANIFEST=<path-to-immutable-threat-locator-manifest.json>
export OPSLENS_PROFILE=<existing-profile>
```

Use reviewed positive byte limits for each immutable source. Do not guess smaller values until failure and then silently widen them. Record the chosen limits with the operator notes:

```bash
export OPSLENS_GHSA_SILVER_MAX_BYTES=<reviewed-positive-limit>
export OPSLENS_NVD_SILVER_MAX_BYTES=<reviewed-positive-limit>
export OPSLENS_NVD_BRONZE_MAX_BYTES=<reviewed-positive-limit>
export OPSLENS_KEV_BRONZE_MAX_BYTES=<reviewed-positive-limit>
export OPSLENS_EPSS_BRONZE_MAX_BYTES=<reviewed-positive-limit>
```

For authenticated public GitHub reads, an existing token may be supplied by environment name only:

```bash
export GITHUB_TOKEN=<existing-token>
```

The token value is never written to the measurement artifact. If no token is required, omit both the environment variable and the `--github-token-env` argument below.

## Exact human-run command

Confirm that the target artifact does not already exist. The driver deliberately refuses to overwrite evidence.

```bash
PYTHONPATH=src uv run python scripts/run_phase19_gate19_2_live_measurement.py \
  --bundle "$OPSLENS_BUNDLE" \
  --locator-manifest "$OPSLENS_LOCATOR_MANIFEST" \
  --manifest knowledge/corpus/v1/manifest.json \
  --profile "$OPSLENS_PROFILE" \
  --region us-east-1 \
  --authority-bucket opslens-dev-data-487757851499-us-east-1 \
  --knowledge-base-id BTVJ2PBR2A \
  --data-source-id IEL1LBE026 \
  --source-bucket opslens-dev-data-487757851499-us-east-1 \
  --model-id us.anthropic.claude-haiku-4-5-20251001-v1:0 \
  --repository-url https://github.com/openedx/mockprock \
  --repository-ref 18c954d8604df4740c829ba17fa2f3640b92b900 \
  --repository-commit 18c954d8604df4740c829ba17fa2f3640b92b900 \
  --run-id "gate19.2-live-$(date -u +%Y%m%dT%H%M%SZ)" \
  --opslens-commit-sha "$(git rev-parse HEAD)" \
  --github-token-env GITHUB_TOKEN \
  --ghsa-silver-max-bytes "$OPSLENS_GHSA_SILVER_MAX_BYTES" \
  --nvd-silver-max-bytes "$OPSLENS_NVD_SILVER_MAX_BYTES" \
  --nvd-bronze-max-bytes "$OPSLENS_NVD_BRONZE_MAX_BYTES" \
  --kev-bronze-max-bytes "$OPSLENS_KEV_BRONZE_MAX_BYTES" \
  --epss-bronze-max-bytes "$OPSLENS_EPSS_BRONZE_MAX_BYTES" \
  --output labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
```

If running unauthenticated against public GitHub, remove this line entirely:

```text
--github-token-env GITHUB_TOKEN
```

Do not retry the entire command automatically. A failed run is separate evidence and must be understood before another human attempt receives a new run id/output decision.

## Operator checklist before pressing Enter

- [ ] current `HEAD` is the exact reviewed/green commit intended for the artifact;
- [ ] working tree has no unexpected change;
- [ ] `uv lock --check`, Ruff, Pyright, unit tests, and measurement-contract verifier pass;
- [ ] `aws sts get-caller-identity` shows the intended existing identity;
- [ ] no IAM/resource/public-endpoint change is planned;
- [ ] bundle and locator manifest correspond to the frozen CVE/GHSA anchor;
- [ ] source byte limits were reviewed explicitly;
- [ ] repository URL, ref, and commit exactly match the frozen anchor;
- [ ] KB/data-source/source-bucket/model coordinates exactly match retained resources;
- [ ] output artifact path does not already exist;
- [ ] no third-party repository code will be executed;
- [ ] PR #89 is untouched.

## Measurement contract

The artifact records:

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

Evidence semantics are separate from numeric values. Frozen coverage remains:

```text
GitHub HTTP requests:              MEASURED
Athena query count:                NOT_APPLICABLE
Athena bytes scanned:              NOT_APPLICABLE
Bedrock Retrieve count:            MEASURED
Bedrock Retrieve client latency:   MEASURED
Bedrock model call count:          MEASURED
Bedrock input tokens:              MEASURED
Bedrock output tokens:             MEASURED
Bedrock model client latency:      MEASURED
Bedrock model provider latency:    MEASURED
retry count:                       MEASURED
throttle count:                    UNMEASURED
```

Do not reinterpret a numeric zero for Athena or throttling as measurement authority. In particular, `throttle_count` remains `UNMEASURED` under the frozen experiment even if the numeric counter is zero.

Bedrock latency values come from retained invocation evidence:

- Retrieve client elapsed time: `BedrockRetrieveInvocationEvidence.client_elapsed_ms`;
- model client elapsed time: `BedrockHybridSynthesisInvocationEvidence.client_elapsed_ms`;
- provider model latency: `BedrockHybridSynthesisInvocationEvidence.bedrock_latency_ms`.

## Successful evidence artifact

A successful admitted run is written atomically to:

```text
labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
```

The file contains bounded metadata only, including:

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
outcome = SUCCESS
public endpoint count = 0
new AWS resource count = 0
new IAM role/policy count = 0
third-party repository code executions = 0
```

The artifact must not contain credentials, authorization headers, raw provider response bodies, full prompts, or retrieved source text.

The writer fsyncs already-admitted bytes to a same-directory temporary file and publishes the final path using create-without-replace semantics. A prior or concurrently created artifact is never overwritten.

## Failure-path validation

The implementation has offline tests for frozen-coordinate rejection, provider/executor failure, artifact byte admission, and no-overwrite persistence. For the human lab, validate at least one deterministic fail-closed input path **before paid provider execution**, for example by changing the repository ref to `main` while leaving all other inputs unchanged.

Expected behavior:

```text
exit != 0
no final artifact created
no fallback repository/model/KB selected
no missing measurement backfilled as zero
```

Do not turn that deliberate failure test into a second live success attempt automatically.

## After the successful run

Inspect and preserve the artifact, then verify at minimum:

```bash
python -m json.tool labs/evidence/phase-19-gate-19-2-live-measurement-v1.json >/dev/null
sha256sum labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
```

On macOS, use `shasum -a 256` instead of `sha256sum` if necessary.

Review:

1. exact OpsLens commit and frozen repository commit;
2. all nine stage durations in order;
3. GitHub physical request count;
4. Bedrock Retrieve count/latency;
5. model count/tokens/client/provider latency;
6. retries;
7. Athena classifications remain `NOT_APPLICABLE`;
8. throttle classification remains `UNMEASURED`;
9. safety counters remain exactly zero;
10. final result hash and serialized byte count are present.

## Runtime decision after measurement

Only after the live artifact exists and passes deterministic review may Gate 19.2 evaluate:

```text
SYNC
ASYNC
DEFERRED_PENDING_MEASUREMENT
```

The decision must be derived from the measured workload characteristics and retained service limits, not from the prior `ASYNC_SUBMIT_STATUS_RESULT` hypothesis.

If the evidence is incomplete, inconsistent, or still materially insufficient for the topology decision, retain:

```text
DEFERRED_PENDING_MEASUREMENT
```

## Stop conditions

Stop immediately if:

- a required permission is absent;
- an operation would create or mutate AWS/IAM/public runtime resources;
- the repository would need to be cloned, built, installed, tested, or otherwise executed;
- provider identity, exact repository commit, or source evidence cannot be established;
- S3 threat-authority materialization cannot complete before the measured workload;
- retrieval provenance/catalog admission fails;
- measurement instrumentation cannot preserve `UNMEASURED` vs real zero;
- a fallback would change repository, model, KB, data source, or runtime;
- the workload would require touching PR #89;
- any deterministic admission/provenance contract fails.

A stopped run is preferable to manufacturing measurement authority.
