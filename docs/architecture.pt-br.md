# Arquitetura do OpsLens

_Última atualização: 2026-09-03_

Este documento é o baseline arquitetural acumulado após a conclusão da **Phase 5 — Risk Prioritization Engine**.

O próximo boundary do roadmap é a **Phase 6 — Semantic Query Layer**.

## 1. Propósito

OpsLens é uma plataforma open source de software supply chain e threat intelligence construída na AWS.

O objetivo do produto é:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência exata prova isso e quais findings devo priorizar?

A arquitetura estabelece deliberadamente evidência determinística confiável e enforcement de política antes de adicionar raciocínio semântico, generativo ou agentic.

Invariante central:

> **Agents reason. Code verifies evidence.**

Boundaries permanentes adicionais:

> **READ, NEVER EXECUTE third-party repository code.**

> **Repository Risk != Runtime Exposure.**

## 2. Princípios arquiteturais permanentes

Salvo mudança explícita por ADR:

- evidência bruta de terceiros é preservada antes de enrichment ou interpretação;
- fatos determinísticos permanecem autoritativos;
- versões exatas da fonte e hashes de conteúdo participam da proveniência;
- package identity normalization permanece determinística;
- parsing de versão e vulnerable-range matching permanecem determinísticos;
- aplicabilidade de vulnerabilidade permanece determinística;
- reconciliação CVE/GHSA/NVD permanece determinística;
- evidência KEV/EPSS/CVSS permanece determinística e source-preserving;
- avaliação da política de risco permanece determinística;
- validação de semantic query e compilação SQL permanecem determinísticas;
- validação de evidência permanece determinística;
- enforcement de limites de execução/tools/custo permanece determinístico;
- LLMs poderão classificar, planejar, rotear, sintetizar e explicar sobre evidência validada;
- LLMs não substituem aplicabilidade, evidência de fonte nem enforcement da política de risco;
- planejamento em linguagem natural nunca recebe autoridade SQL irrestrita;
- conteúdo de repositório de terceiro é dado não confiável para inspeção, nunca código a executar;
- Repository Risk não é Runtime Exposure;
- evidência ausente não é convertida silenciosamente em evidência benigna;
- entrega duplicada é esperada e replay precisa ser seguro;
- divergências de schema, proveniência, autoridade ou evidência exata falham fechado;
- IAM usa least privilege e separação de responsabilidades;
- serviços AWS entram somente para requisitos concretos;
- custo e observabilidade são requisitos arquiteturais;
- um ambiente `dev` real é preferido a ambientes fictícios de portfólio.

## 3. Forma atual do sistema

O sistema implementado possui agora quatro camadas determinísticas.

```text
THREAT INTELLIGENCE DATA
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
        |
        v
DETERMINISTIC CORRELATION
PyPI identity + PEP 440 + GHSA applicability + CVE/NVD evidence
        |
        v
REPOSITORY INTELLIGENCE
snapshot público GitHub imutável + uv.lock inerte + findings determinísticos
        |
        v
RepositoryAnalysisResult
        |
        v
RISK PRIORITIZATION
Risk Policy v1 versionada + factor evidence + ranking determinístico
        |
        v
RiskPrioritizationResult
```

A Phase 6 adicionará uma camada de planejamento semântico **acima** dessas autoridades:

```text
pergunta em linguagem natural
 -> planner Bedrock
 -> SemanticQuery tipada
 -> validação determinística
 -> compilador SQL determinístico
 -> Athena limitado
```

O planner não receberá autoridade direta para SQL arbitrário.

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

Existe apenas um ambiente real: `dev`.

A administração humana usa credenciais temporárias do IAM Identity Center. O GitHub Actions assume roles AWS por OIDC; access keys persistentes não são armazenadas no GitHub.

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

As Phases 3, 4 e 5 não adicionaram recursos AWS nem novas permissões IAM.

## 5. Threat Intelligence Data Lake — Phase 2

A Phase 2 preserva autoridade source-local. NVD, KEV, EPSS e GHSA não são achatados em um registro universal com perda de semântica.

### 5.1 FIRST EPSS

```text
FIRST EPSS
 -> EventBridge Scheduler
 -> Lambda de ingestão EPSS
 -> S3 Bronze imutável
 -> transformer Silver determinístico
 -> Parquet
 -> Glue: opslens_dev.epss_scores
 -> Athena
```

A seleção temporal é explícita via snapshot date.

A relação Silver canônica inclui o caminho forward e o intervalo histórico concluído:

```text
2021-04-14 .. 2026-08-13
```

O histórico é fixado em um commit específico do archive e preserva evidência exata da fonte. Datas ausentes na fonte permanecem explícitas.

### 5.2 CISA KEV

```text
CISA KEV JSON
 -> ingestão limitada
 -> Bronze imutável
 -> verificação por versão exata
 -> normalização Silver determinística
 -> Parquet
 -> Glue: opslens_dev.kev_entries
 -> Athena
```

Ausência KEV só é significativa contra um snapshot completo e validado.

### 5.3 NVD / CVE

```text
NVD yearly feeds                  NVD CVE API 2.0
       |                                  |
       v                                  v
Bootstrap Bronze                  Incremental Bronze
       |                                  |
       +----------> Silver versionado <---+
                          |
                          v
                    Silver COMPLETE
                          |
                          v
                watermark autoritativo
                          |
                          v
              projeção analítica permanente
                          |
                          v
                 Glue + Athena limitado
```

Invariante de autoridade:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

O analytics projector é downstream-only e não pode avançar o estado autoritativo do NVD.

### 5.4 GitHub Security Advisories

```text
GitHub Global Security Advisories REST API
 -> páginas Bronze reviewed-only + COMPLETE
 -> identidade exata de conteúdo
 -> normalização determinística
 -> Silver imutável por advisory version
 -> Silver COMPLETE
 -> Glue: opslens_dev.ghsa_advisory_versions
 -> Athena
```

Identidades importantes permanecem distintas:

```text
sync_id                       janela lógica da fonte
attempt_id                    observação física exata
observed_advisory_version_id  identidade exata do conteúdo
vulnerability_entry_id        ocorrência exata da vulnerabilidade
```

A evidência GHSA de package/range/fix continua source-local mesmo quando um alias CVE é observado independentemente pelo NVD.

## 6. Vulnerability Correlation Engine — Phase 3

A Phase 3 está concluída para o escopo **PyPI v1**.

### 6.1 Autoridade de identidade

```text
alias de ecossistema da fonte
 -> ecossistema canônico: pypi
package name
 -> normalização PyPA
version
 -> PEP 440 Version
package + version
 -> purl canônico pkg:pypi/...
```

Grafia original e identidade canônica são preservadas.

### 6.2 Autoridade de vulnerable range

Operadores GHSA suportados:

```text
=  <  <=  >  >=
```

Cláusulas separadas por vírgula são conjunções determinísticas.

Estados:

```text
affected
not_affected
unsupported
```

Semânticas inválidas/não suportadas nunca viram `not_affected`.

`first_patched_version` é evidência de remediação e não substitui o range publicado.

### 6.3 Reconciliação GHSA/NVD

A afirmação CVE do GitHub e a versão exata observada no NVD permanecem registros independentes.

```text
no_github_cve
github_asserted_only
nvd_observed
nvd_rejected
```

Um registro NVD compatível cria uma aresta de evidência; não substitui a proveniência GHSA.

### 6.4 Identidade de correlação

```text
correlation:v1@sha256:<digest>
```

Regra permanente:

> **Nenhum LLM decide aplicabilidade de vulnerabilidade.**

## 7. Repository Intelligence — Phase 4

A Phase 4 analisa um repositório público suportado do GitHub sem executar seu código.

Escopo v1:

```text
provider:             repositórios públicos GitHub
evidência:            uv.lock na raiz
packages suportados:  registros PyPI canônicos
operação de rede:     GitHub REST read only e limitado
execução de código:   nunca
```

### 7.1 Autoridade imutável

A autoridade combina o repository ID numérico do GitHub com commit SHA exato.

```text
owner/name/ref
 -> metadata canônica do GitHub
 -> commit SHA exato
 -> tree SHA exato
 -> snapshot imutável
```

Depois da resolução, refs móveis permanecem somente como proveniência.

### 7.2 Transporte GitHub limitado

O boundary de aquisição usa HTTPS para host fixo, apenas GET, timeouts e response bytes limitados, sem redirect, sem auto-retry loop e sem URL absoluta arbitrária fornecida pelo caller.

### 7.3 `uv.lock` imutável

Apenas `uv.lock` na raiz é allowlisted no v1.

O arquivo é lido no `snapshot.commit_sha`, tratado como bytes inertes, limitado a 1 MiB, verificado contra Git blob SHA-1 e hash SHA-256 independente.

Nenhum `uv`, package manager, build, test, Dockerfile, setup hook, workflow ou script é executado.

### 7.4 Parsing e normalização determinísticos

