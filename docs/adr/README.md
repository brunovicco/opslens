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
