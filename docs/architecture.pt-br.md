# Arquitetura do OpsLens

_Última atualização: 2026-09-10_

Este documento é o baseline arquitetural acumulado até a **Phase 17 — Security Hardening: COMPLETE pelo PR de closeout da Phase 17**.

A próxima fase é a **Phase 18 — Evaluation, Cost & Portfolio Readiness**.

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

## 2. Modelo de autoridade

Código determinístico continua sendo autoridade para:

- identidade de fonte e evidência;
- normalização de pacotes e aplicabilidade de versões/ranges;
- reconciliação CVE/GHSA/NVD;
- fatos de KEV, EPSS, CVSS e Risk Policy;
- parsing de consultas estruturadas e compilação SQL;
- admissão de retrieval e completude de evidências obrigatórias;
- identidade de citações e admissão de saída;
- autorização de capabilities e binding de inputs executáveis;
- admissão de resultados de capabilities;
- admissão de handoffs single-agent e multi-agent;
- admissão MCP e projeção de resultados;
- identidade, resolução e admissão de referências A2A;
- política de retry/fallback;
- admissão e correlação de evidência de runtime;
- estado do controle operacional de recovery expresso via Terraform.

Modelos e agentes podem classificar, propor, resumir, explicar ou sintetizar sobre evidências já admitidas. Eles não viram autoridade apenas porque a saída é sintaticamente válida, plausível ou produzida por um serviço gerenciado da AWS.

```text
proposal != authorization
retrieval result != sufficient evidence
citation id != semantic support
capability invocation != execution result
execution result != admitted evidence
repository finding != runtime exposure
AWS authentication != business authorization
scheduler state != business/evidence authority
```

## 3. Forma atual do sistema

### 3.1 Threat intelligence e caminho determinístico de risco

```text
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
 -> raw evidence preservada por fonte
 -> normalização e aplicabilidade determinísticas
 -> evidência de dependências do repositório
 -> correlação de vulnerabilidades
 -> RepositoryAnalysisResult
 -> Risk Policy v1 determinística
 -> RiskPrioritizationResult
```

Raw evidence de terceiros é preservada antes de enriquecimento. Versões exatas das fontes, snapshots imutáveis, hashes e identidades tipadas de evidência participam da proveniência.

### 3.2 Repository intelligence

```text
requisição para repositório público GitHub
 -> admissão estrita da requisição
 -> metadados do repositório confirmados pela fonte
 -> snapshot imutável commit/tree
 -> evidência inerte de uv.lock no commit exato
 -> parsing TOML determinístico
 -> identidade canônica das dependências
 -> aplicabilidade determinística das vulnerabilidades
```

Código de repositórios de terceiros nunca é executado durante a análise.

### 3.3 Caminho estruturado a partir de linguagem natural

```text
pergunta factual em linguagem natural
 -> proposta delimitada do planner Bedrock
 -> parser determinístico
 -> SemanticQuery tipada
 -> compilador SQL determinístico
 -> Athena read-only e delimitado
 -> evidência estruturada
```

O planner não possui autoridade para SQL arbitrário.

### 3.4 Caminho semântico de remediation

```text
pins explícitos de fontes oficiais
 -> corpus canônico determinístico
 -> publicação S3
 -> Bedrock Knowledge Base
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> Retrieve delimitado
 -> admissão por proveniência/hash
 -> montagem determinística de contexto
 -> síntese delimitada via Bedrock Converse
 -> identidade determinística de citação
 -> avaliação de groundedness/suporte
```

`RetrieveAndGenerate` não é o default retido porque retrieval e synthesis são deliberadamente medidos e admitidos como estágios separados.

### 3.5 Caminho de evidência híbrida

```text
proposta EvidenceNeed[]
 -> autoridade determinística de rota
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> aquisição e admissão por classe de evidência
 -> completude ALL_REQUIRED
 -> HybridEvidenceEnvelope
 -> fatos F* estruturados + citações S* semânticas
 -> síntese delimitada conforme a rota
 -> admissão determinística da saída
```

Hybrid significa **roteamento e composição de classes de evidência**, não uma afirmação automática de keyword-plus-vector search.

### 3.6 Fronteira de public analysis

O contrato de public analysis continua sendo uma fronteira de aplicação. Nenhum compute HTTP público ou endpoint público é retido.

