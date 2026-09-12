# Arquitetura do OpsLens

_Última atualização: 2026-09-12_

Este documento é o baseline arquitetural atual até a **Phase 19 Gate 19.8**, com a Gate 19.9 congelando a fronteira de fechamento da V1 focada em demonstração.

A V1 do OpsLens é um laboratório de demonstração e arquitetura, não um SaaS de produção.

## 1. Propósito

OpsLens é um projeto open source de supply chain de software e arquitetura GenAI na AWS.

Pergunta do produto:

> Dado o software realmente usado por um repositório, quais vulnerabilidades o afetam, qual evidência exata comprova isso, quais achados devem ser priorizados e qual orientação verificada pode ajudar na ação?

Invariante central:

> **Agents reason. Code verifies evidence.**

Fronteiras permanentes:

```text
Not every question is a RAG problem.
Structured facts use structured retrieval.
No unrestricted text-to-SQL.
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
Intent classification != execution authority.
retrieved content != instruction authority
model proposal != authorization
tool/protocol success != business truth
historical evidence != standing authority
missing evidence != benign evidence
MEASURED != DERIVED
UNMEASURED != zero
NOT_APPLICABLE != zero
configured limit != measured utilization
artifact hash != S3 VersionId
publication success != deployment authorization
plan != apply
materialized != enabled
demonstration readiness != production readiness
AIP-C01 topic != product requirement
```

## 2. Objetivo arquitetural da V1

A demonstração V1 deve tornar compreensível e reprodutível esta cadeia de autoridade:

```text
evidência de repositório público
 -> evidência inerte de dependências
 -> evidência estruturada de ameaças
 -> aplicabilidade/correlação determinística
 -> priorização de risco determinística
 -> retrieval/raciocínio limitados quando apropriado
 -> resultado baseado em evidências
```

Target canônico para quem avalia o projeto:

```text
clone
 -> setup
 -> um comando determinístico de demo offline
 -> resultado baseado em evidências
```

A conclusão da V1 não exige runtime de produção exposto na Internet.

## 3. Modelo de autoridade

### 3.1 Autoridade determinística

Código determinístico é responsável por:

- admissão de identidade do repositório/fonte;
- identidade imutável do snapshot do repositório;
- normalização de dependências/pacotes;
- aplicabilidade pacote/versão;
- reconciliação GHSA/NVD;
- lookup de evidências KEV/EPSS/CVSS;
- política de risco;
- admissão de semantic queries;
- compilação SQL;
- admissão de evidências de retrieval;
- admissão de citações/resultados;
- autorização de capabilities/tools;
- limites de execução/custo/recursos;
- autoridade de job/state/idempotência/retry no runtime assíncrono;
- identidade de artefatos de deployment;
- fronteiras de evidência de Terraform plan/apply.

### 3.2 Autoridade de modelos/agentes

Modelos e agentes podem:

- classificar;
- planejar;
- rotear;
- resumir;
- explicar;
- sintetizar sobre evidências admitidas.

Eles não podem inventar ou sobrescrever identidade de pacotes, aplicabilidade de vulnerabilidades, proveniência, verdade de risco, SQL arbitrário, autorização de tools ou semântica de evidência ausente.

## 4. Arquitetura retida da plataforma

### 4.1 Threat intelligence

```text
NVD
GitHub Security Advisories
CISA KEV
FIRST EPSS
        |
        v
evidência raw preservando a fonte
        |
        v
normalização/versionamento determinísticos
        |
        v
coordenadas exatas da fonte + hashes/snapshots
```

A proveniência source-local é preservada antes de qualquer enrichment.

### 4.2 Repository intelligence

```text
coordenadas de repositório público no GitHub
 -> admissão estrita da requisição
 -> metadata confirmada pela fonte
 -> snapshot de commit imutável
 -> evidência inerte de uv.lock no commit exato
 -> parsing TOML determinístico
 -> identidade PyPI canônica
```

Código de terceiros nunca é executado.

### 4.3 Correlação de vulnerabilidades e risco

```text
identidade canônica de dependência
 + evidência de aplicabilidade GHSA/NVD
 + snapshot KEV
 + snapshot EPSS
 + evidência CVSS
        |
        v
RepositoryAnalysisResult
        |
        v
Risk Policy determinística
```

O risco permanece determinístico. O modelo pode explicar o resultado admitido, mas não alterá-lo.

### 4.4 Caminho factual estruturado em linguagem natural

```text
pergunta factual em linguagem natural
 -> proposta Bedrock limitada
 -> parser/admissão determinísticos
 -> SemanticQuery tipada
 -> compilador SQL determinístico
 -> Athena read-only limitado
 -> resultado estruturado
```

