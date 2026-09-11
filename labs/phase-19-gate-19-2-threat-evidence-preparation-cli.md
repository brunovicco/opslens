# Phase 19 Gate 19.2 — Threat Evidence Preparation CLI

This command is a **human execution boundary** for read-only pre-measurement authority materialization. It is not part of the measured request-time workload and does not authorize AWS/IAM/public-runtime mutation.

## Preconditions

Use protected `main`, existing operator credentials, the previously built `CrossSourceCveEvidenceV1` JSON, and a separately admitted `RepresentativeThreatAuthorityLocatorManifestV1` containing exact immutable S3 `object_key + VersionId` coordinates.

Do not infer or discover locators during this command. If a required physical locator is unavailable, stop.

## Command

Choose explicit byte ceilings from the already-observed source object sizes plus a reviewed safety margin. Configured ceilings are limits, not measured utilization.

```bash
PYTHONPATH=src uv run python scripts/materialize_phase19_gate19_2_threat_evidence.py \
  --bundle /tmp/opslens-gate19-2-cross-source-evidence.json \
  --locator-manifest /tmp/opslens-gate19-2-authority-locators.json \
  --profile opslens-bootstrap \
  --region us-east-1 \
  --bucket opslens-dev-data-487757851499-us-east-1 \
  --ghsa-silver-max-bytes <reviewed-positive-limit> \
  --nvd-silver-max-bytes <reviewed-positive-limit> \
  --nvd-bronze-max-bytes <reviewed-positive-limit> \
  --kev-bronze-max-bytes <reviewed-positive-limit> \
  --epss-bronze-max-bytes <reviewed-positive-limit> \
  > /tmp/opslens-gate19-2-threat-evidence-preparation.json
```

The CLI configures the S3 client for one total SDK attempt and delegates all source decoding and admission to retained exact-reader/materialization contracts. It performs no S3 listing, locator discovery, `HeadObject`, writes, Athena queries, Bedrock calls, or model calls.

## Output boundary

The JSON output contains only bounded reproducibility metadata:

- input bundle SHA-256;
- locator-manifest SHA-256;
- CVE identity;
- GHSA/NVD authority counts;
- KEV snapshot date, catalog version, SHA-256, and record count;
- EPSS snapshot date, model version, SHA-256, and row count.

Raw KEV/EPSS payloads, credentials, authorization headers, session tokens, and source bodies are intentionally excluded.

## Interpretation

A successful preparation command proves only that the exact admitted physical source objects could be reconstructed and reconciled with the analytical bundle under the retained authority contracts. It is **not** a Gate 19.2 live workload measurement and does not select `SYNC` or `ASYNC`.

S3 calls here remain pre-measurement preparation. Request-time Gate 19.2 provider accounting remains unchanged, including:

```text
athena_query_count:   NOT_APPLICABLE
athena_bytes_scanned: NOT_APPLICABLE
throttle_count:       UNMEASURED unless explicitly instrumented
runtime decision:     DEFERRED_PENDING_MEASUREMENT
```

Stop rather than broaden permissions if existing credentials cannot read an admitted exact object version.
