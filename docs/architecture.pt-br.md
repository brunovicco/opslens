# Arquitetura do OpsLens

_Última atualização: 2026-09-10_

Este documento é o baseline arquitetural acumulado atual até a **Phase 19 — Bounded Public Runtime & Productization, Gate 19.1**.

As Phases 0–18 estão completas. A Phase 19 é a fase atual de productization guiada por evidência.

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

Código determinístico continua sendo autoridade para:

- identidade de fonte e evidência;
- normalização de pacotes e aplicabilidade de versão/range;
- reconciliação CVE/GHSA/NVD;
- fatos KEV, EPSS, CVSS e Risk Policy;
- parsing de consultas estruturadas e compilação SQL;
- admissão de retrieval e completude das evidências obrigatórias;
- identidade de citações e admissão de saída;
- autorização de capabilities e binding do input executável;
- admissão de resultados de capabilities;
- admissão de handoffs single-agent e multi-agent;
- admissão MCP e projeção de resultados;
- identidade, resolução e admissão de referências A2A;
- retry/fallback policy quando explicitamente congelada;
- admissão e correlação de runtime evidence;
- limites de recursos/custo;
- estado dos controles operacionais de recovery expresso via Terraform.

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

Raw evidence de terceiros é preservada antes do enriquecimento. Versões exatas das fontes, snapshots imutáveis, hashes e identidades tipadas participam da proveniência.

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

O caminho inicial lê dados apenas. Não executa package managers, builds, testes, setup hooks, workflows, Dockerfiles, scripts ou código do repositório.

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

O modelo não tem autoridade para gerar SQL arbitrário. O adapter Athena fixa database/workgroup, aceita apenas shapes do compilador, limita rows/paginação, registra bytes/timing e usa cancelamento best-effort no próprio timeout de polling.

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

`RetrieveAndGenerate` não é o default retido porque retrieval e synthesis são medidos e admitidos como estágios separados.

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
proposta EvidenceNeed[]
 -> autoridade determinística de rota
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> aquisição e admissão por classe
 -> completude ALL_REQUIRED
 -> HybridEvidenceEnvelope
 -> fatos F* estruturados + citações S* semânticas
 -> síntese limitada conforme rota
 -> admissão determinística de saída
```

Hybrid significa **roteamento e composição híbridos de evidência**, não uma afirmação automática de keyword + vector search.

## 4. Fronteiras agentic e de interoperabilidade

A Phase 11 retém reasoning direto Bedrock single-agent como referência/default medida.

A Phase 12 retém specialization/handoff determinísticos, mas rejeita como default a topologia de dois modelos porque adicionou chamadas, tokens, latência e custo sem ganho medido de qualidade.

A Phase 13 retém exposição/execução/projeção MCP offline e limitada. MCP não adiciona business authority.

A Phase 14 retém Amazon Bedrock AgentCore somente como alvo opcional de laboratório. IAM/runtime de experimento permanente foi removido após a medição.

A Phase 15 retém interoperabilidade A2A offline baseada em referências e um oracle de conformidade do SDK oficial em CI. Não existe runtime A2A público retido.

## 5. Fronteira de runtime exposure

A Phase 16 retém uma fronteira tipada read-only do Amazon Inspector.

A descoberta medida retornou zero registros atuais. Isso significa apenas:

```text
leitura limitada do Inspector teve sucesso e retornou zero registros
```

Não significa:

```text
runtime exposure = zero
```

Repository risk e runtime exposure permanecem classes de evidência separadas.

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

A arquitetura permanente **não** afirma atualmente:

```text
public HTTP endpoint
public application compute
public MCP runtime
public A2A peer runtime
standing AgentCore experiment runtime
standing Inspector experiment IAM
production multi-tenant request surface
public result store
```

## 7. Estado retido de Security Hardening

A Phase 17 retém controles evidence-backed em CI/CD, dependency/code scanning, adversarial authority regression, telemetry e recovery.

Controles importantes:

```text
protected-main required context:     Repository security invariants
external GitHub Actions:             full 40-hex SHA pins
checkout persisted credentials:      disabled where not required
Dependency Review:                   pull request, fail em high severity
CodeQL Python:                       PR + main + weekly + manual
public/adversarial authority tests:  offline e determinísticos
Lambda telemetry:                    captura implícita event/response/error suprimida
```

Os 12 handlers Lambda retidos com Powertools seguem padrões content-minimized. O failure logging compartilhado evita serialização implícita do traceback da exceção ativa.

### 7.1 Controle de recovery da ingestão agendada

A superfície recorrente concreta continua sendo exatamente três schedules do EventBridge Scheduler:

```text
aws_scheduler_schedule.epss_daily
aws_scheduler_schedule.kev_daily
aws_scheduler_schedule.nvd_incremental_hourly
```

Terraform controla:

```text
scheduled_ingestion_enabled=true   -> ENABLED
scheduled_ingestion_enabled=false  -> DISABLED
```

Isso é um **scheduled-ingestion pause**, não global kill switch. Não cancela invocações Lambda em andamento, retries já admitidos, eventos S3 emitidos, invocações manuais, caminhos de modelo ou autorização de capability.

## 8. Fronteira da Phase 18

A Phase 18 está completa pelo protected PR #290 em:

```text
feca774535b7d83f57c26f4e9fe7da71ce268f0f
```

O artifact histórico de closeout preserva intencionalmente o estado de evidência pré-merge. Documentação corrente carrega a verdade pós-merge.

A Phase 18 preserva:

```text
MEASURED
DERIVED
UNMEASURED
NOT_APPLICABLE
```

além da interpretação separada de `CONFIGURED_LIMIT` para ceilings de recurso.

Semânticas permanentes:

```text
configured limit != measured utilization
lab metric != production SLO
cost evidence != production TCO
portfolio claim != new evidence authority
AIP-C01 coverage != certification guarantee
```

A plataforma não fabrica run rate mensal de produção a partir de medições limitadas de laboratório.

## 9. Phase 19 — Bounded Public Runtime & Productization

### 9.1 Fronteira inicial do public analysis

A Phase 9 encerrou deliberadamente em um handoff de aplicação. Essa fronteira ainda é real em `main`:

```text
JSON não confiável
 -> admissão de request <= 2.048 bytes
 -> coordenadas GitHub validadas
 -> evidência imutável do repositório
 -> planejamento semântico metadata-only e limitado
 -> admissão determinística da rota public-v1
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

