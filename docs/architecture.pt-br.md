# Arquitetura do OpsLens

_Última atualização: 2026-09-11_

Este documento é o baseline arquitetural acumulado atual até a **Phase 19 — Bounded Public Runtime & Productization, Gate 19.5**.

As Phases 0–18 estão completas. A Phase 19 é a fase atual de productization guiada por evidência. A Gate 19.2 selecionou o padrão de interação async submit/status/result com base em evidência representativa admitida. A Gate 19.3 fez protected merge da autoridade de design async concreta. A Gate 19.4 implementou essa topologia em código e Terraform atrás de defaults disabled/non-public. A Gate 19.5 fez protected merge da proveniência imutável dos artefatos API/worker e de coordenadas S3 exatas sem materializar o runtime. A Gate 19.6 de Terraform plan exato/admissão é a próxima; nenhum deployment público é autorizado.

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
queue delivery != business execution authority
provider retry != business retry authority
artifact hash != S3 VersionId
publication success != deployment authorization
plan != apply
AIP-C01 topic != product requirement
```

## 2. Modelo de autoridade

Código determinístico continua sendo autoridade para identidade de fonte/evidência, normalização e aplicabilidade, reconciliação CVE/GHSA/NVD, fatos KEV/EPSS/CVSS/Risk Policy, parsing/compilação de consultas estruturadas, admissão/completude de retrieval, identidade de citações/saída, autorização e admissão de capabilities, handoffs de agentes/MCP/A2A, correlação de runtime evidence, limites de recurso/custo e recovery control via Terraform.

Modelos e agentes podem classificar, propor, resumir, explicar ou sintetizar sobre evidência já admitida. Um serviço gerenciado AWS ou uma saída sintaticamente válida do modelo não vira autoridade de negócio por si só.

A Gate 19.3 estendeu a autoridade determinística para identidade de job público, binding de idempotência, transições de estado, admissão de duplicate delivery, limites de retry e admissão de status/result. A Gate 19.4 implementa essas autoridades com domain/application code tipado, persistência condicional, transporte de fila content-minimized e composição runtime fail-closed. Entrega pela fila continua sendo evidência de transporte, não verdade de estado do job. A Gate 19.5 adiciona identidade de deployment artifact e proveniência imutável de objeto S3 como entradas de planejamento sem conceder autoridade de deployment do runtime.

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

A arquitetura implantada permanente **não** afirma atualmente endpoint HTTP público, application compute público, fila pública, result store público, runtime MCP/A2A público, AgentCore experiment runtime permanente, Inspector experiment IAM permanente ou superfície production multi-tenant. A Gate 19.4 contém definições Terraform disabled para um futuro runtime público async. A Gate 19.5 adicionou apenas versões imutáveis dos deployment artifacts no bucket versionado já existente. Definições no repositório e ZIPs publicados não são recursos do runtime público implantado.

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

A Phase 9 encerrou deliberadamente em um application handoff. Essa fronteira histórica permanece verdadeira no protected `main` do merge da Gate 19.3:

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

### 9.5 Decisão de topologia concreta da Gate 19.3 — COMPLETE DESIGN AUTHORITY

A Gate 19.3 foi protected-merged pelo PR #349 em `18d31c03d27448c88a6ffcba16683f3875a5ba15` e selecionou o identificador lógico:

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

A seleção é evidência arquitetural protegida apenas. A Gate 19.3 não criou nenhum desses recursos nem autorizou deployment.

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

A Gate 19.4 implementa as rotas abaixo no adapter HTTP API/Terraform disabled, mas nenhuma está implantada ou publicamente acessível:

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

Conditional writes do DynamoDB são a autoridade implementada para estado do job. SQS é transporte at-least-once e não pode, sozinho, alterar a verdade de negócio.

O submit público exige `Idempotency-Key` e `SHA256_CANONICAL_PUBLIC_ANALYSIS_REQUEST_V1`:

```text
mesma chave + mesmo fingerprint       -> RETURN_EXISTING_JOB
mesma chave + fingerprint diferente   -> HTTP_409
```

`SUBMITTING` modela explicitamente a fronteira de dual-write DynamoDB/SQS. A implementação persiste `SUBMITTING`, publica a identidade mínima do job e admite `ACCEPTED` condicionalmente; falha na publicação da fila é terminalizada em vez de fingir que DynamoDB e SQS formam uma transação única.

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

A Gate 19.4 representa valores numéricos apenas como configuração:

```text
API reserved concurrency          2     CONFIGURED_LIMIT
worker reserved concurrency       0     CONFIGURED_LIMIT
API Lambda timeout               15 s   CONFIGURED_LIMIT
worker Lambda timeout            60 s   CONFIGURED_LIMIT
queue visibility timeout        120 s   CONFIGURED_LIMIT
redrive receive count             4     CONFIGURED_LIMIT
worker max attempts               3     CONFIGURED_LIMIT
HTTP API burst limit             10     CONFIGURED_LIMIT
HTTP API rate limit               5     CONFIGURED_LIMIT
```

Nenhum deles é utilização medida.

### 9.9 Contrato de responsabilidades IAM

A Gate 19.4 vincula em Terraform a autoridade funcional do API-handler à tabela de jobs e fila exatas:

```text
sqs:SendMessage
dynamodb:GetItem
dynamodb:PutItem
dynamodb:UpdateItem
dynamodb:TransactWriteItems
```

Ela exclui explicitamente `bedrock:Retrieve`, `bedrock:InvokeModel` e autoridade de consumo SQS.

A autoridade funcional do worker é vinculada à fila/tabela exatas e aos recursos retidos de Knowledge Base/modelo:

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

O worker não recebe queue-send, create/transaction/scan de DynamoDB nem autoridade de administração IAM. Escritas de CloudWatch Logs e X-Ray ficam representadas separadamente como runtime-support authority.

A regra permanece:

```text
concrete runtime responsibility
 -> required service action
 -> exact resource
 -> IAM statement
