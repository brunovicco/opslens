<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Inteligência de Cloud e Software Supply Chain na AWS

**Threat Intelligence · Software Supply Chain · Evidência Determinística · AWS Serverless · Automação de Segurança**

</div>

OpsLens é uma plataforma open source de inteligência para software supply chain construída na AWS.

Ela foi projetada para responder:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades representam risco material, por quê e o que devo fazer a respeito?

O projeto constrói primeiro evidência determinística, correlação, limites de segurança, observabilidade e recuperação de falhas. Raciocínio generativo e agentic entram depois dessas fundações.

## Status

| Fase | Escopo | Status |
|---|---|---|
| Phase 0 | AWS Foundation | ✅ Concluída |
| Phase 1 | EPSS Vertical Slice | ✅ Concluída |
| Phase 2.1 | CISA KEV Bronze Ingestion | ✅ Concluída |
| Phase 2.2 | CISA KEV Silver + Analytics | ⏭️ Próxima |

A Phase 2.1 já possui ingestão real do CISA KEV, armazenamento Bronze imutável, validação do contrato da fonte, proveniência SHA-256, idempotência por escrita condicional no S3, retries assíncronos da Lambda, recuperação OnFailure via SQS, roles dedicadas e least privilege, EventBridge Scheduler diário às `23:30 UTC` e infraestrutura Terraform convergida para `No changes`.

A Phase 2.1 está concluída. O agendamento diário do KEV foi validado através de uma execução natural originada pelo Scheduler.

## Arquitetura atual

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
    |
    v
S3 ObjectCreated
    |
    v
EPSS Silver Lambda
    |
    v
S3 Silver / Parquet
    |
    v
AWS Glue Data Catalog
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
    +--> validação da fonte
    +--> proveniência SHA-256
    +--> PutObject condicional
    |
    v
S3 Bronze
    |
    +--> sucesso: evidência raw imutável
    +--> duplicado: already_exists
    +--> falha assíncrona esgotada: SQS OnFailure
```

A transformação Silver e analytics do KEV estão intencionalmente adiados para a Phase 2.2.

## Princípios

- Evidência e correlação determinísticas primeiro; raciocínio generativo depois.
- Agents reason. Code verifies evidence.
- Nem toda pergunta é um problema de RAG.
- Código de repositórios de terceiros não é executado durante análise.
- Risco de repositório e exposição em runtime são conceitos diferentes.
- A evidência bruta da fonte é preservada antes de transformações.
- Resultados derivados precisam ser reproduzíveis.
- Entrega duplicada é esperada e deve ser segura.
- IAM least privilege é requisito arquitetural.
- Identidades de deployment e runtime permanecem separadas.
- Custo, observabilidade e recuperação de falhas fazem parte do desenho.

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

O GitHub Actions não armazena access keys persistentes da AWS.

## Data lake

### EPSS Bronze

```text
bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
```

### EPSS Silver

```text
silver/epss/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

Schema:

```text
cve             string
epss            double
percentile      double
model_version   string
score_timestamp timestamp
source          string
source_sha256   string
```

### CISA KEV Bronze

```text
bronze/kev/snapshot_date=YYYY-MM-DD/known_exploited_vulnerabilities.json
```

`snapshot_date` representa a data UTC em que o OpsLens observou a fonte e é diferente de `dateReleased` e `dateAdded` do CISA.

A ingestão valida sucesso HTTP, limite de tamanho, JSON UTF-8, contrato do objeto de topo, `catalogVersion`, `dateReleased`, `count`, `vulnerabilities` e `count == len(vulnerabilities)`.

## Caminho analítico EPSS validado

```text
snapshot_date: 2026-08-16
model_version: v2026.06.15
source rows:   360399
EPSS > 0.7:    2457
```

O resultado Athena foi validado independentemente contra o Parquet Silver e contra a fonte FIRST Bronze original.

## Ingestão CISA KEV validada

```text
snapshot_date: 2026-08-17
catalogVersion: 2026.08.14
records:        1665
source bytes:   1583171
SHA-256:        52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79
```

Uma nova ingestão do mesmo snapshot retornou `already_exists` sem criar uma nova versão no S3.

## Recuperação de falhas

EPSS Silver e CISA KEV usam processamento assíncrono limitado com `maximum event age = 3600`, `retry attempts = 2` e destinations SQS OnFailure específicas.

