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
| [0046](0046-phase12-multi-agent-closeout.md) | Close Phase 12 around the measured retained architecture rather than the most complex experiment | Accepted |
| [0047](0047-bounded-mcp-capability-exposure.md) | Expose only already-bounded typed capability invocations through a closed MCP identity and admission contract | Accepted |
| [0048](0048-bounded-offline-mcp-protocol-adapter.md) | Prove official MCP interoperability offline while keeping protocol input reference-only and the SDK out of deployed runtime dependencies | Accepted |
| [0049](0049-bounded-mcp-capability-execution-bridge.md) | Bind MCP admission to the existing typed capability executor while keeping business-result transport separate | Accepted |
| [0050](0050-bounded-mcp-structured-result-projection.md) | Project only explicitly allowlisted structured-security business results through MCP after typed execution/result admission | Accepted |
| [0051](0051-phase13-mcp-closeout.md) | Close Phase 13 at the bounded offline MCP boundary rather than inventing a public/deployed runtime without a concrete requirement | Accepted |
| [0052](0052-agentcore-runtime-capability-fit.md) | Use AgentCore Runtime only for a bounded HTTP/SigV4 hosting experiment before capability execution | Accepted |
| [0053](0053-bounded-agentcore-direct-code-public-network-experiment.md) | Use the reproducible direct-code package and a time-bounded PUBLIC network exception for the first AgentCore Runtime experiment | Accepted |
| [0054](0054-retain-agentcore-only-as-optional-lab-target.md) | Retain AgentCore Runtime only as an optional lab target rather than the default OpsLens reasoning runtime | Accepted |
| [0055](0055-remove-standing-agentcore-experiment-iam.md) | Remove standing GitHub AgentCore experiment IAM after the retention decision while preserving the optional lab and service-linked-role safety boundary | Accepted |
| [0056](0056-bounded-a2a-capability-fit.md) | Authorize one bounded offline reference-only A2A interoperability experiment before any network or execution authority | Accepted |
| [0057](0057-bounded-offline-a2a-reference-adapter.md) | Retain a strict offline A2A 1.0 reference adapter and defer any real peer runtime until independent conformance/value is proven | Accepted |
| [0058](0058-official-a2a-sdk-as-ci-conformance-oracle.md) | Use the official A2A SDK only as an isolated exact-source CI conformance oracle while keeping OpsLens admission authoritative | Accepted |
| [0059](0059-phase15-a2a-closeout.md) | Close Phase 15 at the bounded offline A2A interoperability boundary instead of creating an unjustified network runtime | Accepted |
| [0060](0060-bounded-amazon-inspector-runtime-evidence-fit.md) | Treat Amazon Inspector as an independent runtime-evidence authority and authorize read-only discovery before activation or correlation | Accepted |
| [0061](0061-dedicated-temporary-inspector-discovery-role.md) | Use a dedicated temporary least-privilege Inspector discovery role instead of widening the shared GitHub deployment role | Accepted |
| [0062](0062-retain-inspector-read-contract-without-standing-iam-or-scan-activation.md) | Retain the bounded Inspector read/evidence contract while removing temporary IAM and avoiding scan activation solely to manufacture evidence | Accepted |
| [0063](0063-phase16-runtime-exposure-closeout.md) | Close Phase 16 at the proven read-only Inspector boundary with zero current records and no standing experiment IAM | Accepted |
| [0064](0064-evidence-first-security-hardening-priorities.md) | Prioritize Phase 17 hardening from a cross-cutting evidence inventory before changing authority | Accepted |
| [0065](0065-ci-cd-and-workflow-authority-hardening.md) | Harden CI/CD and workflow authority before adding broader security automation | Accepted |
| [0066](0066-bounded-dependency-and-code-scanning-signals.md) | Retain bounded dependency-review and CodeQL signals without moving business or AWS authority | Accepted |
| [0067](0067-bounded-adversarial-authority-regression-suite.md) | Retain a bounded offline adversarial authority regression suite without adding cloud/model/tool authority | Accepted |
| [0068](0068-content-minimized-lambda-telemetry.md) | Disable implicit Lambda event/response/error/traceback capture while retaining bounded operational telemetry | Accepted |
| [0069](0069-bounded-scheduled-ingestion-pause.md) | Pause only recurring source-ingestion scheduling through one bounded Terraform control without inventing a global kill switch | Accepted |
| [0070](0070-phase17-security-hardening-closeout.md) | Close Phase 17 at the evidence-backed security hardening boundary and advance to Phase 18 | Accepted |
| [0071](0071-cross-phase-evidence-classification-and-comparability.md) | Classify cross-phase evidence explicitly and compare only metrics with compatible measurement semantics | Accepted |
| [0072](0072-consolidated-evaluation-and-reliability-view.md) | Project retained evidence into an independent-dimension evaluation and reliability view without creating new comparison authority | Accepted |
| [0073](0073-cost-accounting-and-budget-envelopes.md) | Separate retained cost evidence from configured budget envelopes and forbid unsupported production TCO aggregation | Accepted |
| [0074](0074-portfolio-evidence-and-aip-c01-mapping.md) | Keep portfolio claims and AIP-C01 coverage evidence-bound without creating synthetic readiness or product authority | Accepted |
| [0075](0075-phase18-evaluation-cost-portfolio-closeout.md) | Close Phase 18 at the evidence-backed evaluation, cost, and portfolio boundary without pre-authorizing the next implementation phase | Accepted |
| [0076](0076-bounded-public-runtime-hypothesis-and-launch-contract.md) | Freeze an evidence-backed public workload and defer runtime topology until representative measurement | Accepted for Gate 19.1 |
| [0077](0077-phase19-v1-demonstration-boundary.md) | Close OpsLens V1 as a demonstration architecture lab rather than require production SaaS operations | Accepted for Gate 19.9 |
| [0078](0078-canonical-evidence-serialization.md) | Own JSON canonicalization in one module so evidence identity cannot diverge by encoding | Accepted |
| [0079](0079-retained-artifact-reproducibility.md) | Rebuild retained artifacts from the tree that produced them instead of from HEAD | Accepted |
| [0080](0080-self-applied-supply-chain-evidence.md) | Apply the supply-chain argument to this repository as identity, scanning and watching, without claiming a vulnerability verdict | Accepted |
| [0081](0081-installable-package-and-console-entry-points.md) | Ship the project as an installable package with console entry points paired to the repository scripts | Accepted |
