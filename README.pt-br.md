<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Software Supply Chain e Threat Intelligence Verificáveis na AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Public Analysis · Operational Evidence · Bounded Agent Reasoning · MCP Interoperability · Autoridade Determinística**

</div>

OpsLens é uma plataforma open source de inteligência para software supply chain construída na AWS.

Ela foi projetada para responder:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência exata prova isso, quais findings devo priorizar e qual orientação verificável pode me ajudar a agir?

O projeto mantém deliberadamente separados verdade determinística, admissão de evidência, raciocínio de modelos, autorização, admissão de handoff, interoperabilidade, execução, divulgação de resultados e runtime exposure.

> **Agents reason. Code verifies evidence.**

> **MCP is an interoperability boundary, not new business authority.**

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
| Phase 11 | Single-Agent Baseline | ✅ Concluída |
| Phase 12 | Multi-Agent Architecture | ✅ Concluída |
| Phase 13 | MCP | ✅ Concluída — boundary MCP offline limitado retido |
| Phase 14 | Amazon Bedrock AgentCore | ▶️ Próxima |
| Phase 15 | A2A | ⏳ Planejada |
| Phase 16 | Runtime Exposure with Amazon Inspector | ⏳ Planejada |
| Phase 17 | Security Hardening | ⏳ Planejada |
| Phase 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planejada |

Veja [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Arquitetura](docs/architecture.pt-br.md), o [closeout da Phase 12](labs/phase-12-gate-12-5-multi-agent-closeout.md) e o [closeout MCP da Phase 13](labs/phase-13-gate-13-5-mcp-closeout.md).

## Sistema governado implementado

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

O modelo nunca decide aplicabilidade de vulnerabilidade, verdade da Risk Policy, fatos KEV/EPSS/CVSS ou runtime exposure.

### 2. Caminho estruturado de linguagem natural

```text
pergunta factual em linguagem natural
 -> model planner limitado
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

Fatos estruturados de vulnerabilidade/risco e evidência semântica de remediação permanecem classes separadas de autoridade. Runtime exposure continua `UNSUPPORTED` até existir uma autoridade independente.

### 5. Boundary governado de public analysis

```text
JSON público não confiável
 -> admissão determinística do request
 -> evidência pública GitHub imutável
 -> análise determinística do repositório
 -> semantic planning apenas como proposal
 -> admissão determinística do scope público v1
 -> autoridade híbrida existente
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

O scope público v1 é propriedade do código, não do modelo.

### 6. Operational evidence

A Phase 10 congela:

```text
operational-telemetry:v1
cloudwatch-emf:v1
```

Operational evidence é content-minimized e de baixa cardinalidade. Serialização CloudWatch EMF é um boundary determinístico de representação, não prova de ingestão no CloudWatch.

```text
telemetry evidence != business truth
telemetry evidence != route authority
EMF document created != CloudWatch ingestion proven
```

### 7. Bounded single-agent reasoning

A Phase 11 congela:

```text
single-agent-authority:v1
single-agent-execution:v1
single-agent-evaluation:v1
single-agent-reasoning:v1
single-agent-reasoning-evaluation:v1
```

Boundary permanente de raciocínio:

```text
SingleAgentTask
 -> AgentCapability allowlist controlada por código
 -> uma model reasoning invocation limitada
 -> {decision, capability} transitório e não confiável
 -> parser determinístico
 -> AgentActionProposal
 -> authorize_agent_action(...) determinístico
 -> AuthorizedAgentAction | AgentAbstention | stable rejection
```

O baseline real da Gate 11.4 termina intencionalmente antes da capability execution. A execução tipada permanece um boundary determinístico separado.

### 8. Autoridade limitada de handoff multi-agent

A Phase 12 Gate 12.1 congela:

```text
multi-agent-handoff:v1
```

Partição de especializações controlada por código:

```text
EVIDENCE_ANALYSIS
 -> public_repository_analysis
 -> structured_security_query

GUIDANCE_SYNTHESIS
 -> hybrid_security_answer
 -> knowledge_guidance
```

Boundary de handoff:

```text
SingleAgentTask
 -> TriageAgentTask
 -> MultiAgentHandoffProposal não confiável
 -> binding determinístico com a source task
 -> scope de especialização controlado por código
 -> interseção determinística com source allowed_capabilities
 -> interseção vazia? FAIL CLOSED
 -> AuthorizedMultiAgentHandoff | MultiAgentHandoffAbstention
 -> SpecialistAgentTask com scope reduzido
 -> STOP
```

A redução `4 -> <=2` é narrowing da superfície de raciocínio, não uma alegação de redução de privilégio em runtime. Os modelos continuam sem autoridade de execução.

### 9. Autoridade determinística da comparação multi-agent

A Phase 12 Gate 12.2 congela:

```text
multi-agent-comparison:v1
```

O contrato de comparação foi congelado antes de existir uma segunda invocação real de modelo. O resultado sintético `6/6` é conformidade do evaluator/contrato, não qualidade de modelo.

Identidades exatas:

```text
Phase 11 corpus_sha256:   3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
Phase 11 report_sha256:   724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
Gate 12.2 dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
Gate 12.2 report_sha256:  0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
```

### 10. Experimento multi-agent medido e decisão de retenção

A Gate 12.3 introduziu o primeiro experimento autenticado e limitado com dois modelos, mantendo handoff e capability authorization determinísticos.

Resultado observado:

```text
quality:                           6/6
model invocations:                 10
input/output/total tokens:          5788 / 194 / 5982
provider latency median per task:  1694.0 ms
client elapsed median per task:    2135.0 ms
SDK retries:                       0
capability executions:             0
derived six-case cost:             USD 0.0074338
```

A Gate 12.4 comparou esse resultado com a referência da Phase 11:

```text
quality:                    6/6 -> 6/6      sem ganho
model invocations:          6 -> 10         +66.67%
total tokens:               3395 -> 5982    +76.20%
provider latency median:    809.5 -> 1694   +109.26%
client elapsed median:      977.5 -> 2135   +118.41%
derived cost:               0.0041921 -> 0.0074338 USD  +77.33%
```

Decisão congelada:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
```

A Phase 12 foi encerrada em torno da arquitetura que sobreviveu à medição, não da topologia mais complexa implementada.

### 11. Interoperabilidade MCP limitada e divulgação de resultados

A Phase 13 congela três contratos voltados ao protocolo:

```text
mcp-capability-exposure:v1
mcp-capability-execution:v1
mcp-result-projection:v1
```

Superfície MCP fechada e um-para-um:

```text
opslens.structured_security_query   -> structured_security_query
opslens.knowledge_guidance          -> knowledge_guidance
opslens.hybrid_security_answer      -> hybrid_security_answer
opslens.public_repository_analysis  -> public_repository_analysis
```

Caminho retido da Phase 13:

```text
autoridade tipada existente da Phase 11
 -> identidade MCP fechada
 -> adapter reference-only do MCP SDK oficial
 -> recusa exata de raw argument keys
 -> resolução + admissão determinísticas
 -> exatamente uma tentativa do executor tipado existente
 -> bridge de execução MCP content-addressed
 -> mcp-result-projection:v1 explícito apenas para structured_security_query
 -> linhas CVE + EPSS limitadas
 -> STOP antes de runtime público/de rede
```

A entrada do protocolo continua sendo apenas `invocation_id` e `invocation_sha256`. MCP não pode criar `SemanticQuery`, SQL, URLs, shell commands, credenciais, seleção de provider/model, política de retry/fallback nem `args`/`kwargs` executáveis arbitrários.

O MCP Python SDK oficial está pinado como `mcp==2.2.0` apenas nas dependências de desenvolvimento. Testes reais de interoperabilidade mostraram que a coerção de argumentos gerada pelo SDK/Pydantic pode ignorar campos inesperados; por isso o OpsLens valida o conjunto exato de chaves do request antes da coerção do framework. Um experimento separado de dependency placement mostrou que mover MCP para runtime dependencies aumentava pacotes Lambda não relacionados e quebrava um package-size gate existente; o limite de deploy não foi enfraquecido.

A divulgação de business result é deliberadamente mais estreita que capability execution. A Phase 13 transporta conteúdo de negócio apenas para `structured_security_query`, por meio de um projector explícito que mapeia o shape interno já admitido `("cve", "epss")` para linhas limitadas com `cve` + `epss_score`. Resultados de knowledge, hybrid e public-repository permanecem sem transporte de business content.

A Phase 13 é encerrada nesse boundary offline/in-process limitado. Ela não cria runtime MCP público apenas por completude.

## Baseline real Bedrock da Phase 11

```text
Amazon Bedrock Converse
region:          us-east-1
model/profile:   us.anthropic.claude-haiku-4-5-20251001-v1:0
temperature:     0.0
maxTokens:       96
tools:           disabled
```

Resultado medido:

```text
proposal quality:             6/6
bounds compliance:            6/6
SDK retries:                  0
capability executions:        0
input/output/total tokens:    3291 / 104 / 3395
provider latency median:      809.5 ms
client elapsed median:        977.5 ms
derived six-case cost:        USD 0.0041921
```

Evidência preservada:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
```

O resultado 6/6 é resultado de um acceptance corpus congelado, não uma afirmação de correção universal do modelo.

## Evidência de closeout da Phase 13