```text
JSON não confiável
 -> admissão de requisição <=2048 bytes
 -> coordenadas GitHub validadas
 -> evidência imutável do repositório
 -> planejamento semântico metadata-only e delimitado
 -> admissão determinística do escopo public-v1
 -> autoridade híbrida da Phase 8
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

A operação fixa public v1 é `analyze_public_repository` e exige exatamente:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

Texto bruto do repositório, credenciais, SQL arbitrário, escolha de provider/model ou conteúdo executável do repositório não se tornam autoridade do planner.

## 4. Fundação AWS e serviços standing retidos

```text
environment:             dev
primary Region:          us-east-1
IaC:                     Terraform
human administration:    AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
knowledge retrieval:     Amazon Bedrock Knowledge Base + Amazon S3 Vectors
compute:                  AWS Lambda nos caminhos retidos de ingestão/transformação
recurring triggers:      Amazon EventBridge Scheduler
```

O storage standing inclui data bucket, deployment-artifact bucket, Terraform state bucket e o bucket vetorial de conhecimento no S3 Vectors.

A arquitetura standing **não** afirma possuir:

```text
public HTTP endpoint
public application compute
public MCP runtime
public A2A peer runtime
standing AgentCore experiment runtime
standing Inspector experiment IAM
production multi-tenant request surface
```

## 5. Baseline de knowledge retrieval

O caminho retido de knowledge retrieval controlado usa:

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

Fronteiras permanentes de interpretação:

```text
non-empty retrieval != sufficient evidence != authority to answer
retrieval success != citation attribution success != semantic groundedness
```

## 6. Arquitetura de reasoning e agentic

A Phase 11 reteve a referência single-agent com Bedrock direto como baseline default de reasoning.

A Phase 12 reteve especialização e handoff determinísticos, mas a topologia medida com dois modelos foi rejeitada como default porque adicionou chamadas, tokens, latência e custo sem ganho medido de qualidade.

A Phase 13 reteve contratos offline delimitados de MCP para exposição/execução/projeção de capabilities. MCP não adiciona autoridade de negócio.

A Phase 14 reteve Amazon Bedrock AgentCore somente como alvo opcional de laboratório. IAM standing do experimento e recursos do managed Runtime foram removidos após o experimento, e o workflow histórico mutante permanece retired/fail-closed.

A Phase 15 reteve interoperabilidade A2A offline baseada em referência e um oracle de conformidade com o SDK oficial em CI. Nenhum runtime A2A público/de rede é retido.

## 7. Fronteira de runtime exposure

A Phase 16 introduziu uma fronteira tipada de evidência read-only com Amazon Inspector.

A descoberta medida provou autorização para `ListCoverage` e `ListFindings` com zero registros atuais. O role temporário e dedicado do Inspector foi removido depois e sua ausência foi verificada independentemente.

Assim:

```text
Inspector API success != runtime evidence presence
Inspector finding != repository finding
runtime evidence correlation != capability authorization
```

Repository risk e runtime exposure continuam classes distintas de evidência.

## 8. Security Hardening — estado retido da Phase 17

### 8.1 Gate 17.1 — threat/control-gap inventory

A Gate 17.1 estabeleceu um inventário evidence-first e priorizou somente gaps observados.

### 8.2 Gate 17.2 — autoridade de CI/CD e workflows

Controles retidos no repositório incluem:

```text
protected-main required context:     Repository security invariants
external GitHub Actions:             full 40-hex SHA pins
checkout persisted credentials:      desabilitados onde desnecessários
pull_request_target/workflow_run:     rejeitados por default
EPSS planning identity:              read-only evidence role
EPSS execution identity:             coordinator role
long STS session:                    somente full-backfill execute path
historical AgentCore mutation path:  retired / fail-closed
```

Uma tentativa de escrita direta em `main` protegida foi rejeitada independentemente, provando que o CI obrigatório é enforcement de merge e não apenas intenção documental.

### 8.3 Gate 17.3 — dependency e code scanning

Sinais de segurança retidos:

```text
Dependency Review:  pull_request / fail-on-severity=high / contents:read
CodeQL Python:      PR + main + weekly + manual / contents:read + security-events:write
AWS/OIDC authority: none em ambos os workflows de scanning
```

Saída de scanner continua sendo sinal de engenharia, não autoridade sobre aplicabilidade de vulnerabilidade ou exploitability em runtime.

### 8.4 Gate 17.4 — regressão adversarial de fronteiras de autoridade

A suite offline retida contém oito casos determinísticos em sete classes de ameaça cobrindo abuso de public input, prompt injection direta/indireta, ampliação de capability, evidência forjada de resultado, abuso MCP, smuggling de referência A2A e tentativas delimitadas de amplificação.

```text
adversarial test success != proof of universal safety
```

A suite não possui autoridade AWS/OIDC e não realiza execução real de modelo ou capability.

### 8.5 Gate 17.5 — hardening do conteúdo de telemetry

Todos os 12 handlers Lambda retidos com Powertools suprimem explicitamente captura automática de evento, response e error na fronteira do decorator. O logging compartilhado de falhas evita serialização implícita do traceback da exceção ativa e retém apenas campos operacionais delimitados.

```text
log event suppression != trace response/error suppression
exception text != safe telemetry by default
trace metadata != business/evidence truth
```

A verificação do repositório checa continuamente o contrato retido de telemetry safety.

### 8.6 Gate 17.6 — operational recovery e abuse-cost boundary

A superfície concreta de ingestão automatizada recorrente é composta exatamente por três recursos EventBridge Scheduler:

```text
aws_scheduler_schedule.epss_daily
aws_scheduler_schedule.kev_daily
aws_scheduler_schedule.nvd_incremental_hourly
```

Terraform possui um único controle reversível:

```text
scheduled_ingestion_enabled=true   -> ENABLED
scheduled_ingestion_enabled=false  -> DISABLED
```

A amplificação de entrega do Scheduler continua delimitada por:

```text
maximum_event_age_in_seconds = 3600
maximum_retry_attempts       = 2
```

A prova live medida após o merge concluiu com sucesso:

```text
default convergence
 -> exact 0/3/0 pause plan
 -> exact pause apply
 -> independent 3/3 DISABLED reads
 -> paused convergence
 -> exact 0/3/0 resume plan
 -> exact resume apply
 -> independent 3/3 ENABLED reads
 -> final default convergence