Não existe autoridade de text-to-SQL irrestrita.

### 4.5 Caminho de conhecimento/remediação

```text
corpus oficial de conhecimento
 -> documentos/chunks canônicos
 -> Bedrock Knowledge Base
 -> S3 Vectors
 -> Retrieve limitado
 -> admissão determinística de evidências
 -> síntese limitada
 -> resposta + citações
```

A verdade estruturada de vulnerabilidades permanece fora da autoridade do RAG.

### 4.6 Hybrid retrieval

```text
pergunta
 -> roteamento/scope determinísticos
 -> evidência estruturada e/ou semântica
 -> envelope preservando classes de autoridade
 -> síntese limitada
```

Evidência semântica não substitui fatos estruturados.

### 4.7 Raciocínio agentic

```text
evidência admitida
 -> scope determinístico de capability
 -> proposta/raciocínio de modelo limitado
 -> autorização determinística de capability
 -> execução tipada
 -> admissão de resultado
```

O baseline single-agent mais simples permanece a arquitetura de referência. Especialização/handoff multi-agent é retida onde útil, mas topologias adicionais de modelo não viram default sem ganho de qualidade medido.

### 4.8 MCP e A2A

MCP e A2A são camadas de interoperabilidade limitadas, não nova autoridade de negócio.

```text
requisição de protocolo
 -> admissão estrita de identidade/schema
 -> capability tipada existente
 -> projeção de resultado admitido
```

Runtimes MCP/A2A públicos de produção não são requisitos da V1.

### 4.9 AgentCore

Amazon Bedrock AgentCore é retido como target opcional de laboratório após experimentos de capability fit. Não é o runtime padrão de produção e não mantém IAM experimental permanente apenas por fazer parte do histórico do projeto.

### 4.10 Evidência de runtime exposure

Amazon Inspector é tratado como autoridade independente e read-only para runtime exposure.

```text
Inspector read evidence != repository risk truth
zero Inspector records != zero runtime exposure
```

## 5. Observabilidade, segurança e custo

### 5.1 Observabilidade

Telemetry operacional é content-minimized e não se torna autoridade de negócio.

O projeto mantém evidências operacionais orientadas a CloudWatch/EMF, traces/metrics quando relevantes, contadores explícitos de retry/latência e artefatos persistidos de experimentos.

### 5.2 Segurança

Hardening retido inclui:

- GitHub Actions pinadas por SHA completo;
- Dependency Review;
- CodeQL;
- adversarial authority regression;
- IAM least privilege;
- telemetry Lambda com minimização de conteúdo;
- pause/recovery limitados para ingestão agendada;
- fronteiras de revisão em protected main;
- admissão fail-closed de requests/evidências/resultados.

### 5.3 Semântica de custo

OpsLens distingue:

```text
MEASURED
DERIVED
CONFIGURED_LIMIT
UNMEASURED
NOT_APPLICABLE
```

Evidência de custo de experimento limitado nunca é promovida a claim de TCO de produção.

## 6. Arquitetura do runtime assíncrono da Phase 19

A Gate 19.2 selecionou `ASYNC_SUBMIT_STATUS_RESULT` a partir de evidência de workload representativo.

A Gate 19.3 selecionou:

```text
HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
```

Forma retida:

```text
POST /v1/analyses
 -> API Gateway HTTP API
 -> API Lambda
 -> autoridade de job/idempotência no DynamoDB
 -> fila SQS standard
 -> Lambda worker
 -> autoridades de análise retidas
 -> status/resultado no DynamoDB
 -> SQS DLQ

GET /v1/analyses/{job_id}
GET /v1/analyses/{job_id}/result
```

Entrega na fila é evidência de transporte, não verdade de execução. Autoridade condicional de state/attempt no DynamoDB controla o estado de negócio.

## 7. Evidência de deployment da Phase 19

### 7.1 Artefatos imutáveis

A Gate 19.5 produziu ZIPs determinísticos separados para API/worker e preservou hash de conteúdo e VersionId exato do objeto S3.

```text
artifact hash != S3 VersionId
publication success != deployment authorization
```

### 7.2 Planejamento Terraform exato

A Gate 19.6 admitiu um plano exato antes de qualquer apply:

```text
21 create
0 update
0 delete
0 replacement
```

### 7.3 Materialização controlada e desabilitada

A Gate 19.7 materializou o runtime por operações Terraform limitadas e autorizadas por HUMANO, recuperou uma restrição de reserved concurrency da conta Lambda e provou convergência final:

```text
0 add
0 change
0 destroy
0 replacement
```

Estado retido do runtime:

