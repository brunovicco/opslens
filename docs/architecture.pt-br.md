# Arquitetura do OpsLens

_Última atualização: 2026-09-03_

Este documento é o baseline arquitetural acumulado após a conclusão da **Phase 4 — Repository Intelligence**.

O próximo boundary de autoridade é a **Phase 5 — Risk Prioritization Engine**.

## 1. Propósito

OpsLens é uma plataforma open source de software supply chain e threat intelligence construída na AWS.

O objetivo do produto é:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência exata prova isso e como esses findings devem ser priorizados no futuro?

A arquitetura estabelece deliberadamente evidência determinística confiável antes de adicionar raciocínio semântico ou agentic.

Invariante central:

> **Agents reason. Code verifies evidence.**

## 2. Princípios arquiteturais permanentes

Salvo mudança explícita por ADR:

- evidência bruta de terceiros é preservada antes de enrichment ou interpretação;
- fatos determinísticos permanecem autoritativos;
- versões exatas da fonte e hashes de conteúdo participam da proveniência;
- normalização de package identity permanece determinística;
- parsing de versões e avaliação de ranges permanecem determinísticos;
- aplicabilidade de vulnerabilidade permanece determinística;
- reconciliação CVE/GHSA/NVD permanece determinística;
- lookup de KEV/EPSS/CVSS permanece determinístico;
- avaliação de política de risco permanecerá determinística;
- validação de semantic query e compilação SQL permanecem determinísticas;
- validação de evidência permanece determinística;
- limites de execução/tools/custo permanecem determinísticos;
- LLMs poderão depois classificar, planejar, rotear, sintetizar e explicar sobre evidência validada;
- planejamento em linguagem natural nunca recebe autoridade SQL irrestrita;
- código de repositórios de terceiros é dado não confiável para inspeção, nunca código a executar;
- Repository Risk não é Runtime Exposure;
- entrega duplicada é esperada e replay precisa ser seguro;
- divergências de schema, proveniência, autoridade ou evidência exata falham fechado;
- IAM usa least privilege e separação de responsabilidades;
- serviços AWS entram somente para requisitos concretos;
- custo e observabilidade são requisitos arquiteturais;
- um ambiente `dev` real é preferido a ambientes fictícios de portfólio.

## 3. Forma atual do sistema

O sistema implementado possui três camadas determinísticas.

```text
THREAT INTELLIGENCE DATA
NVD + CISA KEV + FIRST EPSS + GitHub Security Advisories
        |
        v
DETERMINISTIC CORRELATION
PyPI identity + PEP 440 + GHSA range + CVE/NVD alias evidence
        |
        v
REPOSITORY INTELLIGENCE
snapshot público GitHub imutável + uv.lock inerte + findings determinísticos
        |
        v
RepositoryAnalysisResult
```

A Phase 5 adicionará uma quarta camada:

```text
RepositoryAnalysisResult
        |
        v
Risk Policy v1
        |
        v
decisão determinística e versionada de prioridade
```

Risk Policy não se torna nova fonte de verdade de aplicabilidade.

## 4. Fundação AWS

```text
environment:             dev
primary workload Region: us-east-1
IaC:                     Terraform
human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
```

Existe apenas um ambiente real: `dev`.

A administração humana usa credenciais temporárias do IAM Identity Center. GitHub Actions assume roles AWS via OIDC; access keys persistentes não são armazenadas no GitHub.

Layout Terraform:

```text
infra/
  bootstrap/
  environments/
    dev/
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

## 5. Threat Intelligence Data Lake — Phase 2

A Phase 2 preserva autoridade source-local. NVD, KEV, EPSS e GHSA não são achatados em um registro universal com perda de semântica.

### 5.1 FIRST EPSS atual

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

Seleção temporal é explícita via snapshot date.

### 5.2 EPSS histórico

A autoridade histórica em bulk é fixada em um commit específico do archive e preenche a relação Silver canônica do EPSS antes do boundary do caminho forward.

Intervalo congelado:

```text
2021-04-14 .. 2026-08-13
```

O caminho histórico preserva bytes exatos da fonte, hash da fonte, coordenadas Git do archive, S3 VersionIds, semântica de model era, saída Silver determinística e evidência de completion.

Nenhuma data ausente na fonte é substituída silenciosamente.

### 5.3 CISA KEV

```text
CISA KEV JSON
 -> ingestão limitada
 -> Bronze imutável
 -> verificação por versão exata da fonte
 -> normalização Silver determinística
 -> Parquet
 -> Glue: opslens_dev.kev_entries
 -> Athena
```

Ausência KEV só é significativa contra um snapshot completo e validado.

### 5.4 NVD / CVE

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

O analytics projector é estritamente downstream e não pode avançar o estado autoritativo do NVD.

### 5.5 GitHub Security Advisories

```text
GitHub Global Security Advisories REST API
 -> páginas Bronze reviewed-only + COMPLETE
 -> identidade exata do conteúdo do advisory
 -> normalização determinística
 -> um Parquet imutável de uma linha por versão observada
 -> Silver COMPLETE
 -> Glue: opslens_dev.ghsa_advisory_versions
 -> Athena
