<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Software Supply Chain e Threat Intelligence Verificáveis na AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Semantic Query · Grounded Knowledge Retrieval · Hybrid Evidence · Bounded Agent Reasoning · MCP · AgentCore · A2A · Amazon Inspector · Security Hardening · Autoridade Determinística**

</div>

OpsLens é uma plataforma open source de inteligência para software supply chain construída na AWS.

Ela foi projetada para responder:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência exata prova isso, quais findings devo priorizar e qual orientação verificável pode me ajudar a agir?

O projeto mantém deliberadamente separados verdade determinística, admissão de evidência, raciocínio de modelos, autorização, admissão de handoff, interoperabilidade, execução, divulgação de resultados, comportamento de hosting/runtime, runtime exposure, sinais de segurança e operational recovery.

> **Agents reason. Code verifies evidence.**

> **Repository Risk != Runtime Exposure.**

## Estado atual

| Phase | Escopo | Estado |
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
| Phase 13 | MCP | ✅ Concluída — interoperabilidade offline limitada retida |
| Phase 14 | Amazon Bedrock AgentCore | ✅ Concluída — lab opcional retido; IAM de experimento removido |
| Phase 15 | A2A | ✅ Concluída — interoperabilidade offline por referência + conformidade com SDK oficial retidas |
| Phase 16 | Runtime Exposure with Amazon Inspector | ✅ Concluída — read boundary provado; zero registros atuais; IAM temporário removido |
| Phase 17 | Security Hardening | ✅ Concluída — hardening baseado em evidências + recovery medido retidos |
| Phase 18 | Evaluation, Cost & Portfolio Readiness | ▶️ Próxima |

Veja [Current State](docs/current-state.md), [Roadmap](docs/roadmap.md), [Architecture](docs/architecture.pt-br.md), o [índice de ADRs](docs/adr/README.md) e o [closeout da Phase 17](labs/phase-17-closeout.md).

## Arquitetura principal

### 1. Autoridade estruturada de vulnerabilidade e risco

```text
NVD / CVE -----------+
CISA KEV ------------+
FIRST EPSS ----------+----> evidência de threat intelligence preservando origem
GitHub Advisories ---+
                              |
                              v
repositório GitHub público
 -> snapshot imutável do repositório
 -> aquisição limitada GET-only
 -> evidência inerte e exata de uv.lock
 -> normalização determinística PyPI / PEP 440 / purl
 -> aplicabilidade determinística de ranges vulneráveis
 -> enriquecimento NVD/CVSS + CISA KEV + FIRST EPSS
 -> RepositoryAnalysisResult content-addressed
 -> Risk Policy v1 determinística
```

O modelo nunca decide aplicabilidade de vulnerabilidade, verdade da Risk Policy, fatos KEV/EPSS/CVSS ou runtime exposure.

### 2. Semantic Query limitada

```text
pergunta factual em linguagem natural
 -> planner de modelo limitado
 -> proposta estruturada
 -> parser determinístico
 -> SemanticQuery tipada
 -> compilador SQL determinístico
 -> Athena read-only limitado
 -> evidência estruturada
```

O modelo não recebe autoridade de text-to-SQL irrestrito.

### 3. Grounded retrieval com Bedrock

```text
pins imutáveis de fontes oficiais
 -> corpus canônico determinístico
 -> Amazon Bedrock Knowledge Base
 -> Titan Text Embeddings V2
 -> Amazon S3 Vectors
 -> Retrieve limitado
 -> admissão determinística no corpus verificado
 -> montagem de contexto limitada
 -> síntese limitada via Bedrock Converse
 -> identidade determinística de citações
 -> avaliação de groundedness
```

`RetrieveAndGenerate` não é usado deliberadamente. Retrieval, admissão de evidência, síntese, citações e avaliação permanecem testáveis separadamente.

### 4. Autoridade de evidência híbrida

```text
EvidenceNeed[]
 -> autoridade determinística de rota
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> composição de evidência separada por autoridade
 -> checagens de completude
 -> HybridEvidenceEnvelope
 -> síntese limitada por rota
 -> admissão determinística de saída
```

Fatos estruturados de vulnerabilidade/risco e evidência semântica de remediação permanecem classes de autoridade separadas.

### 5. Raciocínio de agente limitado

A Phase 11 permanece como caminho de referência/default medido:

```text
SingleAgentTask
 -> allowlist code-owned de AgentCapability
 -> uma invocação limitada de modelo
 -> proposta de ação não confiável
 -> parser determinístico
 -> authorize_agent_action(...)
 -> AuthorizedAgentAction | AgentAbstention | rejeição
```

Referência medida em seis casos:

```text
quality:                    6/6
model invocations:          6
input/output/total tokens:  3291 / 104 / 3395
provider latency median:    809.5 ms
client elapsed median:      977.5 ms
SDK retries:                0
capability executions:      0
custo de inferência derivado: USD 0.0041921
```

A Phase 12 reteve especialização/handoff determinísticos, mas rejeitou a topologia medida com dois modelos como default porque não houve ganho de qualidade e houve aumento de chamadas, tokens, latência e custo.

