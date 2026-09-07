<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Software Supply Chain e Threat Intelligence Verificáveis na AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Public Analysis Admission · Operational Evidence · Autoridade Determinística**

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
| Phase 10 | Observability & Operational Excellence | 🚧 Em andamento — Gate 10.1 concluída |

A Phase 9 encerra em um **boundary governado de aplicação**, e não em um deployment de produção fictício. O OpsLens possui admissão limitada do request público, orchestration imutável da evidência de repositório, semantic planning proposal-only e handoff determinístico através da autoridade híbrida já existente da Phase 8.

A Gate 10.1 da Phase 10 adiciona agora um contrato provider-neutral e content-minimized de operational evidence sem afirmar que um runtime HTTP público ou backend de telemetry de produção já foi implantado.

```text
telemetry evidence != business truth
telemetry evidence != route authority
telemetry failure != permission to bypass fail-closed application contracts
```

Compute público, runtime IAM, controles de rate/abuse, entrega de telemetry de produção e SLOs derivados de workload continuam trabalho explícito posterior.

Veja [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Arquitetura](docs/architecture.pt-br.md), o [closeout da Phase 9](labs/phase-9-gate-9-4-closeout.md) e a [Gate 10.1](labs/phase-10-gate-10-1-operational-telemetry-contract.md).

## Sistema implementado

O OpsLens possui caminhos governados estruturados, semânticos, híbridos, de public admission e de operational evidence sem misturar níveis de autoridade.

### 1. Autoridade estruturada de vulnerabilidade / risco

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

### 2. Caminho estruturado de perguntas em linguagem natural

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

O planner não recebe autoridade para SQL arbitrário.

### 3. Caminho semântico explicativo / remediação

```text
source pins oficiais e imutáveis
 -> corpus canônico determinístico
 -> Amazon Bedrock Knowledge Base customer-managed
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> Retrieve direto e limitado
 -> admissão determinística contra corpus verificado
 -> montagem limitada de contexto
 -> síntese limitada e não-streaming via Bedrock Converse
 -> identidade determinística de citações
 -> avaliação explícita de suporte / groundedness
```

`RetrieveAndGenerate` não é usado. Retrieval e geração permanecem testáveis e observáveis separadamente.

### 4. Boundary público de análise

```text
JSON público não confiável
 -> admissão estrita <=2048 bytes
 -> coordenadas GitHub owner/name/ref validadas
 -> identidade pública source-confirmed
 -> snapshot imutável commit/tree
 -> evidência inerte uv.lock no commit exato
 -> parser determinístico + normalização PyPI
 -> PublicRepositoryEvidenceExecution
 -> semantic planning request metadata-only <=2048 bytes
 -> proposta não confiável <=1024 bytes
 -> admissão determinística do scope público v1
 -> autoridade híbrida da Phase 8
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

O scope público v1 é propriedade do código, não do modelo. O planner deve propor exatamente:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

e a autoridade de route deve resolver para:

```text
HYBRID
ALL_REQUIRED
STRUCTURED + SEMANTIC
```

O planner não recebe raw repository URL, bytes do lockfile, nomes/versões de dependências, texto/instruções arbitrárias do repositório, SQL, credenciais, seleção de provider/model/tool ou conteúdo executável.

### 5. Contrato de operational evidence

A Gate 10.1 congela:

```text
operational-telemetry:v1
operation: analyze_public_repository
```

Stages limitados:

```text
public_request_admission
repository_evidence
semantic_planning
hybrid_route_admission
public_handoff
```

O contrato de evento não possui arbitrary attributes bag. Ele pode carregar somente semântica operacional limitada e identidades content-addressed da Phase 9 já admitidas (`public_request_id`, `source_execution_id`, `handoff_id`) nos stages onde essas identidades já podem existir.

A projeção de métricas de baixa cardinalidade é determinística:

```text
OperationalStageCount      Count
OperationalStageLatency    Milliseconds
```

com apenas:

```text
ContractVersion
Operation
Stage
Outcome
```

como dimensions. IDs de request/source/handoff nunca se tornam metric dimensions.

Validação exact-head da Gate 10.1:

```text
PR #135 final head:           7742ae003fc8e1ad1d1a6a4f71542875b6d6462c
Operational Observability CI: run 34135197989 / PASS
Ruff:                         PASS
Pyright strict:               0 errors / 0 warnings / 0 informations
pytest:                       14 passed
merge SHA:                    665b86f6e527a0096d7c3db522f4bd2c95b177aa
issue #134:                   CLOSED / COMPLETED
```

## Autoridade híbrida da Phase 8

Hybrid Retrieval significa **hybrid evidence routing**, não automaticamente busca keyword + vector.

```text
EvidenceNeed[]
 -> autoridade determinística de route
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> montagem determinística de evidência tipada
 -> completude ALL_REQUIRED
 -> HybridEvidenceEnvelope
 -> síntese limitada e route-aware
```

Autoridade não é achatada:

```text
fatos estruturados de vulnerabilidade/risco
 -> autoridade estruturada determinística

orientação explicativa/remediação
 -> evidência semântica admitida

resposta combinada
 -> proveniência explícita por classe de evidência
 -> sem authority laundering
