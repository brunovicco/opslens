<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Supply Chain Verificável e Arquitetura GenAI na AWS

**Threat Intelligence · Repository Intelligence · Risco Determinístico · Bedrock RAG · Hybrid Retrieval · Agentic AI · MCP · AgentCore · A2A · Inspector · Evaluation · Security Hardening · Cost Engineering**

</div>

OpsLens é um laboratório open source de arquitetura AWS e uma plataforma de inteligência de supply chain de software construída em torno de um princípio:

> **Agents reason. Code verifies evidence.**

O projeto responde a uma pergunta prática: dado o software realmente usado por um repositório, quais vulnerabilidades o afetam, qual evidência exata comprova isso, o que deve ser priorizado e qual orientação verificada pode ajudar na ação?

A plataforma separa deliberadamente raciocínio probabilístico da autoridade determinística responsável por package/version matching, correlação de vulnerabilidades, política de risco, admissão de consultas semânticas, compilação SQL, admissão de evidências, autorização de ferramentas, admissão de resultados e limites de custo/recursos.

> **Repository Risk != Runtime Exposure.**

## Estado atual

**Phases 0–18 estão completas.** A Phase 18 foi protegida por squash merge no PR #290 em `feca774535b7d83f57c26f4e9fe7da71ce268f0f`.

A **Phase 19 — Bounded Public Runtime & Productization** está em andamento. A Gate 19.1 está completa e foi protegida por squash merge no PR #292 em `ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1`. A Gate 19.2 chegou agora à fronteira explícita de medição live executada por humano após o merge do CLI human-run no PR #339.

```text
19.1  Public Runtime Hypothesis & Launch Contract       COMPLETE
      workload: public-analysis-workload:v1
      runtime decision: DEFERRED_PENDING_MEASUREMENT
      leading hypothesis: ASYNC_SUBMIT_STATUS_RESULT
      AWS/IAM/public endpoint mutations: 0
19.2  Representative Workload Measurement              IN PROGRESS
      latest completed issue: #338
      merged PR: #339
      boundary: HUMAN LIVE MEASUREMENT
```

A forma assíncrona é apenas uma hipótese. O OpsLens não selecionará API Gateway + Lambda, Lambda Function URLs, SQS, ECS/Fargate, AgentCore ou outro runtime público até existir evidência admitida da medição real do workload representativo.

Veja [Estado Atual](docs/current-state.md), [Roadmap](docs/roadmap.md), [Arquitetura](docs/architecture.pt-br.md), [Portfolio Evidence](docs/portfolio-evidence.md), [AIP-C01 Learning Map](docs/aip-c01-learning-map.md), o [runbook da medição live da Gate 19.2](labs/phase-19-gate-19-2-human-live-measurement-runbook.md) e o [índice de ADRs](docs/adr/README.md).

## Arquitetura em resumo

```text
NVD / CISA KEV / FIRST EPSS / GitHub Advisories
        |
        v
evidência de ameaça preservando a fonte
        |
repositório público -> snapshot imutável -> uv.lock inerte
        |
        v
correlação determinística PyPI + PEP 440
        |
NVD/CVSS + KEV + EPSS
        |
RepositoryAnalysisResult -> Risk Policy v1 determinística

pergunta factual em linguagem natural
        |
        v
proposta Bedrock limitada -> admissão SemanticQuery determinística
        |
        v
compilador SQL tipado -> Athena read-only limitada

fontes oficiais de conhecimento
        |
        v
corpus canônico -> Bedrock Knowledge Base -> S3 Vectors
        |
        v
Retrieve limitado -> evidência validada -> síntese + citações

Evidência estruturada + semântica
        |
        v
roteamento/composição determinísticos -> raciocínio de agente limitado
        |
        v
autorização tipada de capability -> execução/admissão de resultado
```

O LLM não recebe autoridade irrestrita de text-to-SQL. Conteúdo recuperado é evidência, não autoridade de instrução. Sucesso de protocolo/ferramenta não equivale à verdade de negócio.

## Fronteira pública do produto

O código atual de public analysis é uma **fronteira de aplicação**, não um serviço HTTP implantado:

