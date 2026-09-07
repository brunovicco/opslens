# Arquitetura do OpsLens

_Última atualização: 2026-09-06_

Este documento é o baseline arquitetural acumulado até a conclusão da **Phase 8 — Hybrid Retrieval**.

O próximo boundary de produto é a **Phase 9 — Public Analyze Your Repository**.

## 1. Propósito

OpsLens é uma plataforma open source de software supply chain e threat intelligence construída na AWS.

Objetivo do produto:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência exata prova isso, quais findings devo priorizar e qual orientação verificável pode me ajudar a agir?

Invariante central:

> **Agents reason. Code verifies evidence.**

Boundaries permanentes:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **Intent classification != execution authority.**

> **No unrestricted text-to-SQL.**

## 2. Princípios arquiteturais

Salvo mudança por ADR explícito:

- evidência bruta de terceiros é preservada antes de enrichment ou interpretação;
- versões exatas de fontes, snapshots imutáveis e hashes participam da proveniência;
- package normalization, version/range evaluation, aplicabilidade, reconciliação CVE/GHSA/NVD, KEV, EPSS, CVSS e Risk Policy permanecem determinísticos;
- planners em linguagem natural produzem propostas limitadas, nunca autoridade de query/execution;
- validação de SemanticQuery e compilação SQL permanecem determinísticas;
- construção do corpus canônico e identidade do checked manifest permanecem determinísticas;
- autorização de route, admissão de evidência, completude de evidência obrigatória, context assembly, identidade canônica de citações, output admission e cálculo de métricas permanecem determinísticos;
- texto recuperado continua sendo conteúdo de instrução não confiável após admissão de proveniência;
- output do modelo é proposta sobre evidência já admitida, nunca nova fonte de verdade estruturada;
- identidade de citação sintaticamente válida não prova suporte semântico;
- evidência estruturada e semântica permanecem classes diferentes de autoridade;
- runtime exposure não é inferido de repository risk;
- divergências de schema, proveniência, autoridade, completude ou identidade content-addressed falham fechado;
- IAM segue least privilege e boundaries reais de responsabilidade do runtime;
- serviços AWS entram por requisitos concretos, não por cobertura de certificação;
- custo e observabilidade são requisitos arquiteturais;
- evidência de first run é preservada antes de otimização;
- experimento negativo é preservado em vez de ajustado até passar.

## 3. Forma atual do sistema

### 3.1 Autoridade estruturada de vulnerabilidade e risco

```text
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
 -> evidência de threat intelligence preservada por fonte
 -> identidade PyPI / aplicabilidade PEP 440 determinísticas
 -> snapshot imutável do repositório + evidência inerte do uv.lock
 -> correlação determinística de vulnerabilidades
 -> RepositoryAnalysisResult
 -> Risk Policy v1 determinística
 -> RiskPrioritizationResult
```

Nenhum LLM decide aplicabilidade de vulnerabilidade, verdade KEV/EPSS/CVSS, score/tier de risco ou runtime exposure.

### 3.2 Caminho estruturado de pergunta em linguagem natural

```text
pergunta factual em linguagem natural
 -> planner Bedrock limitado
 -> proposta estruturada
 -> parser determinístico
 -> SemanticQuery tipada
 -> compilador SQL determinístico
 -> Athena read-only limitado
 -> evidência estruturada de resultado
```

O planner não possui autoridade para SQL arbitrário. ADRs 0020 e 0021 congelam esse boundary.

### 3.3 Caminho semântico explicativo / remediação

```text
source pins oficiais explicitamente autorizados
 -> corpus canônico determinístico
 -> publicação S3 determinística
 -> ingestão em Bedrock Knowledge Base customer-managed
 -> Titan Text Embeddings V2 / 1024 / FLOAT32
 -> Amazon S3 Vectors / cosine
 -> Retrieve direto e limitado
 -> admissão por proveniência/hash contra corpus verificado
 -> context assembly determinístico e limitado
 -> autoridade pré-modelo determinística
 -> síntese limitada e não-streaming via Bedrock Converse
 -> identidade determinística de citações
 -> avaliação explícita de suporte / groundedness
```

