# Arquitetura do OpsLens

_Última atualização: 2026-09-07_

Este documento é o baseline arquitetural acumulado até a **Phase 9 — Public Analyze Your Repository: COMPLETE após o merge da Gate 9.4**.

A próxima fase é a **Phase 10 — Observability & Operational Excellence**.

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
- package normalization, version/range evaluation, aplicabilidade de vulnerabilidade, reconciliação CVE/GHSA/NVD, KEV, EPSS, CVSS e Risk Policy permanecem determinísticos;
- planners em linguagem natural produzem propostas limitadas, nunca autoridade de query/execution;
- validação de SemanticQuery e compilação SQL permanecem determinísticas;
- construção do corpus canônico e identidade do checked manifest permanecem determinísticas;
- autorização de route, admissão de evidência, completude obrigatória, context assembly, identidade canônica de citações, output admission e cálculo de métricas permanecem determinísticos;
- admissão do request público, scope público do produto, binding de snapshot/file, admissão de semantic plan e admissão do handoff público permanecem determinísticos;
- texto recuperado continua conteúdo de instrução não confiável após admissão de proveniência;
- output do modelo é proposta sobre evidência já admitida, nunca nova fonte de verdade estruturada;
- identidade de citação sintaticamente válida não prova suporte semântico;
- evidência estruturada e semântica permanecem classes diferentes de autoridade;
- runtime exposure não é inferido de repository risk;
- divergências de schema, proveniência, autoridade, completude, request/source binding ou identidade content-addressed falham fechado;
- IAM segue least privilege e responsabilidades reais do runtime;
- serviços AWS entram por requisitos concretos, não por cobertura de certificação;
- custo e observabilidade são requisitos arquiteturais;
- evidência de first run é preservada antes de otimização;
- experimento negativo é preservado em vez de ajustado até passar;
- application contract validado não é apresentado como runtime de produção implantado.

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

### 3.5 Boundary público de análise

```text
JSON público não confiável
 -> admissão estrita <=2048 bytes
 -> coordenadas GitHub owner/name/ref validadas
 -> metadata source-confirmed de repositório público
 -> snapshot imutável commit/tree
 -> evidência inerte uv.lock no commit exato
 -> parser determinístico do uv.lock
 -> normalização determinística PyPI da Phase 3
 -> PublicRepositoryEvidenceExecution
 -> semantic planning request metadata-only <=2048 bytes
 -> proposta não confiável <=1024 bytes
 -> admissão determinística do scope público v1
 -> autoridade híbrida existente da Phase 8
 -> PublicAnalysisAdmissionHandoff
 -> STOP
```

A operação pública v1 é fixa:

```text
analyze_public_repository
```

A policy pública determinística exige exatamente:

```text
remediation_guidance
risk_priority
vulnerability_facts
```

O planner não pode redefinir esse scope. Handoff público bem-sucedido exige adicionalmente que a autoridade de route da Phase 8 retorne:

```text
HYBRID
ALL_REQUIRED
STRUCTURED + SEMANTIC
```

O planner não recebe raw repository URL, bytes do lockfile, nomes/versões de dependências, texto/instruções arbitrárias do repositório, SQL, credenciais, seleção de provider/model/tool ou conteúdo executável.

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

Baseline de Knowledge Retrieval:

```text
knowledge base id:     BTVJ2PBR2A
data source id:        IEL1LBE026
embedding model:       amazon.titan-embed-text-v2:0
embedding dimensions:  1024
embedding data type:   FLOAT32
vector store:          Amazon S3 Vectors
distance:              cosine
chunking:              NONE
canonical chunks:      9
synthesis profile:     us.anthropic.claude-haiku-4-5-20251001-v1:0
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

Baseline de retrieval:

```text
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Os casos negativos ainda retornaram vizinhos vetoriais, provando:

```text
non-empty retrieval != sufficient evidence != authority to answer
```

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

Distinção preservada:

```text
retrieval success != citation attribution success != semantic groundedness
```

## 7. Phase 8 — autoridade híbrida

ADR 0025 congela `hybrid-routing:v1`:

```text
vulnerability_facts and/or risk_priority -> STRUCTURED
remediation_guidance                      -> SEMANTIC
structured + remediation                 -> HYBRID
runtime_exposure, alone or mixed         -> UNSUPPORTED
```

Routes suportadas exigem `ALL_REQUIRED`. Classificação de intent/evidence need pode ser proposta; route authority é determinística.

ADR 0026 congela `hybrid-evidence:v1`. Evidência estruturada e semântica permanecem coleções separadas, e rank/score semântico continuam metadata, não verdade.

ADR 0027 congela:

```text
hybrid-evaluation-golden:v1
68d146a41539d661e7345509913a26d3316daa1c48f9f2e1677cb8aea03ca2d1
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

Composite score não é permitido.

ADR 0028 congela `hybrid-synthesis:v1`:

```text
STRUCTURED  -> fatos F* determinísticos / 0 model calls
SEMANTIC    -> evidência S* admitida / <=1 model call
HYBRID      -> F* + S* / <=1 model call
UNSUPPORTED -> abstention explícito / 0 model calls
incomplete  -> reject_before_synthesis / 0 model calls
```

Cada claim explicativa do modelo deve referenciar evidência semântica admitida. IDs desconhecidos falham fechado.

## 8. Phase 8 — baseline medido e governança de otimização

Baseline real da Gate 8.4:

```text
route_accuracy:               1.0
structured_fact_correctness:  1.0
semantic_groundedness:        0.6666666666666666
citation_correctness:         0.6666666666666666
abstention:                   1.0
latency_ms:                   2959.3333333333335
cost:                         UNMEASURED / null
```

O caso semantic-noise preservou a distinção:

```text
admission != semantic support
retrieval rank != groundedness
allowlisted citation != correct question-specific citation target
```

H8.5-01 testou um único candidato prompt-only previamente declarado uma única vez. Não melhorou semantic groundedness nem citation correctness e aumentou total tokens em 280.

Decisão:

```text
H8.5-01 = REJECT
```

O default continua:

```text
HybridSynthesisPromptPolicy.GATE_8_4_V1
hybrid-synthesis-prompt:v1
```

## 9. Phase 9 — admissão do request público

ADR 0029 congela `public-analysis-request:v1`.

```text
bytes não confiáveis
 -> UTF-8 / JSON / duplicate-key / known-field estritos
 -> gramática exata HTTPS github.com repository-root
 -> validators owner/name/ref
 -> PublicAnalysisRequest content-addressed
```

A URL bruta do usuário nunca vira fetch authority.

Distinção preservada:

```text
public request admitted
 != repository proven public
 != repository snapshot resolved
 != repository analyzed
```

## 10. Phase 9 — evidência imutável de repositório

Gate 9.2 congela `public-repository-evidence:v1`:

```text
PublicAnalysisRequest
 -> metadata source-confirmed de repositório público
 -> snapshot exato commit/tree
 -> uv.lock inerte do commit exato
 -> parser determinístico
 -> normalização PyPI determinística da Phase 3
 -> PublicRepositoryEvidenceExecution
```

Coordenadas canônicas confirmadas pela fonte controlam reads após o lookup inicial. Null ref usa default branch declarado pela fonte; ref explícito é resolvido para identidade imutável antes da aquisição do arquivo.

Drift de request/snapshot/file/parser/normalization falha fechado. Código de terceiros nunca é executado.

## 11. Phase 9 — semantic planning e handoff

ADR 0030 congela:

```text
public-semantic-planning:v1
public-analysis-handoff:v1
```

Semantic planning é proposal-only. Como a operação pública v1 é fixa, código determinístico controla o scope obrigatório.

Bounds:

```text
planning request <= 2048 UTF-8 bytes
planner response <= 1024 bytes
planner invocations <= 1 por orchestration
adaptive application retries = 0
```

Admissão fail-closed rejeita output inválido, needs desconhecidos/duplicados, needs obrigatórios ausentes, `runtime_exposure`, replay pelo request hash, source-execution rebinding e divergência da autoridade de route/completude/classe da Phase 8.

Evidência exact-head da Gate 9.3:

```text
PR #129 head:                    34cea42a0ce37cbfa06b33d57f081403edba2552
Python CI #358 / run 34082791753: PASS
Public Analysis Pyright strict:  0 errors / 0 warnings / 0 informations
Public Analysis pytest:          57 passed
merge SHA:                       6f53537c227cade688091187eac1074645e11bf0
```

Gate 9.3 usou fake repository/planner ports e fez zero provider/model calls reais.

## 12. Taxonomia de falhas da Phase 9

```text
request byte/UTF-8/JSON admission failure
request duplicate/unknown-field failure
repository URL grammar failure
repository metadata/visibility failure
ref/default-branch resolution failure
immutable commit/tree resolution failure
exact-commit file evidence failure
file/parser/normalization provenance mismatch
semantic planning request binding failure
planner invocation failure
planner response size/UTF-8/JSON/schema failure
unknown/duplicate/out-of-authority evidence need
under-scoped public-v1 proposal
runtime_exposure proposal
proposal replay/request-hash mismatch
source-execution rebinding
Phase 8 route/completeness/class mismatch
handoff identity mismatch
```

Falha em qualquer estágio não cria autoridade posterior.

## 13. Boundary de runtime / IAM da Phase 9

ADR 0031 encerra a Phase 9 no boundary governado da aplicação.

No closeout:

```text
public HTTP compute:      NOT DEPLOYED
public endpoint:          NOT DEPLOYED
public runtime principal: DOES NOT EXIST
new Phase 9.4 IAM:        NONE
new Phase 9.4 AWS:        NONE
```

Isto é least privilege intencional:

```text
no concrete compute principal
 -> no runtime role
 -> no speculative permissions
