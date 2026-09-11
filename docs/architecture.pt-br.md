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

A Phase 9 encerrou deliberadamente em um handoff de aplicação. Essa fronteira ainda é real no `main` protegido:

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

### 9.2 Composição representativa do produto

A Gate 19.2 compõe as capabilities reais retidas em um workload representativo **não público**, sem transformar essa composição em runtime público implantado:

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

A composição reutiliza autoridade determinística retida em vez de duplicá-la. Evidência de repositório permanece imutável e inerte, threat evidence é admitida antes da janela request-time, risco continua em Risk Policy v1, Bedrock Retrieve e synthesis permanecem limitados e a admissão final permanece determinística.

### 9.3 Workload representativo congelado

A Gate 19.1 congelou:

```text
workload_id: public-analysis-workload:v1
provider: GitHub
visibility: public only
repositories/request: 1
supported dependency evidence: exact-commit inert uv.lock
max dependency records: 5.000
third-party code execution: FORBIDDEN
```

A Gate 19.2 reteve o anchor atual:

```text
repository:      openedx/mockprock
repository URL:  https://github.com/openedx/mockprock
commit/ref:      18c954d8604df4740c829ba17fa2f3640b92b900
evidence file:  uv.lock
dependency:     webob==1.8.10
GHSA anchor:    GHSA-6hx8-3wjj-gr8g
CVE anchor:     CVE-2026-54770
```

O anchor estabelece reprodutibilidade apenas. Não comprova runtime exposure.

### 9.4 Evidência medida da Gate 19.2

A execução operada por humano ocorreu uma única vez a partir do protected main:

```text
e45ba419414e6dd77ecad68f4d2312e9123c2223
```

Artifact canônico:

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

Os dois estágios ligados ao Bedrock mediram:

```text
semantic_evidence = 4160 ms
model_reasoning   = 8938 ms
combined          = 13098 ms / 73,80% do end-to-end
```

O reviewer offline do artifact persistido admitiu a evidência para avaliação de topologia. Zero numérico nunca substitui semântica de evidência: Athena continua `NOT_APPLICABLE` e throttling continua `UNMEASURED`.

### 9.5 Decisão do padrão de interação

A Gate 19.2 seleciona:

```text
ASYNC_SUBMIT_STATUS_RESULT
```

O success path medido terminou em `17.748 ms`; ele **não** excedeu por si só o envelope de referência de 30 segundos do HTTP API. Portanto, a decisão não se baseia em uma alegação de timeout medido.

A razão arquitetural é retry safety combinada com provider-latency coupling, backpressure e failure isolation. Cenários derivados explícitos preservam `MEASURED != DERIVED`:

```text
baseline measured E2E                                      17748 ms   MEASURED
+ one additional model-equivalent client elapsed           26649 ms   DERIVED
+ one additional Retrieve-equivalent and model-equivalent  30797 ms   DERIVED
reference synchronous envelope                             30000 ms   RETAINED FACT
```

Os valores derivados não são medições live adicionais. Eles mostram que uma execução bem-sucedida de 17,7 segundos não deixa margem suficiente para acoplamento síncrono quando retry/failure behavior do provider é considerado.

### 9.6 Runtime concreto permanece não selecionado

O padrão de interação está selecionado; a topologia de serviços não está.

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

A Gate 19.2 não autoriza endpoint público, fila, worker, result store, recurso AWS ou IAM role/policy.

### 9.7 Modelo de responsabilidades IAM

Ainda não existe public runtime role. O próximo gate de topologia deve preservar decomposição de responsabilidades antes da materialização de IAM:

```text
public ingress admission
repository acquisition
job submission/coordination
worker execution
Bedrock Knowledge Base retrieval
Bedrock model invocation
result persistence/status, somente se selecionado
telemetry emission
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

### 9.8 Requisitos de threat, abuse e lifecycle async

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
retry amplification
concurrency exhaustion
cost denial-of-wallet
result tampering
identity/replay
telemetry data leakage
```

O padrão async selecionado também exige autoridade determinística para:

```text
job identity
idempotency key semantics
duplicate-delivery handling
retry ownership
visibility/lease semantics se uma queue for selecionada
status lifecycle
result retention
result integrity
cancellation/disable boundaries
```

Request admission, host GitHub fixo sem redirects, leitura apenas de arquivo inerte, limites de dependências/candidatos, autoridades determinísticas e telemetry content-minimized permanecem aplicáveis.

### 9.9 Contrato de custo e observabilidade

A Gate 19.2 agora fornece medições reais do workload completo para o run representativo retido, mas não fabrica SLOs ou TCO de produção.

O próximo gate de topologia deve definir e depois medir dimensões async apenas se os componentes correspondentes forem realmente selecionados:

```text
job submissions
queue operations
delivery attempts
worker concurrency
result-store operations
status reads
retention/storage
rejected requests
aggregate model-call budget
cost attribution per job/request
```

Telemetry futura obrigatória permanece content-minimized:

```text
request_id
job_id
trace_id
workload_id
repository_identity_hash
stage
duration_ms
outcome
failure_category
provider/service call count
Bedrock token counts when available
retry count
throttle classification
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

### 9.10 Contrato de disable/recovery

Antes de deploy público, cada controle aplicável precisa provar seu escopo:

```text
ingress disable
new-job admission disable
queue consumer pause, se uma queue for selecionada
model invocation disable
result publication disable, se persistência for selecionada
background ingestion pause
```

O scheduler pause da Phase 17 comprova apenas `background ingestion pause` para os três schedules nomeados. Não pode ser renomeado como global kill switch.

### 9.11 Próxima fronteira arquitetural

Após o protected merge do closeout da Gate 19.2, o próximo gate da Phase 19 deve congelar a menor arquitetura async concreta de ingress/job/result e o modelo least-privilege de responsabilidades **antes** do deployment.

Ele deve comparar apenas as combinações mínimas de serviços necessárias para o padrão de interação já selecionado e preservar decisões evidence-gated para:

```text
ingress
job coordination
worker compute
result/status persistence
identity/rate/abuse controls
least-privilege IAM
concurrency/backpressure
observability
disable/recovery
Terraform ownership
```

Nenhum serviço AWS é selecionado apenas porque é comum em sistemas async ou aparece no AIP-C01.

## 10. Authority impact da Gate 19.2

```text
public endpoints:                       0
new AWS resources:                      0
new IAM roles/policies:                 0
third-party repository code executions: 0
PR #89 modifications:                  0
```

O artifact live persiste esses contadores exatamente em zero.

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
