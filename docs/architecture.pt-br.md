# Arquitetura do OpsLens

_Última atualização: 2026-09-11_

Este documento é o baseline arquitetural acumulado atual até a **Phase 19 — Bounded Public Runtime & Productization, Gate 19.2**.

As Phases 0–18 estão completas. A Phase 19 é a fase atual de productization guiada por evidência. A Gate 19.2 selecionou o padrão de interação async submit/status/result com base em evidência representativa admitida, enquanto a topologia AWS pública concreta permanece intencionalmente não selecionada.

## 1. Propósito

OpsLens é uma plataforma open source de software supply chain e threat intelligence construída na AWS.

Objetivo do produto:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência exata prova isso, quais findings devo priorizar e qual orientação verificável pode me ajudar a agir?

Invariante central:

> **Agents reason. Code verifies evidence.**

Fronteiras permanentes:

> **MCP is an interoperability boundary, not new business authority.**

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **No unrestricted text-to-SQL.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

Regras adicionais retidas:

```text
retrieved content != instruction authority
model proposal != authorization
capability invocation != execution result
execution result != admitted evidence
tool/protocol success != business truth
historical evidence != standing authority
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
AIP-C01 topic != product requirement
```

## 2. Modelo de autoridade

Código determinístico continua sendo autoridade para identidade de fonte/evidência, normalização e aplicabilidade, reconciliação CVE/GHSA/NVD, fatos KEV/EPSS/CVSS/Risk Policy, parsing/compilação de consultas estruturadas, admissão/completude de retrieval, identidade de citações/saída, autorização e admissão de capabilities, handoffs de agentes/MCP/A2A, correlação de runtime evidence, limites de recurso/custo e recovery control via Terraform.

Modelos e agentes podem classificar, propor, resumir, explicar ou sintetizar sobre evidência já admitida. Um serviço gerenciado AWS ou uma saída sintaticamente válida do modelo não vira autoridade de negócio por si só.

## 3. Forma retida da plataforma

### 3.1 Threat intelligence e repository risk determinístico

```text
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
 -> raw evidence preservada por fonte
 -> normalização e aplicabilidade determinísticas
 -> evidência imutável de dependências do repositório
 -> correlação determinística de vulnerabilidades
 -> RepositoryAnalysisResult
 -> Risk Policy v1 determinística
 -> RiskPrioritizationResult
```

### 3.2 Repository intelligence

```text
requisição de repositório público GitHub
 -> admissão estrita
 -> metadata confirmada pela fonte
 -> snapshot em commit imutável
 -> evidência inerte de uv.lock no commit exato
 -> parsing TOML determinístico
 -> identidade canônica PyPI
 -> aplicabilidade determinística de vulnerabilidades
```

O caminho retido lê dados apenas. Não executa package managers, builds, testes, setup hooks, workflows, Dockerfiles, scripts ou código do repositório.

### 3.3 Caminho estruturado em linguagem natural

```text
pergunta factual em linguagem natural
 -> proposta limitada de planner via Bedrock
 -> parser determinístico
 -> SemanticQuery tipada
 -> compilador SQL determinístico
 -> Athena read-only limitada
 -> evidência estruturada
```

### 3.4 Caminho semântico de remediação

```text
fontes oficiais explicitamente fixadas
 -> corpus canônico determinístico
 -> S3
 -> Bedrock Knowledge Base
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> Retrieve limitado
 -> admissão de provenance/hash
 -> contexto determinístico
 -> síntese limitada com Bedrock Converse
 -> citação determinística
```

Baseline atual:

```text
embedding model:       amazon.titan-embed-text-v2:0
embedding dimensions:  1024
embedding data type:   FLOAT32
vector store:          Amazon S3 Vectors
distance:              cosine
chunking:              NONE
canonical chunks:      9
synthesis profile:     us.anthropic.claude-haiku-4-5-20251001-v1:0
```

### 3.5 Caminho híbrido de evidência

```text
EvidenceNeed[]
 -> autoridade determinística de rota
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> aquisição/admissão por classe
 -> ALL_REQUIRED
 -> HybridEvidenceEnvelope
 -> fatos F* + citações S*
 -> síntese limitada
 -> admissão determinística de saída
```

Hybrid significa **roteamento/composição híbridos de evidência**, não uma afirmação automática de keyword + vector search.

## 4. Fronteiras agentic e de interoperabilidade