## Interoperabilidade e experimentos de runtime

### MCP — Phase 13

Contratos retidos:

```text
mcp-capability-exposure:v1
mcp-capability-execution:v1
mcp-result-projection:v1
```

MCP permanece uma camada offline limitada de interoperabilidade sobre a autoridade tipada já existente.

```text
MCP tool name != capability authorization
MCP call admission != capability execution
MCP result projection != public runtime exposure
```

Um runtime MCP público/de rede não é atualmente retido.

### Amazon Bedrock AgentCore — Phase 14

A Phase 14 mediu um único experimento limitado de Runtime HTTP/SigV4.

```text
Gate 14.2 replay:          6 / 6 PASS
AgentCore Runtime cost:    USD 0.002380345136128484
Bedrock inference cost:    USD 0.0041921
total observed cost:       USD 0.006572445136128483
runtime cleanup:           RESOURCE_NOT_FOUND
Gate 14.4 IAM cleanup:     0 add / 0 change / 4 destroy
```

Retenção final:

```text
Phase 11 direct Bedrock reasoning:          RETAIN / DEFAULT
AgentCore implementation/evidence:          RETAIN AS OPTIONAL LAB TARGET
AgentCore managed Runtime as default:        DO NOT RETAIN
standing AgentCore Runtime resources:        NONE
standing experiment-specific GitHub IAM:    REMOVED
Gate 14.2 PUBLIC exception:                  NOT RETAINED
```

### A2A — Phase 15

A Phase 15 avaliou A2A sem assumir que adoção de protocolo exige outro runtime de rede.

Baseline autoritativo do protocolo:

```text
A2A release:                 1.0.0
standard bindings:           JSONRPC / GRPC / HTTP+JSON
first OpsLens binding:       JSONRPC
selected operation:          SendMessage
```

Caminho limitado retido:

```text
SpecialistAgentTask já admitida
 -> A2AReference content-addressed
 -> registry local code-owned
 -> projeção estrita A2A 1.0 JSON-RPC SendMessage
 -> validação de duplicate-key / exact-shape
 -> resolução de referência code-owned
 -> metadata de Message ou Task terminal completed
 -> admissão determinística do OpsLens
 -> STOP antes de model/capability execution
```

A Gate 15.2 mediu:

```text
Agent Card bytes:          582
protocol requests:         2
request bytes total:       1308
response bytes total:      989
client elapsed sum:        0.353039 ms
handler elapsed sum:       0.239397 ms
retries:                   0
model invocations:         0
capability executions:     0
new AWS resources:         0
new IAM roles/policies:    0
incremental AWS cost:      USD 0.00
```

A Gate 15.3 verificou o perfil congelado contra o código-fonte do SDK oficial Python A2A:

```text
a2a-sdk version:             1.1.4
release tag:                 v1.1.4
source commit:               2d4d3048b245d2af854bad804f0e722ea9febc08
AgentCard conformance:       PASS
SendMessage request:         PASS
JSON-RPC construction:       PASS
Message response:            PASS
Task response:               PASS
project/runtime dependency:  0
protocol network requests:   0
```

O SDK é retido somente como oracle de conformidade em CI, fixado pelo source commit exato.

Decisão final da Phase 15:

```text
A2AReference content-addressed:                 RETAIN
strict raw JSON admission:                      RETAIN
A2A 1.0 JSONRPC SendMessage profile:            RETAIN
Message / terminal Task metadata admission:     RETAIN
A2A fixtures / CI:                              RETAIN
official exact-source SDK oracle:               RETAIN FOR CI
public/network A2A runtime:                      DO NOT CREATE
standing A2A cloud resources / IAM:             NONE
A2A capability/business-result authority:        DO NOT CREATE
a2a-sdk project/runtime dependency:              DO NOT ADD
```

```text
A2A SDK acceptance != OpsLens admission authority
A2A transport success != business/evidence truth
A2A protocol binding != business authority
```

### Amazon Inspector — Phase 16

A Phase 16 avaliou o Amazon Inspector como autoridade independente de evidência de runtime sem permitir que runtime data redefinisse findings de repositório ou a Risk Policy v1.

A role compartilhada de deployment mediu primeiro um boundary fail-closed de autorização:

```text
run:            34411934819 / #1
ListCoverage:   ACCESS_DENIED / AccessDeniedException
ListFindings:   NOT_ATTEMPTED
AWS mutations:  0
```

Em vez de ampliar esse principal compartilhado, o OpsLens criou uma role temporária dedicada limitada a `ListCoverage` e `ListFindings` para exatamente uma nova medição.

Rerun medido:

```text
run:                    34414116549 / #2
job:                    102675000098
ListCoverage:           SUCCESS / 1 page / 0 records / 0 retries
ListFindings:           SUCCESS / 1 page / 0 records / 0 retries
client elapsed:         465.877452 ms
AWS mutations:          0
model invocations:      0
capability executions:  0
artifact SHA-256:       a6f917e62124b4c604891e1a83db9874e3ef34696110dfaead1af16d45a03365
```