```

não `future feature aspiration -> broad runtime role`.

### 9.10 Observabilidade, custo e minimização de dados

A Gate 19.3 exige evidência operacional para request/job/trace identity, state transitions, attempt number, stage duration, queue age, provider call counts, Bedrock tokens quando disponíveis, retries, throttles, outcome/failure category e result bytes antes que um lançamento público possa ser aceito.

A Gate 19.4 define log groups CloudWatch limitados e autoridade runtime-support de X-Ray, mas não afirma telemetry stream implantado ou SLO de produção. Telemetry permanece content-minimized. Full prompts, repository source, repository file contents, full model responses, credentials, sensitive tokens e raw user payloads permanecem proibidos por default.

A Gate 19.4 não cria claim de TCO de produção. Queue operations, status reads, worker concurrency, storage/retention e aggregate model-call budgets permanecem obrigações futuras de medição depois que existir deployment autorizado.

### 9.11 Contrato de disable/recovery

A implementação disabled da Gate 19.4 representa controles independentes:

```text
new-job admission switch                  false
execute-api endpoint                      disabled
custom public domain                      absent
queue -> worker event source              disabled
worker reserved concurrency               zero
worker provider-execution switch          false
provider-heavy worker executor            not composed
```

A lógica de status/result permanece separada da admissão de novos jobs. O scheduler pause da Phase 17 permanece separado e não é global kill switch.

### 9.12 Fronteira de implementação da Gate 19.4

Todos os recursos Terraform da Gate 19.4 ficam condicionados a:

```text
public_async_runtime_materialized = false
```

O repositório contém definições para autoridade de jobs em DynamoDB, SQS queue/DLQ, API/worker Lambda, rotas HTTP API, log groups CloudWatch, event-source mapping e roles/policies IAM separadas. Essas definições não criam recursos AWS até existir um `terraform apply` explicitamente autorizado.

A materialização de Lambda também exige S3 key exata do deployment artifact, object `VersionId` exato e source-code hash. O worker Lambda recusa enablement provider-heavy até que um provider executor seja separadamente admitido e composto.

### 9.13 Proveniência imutável de artifacts da Gate 19.5 — COMPLETE

A Gate 19.5 foi protected-merged pelo PR #353 em `61749bfac7b7bc9d032567e0b1870f8c1f7dedd4`; o CodeQL pós-merge desse SHA exato concluiu com sucesso.

Ela estabeleceu coordenadas imutáveis exatas de artefatos sem materializar o runtime:

```text
API
  key: lambda/public-analysis/api/sha256=99477676dcc41345c63ed28c81bb41c7f9f47bcf5b072254bc1ef0e2cfcd876e/opslens-public-async-api.zip
  SHA-256: 99477676dcc41345c63ed28c81bb41c7f9f47bcf5b072254bc1ef0e2cfcd876e
  source_code_hash: mUd2dtzEE0XGPtKMgbtBx/n0e89bByJUvB7w4s/Nh24=
  VersionId: E.jfB7dlkGCD.wHAurP7QXo4fuS_PW63

