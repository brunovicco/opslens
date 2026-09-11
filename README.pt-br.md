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

A **Phase 19 — Bounded Public Runtime & Productization** está em andamento. A Gate 19.1 está completa pelo PR #292. A Gate 19.2 está completa pelo protected PR #347 em `71eda2650889d3047259d37be226862ed2a09092`. A Gate 19.3 agora congela a menor topologia async concreta como autoridade de design apenas, sem autorização de deployment.

```text
19.1  Public Runtime Hypothesis & Launch Contract       COMPLETE
      workload: public-analysis-workload:v1
      decisão histórica: DEFERRED_PENDING_MEASUREMENT
      hipótese principal naquele momento: ASYNC_SUBMIT_STATUS_RESULT
19.2  Representative Workload Measurement              COMPLETE
      end-to-end medido: 17.748 ms
      estágios Bedrock medidos: 13.098 ms / 73,80% do E2E
      padrão de interação selecionado: ASYNC_SUBMIT_STATUS_RESULT
      protected merge: PR #347 / 71eda2650889d3047259d37be226862ed2a09092
19.3  Concrete Async Topology Contract                  IN PROGRESS
      issue: #348
      draft PR: #349
      topologia de design selecionada: HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB
      deployment autorizado: NÃO
```

A Gate 19.2 não afirma que a execução bem-sucedida estourou timeout. O baseline medido terminou abaixo de 30 segundos. A decisão async decorre de acoplamento à latência de providers, retry safety, backpressure e isolamento de falhas; os cenários derivados permanecem explicitamente separados da evidência medida.

A Gate 19.3 agora seleciona uma **topologia de design**, não um runtime implantado: API Gateway HTTP API + API Lambda + SQS + Lambda worker + DynamoDB, com DLQ e autoridade explícita para idempotência, estado e retries. Nenhum endpoint público, fila, tabela, função, role/policy IAM ou execução de provider é criado por esta gate.

Veja [Estado Atual](docs/current-state.md), [Roadmap](docs/roadmap.md), [Arquitetura](docs/architecture.pt-br.md), [Portfolio Evidence](docs/portfolio-evidence.md), [AIP-C01 Learning Map](docs/aip-c01-learning-map.md), o [closeout da Gate 19.2](labs/phase-19-gate-19-2-closeout.md), o [contrato de topologia da Gate 19.3](labs/phase-19-gate-19-3-async-topology-contract.md) e o [índice de ADRs](docs/adr/README.md).

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

O código atual de public analysis continua sendo uma **fronteira de aplicação**, não um serviço HTTP implantado:

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

A Gate 19.2 acrescentou uma execução representativa não pública completa, com admissão determinística, accounting de providers, evidência persistida e revisão offline. A execução reutilizou autoridade determinística de repositório/risco, evidência de ameaça previamente admitida, transporte GitHub medido, Bedrock Knowledge Base retrieval limitado, síntese limitada, admissão exata do resultado e persistência atômica da evidência. CI e ChatGPT não executaram o caminho live dos providers.

A Gate 19.3 congela a seguinte forma futura de interação pública sem implantá-la:

```text
POST /v1/analyses
  -> API Gateway HTTP API
  -> API Lambda determinística
  -> estado de job/idempotência no DynamoDB
  -> fila SQS
  -> Lambda worker
  -> resultado admitido de volta ao DynamoDB

GET /v1/analyses/{job_id}
GET /v1/analyses/{job_id}/result
```

A topologia de design selecionada é `HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB`. Ela permanece **evidência de design sem autoridade de deployment** até uma gate futura produzir Terraform exato, IAM least-privilege, testes de lifecycle/idempotência e autorização explícita de deployment.

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
| Phase 19 Gate 19.2 workload representativo | 17.748 ms end-to-end; 4 requests GitHub; 1 Bedrock Retrieve com 4.148 ms client elapsed; 1 chamada de modelo com 8.901 ms client elapsed / 7.772 ms provider latency; 5.936 tokens de entrada + 408 de saída; resultado admitido de 5.285 bytes |

