# Arquitetura do OpsLens

_Última atualização: 2026-09-06_

Este documento é o baseline arquitetural acumulado até a conclusão da **Phase 7 — Knowledge Retrieval with Bedrock**.

O próximo boundary arquitetural é a **Phase 8 — Hybrid Retrieval**.

## 1. Propósito

OpsLens é uma plataforma open source de software supply chain e threat intelligence construída na AWS.

Objetivo do produto:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência exata prova isso, quais findings devo priorizar e qual orientação verificável pode me ajudar a agir?

Invariante central:

> **Agents reason. Code verifies evidence.**

Boundaries permanentes adicionais:

> **Not every question is a RAG problem.**

> **Structured facts use structured retrieval.**

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

> **No unrestricted text-to-SQL.**

## 2. Princípios arquiteturais permanentes

Salvo mudança por ADR explícito:

- evidência bruta de terceiros é preservada antes de enrichment ou interpretação;
- versões exatas da fonte e hashes participam da proveniência;
- normalização de package identity, vulnerable-range matching, aplicabilidade, reconciliação CVE/GHSA/NVD, evidência KEV/EPSS/CVSS e Risk Policy permanecem determinísticas;
- validação de semantic query e compilação SQL permanecem determinísticas;
- normalização do corpus, seleção, hashing e identidade do manifest permanecem determinísticos;
- admissão de retrieval, context assembly, autoridade de citações, admissão de output, validação de suporte e cálculo de métricas permanecem determinísticos;
- outputs de modelos são propostas/evidência, não autoridade sobre verdade estruturada;
- o modelo pode selecionar citation IDs allowlisted, mas não pode criar identidade canônica de fonte;
- citação sintaticamente válida não prova suporte semântico;
- conteúdo recuperado continua sendo conteúdo de instrução não confiável após validação de proveniência;
- divergências de schema, proveniência, autoridade ou identidade content-addressed falham fechado;
- IAM usa least privilege e separação de responsabilidades;
- serviços AWS entram apenas para requisitos concretos e medidos;
- custo e observabilidade são requisitos arquiteturais;
- um único ambiente `dev` real é preferido a ambientes fictícios;
- evidência de first run é preservada antes de otimização.

## 3. Forma do sistema

### Caminho estruturado de vulnerabilidade/risco

```text
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
 -> correlação determinística
 -> Repository Intelligence imutável
 -> RepositoryAnalysisResult
 -> Risk Policy v1 determinística
 -> RiskPrioritizationResult
```

### Caminho estruturado de perguntas em linguagem natural

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

O planner não recebe autoridade para SQL arbitrário.

### Caminho de conhecimento explicativo/remediação

```text
fontes oficiais explicitamente autorizadas
 -> pins imutáveis de repositório/commit/path
 -> aquisição GET-only limitada de texto inerte
 -> normalização determinística + seleção exata de seções
 -> chunks canônicos content-addressed
 -> manifest verificado com hashes/proveniência
 -> publicação S3 determinística
 -> ingestão em Bedrock Knowledge Base customer-managed
 -> Titan Text Embeddings V2 / 1024 / FLOAT32
 -> Amazon S3 Vectors / cosine
 -> Retrieve direto e limitado
 -> reconciliação determinística de S3/hash/metadata
 -> RetrievedChunk[]
 -> context assembly determinístico por prefixo de rank
 -> decisão determinística de autoridade pré-modelo
 -> uma chamada não-streaming e limitada de Bedrock Converse
 -> admissão determinística do output
 -> catálogo determinístico C1..Cn
 -> proposta estruturada de claims + citation IDs
 -> evidência humana pair-level de suporte
 -> métricas determinísticas de groundedness/citation
```

Retrieval e síntese permanecem observáveis separadamente. `RetrieveAndGenerate` continua deliberadamente fora do caminho.

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

Administração humana usa credenciais temporárias do IAM Identity Center. GitHub Actions usa OIDC; access keys persistentes não são armazenadas no GitHub.

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

> **No LLM decides vulnerability applicability.**

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

O priority score é uma política do OpsLens, não probabilidade de exploração, CVSS, EPSS ou runtime exposure.

### Semantic Query

```text
pergunta
 -> planner Bedrock limitado
 -> parser determinístico
 -> SemanticQuery tipada
 -> compilador SQL determinístico
 -> Athena limitado
```

ADRs 0020 e 0021 preservam o boundary de no-unrestricted-text-to-SQL.

## 6. Corpus controlado e vector Knowledge Base da Phase 7

Gate 7.1 congelou os contratos provider-independent de retrieval.

Gate 7.2 autorizou seis arquivos oficiais por pins imutáveis de repositório/commit/path e materializou deterministicamente nove chunks.

Corpus congelado:

```text
manifest id: knowledge-corpus-manifest:v1
documents:   6
chunks:      9
sha256:      98b289a9322849f703c106b573702ad221e81647f9a49eab05455bc95c5e9418
```