Worker
  key: lambda/public-analysis/worker/sha256=0d04b472476ad7825b5190352da1642db9a7d42d1ce349d21a39fac8f6ecbdc9/opslens-public-async-worker.zip
  SHA-256: 0d04b472476ad7825b5190352da1642db9a7d42d1ce349d21a39fac8f6ecbdc9
  source_code_hash: DQS0ckdq14JbUZA1LaFkLbmn1C0c40nSGjn6yPbsvck=
  VersionId: sxiOdii4yFwR13t23xP5A8EU1JPV_7P1
```

A evidência de publicação registra exatamente duas mutações S3 `PutObject` create-only, zero retries automáticos, zero mutações de runtime/IAM/Terraform/endpoint público, `terraform_plan_input_ready=true` e `terraform_apply_authorized=false`.

### 9.14 Próxima fronteira arquitetural — Gate 19.6

A Gate 19.6 pode definir `public_async_runtime_materialized=true` **somente para um Terraform plan exato** e consumir as coordenadas `Key + VersionId + source_code_hash` admitidas na Gate 19.5. O plan é evidência para inspeção, não autoridade de deployment.

A admissão offline deve verificar inventário exato de resource changes, actions/resources IAM exatos, coordenadas dos artefatos, concurrency/timeouts configurados, visibility/redrive SQS, configuração DynamoDB, exatamente as três rotas HTTP, estado do execute-api endpoint, estado do event-source mapping, recursos CloudWatch, tags e ausência de deletes/replacements/resources inesperados.

Materialization e enablement permanecem separados. O estado de planejamento pretendido para Gate 19.6 preserva:

```text
execute-api endpoint                      disabled
new-job admission switch                  false
queue -> worker event source              disabled
worker reserved concurrency               zero
worker provider-execution switch          false
provider-heavy worker executor            not composed
custom public domain                      absent
```

`terraform plan != terraform apply`. Sucesso do plan não é autorização de deployment. Nenhum apply, public enablement, worker enablement, IAM broadening ou execução pública provider-heavy é autorizado pela Gate 19.6.

## 10. Authority impact atual da Phase 19

```text
deployment artifact S3 PutObject mutations: 2
public endpoints enabled:                    0
runtime AWS resources created/changed:       0
IAM roles/policies created/changed:          0
Terraform apply executions:                  0
provider-heavy public executions:            0
third-party repository code executions:      0
PR #89 modifications:                        0
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

Gate 19.4:

- `labs/phase-19-gate-19-4-disabled-async-runtime.md`
- `labs/evidence/phase-19-gate-19-4-disabled-async-runtime-v1.json`
- `scripts/verify_phase19_gate19_4_disabled_async_runtime.py`

Gate 19.5:

- `labs/evidence/phase-19-gate-19-5-prepublication-v1.json`
- `labs/evidence/phase-19-gate-19-5-artifact-publication-v1.json`
- `labs/phase-19-gate-19-5-immutable-artifact-publication-runbook.md`
- `labs/phase-19-gate-19-5-closeout.md`
- `scripts/build_phase19_async_lambda_artifacts.py`
- `scripts/verify_phase19_gate19_5_async_artifact_build.py`
- `scripts/publish_phase19_gate19_5_async_artifacts.py`
- `scripts/verify_phase19_gate19_5_artifact_publication.py`

PR #89 permanece como trabalho deferred separado do Governed LLM Gateway e não é dependência da Phase 19, salvo reavaliação explícita futura.