A Phase 11 retém reasoning direto Bedrock single-agent como referência/default medida. A Phase 12 retém specialization/handoff determinísticos, mas rejeita como default a topologia de dois modelos por overhead sem quality lift. A Phase 13 retém MCP offline limitado. A Phase 14 retém AgentCore apenas como lab opcional. A Phase 15 retém interoperabilidade A2A offline sem runtime A2A público.

## 5. Fronteira de runtime exposure

A Phase 16 retém uma fronteira tipada read-only do Amazon Inspector. A leitura medida retornou zero registros; isso não equivale a `runtime exposure = zero`. Repository risk e runtime exposure permanecem classes de evidência separadas.

## 6. Fundação AWS e recursos permanentes

```text
environment:             dev
primary Region:          us-east-1
IaC:                     Terraform
human administration:    AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           padrões CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
knowledge retrieval:     Amazon Bedrock Knowledge Base + Amazon S3 Vectors
compute:                  AWS Lambda para ingestion/transformation retidas
recurring triggers:      Amazon EventBridge Scheduler
```

A arquitetura permanente ainda não afirma endpoint HTTP público, application compute público, runtime MCP/A2A público, AgentCore público, superfície production multi-tenant ou result store público.

## 7. Estado retido de Security Hardening

A Phase 17 retém protected-main security invariants, Actions em SHA completo, Dependency Review, CodeQL, adversarial authority tests, telemetry content-minimized e recovery Terraform-owned para exatamente três schedules recorrentes.

```text
aws_scheduler_schedule.epss_daily
aws_scheduler_schedule.kev_daily
aws_scheduler_schedule.nvd_incremental_hourly
```

`scheduled_ingestion_enabled=false` é scheduled-ingestion pause, não global kill switch.

## 8. Fronteira da Phase 18

A Phase 18 está completa pelo protected PR #290 em `feca774535b7d83f57c26f4e9fe7da71ce268f0f`. O closeout histórico preserva intencionalmente o estado pré-merge.

```text
MEASURED
DERIVED
UNMEASURED
NOT_APPLICABLE
CONFIGURED_LIMIT
```

Permanecem válidos `configured limit != measured utilization`, `lab metric != production SLO`, `cost evidence != production TCO` e `portfolio claim != new evidence authority`.

## 9. Phase 19 — Bounded Public Runtime & Productization

### 9.1 Fronteira inicial do public analysis

A Phase 9 encerrou deliberadamente em um application handoff:

```text
JSON não confiável
 -> admissão <= 2.048 bytes
 -> coordenadas GitHub validadas
 -> evidência imutável
 -> planejamento semântico metadata-only e limitado
 -> admissão determinística public-v1
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

A operação `analyze_public_repository` exige `remediation_guidance`, `risk_priority` e `vulnerability_facts` com completude `ALL_REQUIRED`.

### 9.2 Contrato histórico da Gate 19.1

A Gate 19.1 congelou:

```text
public-analysis-workload:v1
```

Sua decisão histórica permanece explicitamente preservada como:

```text
DEFERRED_PENDING_MEASUREMENT
```

com hipótese principal:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

A Gate 19.1 não criou endpoint público, worker, queue, result store ou runtime IAM. Esse marcador histórico permanece na documentação corrente para que a evidência da Gate 19.2 não reescreva retrospectivamente a autoridade da Gate 19.1.

### 9.3 Composição representativa da Gate 19.2

```text
public_request_admission
 -> repository_acquisition
 -> dependency_evidence
 -> vulnerability_correlation
 -> risk_prioritization
 -> structured_evidence
 -> semantic_evidence
 -> model_reasoning
 -> result_admission