```text
issue:                  #192
PR:                     #193
final head:             99dd3d979a5205e38f2c1a4dfc84dc9f82d0e0c7
PR merge test commit:   7ec68aa12bc0a08b698ed0ddf76434e7bd97fe85
MCP CI:                 34250265151 / run #52 / PASS
job:                    102142600531
uv lock --check:        PASS
MCP SDK pin:            PASS
MCP import smoke:       PASS
Ruff:                   PASS
Pyright strict:         0 errors / 0 warnings / 0 informations
pytest MCP slice:       29 passed in 0.90s
review threads:         0
PR comments:            0
model invocations:      0
new AWS/IAM:            0
public MCP endpoint:    0
MCP deployed runtime:   0
merge SHA:              c449cfc8e18dfd240ceedbe6e8e4d143601f0254
```

Artefatos de closeout:

```text
labs/evidence/phase-13-closeout-v1.json
labs/phase-13-gate-13-5-mcp-closeout.md
docs/adr/0051-phase13-mcp-closeout.md
```

## Invariantes de segurança e autoridade

- Evidência bruta de terceiros é preservada antes da transformação.
- Versões exatas e hashes participam da identidade da evidência.
- Normalização, ranges/versions, aplicabilidade, KEV/EPSS/CVSS e Risk Policy permanecem determinísticos.
- Código de terceiros nunca é executado.
- Public request admission não concede fetch authority arbitrária.
- Planejamento em linguagem natural não recebe autoridade SQL irrestrita.
- Retrieval output é evidência, não verdade determinística.
- Texto recuperado continua não confiável como instrução após validação de proveniência.
- Hybrid routing e completude obrigatória permanecem determinísticos.
- Citation IDs vêm somente de evidência admitida.
- Agent action proposal não é capability authorization.
- Handoff proposal não é handoff admission.
- Handoff admission não é capability authorization.
- Authorized action não é capability invocation.
- Capability invocation não é execution result.
- MCP tool name não é capability authorization.
- MCP exposure não é autoridade para argumentos executáveis.
- MCP admission não é capability execution.
- MCP capability execution não é autoridade para business-result transport.
- MCP result admission não é autoridade para protocol result projection.
- MCP result projection não é public runtime exposure.
- Sucesso de transporte MCP não é verdade de negócio/evidência.
- Raw output de modelo/provider/downstream não vira autoridade canônica apenas porque foi transportado por um protocolo.
- Seleção de provider/model e política de retry/fallback permanecem controladas por código.
- Runtime exposure não é inferido de repository risk.
- Least privilege, observabilidade, diagnóstico de falhas e cost accounting são requisitos arquiteturais.

## O que a Phase 13 não prova

```text
generic business-result serialization
knowledge-guidance business-result transport
hybrid-security-answer business-result transport
public-repository-analysis business-result transport
persistent invocation/result registry
stdio subprocess deployment interoperability
Streamable HTTP production interoperability
public MCP endpoint
MCP transport authentication ou authorization
network reliability ou production SLOs
comportamento do Amazon Bedrock AgentCore
interoperabilidade A2A
runtime exposure / evidência Amazon Inspector
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
reasoning profile:       us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:               não
tools no reasoning:      nenhum
```

## Documentação

- [Current State](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [Architecture — English](docs/architecture.md)
- [Arquitetura — Português](docs/architecture.pt-br.md)
- [Índice de ADRs](docs/adr/README.md)
- [Índice de documentação](docs/README.md)
- [Closeout da Phase 11](labs/phase-11-gate-11-6-closeout.md)
- [Closeout da Phase 12](labs/phase-12-gate-12-5-multi-agent-closeout.md)
- [Closeout MCP da Phase 13](labs/phase-13-gate-13-5-mcp-closeout.md)
- [ADR 0051 — Phase 13 MCP Closeout](docs/adr/0051-phase13-mcp-closeout.md)

## Próxima — Phase 14: Amazon Bedrock AgentCore

A Phase 14 começa avaliando o Amazon Bedrock AgentCore contra uma necessidade concreta de runtime/workload do OpsLens. A adoção de managed runtime não é automática e não transforma retroativamente a prova MCP offline da Phase 13 em runtime público.

A primeira gate da Phase 14 deve preservar a referência de reasoning da Phase 11, a decisão medida de topologia da Phase 12 e os boundaries de admissão/execução/result projection MCP da Phase 13. Identidade, IAM, observabilidade, falhas, retry policy, lifecycle e custo precisam ser definidos antes de provisionar recursos de runtime.

A PR #89 de Governed LLM Gateway continua como trabalho cross-project deferred e precisa ser reavaliada separadamente contra a arquitetura vigente do OpsLens antes de qualquer merge.

---

OpsLens é construído intencionalmente primeiro como sistema de evidência e só adota complexidade agentic/de interoperabilidade quando a evidência medida justifica esse aumento de complexidade.
