<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Software Supply Chain e Threat Intelligence Verificáveis na AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Public Analysis · Operational Evidence · Bounded Agent Reasoning · MCP Interoperability · Evidência de AgentCore Runtime · Autoridade Determinística**

</div>

OpsLens é uma plataforma open source de inteligência para software supply chain construída na AWS.

Ela foi projetada para responder:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência exata prova isso, quais findings devo priorizar e qual orientação verificável pode me ajudar a agir?

O projeto mantém deliberadamente separados verdade determinística, admissão de evidência, raciocínio de modelos, autorização, admissão de handoff, interoperabilidade, execução, divulgação de resultados, comportamento de hosting/runtime e runtime exposure.

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
| Phase 14 | Amazon Bedrock AgentCore | ✅ Concluída — lab opcional retido; IAM de experimento removido |
| Phase 15 | A2A | ▶️ Próxima / planejada |
| Phase 16 | Runtime Exposure with Amazon Inspector | ⏳ Planejada |
| Phase 17 | Security Hardening | ⏳ Planejada |
| Phase 18 | Evaluation, Cost & Portfolio Readiness | ⏳ Planejada |

Veja [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Arquitetura](docs/architecture.pt-br.md), o [closeout MCP da Phase 13](labs/phase-13-gate-13-5-mcp-closeout.md) e o [closeout da Gate 14.4](labs/phase-14-gate-14-4-agentcore-iam-cleanup.md).

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

O baseline real termina antes de capability execution. A execução tipada permanece um boundary determinístico separado.

Referência medida:

```text
quality:                    6/6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
derived six-case cost:      USD 0.0041921
```

### 8. Autoridade limitada de handoff multi-agent

A Phase 12 retém especialização e admissão de handoff determinísticas:

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

A topologia medida com dois modelos não foi retida como default porque não trouxe ganho de qualidade e aumentou invocações, tokens, latência e custo.

Decisão retida:

```text
Phase 11 single-agent reasoning reference:      RETAIN
Gate 12.1 deterministic specialization/handoff: RETAIN
Gate 12.2 deterministic comparison discipline: RETAIN
Gate 12.3 two-model topology as default:        DO NOT RETAIN
Gate 12.3 implementation/evidence:              PRESERVE HISTORICALLY
```

### 9. Interoperabilidade MCP limitada e divulgação de resultados

A Phase 13 congela:

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

Caminho retido:

```text
autoridade tipada existente da Phase 11
 -> identidade MCP fechada
 -> adapter reference-only do MCP SDK oficial
 -> recusa exata de raw argument keys
 -> resolução + admissão determinísticas
 -> exatamente uma tentativa do executor tipado existente
 -> admissão tipada de resultado existente
 -> projeção explícita apenas para structured_security_query
 -> linhas CVE + EPSS limitadas
 -> STOP antes de runtime público/de rede
```

MCP não pode criar `SemanticQuery`, SQL, URLs, shell commands, credenciais, seleção de provider/model, política de retry/fallback nem argumentos executáveis arbitrários. Hosting MCP público/de rede continua como non-claim.

### 10. Experimento medido com AgentCore Runtime

A Gate 14.1 autorizou apenas um experimento limitado de Runtime. A Gate 14.2 hospedou o boundary de raciocínio retido da Phase 11 sem adicionar autoridade de capability execution:

```text
AgentCore Runtime HTTP / IAM SigV4
 -> admissão exata do request
 -> autoridade SingleAgentTask retida
 -> uma invocação fixa de raciocínio Bedrock
 -> parser determinístico
 -> authorize_agent_action(...) existente
 -> AgentCoreReasoningProjection apenas com metadata
 -> STOP antes de capability execution
```

Run #11 terminal bem-sucedido:

