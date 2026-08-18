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
| --- | --- | --- |
| Phase 0 | AWS Foundation | ✅ Concluída |
| Phase 1 | EPSS Vertical Slice | ✅ Concluída |
| Phase 2.1 | CISA KEV Bronze Ingestion | ✅ Concluída |
| Phase 2.2 | CISA KEV Silver + Analytics | ✅ Concluída |
| Phase 2.3 | NVD / CVE | ▶️ Próxima |

A Phase 2.2 agora fornece o caminho completo de evidência CISA KEV:

- evidência Bronze imutável da fonte;
- processamento Bronze-to-Silver pela versão exata do S3;
- normalização determinística;
- persistência Silver Parquet tipada;
- processamento event-driven idempotente;
- recuperação assíncrona de falhas com limites explícitos;
- registro no AWS Glue Data Catalog;
- partition projection `snapshot_date` do tipo `injected`;
- consultas determinísticas no Amazon Athena;
- cross-check independente entre Parquet e Athena;
- enforcement explícito da dimensão temporal;
- evidência medida de scan e latência no Athena.

O próximo vertical slice principal da Phase 2 é a ingestão e normalização NVD/CVE.

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
    v
S3 ObjectCreated:Put
    |
    v
KEV Silver Lambda
    |
    +--> leitura pelo VersionId exato
    +--> verificação evento / evidência S3
    +--> normalização determinística
    +--> serialização Parquet tipada
    +--> PutObject Silver condicional
    |
    v
S3 Silver / Parquet
    |
    +--> entrega duplicada: already_exists
    +--> falha assíncrona esgotada: SQS OnFailure
    |
    v
AWS Glue Data Catalog
opslens_dev.kev_entries
    |
    v
Amazon Athena
opslens-dev
```

A notification do S3 está restrita ao prefixo Bronze do KEV e ao nome de arquivo canônico. O KEV Silver grava em `silver/kev/`, evitando invocação recursiva.

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
- Serviços AWS entram apenas quando resolvem um requisito concreto.

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

A role de deployment do GitHub é assumida via OIDC e sua relação de confiança é restrita ao boundary de deployment do repositório.

## Data lake

### EPSS Bronze

```text
bronze/epss/snapshot_date=YYYY-MM-DD/epss_scores.csv.gz
```

Propriedades:

- artefato comprimido original do FIRST preservado;
- chave determinística;
- proveniência SHA-256;
- metadados da fonte;
- versionamento S3;
- escritas condicionais.

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

Partição:

```text
snapshot_date string
```

O Silver é determinístico e serializado em Parquet.

### CISA KEV Bronze

```text
bronze/kev/snapshot_date=YYYY-MM-DD/known_exploited_vulnerabilities.json
```

`snapshot_date` representa a data UTC em que o OpsLens observou a fonte e é diferente de `dateReleased` do catálogo e `dateAdded` no nível da vulnerabilidade.

A ingestão valida sucesso HTTP, limite de tamanho, JSON UTF-8, contrato do objeto de topo, `catalogVersion`, `dateReleased`, `count`, `vulnerabilities` e `count == len(vulnerabilities)`.

Campos adicionais desconhecidos da fonte continuam permitidos, e os bytes exatos da fonte são preservados.

### CISA KEV Silver

```text
silver/kev/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

Colunas físicas do Parquet:

```text
cve
vendor_project
product
vulnerability_name
date_added
short_description
required_action
due_date
known_ransomware_campaign_use
notes
cwes
catalog_version
catalog_date_released
source
source_sha256
retrieved_at
```

Partição:

```text
snapshot_date string
```

A transformação Silver:

- lê a versão exata do objeto Bronze referenciada pelo evento S3;
- cruza `VersionId`, ETag, tamanho e metadados de proveniência do Bronze;
- falha de forma fechada em divergências de transporte ou proveniência;
- rejeita CVEs duplicadas e valores de ransomware não suportados;
- preserva a ordem determinística da fonte;
- grava Parquet com schema Arrow explícito;
- usa persistência condicional para impedir que uma entrega duplicada crie uma segunda versão Silver.

## Caminho analítico EPSS validado

