# Arquitetura do OpsLens

_Última atualização: 2026-09-11_

Este documento é o baseline arquitetural acumulado atual até a **Phase 19 — Bounded Public Runtime & Productization, Gate 19.3**.

As Phases 0–18 estão completas. A Phase 19 é a fase atual de productization guiada por evidência. A Gate 19.2 selecionou o padrão de interação async submit/status/result com base em evidência representativa admitida. A Gate 19.3 agora seleciona a menor topologia async concreta como **autoridade de design apenas**; nenhum deployment público é autorizado.

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
responsibility -> required action -> exact resource -> IAM statement
AIP-C01 topic != product requirement
```

## 2. Modelo de autoridade

Código determinístico continua sendo autoridade para identidade de fonte/evidência, normalização e aplicabilidade, reconciliação CVE/GHSA/NVD, fatos KEV/EPSS/CVSS/Risk Policy, parsing/compilação de consultas estruturadas, admissão/completude de retrieval, identidade de citações/saída, autorização e admissão de capabilities, handoffs de agentes/MCP/A2A, correlação de runtime evidence, limites de recurso/custo e recovery control via Terraform.

Modelos e agentes podem classificar, propor, resumir, explicar ou sintetizar sobre evidência já admitida. Um serviço gerenciado AWS ou uma saída sintaticamente válida do modelo não vira autoridade de negócio por si só.

A Gate 19.3 estende a autoridade determinística para futura identidade de job público, binding de idempotência, transições de estado, admissão de duplicate delivery, limites de retry e admissão de status/result. Entrega pela fila é evidência de transporte, não verdade de estado do job.

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

Raw evidence de terceiros é preservada antes do enrichment. Versões exatas de fonte, snapshots imutáveis, hashes e identidades tipadas participam da provenance.

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

O modelo não possui autoridade para SQL arbitrário. O adapter Athena fixa database/workgroup, aceita apenas shapes compilados pelo código, limita rows/paginação, registra scan/timing evidence e aplica cancelamento best-effort no próprio polling timeout.

### 3.4 Caminho semântico de remediação

```text
fontes oficiais explicitamente fixadas
 -> corpus canônico determinístico
 -> publicação S3
 -> Bedrock Knowledge Base
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> Retrieve limitado
 -> admissão de provenance/hash
 -> montagem determinística de contexto
 -> síntese limitada com Bedrock Converse
 -> identidade determinística de citação
 -> avaliação de groundedness/support
```

`RetrieveAndGenerate` não é o default retido porque retrieval e synthesis são medidos e admitidos separadamente.

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

A arquitetura permanente **não** afirma atualmente endpoint HTTP público, application compute público, fila pública, result store público, runtime MCP/A2A público, AgentCore experiment runtime permanente, Inspector experiment IAM permanente ou superfície production multi-tenant.

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

A Gate 19.1 não criou endpoint público, worker, queue, result store ou runtime IAM. Gates posteriores não reescrevem essa decisão histórica.

### 9.3 Composição e evidência representativa da Gate 19.2

A Gate 19.2 compôs capacidades retidas em um workload representativo **não público**:

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

O anchor de medição foi `openedx/mockprock` no commit exato `18c954d8604df4740c829ba17fa2f3640b92b900`, com `uv.lock` inerte, `webob==1.8.10`, GHSA `GHSA-6hx8-3wjj-gr8g` e CVE `CVE-2026-54770`. Isso estabelece reprodutibilidade, não runtime exposure.

A execução human-operated ocorreu uma única vez a partir do protected main `e45ba419414e6dd77ecad68f4d2312e9123c2223`.

Artefato canônico:

```text
labs/evidence/phase-19-gate-19-2-live-measurement-v1.json
SHA-256: 04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114
run id: gate19.2-live-20260911T131121Z
outcome: SUCCESS
```

Evidência request-time medida:

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

Os estágios Bedrock somaram `13.098 ms`, ou `73,80%` do end-to-end. Zero numérico nunca substitui semântica de evidência.

### 9.4 Decisão do padrão de interação da Gate 19.2 — COMPLETE

A Gate 19.2 selecionou:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

O success path medido terminou em `17.748 ms`; ele **não** excedeu por si só o envelope HTTP API de referência de 30 segundos. A decisão vem de retry safety, provider-latency coupling, backpressure e failure isolation.

Cenários derivados preservam `MEASURED != DERIVED`:

```text
baseline measured E2E                                      17748 ms   MEASURED
+ one additional model-equivalent client elapsed           26649 ms   DERIVED
+ one additional Retrieve-equivalent and model-equivalent  30797 ms   DERIVED
reference synchronous envelope                             30000 ms   RETAINED FACT
```

A Gate 19.2 foi protected-merged pelo PR #347 em `71eda2650889d3047259d37be226862ed2a09092`. Ela não autorizou deployment público.

### 9.5 Decisão de topologia concreta da Gate 19.3 — DESIGN ONLY

A Gate 19.3 seleciona o identificador lógico:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

Forma selecionada:

```text
cliente público
  -> Amazon API Gateway HTTP API
  -> API Lambda
       -> tabela DynamoDB jobs/idempotency
       -> SQS standard job queue
            -> Lambda worker
                 -> autoridade determinística retida de repository/risk
                 -> Bedrock Knowledge Base Retrieve
                 -> invocação de modelo limitada retida
                 -> admissão determinística do resultado final
                 -> update de status/result no DynamoDB
       -> SQS dead-letter queue