O parser usa `tomllib` da stdlib sobre bytes previamente verificados, preserva source indexes e resolution markers, limita 5.000 registros e mantém source kinds não suportados de forma explícita.

Registros PyPI suportados são normalizados somente pela autoridade da Phase 3.

### 7.5 Repository vulnerability findings

```text
locked dependency
 + ocorrência GHSA exata
 -> canonical package join
 -> range evaluation determinística
 -> affected | not_affected | unsupported
```

Somente `affected` emite finding.

```text
repository-finding:v1@sha256:<digest>
```

O finding prova repository-risk evidence no snapshot imutável; não prova presença ou explorabilidade em runtime.

### 7.6 Enrichment NVD/CVSS

Findings afetados podem receber evidência NVD exata sem alterar applicability truth.

Todas as observações CVSS suportadas são preservadas. A Phase 4 propositalmente não escolhe score preferred/highest/merged.

### 7.7 Enrichment CISA KEV

Estados:

```text
present
absent
cve_unavailable
```

`absent` só é válido após provar non-membership em snapshot completo validado.

### 7.8 Enrichment FIRST EPSS

Estados:

```text
score_present
score_absent
cve_unavailable
```

A evidência vem de exatamente um snapshot atual ou histórico explicitamente selecionado. Não existe seleção automática de `latest`, max-score, trend ou nearest-date.

### 7.9 Projeção final

`RepositoryAnalysisResult` deriva uma projeção consumer-facing da cadeia totalmente validada.

Identidades finais:

```text
repository-analysis-finding:v1@sha256:<digest>
repository-analysis:v1@sha256:<digest>
```

A Phase 4 não atribui prioridade nem runtime exposure.

## 8. Risk Prioritization Engine — Phase 5

A Phase 5 introduz uma **autoridade downstream de política**, separada dos fatos da Phase 4.

### 8.1 Boundary arquitetural

```text
RepositoryAnalysisResult
 -> application projection
 -> RiskFindingInput
 -> Risk Policy v1 pura e determinística
 -> RiskFactorContribution[]
 -> priority score + tier
 -> completeness / review_required
 -> ranking determinístico
 -> RiskPrioritizationResult
```

O domínio `risk_policy` não faz chamadas de rede e não conhece adapters AWS, GitHub, NVD, KEV ou EPSS.

### 8.2 Risk Policy v1

Máximo: `100`.

```text
KEV presente                         +40

EPSS >= 0.70                         +30
EPSS >= 0.30 e < 0.70               +20
EPSS >= 0.10 e < 0.30               +10
EPSS < 0.10                            +0

maior CVSS suportado >= 9.0           +20
maior CVSS suportado >= 7.0           +10
maior CVSS suportado >= 4.0            +5
maior CVSS suportado < 4.0              +0

fixed version conhecida               +10
```

Priority tiers:

```text
P0  score >= 80
P1  score >= 60 e < 80
P2  score >= 30 e < 60
P3  score < 30
```

Esse valor é explicitamente um **priority score do OpsLens**.

Não é probabilidade de exploração, substituto de EPSS/CVSS/KEV nem score de runtime exposure.

### 8.3 Agregação CVSS da política

A Phase 4 preserva todas as observações NVD CVSS suportadas.

A Risk Policy v1 introduz a agregação downstream:

```text
max supported observed CVSS base score
```

O valor selecionado existe apenas na evidência da política. As observações originais permanecem intactas.

Se existir uma família CVSS futura não suportada, o v1 não atribui pontos CVSS e marca a avaliação como `partial/review_required` em vez de fingir completude.

### 8.4 Evidência ausente

```text
KEV ausente em catálogo completo      -> evidência negativa completa
EPSS ausente em snapshot completo     -> evidência negativa completa
CVE indisponível                      -> partial / review_required
sem CVSS suportado                    -> partial / review_required
família CVSS não suportada            -> partial / review_required
```

Evidência ausente não ganha pontos fabricados, mas score baixo com evidência parcial também não pode ser apresentado como conclusão completa de baixo risco.

### 8.5 Fixed version

Uma first patched version conhecida vale `+10` como actionability bonus explícito.

Isso não altera aplicabilidade. Ausência de fix conhecido não prova que remediação é impossível.

### 8.6 Identidades da política

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

Mesma evidência + mesma política reproduz as mesmas identidades e prioridade.

### 8.7 Ranking

```text
1. priority_score descending
2. analysis_finding_id ascending
```

O tie breaker serve apenas para reprodutibilidade e não possui semântica de risco.