Gate 7.3 selecionou uma Bedrock vector Knowledge Base customer-managed apoiada por S3 Vectors:

```text
knowledge base id:     BTVJ2PBR2A
data source id:        IEL1LBE026
source prefix:         knowledge/corpus/v1/bedrock/
chunking:              NONE
embedding model:       amazon.titan-embed-text-v2:0
embedding dimensions:  1024
embedding data type:   FLOAT32
vector store:          Amazon S3 Vectors
distance:              cosine
reranking:             deferred
hybrid search:         deferred
```

A ingestão bem-sucedida materializou exatamente nove vetores.

A service role da Knowledge Base é uma identidade de integração de ingestão/vector store, não identidade humana nem runtime da aplicação.

## 7. Retrieval direto e admissão determinística

Gate 7.4 usa `Retrieve` direto da Knowledge Base.

Caminho de admissão:

```text
resultado do provider
 -> localização S3 esperada exata
 -> lookup no manifest verificado
 -> SHA-256 + byte-count do texto retornado
 -> reconciliação de metadata canônica
 -> rank determinístico
 -> RetrievedChunk
```

IDs do provider não viram identidade canônica do OpsLens.

Baseline congelado da Gate 7.5:

```text
10 casos
8 positivos
2 negativos/out-of-authority
Recall@1:   0.375
Recall@3:   0.750
Recall@5:   0.875
Recall@10:  1.000
MRR:        0.5699404761904762
provenance correctness: 1.0
```

Os dois casos negativos retornaram nearest neighbors. Similaridade vetorial e retrieval não vazio são evidência, não autoridade de routing/answerability.

## 8. Context assembly e síntese

Bounds provider-independent de contexto:

```text
default max chunks:      5
hard max chunks:         10
max admitted text bytes: 16.384 UTF-8 bytes
```

Algoritmo:

```text
RetrievalEvidence
 -> preservar rank
 -> admitir o próximo chunk inteiro se couber
 -> parar em max chunks ou no primeiro chunk inteiro que não couber
 -> nunca truncar
 -> nunca pular/backfill ranks inferiores
 -> AssembledContext
```

Autoridade pré-modelo é determinística:

```text
SUPPORTED
UNSUPPORTED
```

`UNSUPPORTED` não pode formar request de síntese.

Boundary de síntese do ADR 0023:

```text
question:                 <= 1.000 caracteres
model calls/application:  1 máximo
answer:                   <= 4.000 caracteres
raw response parser:      <= 65.536 caracteres
Region:                   us-east-1
API:                      bedrock-runtime / Converse
model/profile:            us.anthropic.claude-haiku-4-5-20251001-v1:0
streaming:                não
temperature:              0.0
provider maxTokens:       2.048
tools:                    nenhum
structured output:        JSON Schema
```

Classes de trust permanecem separadas:

```text
trusted system instructions
untrusted user question
untrusted but source-verified retrieved evidence
```

Logging automático do body de invocação continua desabilitado porque prompts contêm texto de usuário/fonte. Metadata content-free e hashes são registrados.

## 9. Autoridade determinística de citações e groundedness

```text
AssembledContext
 -> ContextEvidenceBlock[] selecionados
 -> C1..Cn determinísticos
 -> CitationCatalog
 -> GroundedSynthesisRequest
 -> claims estruturados + citation IDs
 -> admissão determinística de output
```

Canonical URI/source/document/chunk/hash vêm da evidência admitida, nunca do output do modelo.

Citation ID válido garante cobertura sintática, não suporte semântico.

Baseline `knowledge-grounding-golden:v1`:

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

Evidência humana de suporte é preservada como metadata content-addressed em:

```text
labs/evidence/phase-7-gate-7-7-first-run-review-v1.json
```

### Lição: retrieval success != groundedness

O target de isolation foi recuperado em rank 1 e virou `C1`, mas o modelo citou `C2` nos dois claims. A revisão exact-chunk marcou os dois pares como unsupported.

```text
retrieval success
 != citation attribution success
 != claim groundedness
```

### Lição: retrieval existence != answerability

O caso de TLS cipher recuperou cinco vizinhos vetoriais, mas retornou corretamente `insufficient_evidence`.

```text
non-empty vector retrieval
 != sufficient evidence
 != authority to answer
```

A fraqueza da Gate 7.7 permanece congelada. Mudança de prompt/citation selection exige nova versão e nova avaliação.

## 10. Taxonomia de falhas da Phase 7

Gate 7.8 congela o diagnóstico por estágio:

```text
1. route / authority failure
2. provider retrieval failure
3. retrieval evidence-admission failure
4. retrieval relevance / coverage failure
5. context-assembly failure
6. synthesis transport failure
7. synthesis output-admission failure
8. answerability / decision failure
9. citation-authority failure
10. citation-attribution failure
11. semantic groundedness failure
```

Essas classes permanecem separadas. Uma falha de citation attribution não pode ser reescrita como retrieval miss, e sucesso do provider não pode esconder falha semântica.