Uma falha controlada do KEV validou três executions, `KevSourceUnavailableError`, `RetriesExhausted`, registro SQS enriquecido e recuperação normal após restaurar a fonte canônica.

## Agendamento

```text
group:           opslens-dev-kev
schedule:        opslens-dev-kev-daily
expression:      cron(30 23 * * ? *)
timezone:        UTC
flexible window: OFF
```

A execution role do Scheduler pode executar somente `lambda:InvokeFunction` na função `opslens-dev-kev-ingestion`.

## Limites de segurança

```text
Human bootstrap
    |
    v
AWS IAM Identity Center

GitHub Actions
    |
   OIDC
    |
    v
OpsLensGitHubDeployRole
    |
    v
Infraestrutura gerenciada por Terraform

Runtime identities
    |
    +-- EPSS ingestion role
    +-- EPSS Silver role
    +-- EPSS Scheduler role
    +-- KEV ingestion role
    +-- KEV Scheduler role
```

A KEV Scheduler role usa `scheduler.amazonaws.com`, `aws:SourceAccount` exato e `aws:SourceArn` do grupo KEV exato. Ela não possui acesso S3, SQS, Glue, Athena nem autorização genérica de Lambda.

## Observabilidade

O runtime utiliza AWS Lambda Powertools, logs estruturados no CloudWatch, custom CloudWatch Metrics, métricas da Lambda, métricas do Scheduler e AWS X-Ray.

## Disciplina de custos

A arquitetura evita serviços que ainda não resolvem um requisito demonstrado: nenhum Glue crawler para EPSS, Step Functions nos caminhos atuais, DynamoDB para idempotência, Iceberg sem necessidade comprovada, Scheduler DLQ para KEV neste estágio ou recursos Silver/Athena do KEV antes do contrato Bronze estar comprovado.

## Estrutura do repositório

```text
.
├── .github/
├── docs/
│   ├── adr/
│   ├── labs/
│   ├── README.md
│   └── architecture.md
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

## Quality gates

O repositório utiliza Ruff, Google-style docstrings, Pyright strict, Pytest, Terraform fmt e validate, TFLint, Checkov, GitHub Actions, plans Terraform canônicos antes de apply e plans `No changes` após deployment.

## Documentação

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/adr/README.md`](docs/adr/README.md)
- [`docs/labs/phase-0-iam-oidc-failure.md`](docs/labs/phase-0-iam-oidc-failure.md)
- [`docs/labs/phase-0-cloudwatch-authorization-failure.md`](docs/labs/phase-0-cloudwatch-authorization-failure.md)
- [`docs/labs/phase-1-epss-athena-query.md`](docs/labs/phase-1-epss-athena-query.md)
- [`docs/labs/phase-2-kev-async-failure-recovery.md`](docs/labs/phase-2-kev-async-failure-recovery.md)
- [`docs/README.md`](docs/README.md)

## Roadmap

```text
Phase 2.1  CISA KEV Bronze ingestion
Phase 2.2  CISA KEV Silver + Glue + Athena
Phase 2.x  NVD / CVE
Phase 2.x  GitHub Security Advisories
Phase 2.x  histórico EPSS
```

A arquitetura comprovada do EPSS é reutilizada quando fizer sentido, mas não é tratada como template obrigatório para toda fonte.

## Licença

Apache License 2.0.
## Semântica do snapshot diário do KEV

O contrato Bronze da Phase 2.1 preserva uma observação imutável por
`snapshot_date` UTC.

A primeira escrita bem-sucedida do dia se torna a evidência Bronze canônica:

```text
primeira observação bem-sucedida
        |
        v
PutObject condicional
If-None-Match: "*"
        |
        v
objeto canônico imutável
```

Uma atualização posterior da CISA observada na mesma data UTC resolve para a
mesma chave e produz o resultado esperado `already_exists`.

A validação agendada de `2026-08-17` demonstrou diretamente esse comportamento:

```text
observação às 03:52 UTC
catalogVersion: 2026.08.14
records:        1665

observação às 23:30 UTC
catalogVersion: 2026.08.17
records:        1666

Bronze canônico após as duas observações
catalogVersion: 2026.08.14
records:        1665
versões S3:     1
```

Portanto, `snapshot_date` significa **a data UTC em que o OpsLens preservou
pela primeira vez a fonte com sucesso**, e não necessariamente a última revisão
publicada pela CISA naquele dia.

Capturar revisões intradiárias da fonte está intencionalmente fora do contrato
da Phase 2.1.
