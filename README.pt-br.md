<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Inteligência Agentic de Cloud e Software Supply Chain na AWS

**Threat Intelligence · Software Supply Chain · Evidência Determinística · AWS Serverless · Automação de Segurança**

</div>

OpsLens é uma plataforma open source de inteligência para software supply chain construída na AWS.

Ela foi projetada para responder:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades representam risco material, por quê e o que devo fazer a respeito?

O projeto constrói primeiro evidência determinística, proveniência, correlação, limites de least privilege, observabilidade, recuperação de falhas e controles de custo. Raciocínio generativo e agentic entram depois dessas fundações.

> **Agents reason. Code verifies evidence.**

## Status

| Fase | Escopo | Status |
| --- | --- | --- |
| Phase 0 | AWS Foundation | ✅ Concluída |
| Phase 1 | EPSS Vertical Slice | ✅ Concluída |
| Phase 2.1 | CISA KEV Bronze Ingestion | ✅ Concluída |
| Phase 2.2 | CISA KEV Silver + Analytics | ✅ Concluída |
| Phase 2.3A–2.3G | NVD / CVE Bronze, Silver, Watermark, Glue + Athena | ✅ Concluída |
| Phase 2.4 | GitHub Security Advisories | 🚧 Em andamento — runtime Silver 2.4D concluído; Glue/Athena 2.4E é o próximo gate |
| Phase 2.5 | Expansão histórica do EPSS | ⏳ Não iniciada |
| Phase 3 | Vulnerability Correlation Engine | ⏳ Não iniciada |

O caminho determinístico de evidência do NVD está completo desde a ingestão imutável da fonte até Silver versionado, promoção do watermark autoritativo, projeção analítica permanente, AWS Glue e consultas Athena com custo limitado. O caminho GHSA agora está concluído até a ingestão Bronze de advisories reviewed e o runtime Silver imutável de versões de advisory, com proveniência por VersionId exato do S3 e evidência COMPLETE segura para replay. O milestone atual do roadmap é a Phase 2.4E — GHSA Glue/Athena Analytics.

## Arquitetura atual

O OpsLens possui hoje quatro caminhos implementados de threat intelligence.

### FIRST EPSS

```text
FIRST EPSS
    |
    v
EventBridge Scheduler
    |
    v
EPSS Ingestion Lambda
    |
    v
S3 Bronze
bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
    |
    v
S3 ObjectCreated
    |
    v
EPSS Silver Lambda
    |
    v
S3 Silver / Parquet
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
    |
    v
AWS Glue Data Catalog
opslens_dev.epss_scores
    |
    v
Amazon Athena
```

### CISA KEV

```text
CISA KEV JSON
    |
    v
EventBridge Scheduler
    |
    v
KEV Ingestion Lambda
    |
    +--> fetch HTTP limitado
    +--> validação do contrato da fonte
    +--> proveniência SHA-256
    +--> S3 PutObject condicional
    |
    v
S3 Bronze
bronze/kev/snapshot_date=YYYY-MM-DD/known_exploited_vulnerabilities.json
    |
    v
S3 ObjectCreated:Put
    |
    v
KEV Silver Lambda
    |
    +--> leitura por VersionId exato
    +--> verificação evento/S3
    +--> normalização determinística
    +--> serialização Parquet tipada
    +--> PutObject Silver condicional
    |
    v
S3 Silver / Parquet
silver/kev/snapshot_date=YYYY-MM-DD/part-00000.parquet
    |
    v
AWS Glue Data Catalog
opslens_dev.kev_entries
    |
    v
Amazon Athena
```

### NVD CVE

```text
NVD yearly feeds                  NVD CVE API 2.0
       |                                  |
       v                                  v
Bootstrap ingestion                Incremental ingestion
       |                                  |
       +-------------> S3 Bronze <--------+
                       evidência imutável
                              |
                              v
                     NVD Silver runtime
                              |
                              v
                Silver versionado / Parquet
                              |
                              v
                  evidência Silver COMPLETE
                              |
                              v
                elegibilidade para promoção
                              |
                              v
                  watermark autoritativo
                              |
                              v
            NVD Analytics Projector Lambda
                              |
                              v
               namespace analítico limpo
                              |
                              v
                   AWS Glue Data Catalog
                 opslens_dev.nvd_cve_versions
                              |
                              v
                       Amazon Athena
```

