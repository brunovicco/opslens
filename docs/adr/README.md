# Architecture Decision Records

Architecture Decision Records document significant OpsLens decisions whose rationale should remain traceable over time.

ADRs are added only for decisions with meaningful architectural trade-offs.

## Records

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-terraform-state-strategy.md) | Terraform state strategy | Accepted |
| [0002](0002-github-actions-oidc.md) | GitHub Actions OIDC deployment identity | Accepted |
| [0003](0003-aws-region-strategy.md) | AWS regional strategy | Accepted |
| [0004](0004-nvd-ingestion-and-versioning-strategy.md) | NVD ingestion and vulnerability versioning strategy | Accepted |
| [0005](0005-ghsa-source-and-synchronization-strategy.md) | GitHub Security Advisory source and synchronization strategy | Accepted |
| [0006](0006-ghsa-silver-content-versioning-and-physical-shape.md) | GHSA Silver content versioning and physical shape | Accepted |
| [0007](0007-ghsa-runtime-credential-and-retry-strategy.md) | GHSA runtime credential and retry strategy | Accepted |
| [0008](0008-pypi-correlation-semantics.md) | Start vulnerability correlation with PyPI semantics | Accepted |
| [0009](0009-immutable-public-repository-snapshot.md) | Use exact GitHub commit identity for repository snapshots | Accepted |
| [0010](0010-bounded-read-only-github-rest-transport.md) | Bound public GitHub REST acquisition before dependency reads | Accepted |
| [0011](0011-immutable-uv-lock-evidence.md) | Bind `uv.lock` evidence to an exact immutable repository snapshot | Accepted |
| [0012](0012-deterministic-uv-lock-parser.md) | Parse verified `uv.lock` evidence deterministically | Accepted |
| [0013](0013-phase3-pypi-normalization-bridge.md) | Normalize locked PyPI records through the Phase 3 identity contract | Accepted |
| [0014](0014-deterministic-repository-vulnerability-findings.md) | Emit deterministic repository vulnerability findings from normalized lock and GHSA evidence | Accepted |
| [0015](0015-repository-nvd-cvss-enrichment.md) | Enrich repository findings with exact NVD and CVSS evidence | Accepted |
| [0016](0016-repository-kev-snapshot-enrichment.md) | Enrich repository findings from a complete CISA KEV snapshot | Accepted |
| [0017](0017-repository-epss-snapshot-enrichment.md) | Enrich repository findings from one exact EPSS score snapshot | Accepted |
| [0018](0018-repository-analysis-result-projection.md) | Project the final repository analysis result and defer cache infrastructure | Accepted |
| [0019](0019-deterministic-risk-policy-v1.md) | Prioritize repository findings with deterministic Risk Policy v1 | Accepted |
| [0020](0020-no-unrestricted-text-to-sql.md) | Reject unrestricted text-to-SQL in the Semantic Query Layer | Accepted |
| [0021](0021-bounded-bedrock-semantic-query-planner.md) | Bound Bedrock semantic planning before model invocation | Accepted |
| [0022](0022-customer-managed-bedrock-kb-with-s3-vectors.md) | Use a customer-managed Bedrock Knowledge Base with S3 Vectors | Accepted |
| [0023](0023-bounded-bedrock-knowledge-synthesis.md) | Bound Bedrock knowledge synthesis after deterministic context admission | Accepted |
| [0024](0024-phase7-runtime-iam-boundary.md) | Freeze the future least-privilege Phase 7 application runtime IAM boundary | Accepted |
| [0025](0025-deterministic-hybrid-routing-authority.md) | Freeze deterministic hybrid routing and authority semantics | Accepted |
| [0026](0026-deterministic-hybrid-evidence-envelope.md) | Preserve authority classes in deterministic hybrid evidence | Accepted |
| [0027](0027-frozen-hybrid-evaluation-contract.md) | Freeze hybrid evaluation cases and independent metric dimensions before synthesis | Accepted |
| [0028](0028-bounded-route-aware-hybrid-synthesis.md) | Bound model synthesis behind deterministic hybrid route/evidence authority | Accepted |
| [0029](0029-public-repository-request-admission.md) | Admit public repository requests as validated coordinates, not fetch URLs | Accepted |
| [0030](0030-public-semantic-planning-authority.md) | Keep public semantic planning proposal-only and deterministic-scope admitted | Accepted |
| [0031](0031-phase9-public-analysis-closeout.md) | Close Phase 9 at the governed application boundary, not a fictional public runtime | Accepted |
| [0032](0032-content-minimized-operational-telemetry-contract.md) | Treat operational telemetry as content-minimized evidence, not execution authority | Accepted |
| [0033](0033-governed-operational-orchestration-instrumentation.md) | Instrument governed public analysis without moving deterministic authority | Accepted |
| [0034](0034-bounded-cloudwatch-emf-telemetry-adapter.md) | Adapt admitted operational evidence to bounded CloudWatch EMF without deploying runtime authority | Accepted |
| [0035](0035-phase10-observability-closeout.md) | Close Phase 10 at the proven observability boundary and defer production runtime claims | Accepted |
| [0036](0036-bounded-single-agent-capability-authorization.md) | Separate agent action proposal from deterministic capability authorization before execution | Accepted |
| [0037](0037-typed-single-agent-capability-execution.md) | Bind authorized actions to exact typed invocation and result admission | Accepted |
| [0038](0038-offline-single-agent-evaluation-before-runtime.md) | Freeze deterministic single-agent evaluation before real model reasoning | Accepted |
| [0039](0039-bounded-single-agent-model-reasoning.md) | Add one bounded provider-neutral model reasoning step behind deterministic authorization | Accepted |
| [0040](0040-preserve-measured-reasoning-baseline-without-premature-optimization.md) | Preserve the measured reasoning baseline when no material optimization target is observed | Accepted |
| [0041](0041-phase11-single-agent-baseline-closeout.md) | Close Phase 11 at the bounded single-agent reference before multi-agent complexity | Accepted |
| [0042](0042-bounded-multi-agent-specialization-handoff.md) | Bound multi-agent specialization before adding another model call | Accepted |
| [0043](0043-freeze-multi-agent-comparison-before-second-model-call.md) | Freeze deterministic multi-agent comparison before a second model call | Accepted |
| [0044](0044-first-bounded-real-two-model-comparison.md) | Measure the first bounded real two-model topology without moving authority into models | Accepted |
| [0045](0045-do-not-retain-two-model-topology-without-measured-lift.md) | Retain the simpler single-agent reference and deterministic handoff boundary when the two-model topology adds material overhead without measured lift | Accepted |