A operação public v1 é:

```text
analyze_public_repository
```

com exatamente:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

sob completude `ALL_REQUIRED`.

O public semantic planner recebe apenas metadata limitada. Raw repository text, credenciais, SQL arbitrário, seleção de provider/model e conteúdo executável do repositório não viram autoridade do planner.

### 9.2 Gap real de composição

O repositório já contém implementações reais de vulnerability/risk determinísticos, Athena limitada, Bedrock Knowledge Base retrieval, synthesis limitada, capability execution/result admission e hybrid output admission.

Esses componentes **não** estão atualmente compostos após `PublicAnalysisAdmissionHandoff` em uma execução representativa única do produto público.

Portanto:

```text
rich retained capabilities != executable public product workload
```

Nenhuma topologia HTTP pública deve ser escolhida com base em latência parcial.

### 9.3 Frozen workload público

A Gate 19.1 congela:

```text
workload_id: public-analysis-workload:v1
provider: GitHub
visibility: public only
repositories/request: 1
supported dependency evidence: exact-commit inert uv.lock
max dependency records: 5.000
third-party code execution: FORBIDDEN
```

Limites existentes evidence-backed são reutilizados. Medições ausentes do request completo permanecem `UNMEASURED`.

Exemplos:

```text
request body                        CONFIGURED_LIMIT  2.048 bytes
repository URL                      CONFIGURED_LIMIT  256 chars
GitHub success-path physical calls  DERIVED           4
GitHub adapter retries              CONFIGURED_LIMIT  0
GitHub per-call timeout             CONFIGURED_LIMIT  10 seconds
Athena scan cutoff/query            CONFIGURED_LIMIT  10.485.760 bytes
Knowledge Retrieve top_k            CONFIGURED_LIMIT  <= 10
Knowledge context                   CONFIGURED_LIMIT  <= 16.384 UTF-8 bytes
knowledge/hybrid synthesis output   CONFIGURED_LIMIT  <= 2.048 tokens
public Athena query count           UNMEASURED
public Bedrock call count           UNMEASURED
public end-to-end p50/p95            UNMEASURED
public final response bytes         UNMEASURED
public request cost                 UNMEASURED
```

### 9.4 Decisão de runtime

A Gate 19.1 registra:

```text
DEFERRED_PENDING_MEASUREMENT
```

com hipótese principal:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

A hipótese não é arquitetura permanente autorizada.

Sync permanece viável apenas se o workload representativo completo couber com folga no timeout do ingress selecionado sob testes upper-bound/p95. Async passa a ser justificado se variabilidade de latência, backpressure, failure isolation, retry safety ou evidência de timeout tornar o acoplamento síncrono inseguro.

### 9.5 Conjunto de candidatos