A cadeia machine-readable da Phase 18 começa em `labs/evidence/phase-18-gate-18-1-evidence-inventory-v1.json` e termina em `labs/evidence/phase-18-closeout-v1.json`. Artefatos históricos permanecem evidência imutável mesmo quando a documentação corrente avança.

A Gate 19.2 persistiu o artefato live canônico em `labs/evidence/phase-19-gate-19-2-live-measurement-v1.json`, com hash independente `04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114`, além do closeout machine-readable em `labs/evidence/phase-19-gate-19-2-closeout-v1.json`.

A Gate 19.3 adiciona o contrato design-only em `labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json`; ele não contém evidência medida de deployment e registra explicitamente zero mutações runtime/AWS/IAM.

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

São **limites configurados, não utilização medida**. A Gate 19.2 fornece evidência de medição do workload completo, mas não converte limites configurados em utilização observada nem trata valores `UNMEASURED` como zero. Em particular, as métricas request-time do Athena permanecem `NOT_APPLICABLE` no caminho direto retido de structured evidence e `throttle_count` permanece `UNMEASURED`, mesmo com contador numérico igual a zero.

A Gate 19.3 não introduz afirmação de produção sobre concurrency, queue depth, retention, timeout ou custo mensal. Qualquer configuração runtime futura é `CONFIGURED_LIMIT` até ser medida separadamente.

## Fronteiras retidas

O reasoning direto via Bedrock da Phase 11 permanece como referência/default. A Phase 12 preserva specialization/handoff determinísticos, mas rejeita o default com dois modelos porque adicionou overhead sem ganho de qualidade. MCP e A2A permanecem camadas limitadas de interoperabilidade, não runtimes públicos. AgentCore fica como lab opcional, sem runtime/IAM de experimento permanente. Inspector permanece uma autoridade independente e read-only de runtime evidence; o resultado com zero registros não redefine repository risk.

Security Hardening retém Actions em SHA completo, invariantes de segurança no `main` protegido, separação de identidades privilegiadas, Dependency Review, CodeQL, oito casos adversariais em sete classes de ameaça, telemetry content-minimized em 12 handlers Lambda com Powertools e um pause Terraform-owned para exatamente três schedules recorrentes de ingestão.

## O que não é afirmado

OpsLens não afirma atualmente um runtime HTTP público de produção implantado, MCP/A2A públicos, AgentCore como runtime default de produção, SLOs de produção derivados de labs, TCO/run rate de produção, zero runtime exposure por causa do Inspector ter retornado zero registros, limites configurados como utilização medida, um global platform kill switch ou um score/probabilidade de aprovação na certificação.

A Phase 19 agora possui uma decisão baseada em evidência para o padrão de interação async e uma seleção de topologia concreta **apenas em nível de design**. Ela **não** afirma que API Gateway, Lambda, SQS, DynamoDB, DLQ, roles IAM ou qualquer outro recurso da Gate 19.3 tenha sido criado, configurado, habilitado ou exposto publicamente.

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

Comece por [docs/README.md](docs/README.md). Para portfólio e arquitetura, os principais pontos de entrada são [Arquitetura](docs/architecture.pt-br.md), [Portfolio Evidence](docs/portfolio-evidence.md), [Estado Atual](docs/current-state.md), [Roadmap](docs/roadmap.md), o [closeout da Phase 18](labs/phase-18-closeout.md), o [launch contract da Gate 19.1](labs/phase-19-gate-19-1-public-runtime-hypothesis.md), o [closeout da Gate 19.2](labs/phase-19-gate-19-2-closeout.md), o [contrato de topologia da Gate 19.3](labs/phase-19-gate-19-3-async-topology-contract.md) e o [índice de ADRs](docs/adr/README.md).

---

PR #89 / `feat/governed-gateway-semantic-planner` permanece como trabalho deferred separado do Governed LLM Gateway e não é dependência da Phase 19, salvo reavaliação explícita futura.
