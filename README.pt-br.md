<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Software Supply Chain e Threat Intelligence Verificáveis na AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Evidência Determinística**

</div>

OpsLens é uma plataforma open source de inteligência para software supply chain construída na AWS.

Ela foi projetada para responder:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência exata prova isso, quais findings devo priorizar e qual orientação verificável pode me ajudar a agir?

O projeto mantém deliberadamente a verdade determinística separada do raciocínio de modelos.

> **Agents reason. Code verifies evidence.**

Boundaries permanentes adicionais:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

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
| Phase 8 | Hybrid Retrieval | ⏳ Próxima |

A Phase 7 foi encerrada preservando o baseline medido da Gate 7.7 e consolidando a arquitetura na Gate 7.8. O closeout deliberadamente **não** faz prompt tuning contra o resultado observado.

Veja [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md) e [Arquitetura](docs/architecture.pt-br.md).

## Sistema implementado

O OpsLens agora possui dois caminhos complementares de evidência.

### Caminho de autoridade estruturada

```text
NVD / CVE -----------+
CISA KEV ------------+
FIRST EPSS ----------+----> evidência de threat intelligence preservada
GitHub Advisories ---+
                              |
                              v
repositório público GitHub
 -> snapshot imutável do repositório
 -> aquisição GET-only limitada
 -> evidência exata e inerte do uv.lock
 -> normalização determinística PyPI / PEP 440 / purl
 -> aplicabilidade determinística de vulnerable ranges
 -> enrichment NVD/CVSS + CISA KEV + FIRST EPSS
 -> RepositoryAnalysisResult content-addressed
 -> Risk Policy v1 determinística
 -> planejamento SemanticQuery limitado
 -> compilação SQL determinística
 -> Athena read-only limitado
```

O modelo nunca decide aplicabilidade de vulnerabilidade, verdade da Risk Policy ou SQL arbitrário.

### Caminho de conhecimento explicativo / remediação

```text
source pins oficiais e imutáveis
 -> corpus canônico determinístico
 -> Amazon Bedrock Knowledge Base customer-managed
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> Retrieve direto e limitado
 -> admissão determinística contra o corpus verificado
 -> montagem determinística e limitada de contexto
 -> uma síntese limitada via Bedrock Converse
 -> autoridade determinística de citações C1..Cn
 -> proposta estruturada de claims + citation IDs
 -> evidência humana de suporte
 -> métricas determinísticas de groundedness
```

`RetrieveAndGenerate` não é usado. Retrieval e geração permanecem observáveis e testáveis separadamente.

## Baseline medido da Phase 7

### Qualidade de retrieval

Fixture congelada `knowledge-retrieval-golden:v1`:

```text
10 casos: 8 positivos + 2 negativos/out-of-authority
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Os dois casos negativos ainda retornaram vizinhos vetoriais. Logo, score de similaridade ou retrieval não vazio são evidência, não autoridade de answerability.

### Qualidade de groundedness / citações

Fixture congelada `knowledge-grounding-golden:v1`:

```text
decision accuracy:          1.0
citation target precision:  0.2857142857142857
citation target recall:     0.5
claim supportedness:        0.8461538461538461
unsupported claim rate:     0.15384615384615385
citation correctness:       0.8461538461538461
abstention precision:       1.0
abstention recall:          1.0
```

O failure mais útil foi preservado: em um caso, o retrieval encontrou a evidência correta em rank 1, mas o modelo citou um chunk adjacente. O OpsLens trata isso como falha de attribution/groundedness, em vez de escondê-la atrás de retrieval bem-sucedido.

O caso exato de TLS cipher fora do corpus retornou corretamente `insufficient_evidence`, mesmo com retrieval vetorial não vazio.

## Baseline AWS da Phase 7

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

Nenhuma role de runtime da aplicação foi criada na Phase 7. O boundary futuro de IAM foi documentado antes de existir compute: `bedrock:Retrieve` será limitado à Knowledge Base específica, enquanto a invocação não-streaming do modelo usará o US Geographic inference profile exato e os foundation-model resources exigidos para as regiões de destino. `RetrieveAndGenerate`, inferência streaming, administração da Knowledge Base e acesso direto ao vector store não fazem parte do entitlement de runtime.

Veja [ADR 0024](docs/adr/0024-phase7-runtime-iam-boundary.md).

## Invariantes de segurança e autoridade

- Evidência bruta de terceiros é preservada antes da transformação.
- Versões exatas da fonte e hashes participam da identidade da evidência.
- Normalização de packages, ranges/versions, aplicabilidade, KEV/EPSS/CVSS e Risk Policy permanecem determinísticas.
- Código de repositórios de terceiros nunca é executado.
- Planejamento em linguagem natural não recebe autoridade SQL irrestrita.
- Retrieval output é evidência, não verdade determinística.
- Texto recuperado continua sendo conteúdo de instrução não confiável mesmo após validação de proveniência.
- Citation IDs vêm somente do contexto já admitido.
- Um citation ID válido prova cobertura sintática, não suporte semântico.
- Evidência ausente não é interpretada silenciosamente como benigna.
- Evidência de first run é preservada antes de otimização.
- Least privilege, observabilidade, diagnóstico de falhas e cost accounting são requisitos arquiteturais.

## Disciplina de custo

O OpsLens não inventa custos que a evidência de runtime não consegue sustentar.

A primeira avaliação grounded de quatro casos contabilizou diretamente:

```text
model input:             $0.0129074
model output:            $0.0035475
model subtotal:          $0.0164549
4 S3 Vectors requests:   $0.0000100
computable total:        $0.0164649
```

Esse valor não é chamado de conta AWS completa, porque query embeddings e as unidades de S3 Vectors data-processed/data-returned não aparecem no artifact de runtime.

## Quality gates

Slices dedicados de Python CI cobrem:

```text
Correlation
Repository Intelligence
Risk Policy
Semantic Query
Knowledge Retrieval
```

O projeto usa Ruff, Pyright strict, pytest e regressions. Mudanças com AWS usam adicionalmente Terraform validation, TFLint, Checkov, planos canônicos, verificação de deployment e checks pós-apply.

## Estrutura do repositório

```text
.
├── .github/
├── docs/
│   ├── adr/
│   ├── labs/
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
│   └── knowledge_retrieval/
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
- [Closeout da Phase 7 Gate 7.8](labs/phase-7-gate-7-8-closeout.md)

## Próxima — Phase 8: Hybrid Retrieval

Phase 8 não significará “concatenar rows de SQL com chunks vetoriais”. O primeiro passo será congelar um contrato explícito de routing e autoridade entre evidência estruturada e evidência semântica.

Regra inicial:

```text
fatos estruturados de vulnerabilidade/risco -> autoridade estruturada determinística
orientação explicativa/remediação            -> retrieval semântico limitado
resposta combinada                            -> proveniência explícita por classe de evidência
```

Qualquer reranker, keyword/vector hybrid mode, nova tecnologia vetorial ou mudança de prompt precisará ser justificada por requisito medido de qualidade, custo ou failure behavior, e não por cobertura de certificação.

---

O OpsLens é construído intencionalmente primeiro como sistema de evidência e só depois como sistema agentic.