```text
HTTP API + Lambda synchronous             MEASUREMENT_GATED
Regional REST API + Lambda synchronous    MEASUREMENT_GATED
API + submit/queue/worker/result           LEADING_HYPOTHESIS
Lambda Function URL                       NOT_FAVORED_FOR_PUBLIC_V1
ECS/Fargate/ALB                            DEFERRED_NO_CURRENT_NEED
AgentCore public runtime                   DEFERRED_NO_CURRENT_NEED
```

ADRs/labs distinguem fatos documentados da AWS de medições do OpsLens.

### 9.6 Modelo de responsabilidades IAM

A Gate 19.1 não cria IAM role. Permissões futuras são decompostas por responsabilidade concreta:

```text
public ingress
repository acquisition
Athena structured retrieval
Bedrock Knowledge Base retrieval
Bedrock model invocation
result persistence, somente se justificado
telemetry emission
async queue/job coordination, somente se justificado
```

Regra:

```text
concrete runtime responsibility
 -> required service action
 -> exact resource
 -> IAM statement
```

não:

```text
future feature aspiration
 -> broad runtime role
```

### 9.7 Threat and abuse model

A futura superfície pública deve tratar pelo menos:

```text
oversized request
malformed JSON
repository URL abuse
SSRF-style source redirection
repository enumeration
large repository amplification
dependency explosion
GitHub API abuse
prompt injection from repository content
retrieval poisoning
model amplification
Athena scan amplification
Bedrock token amplification
retry amplification
concurrency exhaustion
cost denial-of-wallet
result tampering
identity/replay
telemetry data leakage
```

Request admission, host GitHub fixo sem redirects, leitura apenas de arquivo inerte, limites de dependências/candidatos, autoridades determinísticas e telemetry content-minimized já mitigam parte da superfície. Identity/rate/global quota/concurrency/aggregate model-call controls públicos ficam sem definição até a topologia ser escolhida.

### 9.8 Contrato de custo e observabilidade

O primeiro experimento real deve medir dimensões por request de forma independente:

```text
cost/request
Bedrock input/output tokens
Athena bytes scanned
GitHub request count
runtime duration
queue operations, se aplicável
storage, se aplicável
retries
throttles
rejected requests
concurrency
```

Telemetry futura obrigatória, content-minimized:

```text
request_id
trace_id
workload_id
repository_identity_hash
stage
duration_ms
outcome
failure_category
provider/service call count
Bedrock token counts when available
Athena bytes scanned
retry count
throttle count
admission rejection reason
cost attribution identifiers when available
```

Proibido por default:

```text
full prompt
repository source code
repository file contents
full model response
sensitive tokens
credentials
raw user payload
```

Telemetry não se torna business/evidence authority.

### 9.9 Contrato de disable/recovery

Antes de deploy público, cada controle aplicável precisa provar seu escopo:

```text
ingress disable
new-job admission disable
queue consumer pause
model invocation disable
Athena execution disable
background ingestion pause
```

O scheduler pause da Phase 17 comprova apenas `background ingestion pause` para os três schedules nomeados. Não pode ser renomeado como global kill switch.

### 9.10 Boundary do experimento Gate 19.2

O próximo experimento autorizado é **medição não pública do workload representativo**.

Ele deve compor ou invocar os estágios reais até deterministic final result admission e medir:

```text
end-to-end e per-stage duration
GitHub HTTP calls
Athena query count + bytes scanned quando usado
Bedrock Retrieve count + latency quando usado
Bedrock model calls + tokens + latency quando usado
retry/throttle counts
serialized result bytes
```

Só depois dessa evidência o projeto poderá promover a decisão de runtime para `SYNC` ou `ASYNC`.

Se chamadas AWS/model reais forem necessárias na Gate 19.2, a execução permanece human boundary.

## 10. Authority impact da Gate 19.1

```text
AWS mutations:          0
IAM mutations:          0
new AWS resources:      0
model invocations:      0
capability executions:  0
public endpoints:       0
PR #89 modifications:   0
```

A Phase 19 não adiciona serviços AWS somente por aparência de produto ou cobertura AIP-C01.

## 11. Evidência canônica da Gate 19.1

- `docs/adr/0076-bounded-public-runtime-hypothesis-and-launch-contract.md`
- `labs/phase-19-gate-19-1-public-runtime-hypothesis.md`
- `labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json`
- `scripts/verify_phase19_gate19_1_public_runtime_contract.py`

PR #89 permanece como trabalho deferred separado do Governed LLM Gateway e não é dependência da Phase 19, salvo reavaliação explícita futura.