O boundary de autoridade do NVD é explícito:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

Analytics é estritamente downstream. O projector analítico não pode avançar o watermark, alterar a autoridade Silver, listar o bucket, deletar objetos nem escrever partições no Glue.

### GitHub Security Advisories

```text
GitHub Global Security Advisories REST API
        |
        v
GHSA Bronze Lambda
        |
        v
páginas Bronze versionadas no S3 + COMPLETE
        |
        v
GHSA Silver Lambda
  leituras exatas por VersionId de manifest/páginas
  recomputação do attempt_id
  normalização determinística do advisory
        |
        v
um objeto Parquet imutável de uma linha
por observed_advisory_version_id
        |
        v
manifest Silver COMPLETE
  ocorrência -> VersionId exato do conteúdo
```

A Phase 2.4D comprovou end to end um attempt Bronze real com 10 advisories. Foram criados dez objetos Parquet autoritativos de uma linha e um manifest Silver COMPLETE. Uma segunda invocação reproduziu as mesmas identidades e criou zero novas versões S3. A aplicabilidade de package/version permanece trabalho determinístico da Phase 3.

## Princípios

- Evidência e correlação determinísticas primeiro; raciocínio generativo depois.
- Agents reason. Code verifies evidence.
- A evidência bruta da fonte é preservada antes da transformação.
- VersionIds exatos do S3 fazem parte do modelo de evidência.
- Resultados analíticos derivados precisam permanecer reproduzíveis.
- Entrega duplicada é esperada e deve ser segura.
- Falhar fechado em divergências de evidência, proveniência, schema ou autoridade.
- Risco de repositório e exposição em runtime são conceitos diferentes.
- Código de repositórios de terceiros nunca é executado durante análise.
- IAM least privilege é requisito arquitetural.
- Identidades de deployment e runtime permanecem separadas.
- Custo, observabilidade e recuperação de falhas são preocupações arquiteturais.
- Serviços AWS entram somente quando resolvem um requisito concreto.
- Planejamento em linguagem natural nunca recebe autoridade SQL irrestrita.

## Fundação AWS

```text
Environment:             dev
Primary workload Region: us-east-1
Infrastructure as Code:  Terraform
Human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC
Terraform state:         Amazon S3
Observability:           CloudWatch + X-Ray
Analytics:               AWS Glue + Amazon Athena
```

O GitHub Actions não armazena access keys persistentes da AWS. A identidade de deployment é separada das identidades de runtime de ingestão, transformação, scheduler, promotion e analytics.

## Destaques da implementação NVD

### Bronze imutável

Os yearly feeds do Bootstrap preservam os bytes exatos do gzip e META do NVD sob revisões determinísticas da fonte:

```text
bronze/nvd/cve/bootstrap/
  feed_year=YYYY/
    feed_revision=<source-revision>/
      nvdcve-2.0-YYYY.json.gz
      nvdcve-2.0-YYYY.meta
      manifest.json
```

As execuções incrementais da CVE API preservam páginas exatas da resposta sob uma identidade lógica de update, separando cada observação física exata da fonte:

```text
bronze/nvd/cve/updates/
  update_id=<logical-window-identity>/
    attempt_id=<exact-physical-observation>/
      page_start=000000/response.json
      page_start=000500/response.json
      ...
    manifest.json
```

`update_id` identifica a janela incremental lógica. `attempt_id` identifica a observação física exata da fonte e protege a semântica de replay quando a API do NVD retorna bytes exatos diferentes para a mesma janela lógica.

### Silver versionado

O contrato Silver do NVD separa:

```text
cve_id                  identidade da vulnerabilidade
observed_cve_version_id identidade do conteúdo exato da CVE na fonte
observation_id          identidade da ocorrência Bronze imutável
```