```

Permissões de serviços já provadas permanecem responsabilidades separadas e não são agregadas automaticamente em uma role pública ampla.

## 14. Boundary de cost accounting

Drivers permanecem separados:

```text
Athena execution / bytes scanned
query-time embeddings
S3 Vectors request / processed / returned units
model input tokens
model output tokens
future public runtime infrastructure
```

Gate 8.4/8.5 reportam corretamente `cost = UNMEASURED / null` para custo híbrido em USD. Gate 9.3 usou fake ports e zero model/provider calls reais, portanto o closeout não cria preço sintético por request público.

Estimativa futura em USD exige pricing contract versionado ou reconciliação com billing e deve incluir infraestrutura, concurrency, abuse e retry assumptions.

## 15. Boundary de observabilidade

Evidência atual inclui:

```text
request/snapshot/file/parser/normalization IDs e hashes
route/admission decisions
planning request/proposal/handoff identities
bounded failure categories
provider request/token/latency quando provider real foi executado
exact-head CI evidence
```

OpsLens ainda não afirma possuir:

```text
public-user distributed traces
production request volume
production p95/p99 latency
production error/throttle rates
production request-level AWS cost
production SLO/alert compliance
```

Isto exige runtime implantado e workload medido.

Logging automático de conteúdo de usuário/source/model continua inadequado por padrão; metadata content-free e hashes são preferidos.

## 16. Pré-requisitos para lançamento público

Antes de lançamento real ainda são necessários design concreto e validação medida para:

```text
public HTTP compute / endpoint
runtime identity e least-privilege IAM
request timeout budget
concurrency limits
rate limiting
abuse controls
quota enforcement
cache policy se justificada
kill switch / disable path
cost guardrails e attribution
request-level telemetry
production error/latency distributions
workload-derived SLOs e alerts
rollback / incident procedures
```

Conclusão da Phase 9 não remove esses requisitos.

## 17. Boundary de entrada da Phase 10

Phase 10 pode iniciar somente com estes invariantes congelados:

```text
1. contracts da Phase 9 permanecem boundaries versionados
2. input público nunca vira fetch, SQL, tool, provider/model ou execution authority arbitrários
3. código de terceiros nunca é executado
4. repository risk continua distinto de runtime exposure
5. Phase 8 permanece autoridade de hybrid route/evidence
6. semantic planning permanece proposal-only e content-minimized
7. falha em qualquer admissão impede downstream execution
8. IAM é introduzido apenas para runtime identity concreta
9. production SLO/alert claims exigem workload implantado
10. observability não pode enfraquecer privacy/provenance/content-minimization
11. mudanças de runtime/provider/retrieval exigem hipóteses versionadas e exact-head validation
12. Governed LLM Gateway PR #89 continua deferred até reavaliação separada
```

Se a Phase 10 precisar de um pequeno runtime implantado para produzir telemetry real, ele deve ser explícito sobre compute, IAM, request limits, abuse controls, rollback e custo.

## 18. Decisões deferred

Não adotadas apenas porque a Phase 9 foi concluída:

```text
public compute runtime
runtime cache
reranking
keyword + vector hybrid search
OpenSearch Serverless
alternative embeddings/vector store
new synthesis policy
agents
MCP
AgentCore
A2A
runtime exposure / Inspector integration
Governed LLM Gateway merge
```

Permanecem fases posteriores ou hipóteses separadamente medidas.

## 19. Architecture records

ADRs atuais relevantes:

```text
0020 no unrestricted text-to-SQL
0021 bounded Bedrock Semantic Query planner
0022 customer-managed Bedrock Knowledge Base with S3 Vectors
0023 bounded Bedrock knowledge synthesis
0024 future semantic/runtime IAM boundary
0025 deterministic hybrid routing authority
0026 deterministic hybrid evidence envelope
0027 frozen hybrid evaluation contract
0028 bounded route-aware hybrid synthesis
0029 public repository request admission
0030 public semantic planning proposal authority
0031 Phase 9 public analysis closeout boundary
```

Detalhes históricos e evidência exata de runtime permanecem em `labs/` e `labs/evidence/`, em vez de serem reescritos dentro do baseline arquitetural atual.