`RetrieveAndGenerate` continua deliberadamente fora do caminho para manter retrieval e synthesis mensuráveis separadamente.

### 3.4 Caminho de evidência híbrida

```text
proposta EvidenceNeed[]
 -> autoridade determinística de hybrid route
 -> STRUCTURED | SEMANTIC | HYBRID | UNSUPPORTED
 -> aquisição/admissão determinística por classe de evidência
 -> completude ALL_REQUIRED por need
 -> HybridEvidenceEnvelope
 -> projeção determinística de fatos F*
 -> projeção determinística de citações semânticas S*
 -> síntese limitada e route-aware
 -> output admission determinístico
 -> métricas independentes de qualidade/runtime
```

Hybrid Retrieval significa **routing e composição de evidências híbridas**. Não implica keyword + vector search.

## 4. Fundação AWS

```text
environment:             dev
primary workload Region: us-east-1
AWS account:             487757851499
IaC:                     Terraform
human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
```

Storage principal:

```text
Data:       opslens-dev-data-487757851499-us-east-1
Artifacts:  opslens-dev-artifacts-487757851499-us-east-1
TF state:   opslens-dev-tfstate-487757851499-us-east-1
```

Analytics:

```text
Glue database:    opslens_dev
Athena workgroup: opslens-dev
scan cutoff:      10.485.760 bytes
```

Administração humana usa credenciais temporárias do IAM Identity Center. GitHub Actions usa OIDC; access keys persistentes não são armazenadas no GitHub.

## 5. Autoridades estruturadas determinísticas — Phases 2–6

### Threat Intelligence Data Lake

NVD, KEV, EPSS e GHSA permanecem evidência source-local com proveniência e semântica temporal explícitas.

### Vulnerability Correlation

```text
package/version/purl
 + evidência exata de vulnerable range
 -> avaliação PEP 440 determinística
 -> affected | not_affected | unsupported
 -> reconciliação CVE/GHSA/NVD
 -> evidência content-addressed
```

### Repository Intelligence

```text
repositório público
 -> identidade imutável repository/commit/tree
 -> aquisição GitHub read-only limitada
 -> bytes inertes do uv.lock
 -> parsing TOML determinístico
 -> dependências canônicas
 -> aplicabilidade determinística
 -> RepositoryAnalysisResult
```

Findings de repositório não provam presença ou explorabilidade em runtime.

### Risk Prioritization

```text
RepositoryAnalysisResult
 -> Risk Policy v1 determinística
 -> contribuições por fator
 -> priority score + tier
 -> completeness / review_required
```

O valor de prioridade é score de policy do OpsLens, não probabilidade de exploit, CVSS, EPSS ou runtime exposure.

### Semantic Query

```text
question
 -> planner Bedrock limitado
 -> parser determinístico
 -> SemanticQuery tipada
 -> compilador SQL determinístico
 -> execução Athena limitada
```

Text-to-SQL irrestrito não é permitido.

## 6. Phase 7 — Knowledge Retrieval controlado

Corpus congelado:

```text
manifest id: knowledge-corpus-manifest:v1
documents:   6
chunks:      9
sha256:      98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

Baseline da Knowledge Base:

```text
knowledge base id:     BTVJ2PBR2A
data source id:        IEL1LBE026
chunking:              NONE
embedding model:       amazon.titan-embed-text-v2:0
embedding dimensions:  1024
embedding data type:   FLOAT32
vector store:          Amazon S3 Vectors
distance:              cosine
canonical vectors:     9
```

A admissão de retrieval direto verifica source location esperada, manifest canônico, hash/byte count do texto, metadata e rank determinístico antes de existir um `RetrievedChunk`.

Baseline congelado de retrieval:

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Os dois casos negativos ainda retornaram vizinhos vetoriais, provando:

```text
non-empty retrieval != sufficient evidence != authority to answer
```

## 7. Phase 7 — síntese limitada e autoridade de citações

Perfil de synthesis:

```text
Region:              us-east-1
API:                 bedrock-runtime / Converse
model/profile:       us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:           não
temperature:         0.0
provider maxTokens:  2048
tools:               nenhum
```

Trust classes do prompt permanecem separadas:

```text
trusted system instructions
untrusted user question
untrusted but source-verified retrieved evidence
```

Citation IDs são projetados apenas de evidência admitida. O modelo pode selecioná-los; não pode criar identidade canônica de fonte.

Baseline congelado da Gate 7.7:

```text
decision accuracy:                 1.0
citation target precision:         0.2857142857142857
citation target recall:            0.5
claim supportedness rate:          0.8461538461538461
unsupported claim rate:            0.15384615384615385
citation correctness rate:         0.8461538461538461
abstention precision:              1.0
abstention recall:                 1.0
```

O failure de isolation preservado demonstra:

```text
retrieval success != citation attribution success != semantic groundedness
```

## 8. Phase 8 — routing híbrido determinístico

ADR 0025 congela `hybrid-routing:v1`.

Needs reconhecidos:

```text
vulnerability_facts
risk_priority
remediation_guidance
runtime_exposure
```

Policy:

```text
vulnerability_facts and/or risk_priority -> STRUCTURED
remediation_guidance                      -> SEMANTIC
structured + remediation                 -> HYBRID
runtime_exposure, alone or mixed         -> UNSUPPORTED
```

Classificação de intent/evidence need pode ser proposta. A decisão de route é autoridade determinística.

Routes suportadas exigem evidência `ALL_REQUIRED`. Runtime exposure é válido-mas-indisponível em vez de ser mapeado para repository risk.

## 9. Phase 8 — evidência híbrida determinística

ADR 0026 congela `hybrid-evidence:v1`.

O envelope preserva coleções separadas:

```text
structured_evidence[]
semantic_evidence[]
authority_decision
provenance_by_class
satisfied_needs
completeness
content-addressed identity
```

Não existe `Evidence[]` genérico apagando classe de autoridade.

Evidência estruturada atende somente needs estruturados suportados. Evidência semântica atende somente remediation guidance. Evidência extra/não solicitada, duplicatas, ranks inválidos ou classes obrigatórias incompletas são rejeitados.

Rank/score semântico são dados de proveniência e medição, nunca verdade.

## 10. Phase 8 — evaluation contract congelado

ADR 0027 congela:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
```

Tipos de caso:

```text
structured_only_factual
semantic_only_remediation
true_hybrid
unsupported_out_of_authority
partial_structured_evidence
semantic_retrieval_noise
```

Dimensões:

```text
route_accuracy
structured_fact_correctness
semantic_groundedness
citation_correctness
abstention
latency
cost
```

Composite score não é permitido.

O caso semantic-noise coloca intencionalmente um chunk admitido porém não suportante no rank 1 e o target correto no rank 2.

## 11. Phase 8 — síntese limitada e route-aware

ADR 0028 congela `hybrid-synthesis:v1`.

```text
STRUCTURED
 -> fatos determinísticos F1/F2/...
 -> 0 model calls

SEMANTIC
 -> evidência admitida S1/S2/...
 -> <=1 model call

HYBRID
 -> fatos determinísticos + evidência semântica admitida
 -> <=1 model call

UNSUPPORTED
 -> abstention explícito
 -> 0 model calls

incomplete evidence
 -> reject_before_synthesis
 -> 0 model calls
```

Structured facts permanecem propriedade do código. O modelo não pode alterá-los ou promover valores autorados a fatos canônicos.