```text
recursos do runtime assíncrono materializados: 21
endpoint público habilitado: NÃO
submit habilitado: NÃO
worker habilitado: NÃO
event-source mapping habilitado: NÃO
domínio público customizado: ausente
execuções públicas provider-heavy: 0
```

```text
materialized != enabled
```

## 8. Gate 19.8 — autoridade de threat evidence em request-time

A Gate 19.8 foi mergeada pelo PR #375 em:

```text
e538fa3e96c29cf76dd3aa83a9967e090587b6fb
```

CodeQL pós-merge:

```text
34713360403 / run #393 / success
```

Cadeia provider-neutral:

```text
PublicRepositoryEvidenceExecution
 -> PublicThreatEvidenceScope
 -> PublicThreatEvidenceRequest
 -> PublicThreatEvidenceAuthority
 -> PublicRepositoryThreatEvidence
 -> correlação/enriquecimento determinísticos retidos
```

Semânticas:

```text
scope deriva apenas de evidência admitida do repositório
normalização PyPI incompleta -> fail closed
GHSA fora do scope -> rejeitar
NVD não relacionado -> rejeitar
latest_complete = política de seleção, não proveniência
KEV/EPSS selecionados carregam snapshot date + SHA-256 exatos
autoridade do modelo sobre source truth/aplicabilidade = nenhuma
```

O adapter físico de provider permanece deliberadamente deferido. Como a V1 é offline-first, esse adapter passa a ser experimento Post-V1 em vez de blocker para a primeira versão.

## 9. Gate 19.9 — fronteira de demonstração da V1

A Gate 19.9 congela a fronteira do primeiro release:

```text
modo V1: DEMONSTRATION_ARCHITECTURE_LAB
claim de SaaS de produção: NÃO
runtime exposto na Internet obrigatório: NÃO
credenciais AWS necessárias para demo canônica: NÃO
execução de código de terceiros: NÃO
```

Slices restantes:

```text
19.9   contrato V1 + sincronização de estado atual
19.10  runner determinístico end-to-end
19.11  cenários curados + avaliação determinística
19.12  demo visual local mínima
19.13  polish de portfólio/readme/arquitetura
19.14  closeout V1 + readiness de release
```

## 10. Arquitetura da demo canônica V1

O caminho canônico será local e offline-first:

```text
fixture inerte e curada
 -> contratos existentes de evidência de repositório/dependência
 -> contratos existentes de threat evidence
 -> correlação/enriquecimento determinísticos
 -> risk policy determinística
 -> resultado machine-readable estável
 -> projeção human-readable
 -> explicação opcional limitada sobre evidência admitida
```

A demo deve reutilizar autoridades existentes de domínio/aplicação do OpsLens e não criar uma segunda implementação da verdade de negócio.

Classes obrigatórias de cenário:

```text
material vulnerability
controlled benign
fail-closed incomplete/ambiguous evidence
```

## 11. Não objetivos da V1

A primeira versão não exige:

```text
runtime de produção exposto na Internet
autenticação / OIDC / Cognito
multi-tenancy
billing/quotas comerciais
domínio público customizado
WAF / controles de abuso de produção
operação 24x7
SLO/SLA de produção
programa HA/DR
claim de TCO de produção
habilitação pública de worker/event-source
adapter genérico provider-backed de threat evidence em request-time
```

Esses itens ficam em [`post-v1-backlog.md`](post-v1-backlog.md).

## 12. Fronteira de autoridade atual

A Gate 19.9 é repository-only e offline-only.

```text
operações Terraform/provider: NÃO AUTORIZADAS
mutação AWS:                 NÃO AUTORIZADA
mutação IAM:                 NÃO AUTORIZADA
publicação de artefatos:     NÃO AUTORIZADA
habilitação de runtime:      NÃO AUTORIZADA
execução live provider-heavy:NÃO AUTORIZADA
protected merge:             REVISÃO HUMANA OBRIGATÓRIA
```

## 13. Documentos principais

- [`current-state.md`](current-state.md)
- [`roadmap.md`](roadmap.md)
- [`v1-demonstration-scope.md`](v1-demonstration-scope.md)
- [`v1-completion-checklist.md`](v1-completion-checklist.md)
- [`demo/README.md`](demo/README.md)
- [`post-v1-backlog.md`](post-v1-backlog.md)
- [`adr/0077-phase19-v1-demonstration-boundary.md`](adr/0077-phase19-v1-demonstration-boundary.md)
- [`../labs/phase-19-gate-19-9-v1-demonstration-contract.md`](../labs/phase-19-gate-19-9-v1-demonstration-contract.md)

Labs históricos e evidências machine-readable permanecem registros imutáveis do estado existente em cada experimento.