```text
JSON não confiável
 -> admissão estrita da requisição
 -> coordenadas GitHub validadas
 -> evidência imutável do repositório
 -> planejamento semântico limitado e metadata-only
 -> admissão determinística da rota híbrida
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

A Gate 19.2 contém agora a composição representativa não pública completa e um driver fail-closed, exclusivamente human-run, para uma execução medida. O driver reutiliza autoridade determinística de repositório/risco, evidência de ameaça previamente admitida, transporte GitHub medido, Bedrock Knowledge Base retrieval limitado, síntese limitada, admissão exata do resultado e persistência atômica da evidência. CI e ChatGPT não executam o caminho live dos providers.

A decisão de runtime permanece `DEFERRED_PENDING_MEASUREMENT` até que o operador humano produza e revise o artefato live admitido. Nenhum endpoint público, novo recurso AWS, mutação IAM ou execução de código do repositório de terceiros é autorizada por essa fronteira.

## Evidência medida retida

O portfólio continua deliberadamente baseado em evidência. Exemplos:

| Experimento | Evidência |
| --- | --- |
| Phase 7 grounding review | 11/13 claims suportados; razão derivada `0.8461538461538461` |
| Phase 11 reasoning de referência | 6/6 casos; 3.395 tokens; mediana de provider latency 809,5 ms; custo derivado USD `0.0041921` |
| Phase 12 comparação com dois modelos | 6/6 casos, porém 5.982 tokens, mediana derivada 1.694 ms e custo derivado USD `0.0074338`; não retida como default |
| Phase 14 AgentCore | replay 6/6; total derivado USD `0.006572445136128483`; apenas lab opcional |
| Phase 16 Inspector | leitura limitada bem-sucedida com zero registros; **não** interpretada como zero runtime exposure |
| Phase 17 recovery | ciclo pause/resume dos três schedulers com convergência Terraform final |

A cadeia machine-readable da Phase 18 começa em `labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json` e termina em `labs/evidence/phase-18-closeout-v1.json`. O closeout histórico preserva intencionalmente o estado pré-merge; a documentação corrente reflete o protected merge concluído.

## Limites de custo e recursos

O OpsLens separa custo observado/derivado de limites configurados e proíbe agregação insegura entre experimentos não comparáveis.

```text
semantic planner max output          256 tokens
single-agent max output               96 tokens
multi-agent triage max output         64 tokens
knowledge synthesis max output      2048 tokens
Athena scan cutoff/query         10485760 bytes
Scheduler maximum event age         3600 seconds
Scheduler maximum retry attempts        2
```

São **limites configurados, não utilização medida**. A Gate 19.2 existe especificamente para medir latência do request público completo, chamadas aos providers, utilização de tokens/scan, retries/throttles e tamanho do resultado antes da escolha do runtime.

## Fronteiras retidas

O reasoning direto via Bedrock da Phase 11 permanece como referência/default. A Phase 12 preserva specialization/handoff determinísticos, mas rejeita o default com dois modelos porque adicionou overhead sem ganho de qualidade. MCP e A2A permanecem camadas limitadas de interoperabilidade, não runtimes públicos. AgentCore fica como lab opcional, sem runtime/IAM de experimento permanente. Inspector permanece uma autoridade independente e read-only de runtime evidence; o resultado com zero registros não redefine repository risk.

Security Hardening retém Actions em SHA completo, invariantes de segurança no `main` protegido, separação de identidades privilegiadas, Dependency Review, CodeQL, oito casos adversariais em sete classes de ameaça, telemetry content-minimized em 12 handlers Lambda com Powertools e um pause Terraform-owned para exatamente três schedules recorrentes de ingestão.

## O que não é afirmado

OpsLens não afirma atualmente runtime HTTP público de produção, MCP/A2A públicos, AgentCore como runtime default de produção, SLOs de produção derivados de labs, TCO/run rate de produção, zero runtime exposure por causa do Inspector ter retornado zero registros, limites configurados como utilização medida, um global platform kill switch ou um score/probabilidade de aprovação na certificação.

A Phase 19 também não afirma que async já foi selecionado. `ASYNC_SUBMIT_STATUS_RESULT` permanece apenas como hipótese principal, pendente da medição live admitida do workload representativo.

## Laboratório AIP-C01

OpsLens também é usado como preparação hands-on para **AWS Certified Generative AI Developer - Professional (AIP-C01)**. A Phase 19 acrescenta raciocínio arquitetural prático sobre integração enterprise, APIs síncronas versus assíncronas, responsabilidades IAM, abuse controls, monitoring, performance, cost e troubleshooting sem transformar a amplitude do exame em requisito do produto.

```text
AIP-C01 topic != product requirement
```

## Baseline AWS

```text
environment:          dev
region:               us-east-1
vector store:         Amazon S3 Vectors
embedding model:      amazon.titan-embed-text-v2:0
embedding dimensions: 1024
chunking:             NONE
canonical chunks:     9
synthesis API:        Amazon Bedrock Converse
reasoning profile:    us.anthropic.claude-haiku-4-5-20251001-v1:0
public HTTP runtime:  NONE
```

## Documentação

Comece por [docs/README.md](docs/README.md). Para portfólio e arquitetura, os principais pontos de entrada são [Arquitetura](docs/architecture.pt-br.md), [Portfolio Evidence](docs/portfolio-evidence.md), [Estado Atual](docs/current-state.md), [Roadmap](docs/roadmap.md), o [closeout da Phase 18](labs/phase-18-closeout.md), o [launch contract da Gate 19.1](labs/phase-19-gate-19-1-public-runtime-hypothesis.md), o [runbook da medição live da Gate 19.2](labs/phase-19-gate-19-2-human-live-measurement-runbook.md) e o [índice de ADRs](docs/adr/README.md).

---

PR #89 / `feat/governed-gateway-semantic-planner` permanece como trabalho deferred separado do Governed LLM Gateway e não é dependência da Phase 19, salvo reavaliação explícita futura.
