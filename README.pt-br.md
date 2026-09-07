<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Software Supply Chain e Threat Intelligence Verificáveis na AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Public Analysis · Operational Evidence · Autoridade Determinística**

</div>

OpsLens é uma plataforma open source de inteligência para software supply chain construída na AWS.

Ela foi projetada para responder:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência exata prova isso, quais findings devo priorizar e qual orientação verificável pode me ajudar a agir?

O projeto mantém deliberadamente a verdade determinística separada do raciocínio de modelos.

> **Agents reason. Code verifies evidence.**

Boundaries permanentes:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

## Status atual

| Phase | Escopo | Status |
| --- | --- | --- |
| Phase 0 | AWS Foundation | ✅ Concluída |
| Phase 1 | EPSS Vertical Slice | ✅ Concluída |
| Phase 2 | Threat Intelligence Data Lake | ✅ Concluída |
| Phase 3 | Vulnerability Correlation Engine | ✅ Concluída |
| Phase 4 | Repository Intelligence | ✅ Concluída |
| Phase 5 | Risk Prioritization Engine | ✅ Concluída |
| Phase 6 | Semantic Query Layer | ✅ Concluída |
| Phase 7 | Knowledge Retrieval with Bedrock | ✅ Concluída |
| Phase 8 | Hybrid Retrieval | ✅ Concluída |
| Phase 9 | Public Analyze Your Repository | ✅ Concluída |
| Phase 10 | Observability & Operational Excellence | ✅ Concluída |
| Phase 11 | Single-Agent Baseline | ▶️ Próxima |

A Phase 9 encerra em um **boundary governado de aplicação**, e não em um deployment fictício de produção. A Phase 10 torna esse boundary diagnosticável e adiciona uma representação de telemetry nativa da AWS sem afirmar que existe runtime público implantado ou ingestão real no CloudWatch.

```text
application boundary validated != public runtime deployed
telemetry evidence != business truth
telemetry evidence != route authority
EMF document created != CloudWatch ingestion proven
```

Veja [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Arquitetura](docs/architecture.pt-br.md) e o [closeout da Phase 10](labs/phase-10-gate-10-4-closeout.md).

## Sistema implementado

### 1. Autoridade estruturada de vulnerabilidade e risco

```text
NVD / CVE -----------+
CISA KEV ------------+
FIRST EPSS ----------+----> evidência de threat intelligence preservada
GitHub Advisories ---+
                              |
                              v
repositório público GitHub
 -> snapshot imutável
 -> aquisição GET-only limitada
 -> evidência exata e inerte do uv.lock
 -> normalização determinística PyPI / PEP 440 / purl
 -> aplicabilidade determinística de vulnerable ranges
 -> enrichment NVD/CVSS + CISA KEV + FIRST EPSS
 -> RepositoryAnalysisResult content-addressed
 -> Risk Policy v1 determinística
```

O modelo nunca decide aplicabilidade de vulnerabilidade, verdade da Risk Policy, fatos de KEV/EPSS/CVSS ou runtime exposure.

### 2. Caminho estruturado de linguagem natural

```text
pergunta factual em linguagem natural
 -> planner Bedrock limitado
 -> proposta estruturada
 -> parser determinístico
 -> SemanticQuery tipada
 -> compilador SQL determinístico
 -> Athena read-only limitado
 -> evidência estruturada
```

O planner nunca recebe autoridade para SQL arbitrário.

### 3. Grounded knowledge retrieval

```text
source pins oficiais e imutáveis
 -> corpus canônico determinístico
 -> Amazon Bedrock Knowledge Base
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> Retrieve limitado
 -> admissão determinística contra corpus verificado
 -> montagem limitada de contexto
 -> síntese limitada via Bedrock Converse
 -> identidade determinística de citação
 -> avaliação explícita de groundedness
```

`RetrieveAndGenerate` não é usado deliberadamente. Retrieval, admissão de contexto, síntese, citações e avaliação permanecem testáveis separadamente.

### 4. Autoridade de evidência híbrida

```text
EvidenceNeed[]
 -> autoridade determinística de route
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> composição de evidência separada por autoridade
 -> completude ALL_REQUIRED
 -> HybridEvidenceEnvelope
 -> projeções determinísticas F* / S*
 -> síntese limitada e route-aware
 -> admissão determinística de output
```