Cada claim explicativa do modelo deve referenciar pelo menos um S citation ID admitido. F IDs opcionais servem somente como contexto estruturado. IDs desconhecidos falham fechado.

O adapter de runtime preserva categorias limitadas para provider invocation, response contract, stop reason, output contract e clock anomalies.

## 12. Gate 8.4 — baseline híbrido real

Evidência imutável:

```text
labs/evidence/phase-8-gate-8-4-first-complete-baseline-v1.json
```

Execução medida:

```text
complete:                            true
planned_case_count:                  6
synthesis_invocation_attempt_count:  3
admitted_model_execution_count:      3
route_accuracy:                      1.0
structured_fact_correctness:         1.0
semantic_groundedness:               0.6666666666666666
citation_correctness:                0.6666666666666666
abstention:                          1.0
latency_ms:                          2959.3333333333335
cost:                                UNMEASURED / null
```

Tokens:

```text
input:   4150
output:   289
total:   4439
```

O caso semantic-noise emitiu o claim correto S2/rank 2 e um claim auxiliar S1/rank 1. Output admission aceitou ambos porque os IDs eram admitidos; avaliação independente reduziu corretamente groundedness/citation correctness específicos da pergunta.

## 13. Gate 8.5 — governança de otimização medida

H8.5-01 foi um único candidato prompt-only previamente declarado:

```text
experiment: hybrid-optimization:h8.5-01-v1
candidate:  hybrid-synthesis-prompt:h8.5-01-v1
```

Ele alterou somente trusted synthesis instructions sobre resposta mínima suficiente e relevância direta para a pergunta.

Contracts de autoridade, targets da fixture, evidência semântica, model profile, Region, inference settings, output schema e call budget permaneceram iguais.

Evidência do real run:

```text
labs/evidence/phase-8-gate-8-5-h85-01-first-run-v1.json
```

Resultado:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2997.0
cost:                         UNMEASURED / null
```

A mesma weakness semantic-noise persistiu. Decisão:

```text
H8.5-01 = REJECT
```

O candidato também aumentou input tokens em 306 e total tokens em 280, apesar de reduzir output em 26.

O default continua:

```text
HybridSynthesisPromptPolicy.GATE_8_4_V1
hybrid-synthesis-prompt:v1
```

Não há segundo run nem mutation pós-resultado de H8.5-01 autorizados. Intervenção materialmente diferente exige nova hipótese e nova regra de aceitação previamente declarada.

## 14. Taxonomia de falhas

Diagnóstico atual é orientado por estágio:

```text
routing / authority failure
structured evidence failure
semantic provider retrieval failure
semantic evidence-admission failure
hybrid completeness failure
structured fact projection failure
semantic relevance / selection failure
synthesis provider invocation failure
synthesis response-contract failure
synthesis stop-reason failure
synthesis output-admission failure
citation-attribution failure
semantic groundedness failure
optimization-decision failure
```

Provider success não pode esconder semantic failure, e problema de retrieval/citation não deve ser rotulado como falha de structured authority.

## 15. Boundary de runtime IAM

Ainda não existe application compute principal público no closeout da Phase 8.

Por isso a Phase 8 não cria role especulativa de runtime.

Para o caminho semântico já provado, ADR 0024 registra a forma futura de least privilege:

```text
bedrock:Retrieve
 -> Knowledge Base exata BTVJ2PBR2A

bedrock:InvokeModel
 -> inference profile aprovado e foundation-model resources necessários