```

Identidades importantes permanecem separadas:

```text
sync_id                       janela lógica da fonte
attempt_id                    observação física exata
observed_advisory_version_id  identidade exata do conteúdo
vulnerability_entry_id        ocorrência exata da vulnerabilidade
```

A evidência GHSA de package/range/fix continua source-local mesmo quando um alias CVE também é observado no NVD.

## 6. Vulnerability Correlation Engine — Phase 3

A Phase 3 está concluída para o escopo explicitamente suportado **PyPI v1**.

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

A grafia original da fonte e a identidade canônica são preservadas.

### 6.2 Autoridade de vulnerable range

Operadores GHSA suportados:

```text
=  <  <=  >  >=
```

Cláusulas separadas por vírgula são conjunções determinísticas.

Estados de resultado:

```text
affected
not_affected
unsupported
```

Semânticas inválidas/não suportadas nunca colapsam para `not_affected`.

`first_patched_version` é apenas evidência de remediação; não substitui o vulnerable range publicado.

### 6.3 Boundary GHSA/NVD

A afirmação CVE do GitHub e a versão exata observada no NVD permanecem registros independentes.

Estados de reconciliação incluem:

```text
no_github_cve
github_asserted_only
nvd_observed
nvd_rejected
```

Um registro NVD compatível cria uma aresta de evidência; não substitui a proveniência GHSA.

### 6.4 Identidade da evidência de correlação

O registro final da Phase 3 usa Canonical JSON e content addressing SHA-256:

```text
correlation:v1@sha256:<digest>
```

O registro contém identidade instalada, resultado de aplicabilidade, cláusulas de range, fix evidence, coordenadas GHSA exatas e coordenadas NVD exatas quando fornecidas.

Regra permanente:

> **Nenhum LLM decide aplicabilidade de vulnerabilidade.**

## 7. Repository Intelligence — Phase 4

A Phase 4 analisa um repositório público suportado do GitHub sem executar seu código.

Escopo v1 atual:

```text
provider:             repositórios públicos GitHub
evidência:            uv.lock
packages suportados:  registros PyPI canônicos
operação de rede:     GitHub REST read only e limitado
execução de código:   nunca
```

### 7.1 Identidade imutável do repositório

A identidade usa o repository ID numérico do GitHub mais coordenadas da fonte. O ref solicitado é resolvido para commit SHA e tree SHA exatos.

```text
owner/name/ref
 -> metadata GitHub
 -> commit SHA exato
 -> tree SHA exato
 -> snapshot_id imutável
```

Formato:

```text
github:<repository_id>@<40-char-commit-sha>
```

Depois da resolução, branch names móveis deixam de ser autoridade de evidência.

### 7.2 Transporte GitHub limitado

O transporte é propositalmente estreito:

- host fixo da API GitHub;
- apenas GET;
- timeouts limitados;
- response bytes limitados;
- sem expansão de autoridade via redirect;
- sem retry automático ilimitado;
- falhas explícitas de rate limit;
- sem caminho genérico para execução de URL remota.

### 7.3 Evidência imutável do `uv.lock`

Apenas o path allowlisted `uv.lock` é aceito no v1.

A aquisição sempre usa o commit exato, nunca o ref móvel solicitado.

A evidência verifica:

```text
path/type/name/encoding/size do GitHub
payload Base64
Git blob SHA-1 = sha1("blob <len>\0" + bytes)
SHA-256 independente do OpsLens
limite de 1 MiB
```

Os bytes permanecem dados inertes.

### 7.4 Parsing determinístico do lockfile

O parser usa `tomllib` da stdlib sobre bytes previamente verificados.

Preserva:

- schema/revision do lock;
- `requires-python`;
- resolution markers globais e por package;
- source record indexes zero-based;
- registros duplicados de marker forks;
- source kinds não suportados de forma explícita.

Ele não executa `uv`, não instala dependências e não trata resolution markers como verdade de deployment.

### 7.5 Bridge de normalização da Phase 3

Registros PyPI suportados do lock são normalizados somente pela autoridade existente da Phase 3.

Cada registro PyPI é contabilizado exatamente uma vez como:

```text
normalized
ou
unsupported com motivo explícito
```

### 7.6 Repository vulnerability findings

Dependências normalizadas são ligadas a ocorrências GHSA PyPI exatas por package identity canônica antes da avaliação de aplicabilidade.

```text
locked dependency
 + ocorrência GHSA exata
 -> canonical package join
 -> range evaluator da Phase 3
 -> assessment
 -> affected repository finding quando aplicável