Fatos estruturados de vulnerabilidade/risco e evidência semântica de remediação nunca se tornam uma classe única e indiferenciada de autoridade.

Runtime exposure continua `UNSUPPORTED` até existir uma autoridade independente futura.

### 5. Boundary governado de public analysis

```text
JSON público não confiável
 -> admissão estrita e limitada
 -> coordenadas GitHub owner/name/ref validadas
 -> identidade pública source-confirmed
 -> snapshot imutável commit/tree
 -> evidência inerte uv.lock no commit exato
 -> parsing determinístico + normalização PyPI
 -> PublicRepositoryEvidenceExecution
 -> semantic planning proposal metadata-only e limitado
 -> admissão determinística do scope público v1
 -> autoridade híbrida existente da Phase 8
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

O scope público v1 é propriedade do código, não do modelo.

### 6. Operational evidence e representação CloudWatch EMF

A Phase 10 congela:

```text
operational-telemetry:v1
operation: analyze_public_repository
```

Cinco stages limitados:

```text
public_request_admission
repository_evidence
semantic_planning
hybrid_route_admission
public_handoff
```

Métricas de baixa cardinalidade:

```text
OperationalStageCount      Count
OperationalStageLatency    Milliseconds
```

Dimensions exatas:

```text
ContractVersion
Operation
Stage
Outcome
```

A Gate 10.2 instrumenta o caminho governado por meio das portas injetadas `MonotonicClock` e `OperationalEventSink`. Uma execução bem-sucedida emite exatamente cinco eventos ordenados; stages rejeitados/falhos são terminais.

A Gate 10.3 adiciona serialização AWS-native determinística:

```text
cloudwatch-emf:v1
namespace: OpsLens/Operational
storage resolution: 60 seconds
maximum canonical document: 16 KiB
```

```text
OperationalEvent
 -> project_operational_metrics(...) existente
 -> JSON CloudWatch EMF canônico
 -> CloudWatchEmfDocument content-addressed
 -> EpochMillisecondsClock injetado
 -> EmfLineWriter injetado
 -> STOP
```

`EventId`, `PublicRequestId`, `SourceExecutionId` e `HandoffId` permanecem somente metadata de log e nunca se tornam metric dimensions.

O adapter executa zero retries e tenta escrever no máximo uma vez por `emit(...)`.

## Closeout da Phase 10

A Phase 10 prova:

```text
contrato provider-neutral de operational event
instrumentação determinística e limitada por stage
identidades content-minimized de proveniência/correlação
projeção fixa de métricas de baixa cardinalidade
sink externo best-effort após evidência obrigatória in-process
failure taxonomy limitada e sem conteúdo arbitrário
serialização determinística cloudwatch-emf:v1
semântica separada de monotonic-duration e epoch-milliseconds
zero retries no adapter
evidência operacional/EMF content-addressed
```

Ela **não** prova:

```text
runtime HTTP público
ingestão no CloudWatch
runtime principal / runtime IAM
volume de requests públicos
distributed traces de produção
p95/p99 de produção
taxas de erro/throttle de produção
custo/request de produção
dashboards/alarms de produção
compliance de SLO de produção
```

### Validação exata da Phase 10

```text
Gate 10.1
  PR #135 head: 7742ae003fc8e1ad1d1a6a4f71542875b6d6462c
  CI:           34135197989 / PASS
  pytest:       14 passed
  merge:        665b86f6e527a0096d7c3db522f4bd2c95b177aa

Gate 10.2
  PR #138 head: 24b2affdf464e2548d94273e41007bb3256b561e
  CI:           34141496326 / PASS
  Pyright:      0 errors / 0 warnings / 0 informations
  pytest:       70 passed
  merge:        346b223d9566a5d04d84e279f30793ad52a35b67

Gate 10.3
  PR #141 head: 632e778d36ada833505342708379603a1080d390
  CI:           34143908297 / run #9 / PASS
  Pyright:      0 errors / 0 warnings / 0 informations
  pytest:       26 passed
  merge:        0c5bf6bab39a3980c063fcb44f657c412111fefa
