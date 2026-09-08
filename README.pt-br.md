<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Software Supply Chain e Threat Intelligence Verificáveis na AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Public Analysis · Operational Evidence · Bounded Agent Reasoning · Autoridade Determinística**

</div>

OpsLens é uma plataforma open source de inteligência para software supply chain construída na AWS.

Ela foi projetada para responder:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência exata prova isso, quais findings devo priorizar e qual orientação verificável pode me ajudar a agir?

O projeto mantém deliberadamente separados verdade determinística, admissão de evidência, raciocínio de modelos, autorização, admissão de handoff e execução.

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
| Phase 11 | Single-Agent Baseline | ✅ Concluída |
| Phase 12 | Multi-Agent Architecture | 🚧 Em andamento — Gates 12.1–12.2 concluídas |

Veja [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Arquitetura](docs/architecture.pt-br.md), o [closeout da Phase 11](labs/phase-11-gate-11-6-closeout.md), o [lab da Gate 12.1](labs/phase-12-gate-12-1-bounded-specialization-handoff.md) e o [lab da Gate 12.2](labs/phase-12-gate-12-2-comparative-multi-agent-evaluation.md).

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

Fatos estruturados de vulnerabilidade/risco e evidência semântica de remediação permanecem classes separadas de autoridade.

Runtime exposure continua `UNSUPPORTED` até existir uma autoridade independente.

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

O baseline real de qualidade do modelo na Gate 11.4 termina intencionalmente antes da execução da capability. A execução tipada das capabilities permanece um boundary determinístico separado.

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

Limites congelados:

```text
máximo de handoffs por source task:      1
máximo de capabilities no especialista:  2
model calls reais na Gate 12.1:           0
capability executions na Gate 12.1:       0
```

A redução `4 -> <=2` é narrowing da superfície de raciocínio, não uma alegação de redução de privilégio em runtime. Os modelos continuam sem autoridade de execução.

A proposta de handoff não pode carregar mensagem/contexto arbitrário, seleção de capability, args/kwargs, SQL, URLs, comandos shell, credenciais, seleção de provider/model, política de retry/fallback ou execution result.

### 9. Autoridade determinística da comparação multi-agent

A Phase 12 Gate 12.2 congela:

```text
multi-agent-comparison:v1
```

O contrato de comparação foi congelado antes de existir uma segunda invocação real de modelo:

```text
fixture sintético de comparação congelado
 -> SingleAgentTask admitida
 -> MultiAgentHandoffProposal sintética e não confiável
 -> admissão determinística da Gate 12.1
 -> HANDOFF | ABSTAINED | REJECTED
 -> scoring determinístico e decomposto
 -> report content-addressed
 -> medições de runtime permanecem null / não medidas
 -> STOP
```

Binding exato com a referência da Phase 11:

```text
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
```

Evidência congelada da Gate 12.2:

```text
dataset_sha256: 1ad7f6274edea7d515f5827859d8a39bdde8edecc9a2ed58dc09df16b09dd491
report_sha256:  0586822800f028d0bb5c7cdb937db4af2f685abde3e09c76afd979d4e1abc222
total / passed:                        6 / 6
handoff / abstention cases:             4 / 2
source capability slots for handoffs: 16
specialist capability slots:            8
capability slots removed:               8
offline capability executions:          0
```

O resultado `6/6` é conformidade sintética do evaluator/contrato, não qualidade do triage model, qualidade do specialist model ou um baseline multi-agent real.

Como a Gate 12.2 não invoca modelo, model invocation count, tokens, provider/client latency, SDK retries e inference cost permanecem explicitamente `null`, em vez de zeros inventados.

## Baseline real Bedrock da Phase 11

Provider de raciocínio fixo:

```text
Amazon Bedrock Converse
region:          us-east-1
model/profile:   us.anthropic.claude-haiku-4-5-20251001-v1:0
temperature:     0.0
maxTokens:       96
tools:           disabled
```

Evidência preservada:

```text
labs/evidence/phase-11-gate-11-4-first-real-baseline-v1.json
corpus_sha256: 3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc
report_sha256: 724a4c2918e5628949445d67493e893d7700cffd86fb3c4e74cebb105a357145
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

A primeira execução autenticada revelou uma restrição real do provider: structured outputs do Bedrock rejeitaram JSON Schema `oneOf`. O adapter foi ajustado para um schema fechado e plano, enquanto a consistência ACT/ABSTAIN entre campos continuou sob autoridade determinística da aplicação.

O resultado 6/6 é resultado de um acceptance corpus congelado, não uma afirmação de correção universal do modelo.

## Decisão medida de otimização

A Gate 11.5 manteve intencionalmente a implementação sem mudanças:

```text
optimization decision: NO-CHANGE / NO-EXPERIMENT
```

Prompt compression, troca de modelo, prompt caching, expansão de retry/fallback e expansão de capabilities não foram justificadas por um target material medido.

## Evidência de merge da Phase 12

Gate 12.1:

```text
PR:                     #166
final head:             567cdbde81f058d9545328ca78b718c24d79c9fb
Multi-Agent CI:         34172909750 / run #3 / PASS
multi-agent pytest:     10 passed in 0.39s
Single-Agent CI:        34172909748 / run #48 / PASS
single-agent pytest:    56 passed in 0.44s
merge SHA:              eceed76a6cfc5d7e28e88dfdc503b4863b526ba0
```

Gate 12.2:

```text
PR:                     #169
final head:             953467df99ddeaedd6e19471bd2dce6c5bb8de7c
PR merge test commit:   bab183ee1dbcca0eb6a0bb76b5130180f9f2f7c2
Multi-Agent CI:         34174680219 / run #7 / PASS
multi-agent pytest:     18 passed in 0.27s
merge SHA:              865ba70c813711cb88da9ac7308c8966ff983fd0
```

As Gates 12.1–12.2 não adicionam recurso AWS, permissão IAM, capability execution, AgentCore, MCP, A2A, runtime público ou autoridade de runtime exposure. A Gate 12.2 também não adiciona model call real.

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
- Conformidade de fixture sintético não é qualidade de modelo.
- Raw model output não é evidência canônica.
- Seleção de provider/model e política de retry/fallback permanecem controladas por código.
- Runtime exposure não é inferido de repository risk.
- Least privilege, observabilidade, diagnóstico de falhas e cost accounting são requisitos arquiteturais.

## O que a Phase 12 Gate 12.2 não prova

```text
qualidade de routing do triage model
qualidade de reasoning do specialist model
melhoria de qualidade multi-agent
model invocation count real multi-agent
tokens / latência / retries / custo de inferência reais multi-agent
reliability de runtime multi-agent
redução de privilégio em runtime
capability execution através do fluxo multi-agent
runtime público/deployed de agentes
comportamento de runtime do AgentCore
interoperabilidade MCP
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
- [Closeout da Phase 8](labs/phase-8-gate-8-6-closeout.md)
- [Closeout da Phase 9](labs/phase-9-gate-9-4-closeout.md)
- [Closeout da Phase 10](labs/phase-10-gate-10-4-closeout.md)
- [Baseline real da Gate 11.4](labs/phase-11-gate-11-4-bounded-model-reasoning-baseline.md)
- [Decisão de otimização da Gate 11.5](labs/phase-11-gate-11-5-measured-optimization-decision.md)
- [Closeout da Phase 11](labs/phase-11-gate-11-6-closeout.md)
- [Handoff limitado da Gate 12.1](labs/phase-12-gate-12-1-bounded-specialization-handoff.md)
- [Contrato comparativo da Gate 12.2](labs/phase-12-gate-12-2-comparative-multi-agent-evaluation.md)

## Próxima — Phase 12 Gate 12.3: First Bounded Real Two-Model Comparison

O contrato de comparação agora está congelado. O próximo experimento autorizado pode introduzir no máximo duas chamadas limitadas de reasoning por task:

```text
SingleAgentTask
 -> triage model limitado propõe uma especialização fechada
 -> parser determinístico + handoff admission
 -> SpecialistAgentTask com scope reduzido
 -> specialist reasoning limitado propõe uma capability já permitida
 -> capability authorization determinística
 -> STOP antes da capability execution
```

Os limites iniciais são duas model invocations, um handoff, zero adaptive application retries, zero fallbacks e zero capability executions.

Comportamento real do modelo, tokens, provider/client latency, SDK retries e inference cost devem vir somente de evidência observada do provider. As primeiras observações reais precisam ser preservadas antes de qualquer tuning de prompt/model/topologia. A topologia com dois modelos só será mantida se o valor medido da especialização justificar a chamada adicional, latência, tokens, custo, failure surface e complexidade arquitetural em relação à referência congelada da Phase 11.

AgentCore, MCP e A2A permanecem decisões arquiteturais futuras e separadas.

A PR #89 de Governed LLM Gateway continua como trabalho cross-project deferred e precisa ser reavaliada separadamente contra a arquitetura vigente do OpsLens antes de qualquer merge.

---

O OpsLens é construído intencionalmente primeiro como sistema de evidência e só adota complexidade agentic quando a evidência medida justifica esse aumento de complexidade.