O dataset Silver v1 preserva campos centrais da CVE, descrições, tags, evidência CWE, referências, observações CVSS suportadas, JSON canônico das métricas, árvores de configuração CPE e proveniência Bronze exata.

Contrato físico:

```text
dataset:           nvd_cve_versions
schema_version:    1
Parquet format:    1.0
data page version: 1.0
compression:       snappy
row group size:    5000
```

### Watermark autoritativo

Concluir Bronze incremental não avança a autoridade. Um novo boundary comprometido só é publicado depois da verificação da evidência Silver COMPLETE exata e do sucesso da promoção.

Isso impede que uma janela incremental parcialmente transformada ou não verificável se torne autoritativa.

### Projeção analítica permanente

O analytics projector consome autoridade committed exata e executa uma cópia S3 condicional por versão para um namespace append-only e limpo:

```text
analytics/nvd/cve/schema_version=1/
  source_kind=<bootstrap|incremental>/
  projection_date=YYYY-MM-DD/
    <deterministic-batch-file>.parquet
```

A semântica de replay é estrita: `If-None-Match: *` só pode resultar em `already_projected` depois que o objeto de destino existente é verificado novamente contra VersionId, SHA-256, tamanho, metadata e assinatura Parquet da fonte autoritativa.

O runtime não possui `s3:ListBucket`, permissões de delete, `PutObject` no watermark nem autoridade de mutação de partições no Glue.

## Evidências validadas

### EPSS

Snapshot validado:

```text
snapshot_date: 2026-08-16
model_version: v2026.06.15
source rows:   360399
EPSS > 0.7:    2457
```

Execução observada no Athena:

```text
data scanned:    6084428 bytes
total execution: 1501 ms
```

O resultado foi validado independentemente contra o Parquet Silver e contra a fonte FIRST original.

### CISA KEV

Snapshot validado:

```text
snapshot_date:  2026-08-17
catalogVersion: 2026.08.14
records:        1665
source bytes:   1583171
SHA-256:        52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79
```

Artefato Silver validado:

```text
rows:           1665
columns:        16
size:           257331 bytes
schema version: 1
```

### Projeção NVD Bootstrap

Projeção permanente Bootstrap validada:

```text
rows:                  48293
destination VersionId: NzP5XmGl6yeMoQvmMv4JgCmixd_5N.ba
SHA-256:               4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
replay:                already_projected com VersionId inalterado
```

### Projeção NVD Incremental

Projeção incremental event-driven validada:

```text
committed_through_at:   2026-08-26T21:25:00Z
update_id:              fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
rows:                   331
destination VersionId:  qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl
SHA-256:                3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
```

### Prova NVD no Athena

As queries permanentes do Athena reproduziram a evidência local exata do Parquet e permaneceram abaixo do cutoff do workgroup dev de `10.485.760` bytes:

| Query | Objetivo | Dados escaneados |
| --- | --- | ---: |
| A | Cardinalidade / lineage Bootstrap + Incremental | 536.071 bytes |
| B | Amostra nested CVSS do Bootstrap | 3.928.022 bytes |
| B2 | Equivalência exata de source/type CVSS | 3.928.022 bytes |
| C | Observação Incremental determinística | 43.880 bytes |

A amostra CVSS do Bootstrap continha corretamente duas observações V3.1 distintas com o mesmo vetor numérico: evidência NVD `Primary` e CNA `Secondary`. A amostra Incremental reproduziu exatamente observation, batch, status e timestamp esperados.

## Recuperação de falhas e observabilidade

Os boundaries de runtime usam logs estruturados no CloudWatch, métricas CloudWatch, AWS X-Ray, retries assíncronos limitados e filas SQS OnFailure específicas por fonte.

O runtime analítico do NVD foi validado com:

```text
replay status:               already_projected
replay destination version:  inalterado
invalid async invocation:    aceita com StatusCode 202
retry condition:             RetriesExhausted
approximate invoke count:    3
function error:              Unhandled
error type:                  InvalidNvdAnalyticsProjectionInvocationError
failure queue após cleanup:  0 / 0 / 0
```

