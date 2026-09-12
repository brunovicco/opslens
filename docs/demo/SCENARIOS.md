# OpsLens V1 Demo Scenarios

OpsLens V1 admits exactly three canonical demonstration classes. Every fixture is synthetic, inert, offline, and content-addressed. Demo execution never runs package managers, builds, tests, setup hooks, repository workflows, Dockerfiles, or third-party repository code.

## 1. Material vulnerability

Command:

```bash
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
```

Purpose: prove that admitted dependency and threat evidence can produce a materially relevant finding, deterministic risk prioritization, and provenance.

Expected result:

```text
Requests 2.31.0
applicable synthetic advisory: yes
finding count: 1
Risk Policy v1: 90 / P0
```

The model has no authority over applicability or risk truth.

## 2. Controlled benign

Command:

```bash
uv run python scripts/demo_opslens.py --scenario controlled-benign --format text
```

Purpose: prove that complete admitted evidence may deterministically produce no material finding without confusing absence of a finding with missing evidence.

Expected result:

```text
Requests 2.32.0
applicable synthetic advisory: no
finding count: 0
scoped evidence complete: true
unsupported normalization: 0
benign claim scope: controlled fixture only
live repository safety claim: false
```

The no-finding result is valid only for the controlled fixture. It is not a claim that a live repository is safe.

## 3. Fail-closed incomplete evidence

Command:

```bash
uv run python scripts/demo_opslens.py --scenario fail-closed-incomplete-evidence --format text
```

Purpose: mechanically prove `missing evidence != benign evidence`.

The inert lock fixture contains an unsupported PyPI version identity. The existing threat-scope authority rejects the evidence before repository analysis or risk prioritization.

Expected result:

```text
state: REJECTED_INCOMPLETE_EVIDENCE
normalization reason: invalid_version
analysis performed: NO
risk prioritization performed: NO
benign conclusion: NO
```

No model call can convert incomplete evidence into benign truth.

## Deterministic suite evaluation

Run all three outcomes through the cross-scenario regression projection:

```bash
uv run python scripts/evaluate_opslens_demo.py --format text
uv run python scripts/evaluate_opslens_demo.py --format json
```

The evaluator does not create new business authority. It verifies that the scenarios remain distinct:

```text
material finding != controlled no-finding
controlled no-finding requires complete scoped evidence
controlled no-finding is limited to the controlled fixture only
incomplete evidence -> fail closed
missing evidence != benign evidence
```

## Rules

All canonical fixtures are inert data. The reviewer path requires no AWS credentials and no live provider/model execution after dependencies are installed.

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
missing evidence != benign evidence
```