```text
snapshot_date: 2026-08-16
model_version: v2026.06.15
source rows:   360399
EPSS > 0.7:    2457
```

Pergunta estruturada suportada:

> Quais CVEs possuem EPSS maior que 0,7 em um snapshot específico?

```sql
SELECT
    cve,
    epss,
    percentile
FROM epss_scores
WHERE snapshot_date = '2026-08-16'
  AND epss > 0.7
ORDER BY epss DESC, cve;
```

Execução medida:

```text
Athena engine:          version 3
data scanned:           6084428 bytes
total execution:        1501 ms
estimated query cost:   USD 0.00005000
```

O resultado foi validado independentemente contra o Parquet Silver e contra a fonte FIRST Bronze original.

## Pipeline CISA KEV validado

Snapshot Bronze validado:

```text
snapshot_date:  2026-08-17
catalogVersion: 2026.08.14
records:         1665
source bytes:    1583171
SHA-256:         52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79
```

Artefato Silver validado:

```text
key:             silver/kev/snapshot_date=2026-08-17/part-00000.parquet
rows:            1665
columns:         16
size:            257331 bytes
schema version:  1
Known ransomware:   349
Unknown ransomware: 1316
listas CWE vazias:   171
```

O objeto Silver foi baixado e inspecionado independentemente com PyArrow.

Um replay do mesmo evento Bronze retornou `already_exists`, enquanto o objeto versionado do S3 permaneceu com uma única versão e o mesmo `VersionId`.

## Caminho analítico CISA KEV validado

Snapshot validado:

```text
snapshot_date: 2026-08-17
rows:          1665
table:         opslens_dev.kev_entries
workgroup:     opslens-dev
```

Pergunta estruturada suportada:

> A CVE X estava presente no catálogo CISA KEV em um snapshot específico?

A CVE de validação foi selecionada diretamente do artefato Silver Parquet persistido, e não de memória:

```text
CVE-2002-0367
vendor_project: Microsoft
product: Windows
date_added: 2022-03-03
due_date: 2022-03-24
catalog_version: 2026.08.14
source: cisa-kev
source_sha256: 52a5fe9ab6c3379298707559b5df54fb50daac45d27ea74e85d45f9632b59a79
```

O Athena retornou a mesma evidência do artefato Parquet persistido.

Execuções observadas no Athena:

| Validação | Dados escaneados | Tempo total |
| --- | ---: | ---: |
| Contagem de registros | 0 bytes | 744 ms |
| Membership da CVE | 24.911 bytes | 621 ms |
| Arrays CWE vazios | 3.002 bytes | 842 ms |
| Compatibilidade de timestamps | 13.826 bytes | 945 ms |

A consulta de contagem retornou `1665`, a validação de CWE retornou `171` arrays vazios e os campos `catalog_date_released` e `retrieved_at` foram lidos com sucesso pelo Athena engine version 3.

A tabela Glue usa partition projection `injected` para `snapshot_date`. Uma consulta que omitiu intencionalmente `snapshot_date` falhou com `CONSTRAINT_VIOLATION`, exigindo evidência temporal explícita em vez de tratar implicitamente uma versão não informada como "mais recente".

## Recuperação de falhas

EPSS Silver, ingestão CISA KEV e CISA KEV Silver usam processamento assíncrono limitado da Lambda com `maximum event age = 3600`, `retry attempts = 2` e destinations SQS OnFailure específicas.

Uma falha controlada da ingestão KEV validou três tentativas, `KevSourceUnavailableError`, `RetriesExhausted`, registro SQS enriquecido e recuperação após a restauração da fonte canônica.

Um segundo laboratório controlado, específico do KEV Silver, enviou um evento válido para o parser com ETag propositalmente incorreto. O runtime:

- leu o `VersionId` Bronze exato;
- detectou a divergência entre o evento e a evidência retornada pelo S3;
- lançou `KevBronzeEvidenceMismatchError`;
- repetiu até `approximateInvokeCount = 3`;
- produziu registro SQS OnFailure com `condition = RetriesExhausted`;
- não criou nenhuma versão adicional do objeto Silver.

Isso valida a regra fail-closed: metadados do evento S3 são tratados como evidência a verificar, e não como autoridade confiável.

## Agendamento