```

Nenhum recurso foi criado ou destruído e nenhum novo principal IAM, permissão, serviço, runtime público, model invocation ou capability execution foi introduzido pelo experimento.

Isso é deliberadamente um **scheduled-ingestion pause**, não um global kill switch.

```text
scheduler pause != global workload termination
pause request != applied AWS state
Terraform apply success != independent AWS state verification
bounded retry != guaranteed delivery
failure destination != successful recovery
model token budget != tenant quota
```

Desabilitar os schedules não afirma cancelar Lambdas já em execução, retries já aceitos, eventos S3 já emitidos, invocações manuais, caminhos separados de modelo ou autorização de capabilities.

### 8.7 Gate 17.7 — sincronização arquitetural

A Gate 17.7 fechou `SEC17-DOC-001` sincronizando os baselines arquiteturais EN/PT-BR com a plataforma retida.

```text
PR:                       #276
exact head:               ea0460e549dd1b904d139632bfc2988671e23880
protected merge:          3938c6469a979f5b574755ce9fd56a56523626dc
Security Hardening CI:    34474712369 / #34 / SUCCESS
Dependency Review:        34474712371 / #19 / SUCCESS
CodeQL / Python:          34474712380 / #27 / SUCCESS
```

Sincronização documental não altera runtime nem autoridade de negócio.

### 8.8 Closeout da Phase 17

A Phase 17 fecha no menor boundary sustentado por evidência. Nenhuma evidência posterior na fase justificou outro controle de segurança/runtime.

Retido:

```text
protected-main security enforcement
Dependency Review + CodeQL
adversarial authority regression
content-minimized Lambda telemetry
telemetry-safety verification
bounded scheduled-ingestion pause
operational recovery runbook
synchronized EN/PT-BR architecture
```

Explicitamente deferred ou não criado:

```text
Dependabot version updates
additional continuous pip-audit
broad dependency upgrades
mandatory independent review until governance requires it
public WAF/rate/tenant quotas without a public runtime
public HTTP runtime
global platform kill switch
broad S3/Lambda emergency stop controls
automatic alarm remediation
standing Inspector experiment IAM
public MCP/A2A runtimes
AgentCore as default runtime
```

## 9. Princípios de IAM e trust

- humanos usam credenciais temporárias do IAM Identity Center;
- GitHub Actions usa OIDC em vez de AWS access keys persistentes;
- OIDC trust é delimitado por audience e condições de repositório/ref;
- IAM é introduzido para uma responsabilidade concreta de runtime, não para superfícies futuras especulativas;
- autoridade de plan/evidence é separada de autoridade de mutação quando o workload exige;
- autoridade temporária de experimento é removida depois do experimento que gera evidência quando não integra o runtime retido.

```text
AWS authentication != authorization to perform unrelated work
OIDC authentication != authorization to reuse a shared deployment role
no concrete principal -> no speculative runtime role
```

## 10. Fronteira de observability e privacidade

Observability operacional prefere categorias delimitadas, contadores, latência, hashes e correlation IDs em vez de conteúdo bruto de fonte/modelo/usuário.

Telemetry minimizada em conteúdo ajuda no diagnóstico, mas não vira business truth nem execution authority.

OpsLens ainda não afirma volume de requisições públicas em produção, p95/p99 de usuários públicos, quotas multi-tenant de produção ou cumprimento de SLOs de borda pública porque nenhum runtime público é retido.

## 11. Fronteira de custo e amplificação

Cost drivers permanecem separados:

```text
Athena bytes scanned
embedding/query work
S3 Vectors operations
model input/output tokens
Lambda/runtime execution
Scheduler retries
future public transport/runtime cost if ever deployed
```

Limites de tokens por chamada, limites de scan do Athena, limites de retry do Scheduler e controles de disable dos triggers resolvem problemas diferentes. Nenhum deve ser renomeado como quota universal ou kill switch genérico.

## 12. Semântica de falha e recovery

A arquitetura falha fechada diante de incompatibilidades de schema, proveniência, identidade, escopo, completude, request/source binding, evidence binding, capability binding e identidade content-addressed.

Um estágio que falha não autoriza o próximo apenas porque existe saída parcial.

Operational recovery também distingue desired state, provider state aplicado, provider state observado independentemente e trabalho já admitido.

## 13. Superfícies standing versus históricas

Evidência histórica retida não implica autoridade standing.

```text
historical workflow != inert workflow
historical experiment != standing runtime
historical IAM proof != current IAM principal
retained adapter != deployed network service
retained protocol contract != public peer endpoint
```

Experimentos de AgentCore e Inspector são preservados como evidência enquanto a autoridade standing específica desses experimentos permanece removida. MCP e A2A são retidos como contratos delimitados de interoperabilidade/referência sem runtimes públicos de rede.

## 14. Fronteira de entrada da Phase 18

A Phase 17 está concluída após as Gates 17.1–17.7 e o registro de closeout da Phase 17.

A próxima fase é **Phase 18 — Evaluation, Cost & Portfolio Readiness**. O primeiro passo deve consolidar evidências existentes e determinar comparabilidade antes de criar novos experimentos.

Distinções obrigatórias:

```text
measured value != derived estimate
unmeasured != zero
one experiment != production distribution
quality metric != security metric
latency metric != cost metric
portfolio summary != new technical authority
```

A Phase 18 não deve adicionar runtime público nem ampliar IAM apenas para melhorar a apresentação de portfólio.

A integração deferred com Governed LLM Gateway permanece fora desta fase salvo reautorização explícita.

## 15. Principais architecture records

ADRs retidos importantes incluem:

```text
0020 no unrestricted text-to-SQL
0021 bounded Bedrock Semantic Query planner
0022 customer-managed Bedrock Knowledge Base with S3 Vectors
0023 bounded Bedrock knowledge synthesis
0025 deterministic hybrid routing authority
0026 deterministic hybrid evidence envelope
0027 frozen hybrid evaluation contract
0028 bounded route-aware hybrid synthesis
0029 public repository request admission
0030 public semantic planning proposal authority
0031 Phase 9 public analysis closeout boundary
0059 Phase 15 A2A closeout
0063 Phase 16 runtime-exposure closeout
0064 evidence-first security-hardening priorities
0065 CI/CD and workflow authority hardening
0066 bounded dependency and code-scanning signals
0067 bounded adversarial authority regression suite
0068 content-minimized Lambda telemetry
0069 bounded scheduled-ingestion pause
0070 Phase 17 security-hardening closeout
```

Medições históricas exatas, experimentos, hipóteses rejeitadas, provas de teardown e identidades de runs de CI permanecem em `labs/`, `labs/evidence/`, ADRs, PRs protegidos e histórico Git, em vez de serem reinterpretados como nova autoridade arquitetural neste documento.