```

O anchor atual é `openedx/mockprock` no commit exato `18c954d8604df4740c829ba17fa2f3640b92b900`, com `uv.lock` inerte, `webob==1.8.10`, GHSA `GHSA-6hx8-3wjj-gr8g` e CVE `CVE-2026-54770`. Isso estabelece reprodutibilidade, não runtime exposure.

### 9.4 Evidência medida da Gate 19.2

A execução human-operated ocorreu uma única vez a partir do protected main `e45ba419414e6dd77ecad68f4d2312e9123c2223`.

```text
artifact: labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id: gate19.2-live-20260911T131121Z
outcome: SUCCESS
```

```text
end_to_end_duration_ms                  17748
serialized_result_bytes                 5285
GitHub physical HTTP requests              4     MEASURED
Athena query count                         0     NOT_APPLICABLE
Athena bytes scanned                       0     NOT_APPLICABLE
Bedrock Retrieve count                     1     MEASURED
Bedrock Retrieve client elapsed ms      4148     MEASURED
Bedrock model call count                   1     MEASURED
Bedrock input tokens                    5936     MEASURED
Bedrock output tokens                    408     MEASURED
Bedrock model client elapsed ms         8901     MEASURED
Bedrock provider latency ms             7772     MEASURED
retry count                                0     MEASURED
throttle count                             0     UNMEASURED
```

Os estágios Bedrock somaram `13.098 ms`, ou `73,80%` do end-to-end. Zero numérico não substitui semântica de evidência.

### 9.5 Decisão do padrão de interação

A Gate 19.2 seleciona:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

O success path medido terminou em `17.748 ms`; não houve timeout medido. A decisão vem de retry safety, provider-latency coupling, backpressure e failure isolation.

```text
baseline measured E2E                                      17748 ms   MEASURED
+ one additional model-equivalent client elapsed           26649 ms   DERIVED
+ one additional Retrieve-equivalent and model-equivalent  30797 ms   DERIVED
reference synchronous envelope                             30000 ms   RETAINED FACT
```

Os valores derivados não são medições live adicionais.

### 9.6 Runtime concreto permanece não selecionado

```text
ASYNC_SUBMIT_STATUS_RESULT     SELECTED_INTERACTION_PATTERN
API Gateway                    UNSELECTED
Lambda                         UNSELECTED
SQS                            UNSELECTED
DynamoDB                       UNSELECTED
Step Functions                 UNSELECTED
ECS/Fargate                    UNSELECTED
WAF                            UNSELECTED
AgentCore public runtime       UNSELECTED
```

A Gate 19.2 não autoriza endpoint, queue, worker, result store, recurso AWS ou IAM role/policy.

### 9.7 Próxima responsabilidade de topologia

O próximo gate deve congelar fronteiras para ingress admission, repository acquisition, job submission/coordination, worker execution, Bedrock retrieval/model invocation, optional result/status persistence e telemetry emission antes da materialização de IAM.

```text
concrete runtime responsibility
 -> required service action
 -> exact resource
 -> IAM statement
```

### 9.8 Lifecycle async, abuse e backpressure

O próximo gate deve definir job identity, idempotency, duplicate-delivery handling, retry ownership, status lifecycle, result retention/integrity, concurrency/backpressure, public identity/rate controls, cost amplification controls e disable/cancellation boundaries.

### 9.9 Custo e observabilidade

A Gate 19.2 fornece medição real de workload completo para um run representativo, mas não fabrica SLOs ou TCO de produção. Queue operations, delivery attempts, worker concurrency, result-store operations, status reads, retention/storage e aggregate model-call budget tornam-se obrigações de medição apenas se os respectivos componentes forem selecionados.

Telemetry permanece content-minimized. Full prompts, source code, repository file contents, full model responses, credentials, sensitive tokens e raw user payloads permanecem proibidos por default.

### 9.10 Disable/recovery

Antes de deployment público, controles devem ser explicitamente escopados: ingress disable, new-job admission disable, queue-consumer pause se aplicável, model-invocation disable, result-publication disable se aplicável e background-ingestion pause já comprovado. O scheduler pause da Phase 17 não é global kill switch.

### 9.11 Próxima fronteira arquitetural

Após o protected merge do closeout da Gate 19.2, o próximo gate da Phase 19 deve congelar a menor arquitetura async concreta de ingress/job/result e o modelo least-privilege de responsabilidades **antes** do deployment.

Nenhum serviço AWS é selecionado apenas porque é comum em sistemas async ou aparece no AIP-C01.

## 10. Authority impact da Gate 19.2

```text
public endpoints:                       0
new AWS resources:                      0
new IAM roles/policies:                 0
third-party repository code executions: 0
PR #89 modifications:                  0
```

## 11. Evidência canônica da Phase 19

Gate 19.1:

- `docs/adr/0076-bounded-public-runtime-hypothesis-and-launch-contract.md`
- `labs/phase-19-gate-19-1-public-runtime-hypothesis.md`
- `labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`
- `scripts/verify_phase19_gate19_1_public_runtime_contract.py`

Gate 19.2:

- `labs/phase-19-gate-19-2-human-live-measurement-runbook.md`
- `labs/evidence/phase-19-gate-19-2-live-measurement-v1.json`
- `scripts/verify_phase19_gate19_2_live_measurement.py`
- `labs/phase-19-gate-19-2-closeout.md`
- `labs/evidence/phase-19-gate-19-2-closeout-v1.json`
- `scripts/verify_phase19_gate19_2_closeout.py`

PR #89 permanece como trabalho deferred separado do Governed LLM Gateway e não é dependência da Phase 19, salvo reavaliação explícita futura.
