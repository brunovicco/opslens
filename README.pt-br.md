<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Software Supply Chain e Threat Intelligence Verificáveis na AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Autoridade Determinística**

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
| Phase 9 | Public Analyze Your Repository | ⏳ Próxima |

A Phase 8 encerra com routing/evidence authority híbridos determinísticos, síntese limitada e route-aware, fixture congelada de seis casos, baseline real no Bedrock e um experimento de otimização medido cujo candidato foi corretamente **rejeitado** por não melhorar groundedness nem citation correctness.

Veja [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Arquitetura](docs/architecture.pt-br.md) e o [closeout da Phase 8](labs/phase-8-gate-8-6-closeout.md).

## Sistema implementado

O OpsLens possui três caminhos cooperando, sem misturar seus diferentes níveis de autoridade.

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

Runtime exposure continua `UNSUPPORTED` até existir uma autoridade independente de runtime em fase futura.

## Avaliação congelada da Phase 8

Dataset:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Seis casos congelados:

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

Resultado medido:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

O caso semantic-noise preserva uma falha útil: a evidência rank 1 foi admitida, mas não suportava a pergunta; a evidência rank 2 era o target correto. O modelo usou ambas.

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct citation target
```

## Otimização medida da Gate 8.5

Uma única hipótese prompt-only previamente declarada, `H8.5-01`, foi executada uma vez contra a fixture congelada.

```text
candidate: hybrid-synthesis-prompt:h8.5-01-v1
result:    REJECT
```

O candidato preservou todos os deterministic guardrails, mas não melhorou as duas métricas alvo:

```text
semantic_groundedness: 0.6666666666666666
citation_correctness:  0.6666666666666666
```

Também aumentou o total de tokens do modelo em 280 em relação ao baseline da Gate 8.4. Por isso, não foi promovido.

O runtime default continua:

```text
HybridSynthesisPromptPolicy.GATE_8_4_V1
hybrid-synthesis-prompt:v1
```

Evidência imutável do experimento:

```text
labs/evidence/phase-8-gate-8-5-h85-01-first-run-v1.json
```

Essa é governança de avaliação intencional: uma revisão de prompt plausível não é uma otimização enquanto sua regra de aceitação medida e previamente declarada não passar.

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

Ainda não existe role pública de runtime da aplicação. A Gate 8.6 não adiciona recursos AWS nem permissões IAM. O boundary futuro do caminho semântico continua limitado a `bedrock:Retrieve` na Knowledge Base exata e `bedrock:InvokeModel` não-streaming para o inference profile/resources aprovados. IAM do runtime público será criado somente quando a Phase 9 definir compute real.

## Invariantes de segurança e autoridade

- Evidência bruta de terceiros é preservada antes da transformação.
- Versões exatas das fontes e hashes participam da identidade da evidência.
- Normalização de packages, ranges/versions, aplicabilidade, KEV/EPSS/CVSS e Risk Policy permanecem determinísticas.
- Código de repositórios de terceiros nunca é executado.
- Planejamento em linguagem natural não recebe autoridade SQL irrestrita.
- Retrieval output é evidência, não verdade determinística.
- Texto recuperado continua sendo conteúdo de instrução não confiável após validação de proveniência.
- Routing híbrido e completude de evidência obrigatória são determinísticos.
- Evidência estruturada e semântica permanecem classes de autoridade separadas.
- Citation IDs vêm somente de evidência admitida.
- Citation ID válido prova identidade admitida, não suporte semântico específico para a pergunta.
- Evidência ausente não é silenciosamente interpretada como benigna.
- Runtime exposure não é inferido a partir de repository risk.
- Evidência de first run é preservada antes de otimização.
- Experimentos negativos são preservados em vez de ajustados até “passar”.
- Least privilege, observabilidade, diagnóstico de falhas e cost accounting são requisitos arquiteturais.

## Disciplina de custo

O OpsLens não inventa custos que a evidência de runtime não consegue sustentar.

A Phase 7 possui componentes model/S3 Vectors diretamente computáveis para uma avaliação grounded, enquanto o runtime híbrido das Gates 8.4/8.5 reporta deliberadamente:

```text
cost: UNMEASURED / null
```

Contagem de tokens continua sendo evidência válida de pressão de custo, mas não é convertida silenciosamente em preço completo por request sem um pricing contract determinístico e versionado.

## Quality gates

Slices dedicados de Python CI cobrem:

```text
Correlation
Repository Intelligence
Risk Policy
Semantic Query
Knowledge Retrieval
Hybrid Retrieval
```

O projeto usa Ruff, Pyright strict, pytest e regressions. Mudanças com AWS usam adicionalmente Terraform validation, TFLint, Checkov, planos canônicos, verificação de deployment e checks pós-apply.

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
│   └── hybrid_retrieval/
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
- [Closeout da Phase 7](labs/phase-7-gate-7-8-closeout.md)
- [Gate 8.4 — bounded synthesis](labs/phase-8-gate-8-4-bounded-hybrid-synthesis.md)
- [Gate 8.5 — measured optimization](labs/phase-8-gate-8-5-measured-optimization.md)
- [Closeout da Phase 8](labs/phase-8-gate-8-6-closeout.md)

## Próxima — Phase 9: Public Analyze Your Repository

A Phase 9 poderá expor o evidence system governado como demo pública limitada. Ela deverá preservar aquisição imutável de repositórios, verdade estruturada determinística, autoridade híbrida de route/evidence, output admission fail-closed, zero model calls nos caminhos unsupported/incomplete e limites explícitos de custo/abuso.

Uma superfície pública não justifica introduzir agents, AgentCore, MCP, A2A, rerankers ou nova tecnologia vetorial por padrão. Esses itens permanecem fases posteriores ou novas hipóteses medidas.

A PR #89 de Governed LLM Gateway continua deferred e fora da Phase 8.

---

O OpsLens é construído intencionalmente primeiro como sistema de evidência e só depois como sistema agentic.