### 8.8 Fatores excluídos do v1

```text
direct vs transitive
runtime deployment presence
runtime package activation
reachability
internet exposure
business criticality
asset criticality
```

Uma versão futura da política só poderá usá-los depois que existirem contratos determinísticos upstream.

## 9. Evidência e cache

Identidades content-addressed incluem a threat intelligence selecionada.

```text
mesmo commit
 + evidência temporal KEV/EPSS diferente
 -> RepositoryAnalysisResult potencialmente diferente
 -> RiskPrioritizationResult potencialmente diferente
```

O commit sozinho não é cache key segura.

Nenhum backend de cache foi criado porque ainda não existe workload medido que justifique custo de storage, invalidação, IAM, observabilidade, failure recovery e retenção.

## 10. Boundaries de segurança

```text
Administração humana
 -> AWS IAM Identity Center

GitHub Actions
 -> OIDC
 -> deployment role
 -> mudanças Terraform

Threat-intelligence runtimes
 -> roles source-specific least privilege

Repository Intelligence
 -> autoridade pública GitHub read only limitada
 -> dados inertes
 -> zero execução de código de terceiros

Risk Policy
 -> somente evidência determinística da Phase 4
 -> sem autoridade de rede ou modelo
```

Uma prioridade determinística de repositório continua sendo um resultado de **Repository Risk**. Runtime Exposure permanece domínio separado para fase futura.

## 11. Disciplina de custo

- sem Glue crawler onde schemas explícitos bastam;
- sem DynamoDB/cache antes de reuse medido;
- sem Step Functions sem semântica real de workflow;
- sem Iceberg até existir necessidade;
- sem vector database antes de retrieval;
- sem chamada Bedrock na aplicabilidade ou priorização;
- workgroup Athena dev com cutoff de 10 MiB.

Custo AWS incremental da Phase 5: `$0`.

## 12. Quality gates

Slices determinísticos dedicados:

```text
Correlation
Repository Intelligence
Risk Policy
```

Closeout da Phase 5:

```text
Risk Policy Ruff:                 PASS
Risk Policy Pyright:              0 errors / 0 warnings
Risk Policy pytest:               31 passed
Repository Intelligence pytest:   174 passed
Correlation pytest:               116 passed
```

Mudanças AWS usam adicionalmente Terraform fmt/validate, TFLint, Checkov, review de plano canônico, verificação de deployment e convergência pós-apply.

## 13. ADRs até a Phase 5

```text
0001 Terraform state strategy
0002 GitHub Actions OIDC
0003 AWS Region strategy
0004 NVD ingestion/versioning
0005 GHSA source/synchronization
0006 GHSA Silver content identity
0007 GHSA runtime credentials/retry
0008 PyPI correlation semantics
0009 immutable public repository snapshot
0010 bounded read-only GitHub REST transport
0011 immutable uv.lock evidence
0012 deterministic uv.lock parser
0013 Phase 3 PyPI normalization bridge
0014 deterministic repository vulnerability findings
0015 repository NVD/CVSS enrichment
0016 repository KEV snapshot enrichment
0017 repository EPSS snapshot enrichment
0018 repository analysis result projection
0019 deterministic Risk Policy v1
```

`docs/adr/README.md` é o índice canônico.

## 14. Não objetivos no boundary atual

Ainda não estão implementados:

- private repositories;
- manifests arbitrários;
- ecossistemas além de PyPI v1;
- runtime exposure;
- reachability;
- business/asset criticality;
- unrestricted text-to-SQL;
- RAG/vector retrieval;
- remediation autônoma;
- autoridade agentic sobre evidência determinística;
- MCP arbitrário.

## 15. Próximo boundary — Phase 6 Semantic Query Layer

```text
Pergunta do usuário
 -> Amazon Bedrock planner
 -> SemanticQuery tipada
 -> validator determinístico
 -> compilador SQL determinístico
 -> workgroup Athena read only e limitado
 -> evidência estruturada
```

Guardrail permanente:

> **No unrestricted text-to-SQL.**

O modelo poderá propor uma intenção semântica tipada. Código da aplicação será dono de allowlists, validação, compilação SQL, limites e autoridade de execução.

Antes de implementar a Phase 6, a documentação oficial atual do Amazon Bedrock e Athena deverá ser verificada para APIs, modelos disponíveis, IAM, limites e pricing.

O primeiro gate da Phase 6 deve congelar uma pergunta factual estreita, o contrato tipado de query e o boundary do compilador antes de API/UI/RAG/agentes.