```

Runtime exposure continua `UNSUPPORTED` até existir autoridade independente em fase futura.

## Avaliação congelada da Phase 8

Dataset:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Seis casos:

```text
structured_only_factual
semantic_only_remediation
true_hybrid
unsupported_out_of_authority
partial_structured_evidence
semantic_retrieval_noise
```

Métricas independentes:

```text
route_accuracy
structured_fact_correctness
semantic_groundedness
citation_correctness
abstention
latency
cost
```

Não existe composite score.

## Baseline híbrido real da Gate 8.4

Evidência imutável:

```text
labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json
```

Resultado:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

O caso semantic-noise preserva uma falha útil:

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct citation target
```

## Otimização medida da Gate 8.5

H8.5-01 foi testado exatamente uma vez:

```text
candidate: hybrid-synthesis-prompt:h8.5-01-v1
result:    REJECT
```

Não houve melhoria em:

```text
semantic_groundedness: 0.6666666666666666
citation_correctness:  0.6666666666666666
```

O candidato também aumentou total tokens em 280 e não foi promovido.

O default continua:

```text
HybridSynthesisPromptPolicy.GATE_8_4_V1
hybrid-synthesis-prompt:v1
```

## Contracts da Phase 9

```text
public-analysis-request:v1
public-repository-evidence:v1
public-semantic-planning:v1
public-analysis-handoff:v1
```

Distinções importantes:

```text
public request admitted != repository proven public != repository analyzed
planner proposal != execution authority
repository evidence != runtime exposure
semantic planning != SQL authority
application boundary validated != public runtime deployed
```

Evidência exact-head da Phase 9 permanece nos labs/PRs. A Gate 9.3 terminou com Ruff/Pyright verdes, `57 passed` no Public Analysis e zero provider/model calls reais.

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

Não existe public application runtime role após a Gate 10.1. A Gate 10.1 não adiciona recursos AWS nem permissões IAM. Uma futura runtime role pública só será criada quando existir compute boundary concreta e responsabilidades traduzíveis em least privilege.

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
- Citation ID válido prova identidade admitida, não suporte semântico específico.
- Evidência ausente não é silenciosamente interpretada como benigna.
- Runtime exposure não é inferido de repository risk.
- Operational telemetry não se torna autoridade de aplicação ou route.
- Identificadores de alta cardinalidade não são metric dimensions em `operational-telemetry:v1`.
- Evidência de first run é preservada antes da otimização.
- Experimentos negativos são preservados.
- Least privilege, observabilidade, diagnóstico e cost accounting são requisitos arquiteturais.
- Application boundary validado não é apresentado como production runtime implantado.

## Disciplina de custo

O OpsLens não inventa custos que a evidência de runtime não sustenta.

Gate 8.4/8.5 reportam deliberadamente:

```text
cost: UNMEASURED / null
```

Tokens são evidência válida de pressão de custo, mas não preço completo sem pricing contract determinístico e versionado.

O closeout da Phase 9 e a Gate 10.1 não criam preço sintético por request público. Custo futuro deve incluir infraestrutura concreta, concurrency, abuse e retry assumptions.

## Quality gates

Slices dedicados de Python CI cobrem:

```text
Correlation
Repository Intelligence
Risk Policy
Semantic Query
Knowledge Retrieval
Hybrid Retrieval
Public Analysis
Operational Observability
```

O projeto usa Ruff, Pyright strict, pytest e regressions. Mudanças com AWS usam adicionalmente Terraform validation, TFLint, Checkov, planos canônicos, deployment verification e checks pós-apply.

## Estrutura do repositório

```text
.
├── .github/
├── docs/
│   ├── adr/
│   ├── architecture.md
│   ├── architecture.pt-br.md
│   ├── current-state.md
│   ├── roadmap.md
│   └── README.md
├── infra/
├── knowledge/
├── labs/
│   └── evidence/
├── scripts/
├── src/opslens/
│   ├── correlation/
│   ├── repository_intelligence/
│   ├── risk_policy/
│   ├── semantic_query/
│   ├── knowledge_retrieval/
│   ├── hybrid_retrieval/
│   ├── public_analysis/
│   └── shared/observability/
├── tests/
├── README.md
├── README.pt-br.md
├── pyproject.toml
└── uv.lock
```

## Documentação

- [Current State](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [Architecture — English](docs/architecture.md)
- [Arquitetura — Português](docs/architecture.pt-br.md)
- [Índice de ADRs](docs/adr/README.md)
- [Índice de documentação](docs/README.md)
- [Closeout da Phase 8](labs/phase-8-gate-8-6-closeout.md)
- [Gate 9.1 — request admission](labs/phase-9-gate-9-1-public-request-admission.md)
- [Gate 9.3 — semantic planning](labs/phase-9-gate-9-3-bounded-semantic-planning.md)
- [Closeout da Phase 9](labs/phase-9-gate-9-4-closeout.md)
- [Gate 10.1 — operational telemetry](labs/phase-10-gate-10-1-operational-telemetry-contract.md)

## Próxima — Phase 10 Gate 10.2: Governed Orchestration Instrumentation

A Gate 10.2 conectará `operational-telemetry:v1` à orchestration pública já governada através de boundaries provider-neutral injetados. Ela deve definir sequência determinística de eventos e semântica de falha do sink sem permitir que telemetry altere business, route ou evidence authority.

Um runtime público, exporter de produção, SLO ou alert permanece etapa posterior separada, que exige deployment explícito e evidência medida de workload.

A PR #89 de Governed LLM Gateway continua deferred e precisa ser reavaliada separadamente contra a arquitetura vigente no momento.

---

O OpsLens é construído intencionalmente primeiro como sistema de evidência e só depois como sistema agentic.