```

Evidência unsupported permanece explícita e nunca vira falso negativo.

Um finding positivo prova repository-risk evidence para o snapshot imutável do lockfile; não prova presença nem explorabilidade no runtime.

Findings base usam evidência canônica content-addressed:

```text
repository-finding:v1@sha256:<digest>
```

### 7.7 Enrichment NVD/CVSS

Um finding já afetado pode receber evidência NVD exata sem alterar a verdade de aplicabilidade.

Propriedades:

- a ocorrência GHSA exata é validada novamente antes do alias reconciliation;
- zero ou uma versão NVD exata é fornecida por CVE;
- candidatos duplicados falham fechado em vez de escolher `latest`;
- métricas CVSS são rederivadas do conteúdo canônico exato do NVD;
- todas as observações CVSS suportadas são preservadas;
- nenhum score preferred/highest/merged é escolhido;
- estado NVD rejected permanece distinto.

### 7.8 Enrichment CISA KEV

O enrichment KEV consome um snapshot completo e imutável do catálogo, verifica novamente o hash da fonte e reexecuta o transformer Silver determinístico sobre o catálogo inteiro.

Estados exatos:

```text
present
absent
cve_unavailable
```

`absent` exige CVE afirmado pelo GitHub mais não-membership comprovado no snapshot completo validado.

### 7.9 Enrichment FIRST EPSS

O enrichment EPSS consome exatamente um snapshot atual ou histórico explicitamente selecionado.

Estados exatos:

```text
score_present
score_absent
cve_unavailable
```

Não existe seleção automática de `latest`, nearest-date, max-score, trend ou múltiplas datas dentro do domínio de evidência.

EPSS histórico v1 preserva metadata/percentile indisponíveis em vez de fabricar valores modernos.

### 7.10 Projeção final

`RepositoryAnalysisResult` aceita apenas a cadeia final já validada de enrichment EPSS e deriva uma projeção consumer-facing.

Pode expor:

```text
dependency
installed version
purl
GHSA/CVE
matched range e clauses
fixed version
todas as observações CVSS
evidência KEV
evidência EPSS
referências exatas da cadeia
```

Não expõe risk score, priority nem runtime-exposure assertion.

Identidades finais:

```text
repository-analysis-finding:v1@sha256:<digest>
repository-analysis:v1@sha256:<digest>
```

## 8. Cadeia de evidência e boundary de cache

A identidade final muda quando qualquer evidência autoritativa selecionada muda.

Exemplo intencional:

```text
mesmo commit do repositório
 + snapshot EPSS diferente
 -> analysis_id diferente
```

Portanto, o commit do repositório sozinho não é uma cache key segura.

Reuse futuro deve usar a identidade content-addressed completa. A Phase 4 adiou DynamoDB/ElastiCache/outro cache até um workload medido justificar:

- custo de storage;
- semântica de invalidação;
- superfície IAM;
- observabilidade;
- failure recovery;
- política de retenção.

## 9. Boundaries de segurança

```text
Administração humana
 -> AWS IAM Identity Center

GitHub Actions
 -> OIDC
 -> deployment role
 -> mudanças AWS gerenciadas por Terraform

Runtimes de threat intelligence
 -> roles least-privilege específicas por fonte

Repository Intelligence
 -> autoridade de rede read-only no GitHub público
 -> somente evidência inerte
 -> nenhuma execução de código de terceiros
```

Um finding determinístico continua sendo observação de repositório. Runtime exposure é um domínio independente posterior.

## 10. Disciplina de custo

Exemplos atuais:

- sem Glue crawler onde schemas explícitos bastam;
- sem cache DynamoDB antes de reuse medido;
- sem Step Functions sem semântica real de workflow;
- sem requisito Iceberg até aqui;
- sem vector database antes de retrieval;
- sem chamada Bedrock para aplicabilidade/findings determinísticos;
- Athena dev com cutoff de 10 MiB por scan.

## 11. Quality gates

Mudanças determinísticas de código usam CI escopado para impedir que código novo se esconda atrás de findings históricos.

Gates atuais de correlation/repository:

```text
uv lock --check
uv sync --frozen
Ruff
strict Pyright
Pytest
```

Closeout da Phase 4:

```text
Repository Intelligence pytest: 174 passed
Correlation pytest:             116 passed
Pyright:                         0 errors / 0 warnings
Ruff:                            PASS
```

Mudanças com AWS também usam Terraform fmt/validate, TFLint, Checkov, revisão de plano canônico, verificação de deployment e convergence checks pós-apply.

## 12. Boundary da Phase 5

A Phase 5 introduz **Risk Policy v1** sobre a evidência final da Phase 4.

Fatores candidatos:

```text
affected status
KEV
EPSS
CVSS
fix availability
direct/transitive quando disponível
futura runtime evidence
evidence completeness
```

Invariantes requeridos:

- mesma evidência + mesma policy version => mesma prioridade;
- explicação por fator é reconstruível;
- policy version é registrada;
- evidência ausente/unsupported tem semântica explícita;
- LLM não é necessário para ranking;
- risk policy não pode reescrever aplicabilidade nem source evidence;
- Repository Risk permanece distinto de Runtime Exposure.

Esse boundary começa somente depois da conclusão do sistema de evidência da Phase 4.