```text
source main:                e5072ec68b421677359cebb1eb449578ef7d5b49
workflow run:               34378942784 / SUCCESS
runtime:                    opslens_dev_bounded_runtime-Cl8aNBDGzh
protocol:                   HTTP
network:                    PUBLIC — exceção apenas para experimento dev
artifact SHA256:            a846034ad646c4f6383ac08e47d9ed065b4a9f3349c14104db49a2d510b3ec88
replay:                     6 / 6 PASS
input/output/total tokens:  3291 / 104 / 3395
SDK retries:                0
capability executions:      0
transport elapsed sum:      19981 ms
deployment-role invocation: AccessDeniedException / HTTP 403
cleanup verifier:           RESOURCE_NOT_FOUND
```

Custo observado:

```text
AgentCore Runtime:  USD 0.002380345136128484
Bedrock inference:  USD 0.004192100000000000
TOTAL:              USD 0.006572445136128483
```

As tentativas #1–#10 permanecem preservadas como evidência medida das dependências IAM/lifecycle. O run bem-sucedido não reescreve essas falhas.

A Gate 14.2 **não** aprovou AgentCore nem `PUBLIC` para produção, não estabeleceu production SLO, não criou runtime-exposure truth e não autorizou capability execution.

## Retenção e closeout da Phase 14

A Gate 14.3 comparou o resultado medido do AgentCore com a referência retida da Phase 11 usando somente evidência comparável.

Decisão final:

```text
overall decision:                         RETAIN WITH CHANGES
Phase 11 direct Bedrock reasoning:        RETAIN / DEFAULT
AgentCore implementation/evidence:        RETAIN AS OPTIONAL LAB TARGET
AgentCore managed Runtime as default:      DO NOT RETAIN
PUBLIC network mode:                      DO NOT RETAIN
standing AgentCore Runtime resources:     DO NOT RETAIN
standing experiment-specific GitHub IAM: REMOVE
```

A qualidade, quantidade de chamadas e tokens do corpus de seis casos foram idênticas entre Phase 11 e replay hospedado no AgentCore. O custo de inferência Bedrock permaneceu USD 0.0041921; o AgentCore adicionou USD 0.002380345136128484 de Runtime compute medido, ou 56.78168784448091% em relação ao componente de inferência nesse experimento.

Os boundaries brutos de latência são preservados, mas não são convertidos em uma comparação percentual normalizada porque não estão controlados o suficiente para sustentar essa afirmação.

### Gate 14.4 — limpeza do IAM de experimento

A limpeza de desired state foi mergeada de forma protegida na PR #225:

```text
merge SHA:                 9913c3cbf5f2239d6445042a139a9cca890590c8
exact-head AgentCore CI:   34396085154 / run #63 / PASS
exact-head Terraform CI:   34396085123 / run #267 / PASS
```

Resultado do bootstrap humano:

```text
plano revisado:         0 add / 0 change / 4 destroy
apply:                  0 add / 0 change / 4 destroy
convergência pós-apply: NO CHANGES
```

Verificação IAM independente:

```text
OpsLensAgentCoreReplayRole:                 AUSENTE / NoSuchEntity
OpsLensAgentCoreDeployDevAccess:            AUSENTE / NoSuchEntity
attachment AgentCore no deploy role:        []
OpsLensGitHubDeployRole:                    PRESENTE
AWSServiceRoleForBedrockAgentCoreRuntimeIdentity:
                                            PRESENTE / retido intencionalmente
```

O Runtime Identity service-linked role continua protegido porque a segurança de sua remoção no nível da conta não foi provada. Ele é service-scoped da AWS e não equivale a autoridade ambiente de experimento do GitHub.

O workflow/código histórico do AgentCore permanece como material de laboratório reproduzível, mas está intencionalmente não operacional até que um futuro experimento faça novo re-bootstrap mínimo e orientado por evidência. A exceção `PUBLIC` da Gate 14.2 não é herdada.

## Invariantes de segurança e autoridade