A invocação inválida foi rejeitada antes da execução da projeção, provando fail-closed no boundary de entrada.

## Limites de segurança

```text
Administração humana
    -> AWS IAM Identity Center

GitHub Actions
    -> OIDC
    -> OpsLensGitHubDeployRole
    -> deployment gerenciado por Terraform

Identidades de runtime
    -> roles de ingestão específicas por fonte
    -> roles Silver específicas por fonte
    -> roles de execução de Scheduler
    -> role de NVD promotion
    -> role do NVD analytics projector
```

O NVD analytics projector é deliberadamente mais restrito que o caminho upstream de autoridade. Ele pode ler evidência committed exata e criar objetos analíticos determinísticos, mas não pode alterar o watermark autoritativo nem o estado Silver.

## Disciplina de custos

A arquitetura evita serviços que ainda não resolvem um requisito demonstrado.

Exemplos atuais:

- nenhum Glue crawler para EPSS, KEV ou NVD;
- nenhum requisito de Step Functions no data plane atual;
- nenhum DynamoDB para idempotência;
- nenhum requisito de Iceberg neste estágio;
- nenhum caminho irrestrito de text-to-SQL;
- o workgroup de desenvolvimento do Athena aplica cutoff de 10 MiB por query.

## Quality gates

O repositório utiliza:

```text
Ruff
Pyright strict
Pytest
Terraform fmt / validate
TFLint
Checkov
GitHub Actions
Terraform plan canônico antes de apply
verificações de convergência após deployment
```

O closeout da Phase 2.3G passou Ruff, Pyright strict, a suíte completa de Pytest, Terraform CI, convergência do Bootstrap Terraform e convergência dos recursos da Phase 2.3G.

O PR #28 concluiu em seguida a migração dos artefatos de deployment Lambda legados de EPSS, KEV e NVD Bootstrap. Todos os runtimes Lambda atualmente implantados usam agora artefatos S3 determinísticos e content-addressed, fixados por VersionId exato, e o closeout final completo do Terraform `dev` convergiu com `No changes` e `POST_APPLY_PLAN_RC=0`.

## Estrutura do repositório

```text
.
├── .github/
├── docs/
│   ├── adr/
│   ├── labs/
│   ├── README.md
│   ├── architecture.md
│   └── architecture.pt-br.md
├── infra/
│   ├── bootstrap/
│   └── environments/dev/
├── scripts/
├── src/
│   └── opslens/
├── tests/
├── README.md
├── README.pt-br.md
├── pyproject.toml
└── uv.lock
```

## Documentação

- [Arquitetura — Português](docs/architecture.pt-br.md)
- [Architecture — English](docs/architecture.md)
- [Índice de ADRs](docs/adr/README.md)
- [Índice de labs / evidências](docs/README.md)

## Roadmap

```text
Phase 0    AWS Foundation                                      COMPLETE
Phase 1    EPSS Vertical Slice                                 COMPLETE
Phase 2.1  CISA KEV Bronze ingestion                          COMPLETE
Phase 2.2  CISA KEV Silver + Glue + Athena                    COMPLETE
Phase 2.3  NVD / CVE Bronze + Silver + Watermark + Analytics  COMPLETE
Phase 2.4  GitHub Security Advisories                          IN PROGRESS
Phase 2.5  Historical EPSS                                     NOT STARTED
Phase 3    Vulnerability Correlation Engine                    NOT STARTED
```

A Phase 2.4A — GHSA Source Contract & Workload Spike é o próximo gate de implementação. A expansão histórica do EPSS vem depois, antes do encerramento da Phase 2. A aplicabilidade de vulnerabilidade para package/version permanece um trabalho determinístico da Phase 3 e não é delegada a um LLM.

Os padrões comprovados são reutilizados quando apropriado, mas nenhuma fonte é forçada a seguir um desenho genérico de ingestão quando suas semânticas são diferentes.

## Licença

Apache License 2.0.