A ingestão CISA KEV é executada por EventBridge Scheduler:

```text
group:           opslens-dev-kev
schedule:        opslens-dev-kev-daily
expression:      cron(30 23 * * ? *)
timezone:        UTC
flexible window: OFF
```

Os retries de entrega do Scheduler são limitados a 3600 segundos e 2 tentativas.

A execution role do Scheduler pode executar somente `lambda:InvokeFunction` na função `opslens-dev-kev-ingestion`.

Retries do Scheduler e retries do processamento assíncrono da Lambda são boundaries de falha diferentes.

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
    +-- KEV Silver role
    +-- KEV Scheduler role
```

A role do KEV Silver é intencionalmente restrita:

```text
s3:GetObjectVersion -> bronze/kev/*
s3:PutObject        -> silver/kev/*
sqs:SendMessage     -> fila de falhas KEV Silver
CloudWatch Logs     -> log group KEV Silver
X-Ray telemetry     -> APIs de tracing
```

Ela não possui `s3:GetObject` genérico, `s3:ListBucket`, permissões de delete ou acesso amplo ao SQS.

O S3 pode invocar a Lambda KEV Silver somente a partir do data bucket e da conta AWS esperados.

## Observabilidade

O runtime utiliza AWS Lambda Powertools, logs estruturados no CloudWatch, custom CloudWatch Metrics, métricas da Lambda, métricas do Scheduler e AWS X-Ray.

A primeira transformação KEV Silver real observou:

```text
configured memory:  1024 MB
max memory used:     176 MB
duration:             795.365 ms
billed duration:      2112 ms
rows transformed:     1665
```

Um replay idempotente warm observou máximo de 194 MB. O right-sizing permanece deliberadamente adiado até existir mais evidência de execuções naturais.

## Disciplina de custos

A arquitetura evita serviços que ainda não resolvem um requisito demonstrado.

Exemplos atuais:

- nenhum Glue crawler para EPSS ou CISA KEV;
- nenhum Step Functions nos caminhos atuais de ingestão/transformação;
- nenhum DynamoDB para idempotência;
- nenhum requisito de Iceberg neste estágio;
- nenhum Scheduler DLQ para KEV neste estágio;
- os recursos Glue/Athena do KEV foram introduzidos somente depois da comprovação do runtime Bronze-to-Silver.

O workgroup de desenvolvimento do Athena utiliza cutoff de 10 MiB por query.

O laboratório controlado de falha do KEV Silver, com três tentativas, consumiu aproximadamente `2.283 GB-s` de compute Lambda antes dos efeitos do free tier, mantendo o workload de desenvolvimento desprezível frente ao target de custo do projeto.

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
- [`docs/labs/phase-2-kev-silver-runtime.md`](docs/labs/phase-2-kev-silver-runtime.md)
- [`docs/labs/phase-2-kev-athena-query.md`](docs/labs/phase-2-kev-athena-query.md)
- [`docs/README.md`](docs/README.md)

## Roadmap

```text
Phase 2.1  CISA KEV Bronze ingestion                         CONCLUÍDA
Phase 2.2  CISA KEV Silver runtime                          CONCLUÍDO
Phase 2.2  CISA KEV Glue + Athena                           CONCLUÍDO
Phase 2.3  NVD / CVE                                        PRÓXIMO
Phase 2.4  GitHub Security Advisories                       NÃO INICIADO
Phase 2.5  histórico EPSS                                   NÃO INICIADO
```

A arquitetura comprovada do EPSS é reutilizada quando fizer sentido, mas não é tratada como template obrigatório para toda fonte.

## Semântica do snapshot diário do KEV

O contrato Bronze da Phase 2.1 preserva uma observação imutável por `snapshot_date` UTC.

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

Uma atualização posterior da CISA observada na mesma data UTC resolve para a mesma chave e produz o resultado esperado `already_exists`.

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

Portanto, `snapshot_date` significa **a data UTC em que o OpsLens preservou pela primeira vez a fonte com sucesso**, e não necessariamente a última revisão publicada pela CISA naquele dia.

Capturar revisões intradiárias da fonte está intencionalmente fora do contrato da Phase 2.1.

## Licença

Apache License 2.0.
