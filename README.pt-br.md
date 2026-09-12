<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Supply Chain Verificável e Arquitetura GenAI na AWS

**Threat Intelligence · Repository Intelligence · Risco Determinístico · Bedrock RAG · Hybrid Retrieval · Agentic AI · MCP · AgentCore · A2A · Security · Evaluation · Cost Engineering**

</div>

OpsLens é um laboratório open source de arquitetura AWS e inteligência de supply chain de software construído em torno de um princípio:

> **Agents reason. Code verifies evidence.**

O projeto responde a uma pergunta prática:

> Dado o software realmente usado por um repositório, quais vulnerabilidades o afetam, qual evidência exata comprova isso, o que deve ser priorizado e qual orientação verificada pode ajudar na ação?

O OpsLens separa deliberadamente raciocínio probabilístico da autoridade determinística de identidade de pacotes, aplicabilidade de versões, correlação de vulnerabilidades, evidências KEV/EPSS/CVSS, política de risco, admissão de consultas semânticas, compilação SQL, admissão de evidências, autorização de ferramentas e limites de execução/recursos.

> **Repository Risk != Runtime Exposure.**

## Estado atual

**As Phases 0–18 estão completas. A Phase 19 é a fase final de fechamento da V1.**

Phases 0–18 estão completas. A fase historicamente selecionada após a Phase 18 permanece **Phase 19 — Bounded Public Runtime & Productization**; a Gate 19.9 apenas reduz o escopo necessário para o fechamento demonstrativo da V1, sem reescrever essa decisão.

Checkpoint protegido atual:

```text
main: e538fa3e96c29cf76dd3aa83a9967e090587b6fb
Gate 19.8: COMPLETE
protected merge: PR #375
CodeQL pós-merge: 34713360403 / run #393 / success
Gate 19.9: IN PROGRESS / issue #376
```

Marcadores históricos retidos das Gates 19.1/19.2:

```text
19.1  Public Runtime Hypothesis & Launch Contract       COMPLETE
decisão histórica: DEFERRED_PENDING_MEASUREMENT
public-analysis-workload:v1
19.2  Representative Workload Measurement              COMPLETE
ASYNC_SUBMIT_STATUS_RESULT
```

Esses marcadores preservam a decisão histórica; as Gates 19.2–19.8 posteriores encerraram a pendência de medição sem reescrever a evidência anterior.

O runtime assíncrono AWS retido já foi materializado e convergiu, mas permanece intencionalmente desabilitado e não público:

```text
runtime materializado: SIM
endpoint público habilitado: NÃO
submit habilitado: NÃO
worker habilitado: NÃO
event-source mapping habilitado: NÃO
execução pública provider-heavy: NÃO
```

```text
materialized != enabled
```

## Escopo da V1

A V1 do OpsLens é intencionalmente um **laboratório de demonstração e arquitetura**, não um SaaS de produção.

O objetivo para quem avalia o projeto é:

```text
clone
 -> setup
 -> um comando de demo offline determinístico
 -> resultado baseado em evidências
```

O fechamento da V1 prioriza reprodutibilidade, proveniência, clareza arquitetural, failure paths relevantes e apresentação de portfólio. Ele **não** exige operação pública em produção.

Veja [Escopo de Demonstração da V1](docs/v1-demonstration-scope.md) e [Checklist de Fechamento da V1](docs/v1-completion-checklist.md).

## Arquitetura em resumo

```text
NVD / CISA KEV / FIRST EPSS / GitHub Security Advisories
        |
        v
evidência de ameaça preservando a fonte
        |
repositório público -> snapshot imutável -> evidência inerte de dependências
        |
        v
aplicabilidade determinística pacote/versão
        |
        v
GHSA/NVD/CVSS + KEV + EPSS
        |
        v
RepositoryAnalysisResult -> Risk Policy determinística

pergunta factual estruturada
        |
        v
proposta Bedrock limitada -> admissão SemanticQuery determinística
        |
        v
compilador SQL tipado -> Athena read-only limitado

pergunta de conhecimento/remediação
        |
        v
Bedrock Knowledge Base -> evidência validada -> síntese limitada + citações

evidência estruturada + semântica admitida
        |
        v
autorização determinística -> raciocínio de agente limitado
        |
        v
resultado admitido
```

O modelo pode explicar, classificar, planejar, rotear ou sintetizar sobre evidências admitidas. Ele não possui autoridade sobre identidade de pacote, aplicabilidade de vulnerabilidade, proveniência, política de risco, SQL arbitrário ou autorização de execução.

## Fronteira de segurança para repositórios públicos

O OpsLens trata o conteúdo do repositório como dados não confiáveis.

```text
READ, NEVER EXECUTE third-party repository code.
```

O projeto não executa package managers, builds, testes, setup hooks, Dockerfiles, workflows ou scripts do repositório como parte da análise.

## Linhagem da Phase 19

```text
19.1  Public Runtime Hypothesis & Launch Contract              COMPLETE
19.2  Representative Workload Measurement                     COMPLETE
19.3  Concrete Async Topology Contract                         COMPLETE
19.4  Disabled Async Runtime Implementation                    COMPLETE
19.5  Immutable Async Deployment Artifacts                     COMPLETE
19.6  Exact Terraform Plan & Offline Admission                 COMPLETE
19.7  Controlled Disabled Runtime Materialization              COMPLETE
19.8  Request-time Threat Evidence Authority Contract          COMPLETE
19.9  V1 Demonstration Closeout Contract                       IN PROGRESS
19.10 Deterministic End-to-End Demo Runner                     PLANNED
19.11 Curated Demo Scenarios + Deterministic Evaluation        PLANNED
19.12 Minimal Local Visual Demo                                PLANNED
19.13 Portfolio / README / Architecture Polish                 PLANNED
19.14 V1 Closeout + Release Readiness                          PLANNED
```

