# Phase 19 — Gate 19.10 Deterministic End-to-End Demo Runner

Status: **IN PROGRESS** until protected merge and post-merge verification complete.

Source protected main: `68a135a0c80dacb8cf0b668022796b159878637e`.  
Source issue: #378.  
Gate 19.9: PR #377 / merged / post-merge CodeQL run #414 success.

## Decision

Gate 19.10 implements the canonical V1 reviewer path as one offline deterministic execution:

```text
synthetic public repository fixture
 -> PublicAnalysisRequest
 -> PublicRepositoryEvidenceExecution
 -> retained GHSA/NVD/KEV/EPSS typed evidence
 -> deterministic Phase 3/4 applicability + enrichment
 -> RepositoryAnalysisResult
 -> deterministic Risk Policy v1
 -> stable text or canonical JSON reviewer projection
```

The demo is deliberately **not** a live repository scanner and does not claim that synthetic fixture evidence describes any real repository. Its purpose is to make the retained authority chain reproducible without AWS credentials or provider access.

## Canonical command

```bash
uv sync --frozen
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
```

Machine-readable form:

```bash
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format json
```

The JSON form is content-addressed and byte-stable for the frozen fixture.

## Scenario admitted in this gate

Only one scenario is admitted by Gate 19.10:

```text
material-vulnerability
```

Expected deterministic result:

```text
Requests 2.31.0
GHSA-demo-1910 / CVE-2026-12345
fixed version 2.32.0
KEV present
EPSS 0.42
selected CVSS 9.8
Risk Policy v1 score 90
priority P0
```

Gate 19.11 owns the full three-scenario suite, including controlled-benign and fail-closed incomplete/ambiguous evidence.

## Authority boundary

```text
AWS credentials required:                 NO
network after dependencies are installed: NO
live GitHub/AWS/Bedrock calls:             NO
model execution:                          NO
third-party repository code execution:    NO
Terraform/provider operations:             0
AWS mutations:                             0
IAM mutations:                             0
artifact publications:                     0
runtime enablements:                       0
PR #89 modifications:                     0
```

The repository fixture implements the existing read-only repository source protocol in memory. It never shells out to package managers, build systems, repository workflows, Dockerfiles, setup hooks, or third-party source code.

## Why this architecture

The demo runner does not reimplement vulnerability or risk rules. It constructs inert source evidence and then calls existing application/domain authority. That keeps the portfolio demonstration aligned with the production-style architecture already proven in earlier phases:

```text
Agents reason. Code verifies evidence.
READ, NEVER EXECUTE third-party repository code.
missing evidence != benign evidence
model proposal != authorization
demonstration readiness != production readiness
```

## Verification

The Gate 19.10 verifier must prove offline that:

- the machine-readable contract is intact;
- two independent runs are byte-identical;
- the content-addressed result identity is stable;
- the scenario produces exactly one deterministic P0 finding with score 90;
- text and JSON projections describe the same admitted result;
- demo source contains no provider/network/process execution dependency;
- unsupported scenarios and formats fail closed.

No protected merge is authorized by this lab document.