O read boundary funcionou, mas a conta dev atual retornou zero coverage/findings do Inspector. O OpsLens não ativou nem reconfigurou scanning apenas para fabricar dados de demonstração.

O teardown obrigatório produziu:

```text
cleanup plan:       0 add / 0 change / 2 destroy
cleanup apply:      0 added / 0 changed / 2 destroyed
post-apply plan:    No changes
temporary role:     ABSENT / NoSuchEntity
standing IAM:       NONE
```

Retenção final:

```text
Inspector read-only domain/adapter contract:   RETAIN
historical discovery workflow:                 RETAIN / DISABLED BY DEFAULT
measured zero-record evidence:                 RETAIN
standing Inspector discovery IAM:              NONE
Inspector activation/configuration:             NOT CREATED
hybrid runtime_exposure routing:                NOT CREATED
repository/runtime automatic correlation:       NOT CREATED
```

```text
AWS authentication != Inspector read authorization
Inspector API success != runtime evidence presence
Inspector finding != repository finding
Inspector evidence != model authority
```

## Security Hardening — Phase 17

A Phase 17 começou por um inventário transversal de ameaças/gaps de controle e adicionou somente controles sustentados por evidência.

Postura de segurança retida:

```text
protected-main required context:          Repository security invariants
external Actions references:              full commit SHA
persisted checkout credentials:           disabled where unnecessary
EPSS plan vs execution identity:          separated
Dependency Review:                        retained
CodeQL / Python:                          retained
adversarial regression:                   8 cases / 7 threat classes
Powertools Lambda handlers hardened:      12
scheduled-ingestion recovery control:     retained / Terraform-owned
```

A prova medida de recovery da Gate 17.6 utilizou exatamente três recursos recorrentes do EventBridge Scheduler:

```text
aws_scheduler_schedule.epss_daily
aws_scheduler_schedule.kev_daily
aws_scheduler_schedule.nvd_incremental_hourly
```

e comprovou:

```text
0/3/0 pause plan + apply
 -> independent 3/3 DISABLED reads
 -> paused Terraform convergence
 -> 0/3/0 resume plan + apply
 -> independent 3/3 ENABLED reads
 -> final default Terraform convergence
```

O controle é deliberadamente um **scheduled-ingestion pause**, não um global kill switch. Ele não afirma interromper trabalho já admitido ou em execução.

A Gate 17.7 sincronizou a arquitetura acumulada EN/PT-BR, fechando o drift documental restante.

Closeout canônico:

- [ADR 0070 — closeout da Phase 17 Security Hardening](docs/adr/0070-phase17-security-hardening-closeout.md)
- [Closeout da Phase 17](labs/phase-17-closeout.md)
- [Evidência de closeout da Phase 17](labs/evidence/phase-17-closeout-v1.json)

## O que deliberadamente não é afirmado

O OpsLens atualmente **não** afirma:

```text
public HTTP production runtime
public WAF / tenant quota controls without a public runtime
public MCP production runtime
AgentCore as the default/production OpsLens runtime
PUBLIC AgentCore networking as a production decision
public/network A2A runtime
A2A-derived capability authorization
A2A business-result authority
runtime exposure inferred from the zero-record Inspector experiment
standing Inspector experiment IAM
global platform kill switch
termination of in-flight work through the Scheduler pause
production SLOs for experimental runtime boundaries
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
streaming:               no
tools in reasoning:      none
```

## Documentação e evidências

- [Current State](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [Architecture — English](docs/architecture.md)
- [Architecture — Português](docs/architecture.pt-br.md)
- [Índice de ADRs](docs/adr/README.md)
- [Índice da documentação](docs/README.md)
- [Closeout da Phase 11](labs/phase-11-gate-11-6-closeout.md)
- [Closeout da Phase 12](labs/phase-12-gate-12-5-multi-agent-closeout.md)
- [Closeout MCP da Phase 13](labs/phase-13-gate-13-5-mcp-closeout.md)
- [Decisão de retenção AgentCore da Phase 14](labs/phase-14-gate-14-3-agentcore-retention-decision.md)
- [Cleanup IAM da Phase 14](labs/phase-14-gate-14-4-agentcore-iam-cleanup.md)
- [Closeout A2A da Phase 15](labs/phase-15-closeout.md)
- [Closeout Amazon Inspector da Phase 16](labs/phase-16-closeout.md)
- [Closeout Security Hardening da Phase 17](labs/phase-17-closeout.md)
- [Evidência de closeout da Phase 17](labs/evidence/phase-17-closeout-v1.json)

## Próxima phase planejada

```text
Phase 18 — Evaluation, Cost & Portfolio Readiness
```

A Gate 18.1 começa com um inventário transversal de evidências e uma matriz de comparabilidade. Valores existentes devem ser classificados como `MEASURED`, `DERIVED`, `UNMEASURED` ou `NOT_APPLICABLE` antes de produzir visões consolidadas de qualidade, latência, custo, reliability, segurança e portfólio.

---

A PR #89 / `feat/governed-gateway-semantic-planner` pertence ao trabalho separado do Governed LLM Gateway e permanece intencionalmente fora da Phase 18 salvo reautorização explícita.