```

Lógica híbrida de route/evidence/projection não exige entitlement Bedrock mais amplo.

O caminho estruturado preserva autoridade Athena read-only limitada. IAM de runtime exposure fica deferred porque runtime exposure continua unsupported.

A policy deve ser revalidada contra documentação AWS atual imediatamente antes de deployment real da Phase 9.

## 16. Boundary de cost accounting

Drivers de custo permanecem separados:

```text
execução Athena / bytes scanned
query-time embeddings
S3 Vectors request / processed / returned units
model input tokens
model output tokens
```

Gate 8.4 e Gate 8.5 reportam corretamente `cost = UNMEASURED / null`. Evidência de tokens não é a conta AWS completa.

Qualquer estimativa USD futura exige pricing contract explícito e versionado ou reconciliação com billing, em vez de misturar rates potencialmente desatualizados com runtime evidence.

## 17. Boundary de observabilidade

Evidência híbrida atual de lab/runtime captura:

```text
route e case identity
expected/observed behavior
synthesis invocation attempt
bounded failure category/diagnostic
provider request ID
model/profile e Region
token/cache counts
Bedrock latency e client elapsed time
SDK retries
stop reason
request/prompt/envelope/catalog/result hashes
projeções F estruturadas
mapeamentos S citation/chunk
métricas independentes de qualidade
otimization decision/rejection reasons
```

A Phase 8 não afirma possuir:

```text
production SLOs
continuous deployed hybrid metrics
public-user distributed traces
production alert thresholds
high-volume percentiles/error rates
complete request-level AWS bill attribution
```

Isso exige runtime público implantado e workload medido.

Automatic model-invocation content logging continua inadequado porque prompts contêm user/source text; metadata content-free e hashes são preferidos.

## 18. Boundary de entrada da Phase 9

Public Analyze Your Repository só pode iniciar com estes invariantes congelados:

```text
1. aquisição pública permanece GET-only e código do repositório nunca é executado
2. identidade imutável do snapshot antecede dependency analysis
3. aplicabilidade e risco permanecem verdade estruturada determinística
4. hybrid route authority permanece determinística
5. routes suportadas exigem ALL_REQUIRED
6. runtime exposure permanece UNSUPPORTED até existir autoridade separada de runtime
7. model synthesis recebe apenas evidência admitida e não cria proveniência/verdade estruturada canônica
8. structured-only, unsupported e incomplete preservam zero model calls
9. hybrid-synthesis-prompt:v1 continua runtime default; H8.5-01 permanece evidência rejeitada
10. public inputs, request size, provider calls, output size, timeout, concurrency e cost budgets são limitados
11. falhas de provider/evidence/output/citation continuam fail closed
12. telemetry evita logging automático de user/source prompt content
13. abuse/rate/cost controls existem antes do lançamento público
14. SLOs/alerts de produção são derivados de workload implantado, não de amostras de lab
15. runtime IAM identity é criada somente quando o compute boundary da Phase 9 for concreto
16. mudanças de prompt/retrieval/reranking/vector exigem novas hipóteses versionadas
```

Phase 9 deve expor o evidence system já governado, não introduzir complexidade agentic por padrão.

## 19. Decisões deferred

Não adotadas apenas porque a Phase 8 terminou:

```text
reranking
keyword + vector hybrid search
OpenSearch Serverless
alternative embeddings/vector store
runtime cache
similarity thresholds
new synthesis policy
agents
MCP
AgentCore
A2A
runtime exposure / Inspector integration
```

Continuam fases futuras ou hipóteses separadamente medidas.

A PR #89 de Governed LLM Gateway continua deferred para a futura Phase 14 Case 3 e não faz parte da Phase 8.

## 20. Architecture records

ADRs atuais relevantes:

```text
0020 no unrestricted text-to-SQL
0021 bounded Bedrock Semantic Query planner
0022 customer-managed Bedrock Knowledge Base with S3 Vectors
0023 bounded Bedrock knowledge synthesis
0024 future Phase 7/runtime IAM boundary
0025 deterministic hybrid routing authority
0026 deterministic hybrid evidence envelope
0027 frozen hybrid evaluation contract
0028 bounded route-aware hybrid synthesis
```

Detalhes históricos de implementação e evidência exata de runtime permanecem em `labs/` e `labs/evidence/`, em vez de serem reescritos dentro do baseline arquitetural atual.