leituras de status/result
  -> Amazon API Gateway HTTP API
  -> API Lambda
  -> tabela DynamoDB jobs
```

A seleção é evidência arquitetural apenas. A Gate 19.3 não cria nenhum desses recursos.

### 9.6 Comparação de candidatos

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB            SELECTED
HTTP_API_LAMBDA_DYNAMODB_STREAMS_LAMBDA        REJECTED
HTTP_API_LAMBDA_STEP_FUNCTIONS_STANDARD_LAMBDA REJECTED
FUNCTION_URL_LAMBDA_SQS_LAMBDA_DYNAMODB        REJECTED
HTTP_API_LAMBDA_SQS_FARGATE_DYNAMODB           REJECTED
```

Racional:

- HTTP API oferece uma fronteira gerenciada explícita de routing/rate sem selecionar capacidades exclusivas de REST API ainda não justificadas;
- API Lambda mantém request/idempotency/status determinísticos fora da latência provider-heavy do worker;
- SQS expressa diretamente buffering at-least-once, retry isolation e backpressure;
- DLQ limita poison/repeated delivery em vez de permitir redelivery ilimitado;
- o workload medido de `17.748 ms` não justifica Fargate/container scheduling;
- o resultado medido de `5.285` bytes e os requisitos de estado condicional/idempotência justificam DynamoDB em vez de armazenamento blob-scale;
- Step Functions Standard acrescenta orquestração não requerida por uma única operação linear de análise;
- DynamoDB Streams acopla dispatch à persistence stream e oferece uma fronteira mais fraca para queue-specific failure/backpressure nesse caso.

Nenhum score arquitetural numérico é fabricado.

### 9.7 Contrato público de interação e estado de job

Rotas futuras, não implantadas pela Gate 19.3:

```text
POST /v1/analyses
GET  /v1/analyses/{job_id}
GET  /v1/analyses/{job_id}/result
```

Vocabulário de estados:

```text
SUBMITTING
ACCEPTED
RUNNING
SUCCEEDED
FAILED
EXPIRED
```

Conditional writes do DynamoDB são a autoridade planejada para estado do job. SQS é transporte at-least-once e não pode, sozinho, alterar a verdade de negócio.

O submit público exige `Idempotency-Key` e `SHA256_CANONICAL_PUBLIC_ANALYSIS_REQUEST_V1`:

```text
mesma chave + mesmo fingerprint       -> RETURN_EXISTING_JOB
mesma chave + fingerprint diferente   -> HTTP_409
```