```

## Avaliação híbrida congelada

Dataset:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Primeiro baseline real completo da Gate 8.4:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

A Gate 8.5 testou uma hipótese prompt-only predefinida exatamente uma vez e a rejeitou porque as métricas alvo de qualidade não melhoraram.

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct citation target
```

## Baseline AWS

```text
environment:             dev
Region:                  us-east-1
knowledge base:          BTVJ2PBR2A
data source:             IEL1LBE026
vector store:            Amazon S3 Vectors
embedding model:         amazon.titan-embed-text-v2:0
dimensions:              1024
chunking:                NONE
canonical chunks:        9
synthesis API:           bedrock-runtime / Converse
synthesis profile:       us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:               não
tools:                   nenhum
```

A Phase 10 adiciona **zero** recursos de runtime público e **zero** permissões de runtime IAM. Em particular, não concede `logs:PutLogEvents` nem `cloudwatch:PutMetricData`.

## Invariantes de segurança e autoridade

- Evidência bruta de terceiros é preservada antes da transformação.
- Versões exatas e hashes participam da identidade da evidência.
- Normalização, ranges/versions, aplicabilidade, KEV/EPSS/CVSS e Risk Policy permanecem determinísticos.
- Código de terceiros nunca é executado.
- Public request admission não concede fetch authority arbitrária.
- Public semantic planning não controla product scope nem execution authority.
- Planejamento em linguagem natural não recebe autoridade SQL irrestrita.
- Retrieval output é evidência, não verdade determinística.
- Texto recuperado continua não confiável como instrução após validação de proveniência.
- Hybrid routing e completude obrigatória são determinísticos.
- Evidência estruturada e semântica permanecem classes separadas.
- Citation IDs vêm somente de evidência admitida.
- Runtime exposure não é inferido de repository risk.
- Operational telemetry não se torna business ou route authority.
- IDs de correlação de alta cardinalidade não viram metric dimensions.
- Delivery accounting de telemetry não pode inventar identidades de evidência.
- Serialização EMF não é apresentada como ingestão no CloudWatch.
- Evidência de first run e experimentos negativos são preservados.
- Least privilege, observabilidade, diagnóstico de falhas e cost accounting são requisitos arquiteturais.

## Disciplina de custo

OpsLens não inventa custos que a evidência de runtime não suporta.

```text
unmeasured cost != zero cost
```

A Phase 10 prova um desenho de controle de cardinalidade, não custo real de CloudWatch. Custo de observabilidade de produção exige volume de workload, ingestão, retenção, quantidade de time series, retries e evidência real de runtime.

## Documentação

- [Current State](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [Architecture — English](docs/architecture.md)
- [Arquitetura — Português](docs/architecture.pt-br.md)
- [Índice de ADRs](docs/adr/README.md)
- [Índice de documentação](docs/README.md)
- [Closeout da Phase 8](labs/phase-8-gate-8-6-closeout.md)
- [Closeout da Phase 9](labs/phase-9-gate-9-4-closeout.md)
- [Gate 10.1](labs/phase-10-gate-10-1-operational-telemetry-contract.md)
- [Gate 10.2](labs/phase-10-gate-10-2-governed-orchestration-instrumentation.md)
- [Gate 10.3](labs/phase-10-gate-10-3-cloudwatch-emf-adapter.md)
- [Closeout da Phase 10](labs/phase-10-gate-10-4-closeout.md)

## Próxima — Phase 11: Single-Agent Baseline

A Phase 11 começa com **um único agente limitado** sobre capabilities já governadas do OpsLens, antes de qualquer complexidade multi-agent.

```text
agent reasoning may select/use already-authorized capabilities
agent reasoning does not acquire deterministic truth or execution authority
```

A primeira gate da Phase 11 deve congelar a superfície exata de tools/capabilities, execution limits, failure/abstention semantics, evidence handoff, evaluation fixture e mapeamento para a observabilidade da Phase 10 antes da escolha de infraestrutura gerenciada de runtime de agentes.

A PR #89 de Governed LLM Gateway permanece deferred e precisa ser reavaliada separadamente contra a arquitetura vigente do OpsLens.

---

O OpsLens é construído intencionalmente primeiro como sistema de evidência e só depois como sistema agentic.