- Evidência bruta de terceiros é preservada antes da transformação.
- Versões exatas e hashes participam da identidade da evidência.
- Normalização, ranges/versions, aplicabilidade, KEV/EPSS/CVSS e Risk Policy permanecem determinísticos.
- Código de terceiros nunca é executado.
- Public request admission não concede fetch authority arbitrária.
- Planejamento em linguagem natural não recebe autoridade SQL irrestrita.
- Retrieval output é evidência, não verdade determinística.
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
- MCP result projection não é public runtime exposure.
- AgentCore hosting não é business authorization.
- Runtime authentication não é capability authorization.
- Runtime execution role não é model/tool authority.
- Runtime telemetry não é business truth.
- Runtime deployment não é runtime-exposure truth.
- Seleção de provider/model e política de retry/fallback permanecem controladas por código.
- Runtime exposure não é inferido de repository risk.
- Least privilege, observabilidade, diagnóstico de falhas e cost accounting são requisitos arquiteturais.

## O que a evidência agentic/runtime atual não prova

```text
generic business-result serialization
knowledge-guidance business-result transport
hybrid-security-answer business-result transport
public-repository-analysis business-result transport
persistent invocation/result registry
public MCP endpoint
production MCP network SLOs
AgentCore como runtime default/de produção do OpsLens
PUBLIC no AgentCore como decisão de rede para produção
production AgentCore SLOs ou security posture
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
AgentCore retained state: lab opcional disabled-by-default; sem IAM GitHub de experimento ativo
```

## Documentação e evidência

- [Current State](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [Architecture — English](docs/architecture.md)
- [Arquitetura — Português](docs/architecture.pt-br.md)
- [Índice de ADRs](docs/adr/README.md)
- [Índice de documentação](docs/README.md)
- [Closeout da Phase 11](labs/phase-11-gate-11-6-closeout.md)
- [Closeout da Phase 12](labs/phase-12-gate-12-5-multi-agent-closeout.md)
- [Closeout MCP da Phase 13](labs/phase-13-gate-13-5-mcp-closeout.md)
- [Experimento medido da Gate 14.2](labs/phase-14-gate-14-2-bounded-agentcore-runtime.md)
- [Decisão de retenção da Gate 14.3](labs/phase-14-gate-14-3-agentcore-retention-decision.md)
- [Limpeza de IAM da Gate 14.4](labs/phase-14-gate-14-4-agentcore-iam-cleanup.md)
- [ADR 0054 — AgentCore somente como lab opcional](docs/adr/0054-retain-agentcore-only-as-optional-lab-target.md)
- [ADR 0055 — remoção do IAM permanente do experimento AgentCore](docs/adr/0055-remove-standing-agentcore-experiment-iam.md)
- [Evidência pós-apply da Gate 14.4](labs/evidence/phase-14-gate-14-4-agentcore-iam-cleanup-postapply-v1.json)

## Próxima — Phase 15 A2A

A Phase 15 começa por capability fit, não por implementação automática.

A primeira pergunta arquitetural é:

> Qual boundary existente entre agentes/serviços tem um problema concreto de interoperabilidade que justifique A2A, e quais contratos de identidade, mensagem, proveniência, replay, falha, observabilidade, custo e autoridade precisam ser congelados antes de qualquer transporte de rede?

Restrições permanentes da Phase 15:

```text
A2A message != capability authorization
A2A peer identity != business authority
A2A transport success != business/evidence truth
A2A handoff proposal != handoff admission
A2A must not assume AgentCore hosting
A2A must not promote MCP into a public runtime as a side effect
```

A PR #89 de Governed LLM Gateway continua como trabalho cross-project deferred e precisa ser reavaliada separadamente contra a arquitetura vigente do OpsLens antes de qualquer merge.

---

OpsLens é construído intencionalmente primeiro como sistema de evidência e só adota complexidade agentic/de interoperabilidade quando a evidência medida justifica esse aumento de complexidade.
