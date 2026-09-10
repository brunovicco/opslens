# OpsLens — AIP-C01 Evidence Learning Map

_Last updated: 2026-09-10_

OpsLens is also used as a hands-on laboratory for **AWS Certified Generative AI Developer - Professional (AIP-C01)**. This map connects the current 2026 exam-guide tasks to repository evidence without turning certification coverage into product requirements.

> **AIP-C01 topic != product requirement.**

> **Exam coverage != certification guarantee.**

## Evidence states

`EVIDENCED` means substantial repository work directly exercises the core engineering concerns of the task. `PARTIAL` means OpsLens exercises part of the task while important examples or subskills remain study-only. `STUDY_ONLY` means no product-backed implementation evidence is claimed.

These states are intentionally qualitative. They are not a readiness score, pass probability, or claim that every service/example listed in the exam guide has been implemented.

## Exam domains

| Domain | Weight | OpsLens orientation |
| --- | ---: | --- |
| 1 — Foundation Model Integration, Data Management, and Compliance | 31% | Bedrock, corpus/data admission, S3 Vectors, retrieval, prompt/output contracts |
| 2 — Implementation and Integration | 26% | Agents, Bedrock APIs, AgentCore experiment, MCP/A2A, enterprise integration |
| 3 — AI Safety, Security, and Governance | 20% | deterministic authority, IAM, adversarial tests, telemetry minimization, governance evidence |
| 4 — Operational Efficiency and Optimization for GenAI Applications | 12% | cost/resource envelopes, topology optimization, observability |
| 5 — Testing, Validation, and Troubleshooting | 11% | frozen evals, comparability, failure paths, operational troubleshooting |

## Task mapping

| Task | Status | Primary OpsLens evidence |
| --- | --- | --- |
| 1.1 Analyze requirements and design GenAI solutions. | EVIDENCED | architecture; Phase 17 closeout |
| 1.2 Select and configure FMs. | PARTIAL | bounded Bedrock reasoning; topology retention decisions |
| 1.3 Implement data validation and processing pipelines for FM consumption. | EVIDENCED | canonical corpus; Bedrock KB ADR |
| 1.4 Design and implement vector store solutions. | EVIDENCED | Bedrock KB + Amazon S3 Vectors |
| 1.5 Design retrieval mechanisms for FM augmentation. | EVIDENCED | retrieval evaluation; hybrid routing |
| 1.6 Implement prompt engineering strategies and governance for FM interactions. | PARTIAL | semantic planner + bounded synthesis contracts |
| 2.1 Implement agentic AI solutions and tool integrations. | EVIDENCED | capability authorization; MCP; A2A |
| 2.2 Implement model deployment strategies. | PARTIAL | direct Bedrock vs bounded AgentCore hosting experiment |
| 2.3 Design and implement enterprise integration architectures. | EVIDENCED | event-driven AWS architecture; CI/CD boundaries |
| 2.4 Implement FM API integrations. | EVIDENCED | Bedrock planner/reasoning APIs and deterministic admission |
| 2.5 Implement application integration patterns and development tools. | PARTIAL | observability/CI/CD/integration tooling |
| 3.1 Implement input and output safety controls. | EVIDENCED | adversarial authority regressions; output admission |
| 3.2 Implement data security and privacy controls. | PARTIAL | least-privilege IAM; content-minimized telemetry |
| 3.3 Implement AI governance and compliance mechanisms. | EVIDENCED | ADR/evidence trail; CI enforcement; explicit deferrals |
| 3.4 Implement responsible AI principles. | PARTIAL | groundedness/abstention/negative evidence; broader fairness remains study-only |
| 4.1 Implement cost optimization and resource efficiency strategies. | EVIDENCED | Gate 18.3 cost accounting and configured limits |
| 4.2 Optimize application performance. | EVIDENCED | measured Phase 11/12 comparison and simpler-topology retention |
| 4.3 Implement monitoring systems for GenAI applications. | EVIDENCED | Phase 10 observability; telemetry hardening |
| 5.1 Implement evaluation systems for GenAI. | EVIDENCED | frozen hybrid evals; Gates 18.1/18.2 |
| 5.2 Troubleshoot GenAI applications. | EVIDENCED | failure-path labs, typed errors, traces/metrics, recovery controls |

Machine-readable mapping: `labs/evidence/phase-18-gate-18-4-aip-c01-evidence-map-v1.json`.

## Explicit study-only topics

The exam guide covers a broader AWS service surface than the current product needs. Topics kept intentionally outside the retained OpsLens implementation include Amazon Bedrock Guardrails; Bedrock Prompt Management and Prompt Flows; SageMaker custom FM training/fine-tuning and Model Registry; Bedrock provisioned throughput; dedicated PII discovery with services such as Macie/Comprehend; and public API Gateway/WAF/tenant-quota patterns while OpsLens has no retained public HTTP runtime.

These are study gaps, not product defects. A service is added to OpsLens only when a concrete architecture requirement and evidence justify it.

## Study method

For each task, use the referenced ADR/lab as the implementation anchor, then study the broader exam-guide examples separately. Be able to explain not only *what* OpsLens implemented but also the AWS alternatives, trade-offs, IAM boundary, cost model, observability signal, failure mode, and why an exam-topic service may be inappropriate for this workload.