`SUBMITTING` modela explicitamente a fronteira de dual-write DynamoDB/SQS. O design não finge que esses serviços fornecem uma única transação atômica.

### 9.8 Retry, duplicate delivery e backpressure

```text
queue semantics:       AT_LEAST_ONCE
worker batch size:     1
duplicate authority:   DYNAMODB_CONDITIONAL_STATE_AND_ATTEMPT_ADMISSION
retry owner:           SQS/Lambda event source + worker state machine
provider retry owner:  bounded worker policy
DLQ:                   REQUIRED
unbounded retry:       FORBIDDEN
backpressure:          SQS queue depth/age + Lambda reserved concurrency
```

Valores numéricos futuros de retry/concurrency/retention permanecem `CONFIGURED_LIMIT` até serem medidos.

### 9.9 Contrato de responsabilidades IAM

A autoridade planejada do API-handler role fica limitada ao control plane público e submissão:

```text
sqs:SendMessage
dynamodb:GetItem
dynamodb:PutItem
dynamodb:UpdateItem
dynamodb:TransactWriteItems
```

Ela exclui explicitamente `bedrock:Retrieve`, `bedrock:InvokeModel` e `sqs:ReceiveMessage`.

A autoridade planejada do worker role fica limitada ao consumo da fila, updates exatos do job, retrieval no Knowledge Base retido e invocação do modelo retido:

```text
sqs:ReceiveMessage
sqs:DeleteMessage
sqs:ChangeMessageVisibility
sqs:GetQueueAttributes
dynamodb:GetItem
dynamodb:UpdateItem
bedrock:Retrieve
bedrock:InvokeModel
```

ARNs exatos pertencem à futura gate de implementação Terraform.

A regra permanece:

```text
concrete runtime responsibility
 -> required service action
 -> exact resource
 -> IAM statement
```

não `future feature aspiration -> broad runtime role`.

### 9.10 Observabilidade, custo e minimização de dados

A Gate 19.3 exige futura evidência operacional para request/job/trace identity, state transitions, attempt number, stage duration, queue age, provider call counts, Bedrock tokens quando disponíveis, retries, throttles, outcome/failure category e result bytes.

Telemetry permanece content-minimized. Full prompts, repository source, repository file contents, full model responses, credentials, sensitive tokens e raw user payloads permanecem proibidos por default.

A Gate 19.3 não cria claim de SLO ou TCO de produção. Queue operations, status reads, worker concurrency, storage/retention e aggregate model-call budgets tornam-se obrigações de medição somente após existir implementação.

### 9.11 Contrato de disable/recovery

A futura implementação deve suportar independentemente:

```text
disable new submit route
preserve status/result reads during submit pause
disable queue -> worker event source
set worker reserved concurrency to zero
disable model invocation at worker authorization/runtime guard
```

O scheduler pause da Phase 17 permanece separado e não é global kill switch.

### 9.12 Próxima fronteira arquitetural

Após o protected merge da Gate 19.3, a próxima gate poderá implementar a topologia selecionada em Terraform e application adapters **atrás de defaults disabled/non-public**.

Antes de qualquer AWS apply ou public enablement, deverá produzir inventory/plan Terraform exato, IAM least-privilege vinculado a ARNs concretos, testes de lifecycle/idempotency, duplicate-delivery/retry/backpressure/failure injection, testes de telemetry content-minimized e limites explícitos de custo/concurrency classificados como `CONFIGURED_LIMIT`.

Nenhum apply ou public enablement é autorizado pela Gate 19.3.

## 10. Authority impact da Gate 19.3

```text
public endpoints created:               0
new AWS resources created:              0
new IAM roles/policies created:         0
AWS/provider live executions:           0
third-party repository code executions: 0
PR #89 modifications:                   0
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

Gate 19.3:

- `labs/phase-19-gate-19-3-async-topology-contract.md`
- `labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json`
- `scripts/verify_phase19_gate19_3_async_topology_contract.py`

PR #89 permanece como trabalho deferred separado do Governed LLM Gateway e não é dependência da Phase 19, salvo reavaliação explícita futura.