### Topologia AWS assíncrona retida

```text
HTTP API
 -> API Lambda
 -> autoridade de job/idempotência no DynamoDB
 -> fila SQS standard
 -> Lambda worker
 -> status/resultado no DynamoDB
 -> SQS DLQ
```

Essa topologia permanece como evidência de arquitetura e deployment. A V1 não exige sua habilitação pública.

## Autoridade de threat evidence em request-time

A Gate 19.8 introduziu a fronteira provider-neutral:

```text
PublicRepositoryEvidenceExecution
 -> PublicThreatEvidenceScope
 -> PublicThreatEvidenceRequest
 -> PublicThreatEvidenceAuthority
 -> evidência exata GHSA/NVD/KEV/EPSS + proveniência
 -> correlação/enriquecimento determinísticos
```

Semânticas importantes:

```text
scope deriva apenas de evidência admitida do repositório
normalização incompleta de pacote -> fail closed
evidência fora do scope -> rejeitar
latest_complete = política de seleção, não proveniência
missing evidence != benign evidence
autoridade do modelo sobre aplicabilidade/source truth = nenhuma
```

Um adapter provider-backed genérico para request-time permanece como experimento Post-V1, pois o caminho canônico da V1 será offline-first.

## Evidência medida

O OpsLens separa evidência medida, derivada, configurada e não medida.

O workload representativo retido da Phase 19 mediu:

| Métrica | Evidência |
| --- | ---: |
| Duração end-to-end | 17.748 ms |
| Resultado serializado | 5.285 bytes |
| Requests físicos GitHub | 4 medidos |
| Chamadas Bedrock Retrieve | 1 medida |
| Bedrock Retrieve client elapsed | 4.148 ms |
| Chamadas de modelo Bedrock | 1 medida |
| Tokens de entrada | 5.936 |
| Tokens de saída | 408 |
| Bedrock model client elapsed | 8.901 ms |
| Bedrock provider latency | 7.772 ms |
| Retries | 0 medidos |
| Throttle count | UNMEASURED |

Esses são números de um experimento limitado, não SLO nem TCO de produção.

## O que o projeto demonstra

O OpsLens mantém evidências para:

- fundação AWS e IAM least privilege;
- NVD, GitHub Advisories, CISA KEV e FIRST EPSS;
- evidência imutável de repositórios públicos;
- correlação determinística PyPI/PEP 440;
- priorização determinística de risco;
- semantic query com proposta Bedrock limitada e compilação SQL determinística;
- Bedrock Knowledge Bases e S3 Vectors;
- hybrid retrieval e grounded synthesis;
- experimentos single-agent e multi-agent medidos;
- MCP e A2A com fronteiras limitadas;
- experimentação de capability fit com AgentCore;
- runtime exposure evidence com Amazon Inspector;
- observabilidade e telemetry com minimização de conteúdo;
- adversarial/security authority regression;
- avaliação e evidência de custo;
- artefatos imutáveis de deployment Lambda;
- admissão de plano Terraform exato;
- materialização controlada e convergência de runtime;
- contrato determinístico de autoridade de threat evidence em request-time.

## Trabalho restante da V1

O restante é intencionalmente pequeno e focado em demonstração:

```text
Gate 19.9   congelar contrato V1 e sincronizar estado atual
Gate 19.10  runner determinístico canônico de demonstração
Gate 19.11  três cenários curados + avaliação de regressão
Gate 19.12  demo visual local mínima
Gate 19.13  polish final de portfólio/arquitetura
Gate 19.14  fechar Phase 19 e preparar release v1.0.0
```

O target aproximado do comando canônico será:

```bash
uv sync --frozen
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
```

O contrato exato pertence à Gate 19.10 e pode mudar antes do merge.

## Não objetivos da V1

A primeira versão não exige:

```text
runtime de produção exposto na Internet
autenticação / OIDC / Cognito
multi-tenancy
quotas comerciais ou billing
domínio público customizado
WAF ou controles de abuso de produção
operação 24x7
SLO/SLA de produção
programa HA/DR
claim de TCO de produção
habilitação pública de worker/event-source
```

Veja [Backlog Post-V1 / Experimentos](docs/post-v1-backlog.md).

## Documentação

- [Estado Atual](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [Escopo de Demonstração V1](docs/v1-demonstration-scope.md)
- [Checklist de Fechamento V1](docs/v1-completion-checklist.md)
- [Área de Demo](docs/demo/README.md)
- [Arquitetura](docs/architecture.pt-br.md)
- [Portfolio Evidence](docs/portfolio-evidence.md)
- [AIP-C01 Learning Map](docs/aip-c01-learning-map.md)
- [Architecture Decision Records](docs/adr/README.md)

## Regras permanentes de engenharia

```text
Agents reason. Code verifies evidence.
Not every question is a RAG problem.
Structured facts use structured retrieval.
No unrestricted text-to-SQL.
READ, NEVER EXECUTE third-party repository code.
Repository Risk != Runtime Exposure.
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

## Licença

Apache License 2.0.
