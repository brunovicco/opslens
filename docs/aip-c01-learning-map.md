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
| 2 — Implementation and Integration | 26% | Agents, Bedrock APIs, AgentCore experiment, MCP/A2A, enterprise/public integration patterns |
| 3 — AI Safety, Security, and Governance | 20% | deterministic authority, IAM, adversarial tests, telemetry minimization, governance evidence |
| 4 — Operational Efficiency and Optimization for GenAI Applications | 12% | cost/resource envelopes, topology optimization, observability, workload measurement |
| 5 — Testing, Validation, and Troubleshooting | 11% | frozen evals, comparability, failure paths, operational troubleshooting |

## Task mapping

| Task | Status | Primary OpsLens evidence |
| --- | --- | --- |
| 1.1 Analyze requirements and design GenAI solutions. | EVIDENCED | architecture; Phase 17/18 closeout; Phase 19 workload-first launch contract |
| 1.2 Select and configure FMs. | PARTIAL | bounded Bedrock reasoning; topology retention decisions |
| 1.3 Implement data validation and processing pipelines for FM consumption. | EVIDENCED | canonical corpus; Bedrock KB ADR |
| 1.4 Design and implement vector store solutions. | EVIDENCED | Bedrock KB + Amazon S3 Vectors |
| 1.5 Design retrieval mechanisms for FM augmentation. | EVIDENCED | retrieval evaluation; hybrid routing |
| 1.6 Implement prompt engineering strategies and governance for FM interactions. | PARTIAL | semantic planner + bounded synthesis contracts |
| 2.1 Implement agentic AI solutions and tool integrations. | EVIDENCED | capability authorization; MCP; A2A |
| 2.2 Implement model deployment strategies. | PARTIAL | direct Bedrock vs bounded AgentCore hosting experiment; public runtime remains measurement-gated |
| 2.3 Design and implement enterprise integration architectures. | EVIDENCED | event-driven AWS architecture; CI/CD boundaries; Gate 19.1 sync/async and responsibility decomposition |
| 2.4 Implement FM API integrations. | EVIDENCED | Bedrock planner/reasoning APIs; deterministic admission; Gate 19.1 public integration envelope |
| 2.5 Implement application integration patterns and development tools. | PARTIAL | observability/CI/CD/integration tooling; Gate 19.1 public launch contract |
| 3.1 Implement input and output safety controls. | EVIDENCED | adversarial authority regressions; output admission; public threat/abuse model |
| 3.2 Implement data security and privacy controls. | PARTIAL | least-privilege IAM; content-minimized telemetry; public telemetry deny-by-default fields |
| 3.3 Implement AI governance and compliance mechanisms. | EVIDENCED | ADR/evidence trail; CI enforcement; explicit deferrals; responsibility-to-permission model |
| 3.4 Implement responsible AI principles. | PARTIAL | groundedness/abstention/negative evidence; broader fairness remains study-only |
| 4.1 Implement cost optimization and resource efficiency strategies. | EVIDENCED | Gate 18.3 cost accounting/configured limits; Gate 19.1 request-level cost/abuse measurement contract |
| 4.2 Optimize application performance. | EVIDENCED | measured Phase 11/12 comparison; simpler-topology retention; Gate 19.1 workload-first sync/async decision rule |
| 4.3 Implement monitoring systems for GenAI applications. | EVIDENCED | Phase 10 observability; telemetry hardening; Gate 19.1 predeploy telemetry contract |
| 5.1 Implement evaluation systems for GenAI. | EVIDENCED | frozen hybrid evals; Gates 18.1/18.2 |
| 5.2 Troubleshoot GenAI applications. | EVIDENCED | failure-path labs, typed errors, traces/metrics, recovery controls, Gate 19.1 staged runtime measurement plan |

The Phase 18 machine-readable mapping remains `labs/evidence/phase-18-gate-18-4-aip-c01-evidence-map-v1.json`. Gate 19.1 extends the learning narrative but does not rewrite that historical Phase 18 evidence artifact or its 14 `EVIDENCED` / 6 `PARTIAL` count.

## Phase 19 learning focus

Gate 19.1 is particularly useful for AIP-C01 because it forces distinctions that commonly matter in Professional-level architecture scenarios:

```text
Lambda timeout != API integration timeout
configured throttle != guaranteed quota
SQS at-least-once != exactly-once business execution
service authentication != business authorization
component latency != end-to-end latency
configured limit != measured utilization
longer timeout available != synchronous architecture justified
AIP-C01 service example != OpsLens product requirement
```

The current gate studies API Gateway HTTP/REST integration envelopes, Lambda runtime/concurrency semantics, SQS duplicate-delivery implications, Bedrock/Athena permission responsibilities, denial-of-wallet controls, and predeployment observability. It deliberately does **not** deploy those services until the workload supports the decision.

## Explicit study-only topics

The exam guide covers a broader AWS service surface than the current product needs. Topics kept intentionally outside the retained OpsLens implementation include Amazon Bedrock Guardrails; Bedrock Prompt Management and Prompt Flows; SageMaker custom FM training/fine-tuning and Model Registry; Bedrock provisioned throughput; dedicated PII discovery with services such as Macie/Comprehend; and concrete public API Gateway/WAF/tenant-quota implementation while OpsLens still has no retained public HTTP runtime.

Phase 19 can move some public integration topics from design study into hands-on evidence later, but only after representative workload measurement justifies a concrete runtime. These remain study gaps, not product defects.

## Study method

For each task, use the referenced ADR/lab as the implementation anchor, then study the broader exam-guide examples separately. Be able to explain not only *what* OpsLens implemented but also the AWS alternatives, trade-offs, IAM boundary, cost model, observability signal, failure mode, and why an exam-topic service may be inappropriate for this workload.
