# OpsLens V1 Demo Scenarios

Gate 19.11 will admit exactly three canonical demonstration classes. Concrete fixture identities and hashes are intentionally deferred until Gate 19.10 establishes the demo runner contract.

## 1. Material vulnerability

Purpose: prove that admitted dependency and threat evidence can produce a materially relevant finding, deterministic risk prioritization, provenance, and a bounded explanation.

Expected authority properties:

- exact dependency identity;
- exact vulnerability applicability evidence;
- exact KEV/EPSS/NVD/GHSA provenance where available;
- deterministic risk result;
- explanation cannot change applicability or risk authority.

## 2. Controlled benign

Purpose: prove that complete admitted evidence may deterministically result in no material finding without conflating absence of a finding with missing evidence.

Expected authority properties:

- complete fixture evidence is explicit;
- no material finding is derived from admitted facts;
- result cannot be reused as evidence that a live repository is safe.

## 3. Fail-closed incomplete or ambiguous evidence

Purpose: prove `missing evidence != benign evidence`.

Expected authority properties:

- missing/ambiguous source coordinate is explicit;
- analysis fails closed or returns an explicit incomplete state;
- no model call can convert incomplete evidence into benign truth.

## Rules

All canonical fixtures must be inert data. Demo execution must never run package managers, builds, tests, setup hooks, repository workflows, Dockerfiles, or third-party repository code.