## 11. Boundary futuro de IAM do runtime da aplicação

Ainda não existe compute principal da aplicação. Gate 7.8 documenta o entitlement futuro antes de criar uma role.

### Entitlement de retrieval

O runtime provado precisa apenas de:

```text
Action:   bedrock:Retrieve
Resource: arn:aws:bedrock:us-east-1:487757851499:knowledge-base/BTVJ2PBR2A
```

O caminho provado não requer `RetrieveAndGenerate`, administração de data source/Knowledge Base ou acesso direto a S3 Vectors.

### Entitlement de síntese

A aplicação chama `Converse` não-streaming. A autorização correspondente usa `bedrock:InvokeModel`.

Inference profile US Geographic selecionado:

```text
us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Para requests com origem em `us-east-1`, a AWS documenta destinos:

```text
us-east-1
us-east-2
us-west-2
```

A future role precisa de `bedrock:InvokeModel` sobre:

```text
inference-profile ARN exato em us-east-1
foundation-model ARN exato do Claude Haiku 4.5 em us-east-1
foundation-model ARN exato do Claude Haiku 4.5 em us-east-2
foundation-model ARN exato do Claude Haiku 4.5 em us-west-2
```

As permissões nos foundation models devem ser condicionadas ao `bedrock:InferenceProfileArn` exato.

`bedrock:InvokeModelWithResponseStream` permanece ausente porque o contrato da Phase 7 é não-streaming.

Veja ADR 0024.

## 12. Boundary de cost accounting

Phase 7 separa os drivers de custo:

```text
embedding em ingestão
S3 Vectors storage
S3 Vectors writes
query embedding
S3 Vectors query request fee
S3 Vectors data processed
S3 Vectors data returned
synthesis input tokens
synthesis output tokens
```

Primeiro run grounded de quatro casos:

```text
model input:             $0.0129074
model output:            $0.0035475
model subtotal:          $0.0164549
4 S3 Vectors requests:   $0.0000100
computable total:        $0.0164649
```

Isso não é apresentado como bill completo porque query embedding e S3 Vectors processed/returned não aparecem na evidência de runtime.

Cost Explorer/billing continuam sendo a fonte de reconciliação da conta real.

## 13. Boundary de observabilidade

A evidência de laboratório/runtime captura:

```text
provider request IDs
retrieval result counts/ranks/scores
canonical provenance hashes
context/catalog/request/result hashes
model/profile identity
input/output/total/cache tokens
Bedrock latency
client elapsed time
SDK retry count
stop reason
answer/abstention decision
claim/citation mappings
human support-judgment hashes
```

Phase 7 não afirma:

```text
production SLOs
métricas contínuas do runtime RAG implantado
end-user trace correlation
production alert thresholds
distribuições de custo/latência em alto volume
```

Isso exige runtime implantado e workload medido.

## 14. Boundary de entrada da Phase 8

Hybrid Retrieval não pode simplesmente concatenar rows do Athena com chunks vetoriais.

Phase 8 começa por um contrato explícito de routing entre classes de evidência:

```text
fatos estruturados de vulnerabilidade/risco
 -> autoridade estruturada determinística

orientação explicativa/remediação
 -> evidência semântica limitada

resposta combinada
 -> proveniência explícita por classe
 -> sem authority laundering
```

Critérios de entrada:

```text
1. baseline da Gate 7.7 permanece imutável
2. route eligibility é explícita e tipada
3. structured truth continua autoritativa para vulnerabilidade/risco
4. semantic evidence permanece explicativa/remediação
5. evidência combinada preserva proveniência por classe
6. falta de evidência obrigatória produz partial/unsupported explícito
7. qualidade, custo, falhas e observabilidade continuam mensuráveis separadamente
8. novos serviços/rerankers/search modes exigem justificativa medida
```

Phase 8 inicia offline-first pelo contrato de routing/authority antes de adicionar recurso AWS ou model call.

## 15. Não adoções deliberadas no closeout da Phase 7

- sem OpenSearch Serverless antes de requisito medido;
- sem reranker antes de hipótese de qualidade/groundedness medida;
- sem keyword/vector hybrid apenas porque a feature existe;
- sem runtime cache antes de requisitos de reuse/invalidation;
- sem application IAM role antes de existir compute real;
- sem citações canônicas geradas pelo provider;
- sem similarity threshold pós-hoc derivado do fixture pequeno;
- sem prompt tuning dentro do baseline congelado da Gate 7.7.

## 16. Architecture records

ADRs atuais relevantes:

```text
0020 No unrestricted text-to-SQL
0021 Bounded Bedrock semantic-query planner
0022 Customer-managed Bedrock KB with S3 Vectors
0023 Bounded Bedrock knowledge synthesis
0024 Phase 7 future application runtime IAM boundary
```

Evidência do closeout:

```text
labs/phase-7-gate-7-8-closeout.md
```
