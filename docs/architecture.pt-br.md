# Arquitetura do OpsLens

🇺🇸 [English](architecture.md) | 🇧🇷 **Português**

_Última atualização: 2026-08-27_

## Visão geral

OpsLens é uma plataforma open source de inteligência para software supply chain construída na AWS.

A arquitetura implementada cobre atualmente:

- fundação de identidade e deployment na AWS;
- FIRST EPSS Bronze, Silver determinístico, Glue e Athena;
- CISA KEV Bronze, Silver determinístico, Glue e Athena;
- NVD CVE Bootstrap Bronze por yearly feed;
- NVD CVE API 2.0 Bronze incremental;
- NVD Silver versionado;
- promoção do watermark autoritativo do NVD;
- projeção analítica permanente do NVD;
- AWS Glue Data Catalog e Athena para NVD;
- verificação de evidência por versão exata de objeto S3;
- persistência condicional idempotente;
- retries assíncronos limitados e recuperação via SQS OnFailure;
- observabilidade com CloudWatch, métricas e X-Ray;
- infraestrutura gerenciada por Terraform com controles explícitos de custo.

O projeto prioriza evidência determinística e correlação estruturada antes de raciocínio generativo.

A invariante central é:

> **Agents reason. Code verifies evidence.**

---

## Princípios arquiteturais

- Evidência bruta é preservada antes de enriquecimento ou interpretação.
- Fatos determinísticos permanecem autoritativos; modelos podem explicá-los, mas não estabelecê-los.
- VersionIds exatos de objetos S3 fazem parte do modelo de evidência.
- Detalhes de AWS SDK e runtime ficam fora do core de domínio sempre que possível.
- Bootstrap humano, deployment via GitHub, ingestão, transformação, scheduling, promotion e analytics usam boundaries IAM separados.
- Entrega duplicada é esperada e precisa ser segura.
- Boundaries operacionais emitem logs estruturados, métricas e traces.
- Risco de repositório e exposição em runtime são conceitos diferentes.
- Serviços AWS entram apenas quando resolvem um requisito demonstrado.
- Custo e observabilidade são requisitos arquiteturais.
- Código de terceiros é dado para inspeção, nunca código para execução.
- Planejamento em linguagem natural nunca recebe autoridade SQL irrestrita.

---

## Fundação AWS

### Administração humana

```text
AWS IAM Identity Center
    |
    v
credenciais humanas temporárias
    |
    v
profile opslens-bootstrap
```

### Deployment via GitHub

```text
GitHub Actions
    |
    v
OIDC
    |
    v
AWS STS
    |
    v
OpsLensGitHubDeployRole
```

Nenhuma access key persistente da AWS é armazenada no GitHub.

A identidade de deployment é separada de todas as identidades de runtime.

### Terraform

```text
infra/
    bootstrap/
    environments/
        dev/
```

Existe apenas um ambiente real atualmente:

```text
dev
```

O state do Terraform fica remoto no Amazon S3. O projeto evita ambientes fictícios de staging ou produção criados apenas para aparência de portfólio.

---

## Data plane implementado

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

O EPSS preserva o artefato comprimido original do FIRST, proveniência SHA-256, versionamento S3, transformação Silver determinística e analytics temporal por `snapshot_date`.

### CISA KEV

```text
CISA KEV JSON
    |
    v
EventBridge Scheduler
opslens-dev-kev-daily
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
    +--> schema Arrow tipado
    +--> serialização Parquet
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
opslens-dev
```

O runtime KEV Silver falha fechado em divergências de transporte ou proveniência e usa retries limitados da Lambda com destination SQS OnFailure dedicada.

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
                 verificação de promoção
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

O caminho NVD separa deliberadamente preservação da fonte, conclusão da transformação, compromisso de autoridade e disponibilidade analítica.

A invariante de autoridade é:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

Uma janela Bronze-complete não pode se tornar autoritativa até que a evidência Silver determinística esteja completa e as verificações exatas de promotion passem. Analytics permanece downstream-only e não pode alterar autoridade upstream.

---

## NVD Bronze

### Bootstrap yearly feeds

Layout canônico:

```text
bronze/nvd/cve/bootstrap/
    feed_year=YYYY/
        feed_revision=<source-revision>/
            nvdcve-2.0-YYYY.json.gz
            nvdcve-2.0-YYYY.meta
            manifest.json
```

A revisão do feed combina o timestamp normalizado de modificação da fonte NVD com o SHA-256 da fonte.

O runtime valida:

- recuperação limitada do META;
- contrato do META;
- recuperação limitada do gzip;
- tamanho comprimido e descomprimido;
- decodificação gzip;
- SHA-256 da fonte;
- revisão determinística do feed;
- VersionIds exatos dos objetos persistidos.

A persistência usa criação condicional de objeto no S3. `412 PreconditionFailed` é tratado apenas como possível duplicata e só resulta em sucesso após verificação da evidência existente.

### Incremental CVE API 2.0

O runtime incremental avança por janelas fechadas de `lastModified` e preserva cada página exata retornada pela API.

Layout canônico:

```text
bronze/nvd/cve/updates/
    update_id=<deterministic-window-identity>/
        page_start=000000/
            response.json
        page_start=000500/
            response.json
        ...
        manifest.json
```

O contrato incremental valida:

- respostas HTTP limitadas;
- pacing respeitoso;
- retries limitados para falhas transitórias da fonte;
- `totalResults` estável;
- paginação contígua;
- cobertura terminal;
- rejeição de CVEs duplicadas;
- bytes exatos da resposta e SHA-256;
- VersionIds exatos persistidos no S3.

Bronze COMPLETE só é gravado depois que todas as páginas foram criadas ou verificadas exatamente.

Concluir Bronze não avança o watermark autoritativo.

---

## NVD Silver versionado

O contrato Silver separa três identidades:

```text
cve_id
    identidade da vulnerabilidade

observed_cve_version_id
    identidade do conteúdo exato da CVE na fonte

observation_id
    identidade da ocorrência Bronze imutável
```

O objeto CVE original completo participa da identidade determinística de conteúdo, permitindo que modificações históricas, rejection e unrejection criem novas versões observadas em vez de sobrescrever histórico.

Silver v1 preserva:

- campos centrais da CVE;
- descrições localizadas e tags;
- evidência CWE / weakness;
- referências;
- observações CVSS v2, v3.0, v3.1 e v4 suportadas;
- JSON canônico das métricas;
- árvores canônicas de configuração CPE;
- proveniência Bronze versionada exata.

Estruturas conhecidas malformadas de métrica ou configuração falham fechado. Famílias futuras desconhecidas não são interpretadas silenciosamente; Bronze imutável continua sendo a evidência da fonte.

Contrato físico:

```text
dataset:           nvd_cve_versions
schema_version:    1
Parquet format:    1.0
data page version: 1.0
compression:       snappy
row group size:    5000
```

Silver COMPLETE liga o conjunto lógico normalizado a bytes Parquet determinísticos, SHA-256, tamanho, row count e VersionId S3 exato.

Para batches incrementais:

```text
Silver row_count == verified Bronze total_results
```

Uma janela incremental válida com zero resultados é suportada.

---

## Watermark autoritativo do NVD

O watermark autoritativo representa o último boundary incremental comprometido.

Promotion só é permitida depois que a evidência exata prova:

```text
Bronze COMPLETE
    -> Silver COMPLETE exato
    -> VersionId + SHA-256 exatos do Silver Parquet
    -> identidade do conjunto lógico de registros
    -> avanço estrito do boundary committed
```

O basis de promotion usa `kind = silver_complete_promotion` e liga o watermark autoritativo ao manifest e ao Parquet Silver exatos.

Isso impede confundir sucesso de Bronze com sucesso de transformação e sucesso de transformação com autoridade committed.

---

## Projeção analítica permanente do NVD

O caminho analítico permanente é uma projeção da autoridade committed, não uma nova fonte de autoridade.

Caminho incremental:

```text
VersionId exato do evento S3 ObjectCreated do watermark
    -> validação estrita do watermark canônico
    -> evidência Silver COMPLETE exata
    -> VersionId + SHA-256 exatos do Silver Parquet
    -> CopyObject condicional a partir da versão exata
    -> destino analítico determinístico
    -> verificação exata do destino
```

Bootstrap usa uma invocação explícita e exata `bootstrap_seed` em vez de fingir que o feed Bootstrap possui watermark incremental.

Namespace permanente:

```text
analytics/nvd/cve/schema_version=1/
    source_kind=<bootstrap|incremental>/
        projection_date=YYYY-MM-DD/
            <deterministic-batch-file>.parquet
```

Comportamento de replay:

```text
CopyObject condicional
If-None-Match: *
        |
        +--> created
        |
        +--> 412 destino existente
                |
                v
          verificação exata do objeto atual
                |
                +--> match exato -> already_projected
                +--> mismatch    -> fail closed
```

O projector verifica VersionId do destino, tamanho, content type, metadata completa, SHA-256 e assinatura Parquet `PAR1`.

O IAM de runtime exclui intencionalmente:

```text
s3:ListBucket
s3:DeleteObject
watermark PutObject
mutação Silver
mutação de partições Glue
```

---

## NVD Glue e Athena

Tabela permanente:

```text
Database: opslens_dev
Table:    nvd_cve_versions
Type:     EXTERNAL_TABLE
Columns:  32 colunas Silver v1
```

Root location:

```text
s3://<data-bucket>/analytics/nvd/cve/schema_version=1/
```

Partition projection:

```text
source_kind_partition -> bootstrap,incremental
projection_date       -> 2026-01-01,NOW
```

Não é necessário crawler nem escrita runtime de partições Glue.

O workgroup de desenvolvimento do Athena aplica:

```text
bytes-scanned cutoff: 10.485.760 bytes
result encryption:    SSE_S3
```

Queries permanentes do NVD validadas:

| Query | Objetivo | Dados escaneados |
| --- | --- | ---: |
| A | Cardinalidade / lineage Bootstrap + Incremental | 536.071 bytes |
| B | Amostra nested CVSS do Bootstrap | 3.928.022 bytes |
| B2 | Equivalência exata de source/type CVSS | 3.928.022 bytes |
| C | Observação Incremental determinística | 43.880 bytes |

Todas permaneceram abaixo do cutoff de 10 MiB e reproduziram a evidência local exata do Parquet.

---

## Evidência NVD validada

### Projeção permanente Bootstrap

```text
rows:                  48293
destination VersionId: NzP5XmGl6yeMoQvmMv4JgCmixd_5N.ba
SHA-256:               4ea6e3ae1d73908d8fb4f953dcf181802bf111001bcdb7f3695e4773fe854541
replay:                already_projected
version após replay:   inalterada
```

### Projeção permanente Incremental

```text
watermark VersionId:   q9Zwn_4jdUZei_jqP6fytSy1aabtus7h
committed_through_at:  2026-08-26T21:25:00Z
update_id:             fc809fd639fc53f56c0e01278b2c4d99b19298c15a02ca2369b8dba392de4abc
rows:                  331
destination VersionId: qPiaURVW17cIGxSqROAgUbqIqIq1L0Jl
SHA-256:               3ad08d8e257128bc8334fc98ae0eade8d4808136b84df8a8ab8de64978bcc6f9
```

A invocação event-driven foi correlacionada no CloudWatch por VersionId exato do watermark, update identity, destination VersionId e contexto de request/trace.

---

## Recuperação de falhas

A plataforma trata entrega de Scheduler, processamento assíncrono Lambda, validação de evidência e recuperação via SQS como boundaries distintos de falha.

Padrões relevantes incluem:

- idade máxima de evento limitada;
- dois retries assíncronos da Lambda;
- destinations SQS OnFailure específicas por fonte;
- parser e validação de evidência fail-closed;
- telemetria estruturada de falhas;
- destinos determinísticos seguros para replay.

O closeout de analytics do NVD validou:

```text
invalid async invocation accepted: StatusCode 202
condition:                         RetriesExhausted
approximateInvokeCount:            3
functionError:                     Unhandled
errorType:                         InvalidNvdAnalyticsProjectionInvocationError
failure queue após cleanup:        0 / 0 / 0
```

O evento inválido nunca atravessou o boundary de execução da projeção.

---

## Observabilidade

O runtime utiliza:

- AWS Lambda Powertools Logger, Metrics e Tracer;
- logs estruturados no CloudWatch;
- métricas de plataforma da AWS Lambda;
- métricas do EventBridge Scheduler;
- AWS X-Ray.

No analytics permanente do NVD, evidência do trigger e evidência de conclusão compartilham `request_id` da Lambda e contexto X-Ray, permitindo reconstruir um evento exato de watermark até seu resultado de projeção.

---

## Limites de segurança

```text
Administração humana
    |
    v
AWS IAM Identity Center

GitHub Actions
    |
    v
OIDC
    |
    v
OpsLensGitHubDeployRole
    |
    v
infraestrutura gerenciada por Terraform

Identidades de runtime
    |
    +-- EPSS ingestion / Silver / Scheduler
    +-- KEV ingestion / Silver / Scheduler
    +-- NVD Bootstrap ingestion
    +-- NVD Incremental ingestion / Scheduler
    +-- NVD Silver
    +-- NVD Promotion
    +-- NVD Analytics Projector
```

Least privilege é avaliado de acordo com a responsabilidade de cada runtime, e não em relação ao data lake inteiro.

---

## Disciplina de custos

A arquitetura evita serviços sem necessidade demonstrada.

Exemplos atuais:

- nenhum Glue crawler para EPSS, KEV ou NVD;
- nenhum requisito de Step Functions no data plane atual;
- nenhum DynamoDB para idempotência;
- nenhum requisito de Iceberg neste estágio;
- nenhum caminho irrestrito de linguagem natural para SQL;
- workgroup dev do Athena limitado a 10 MiB por query.

---

## Modelo de artefato de deployment

O analytics projector permanente do NVD usa artefato determinístico e content-addressed:

```text
build do ZIP exato da Lambda
    -> SHA-256
    -> chave S3 imutável do artefato
    -> VersionId S3 exato
    -> pin no Terraform
```

SHA-256 validado do artefato do projector:

```text
6ae0bf3909744d6bb5e61390885fc469c18b93ef383bd4c2380fdc874de159cf
```

Permanece uma exceção preexistente de convergência no ambiente dev para hashes de artefatos Lambda legados de EPSS, KEV e NVD Bootstrap. Essa dívida está fora do boundary concluído da Phase 2.3G e deve ser tratada em uma mudança separada de artifact lifecycle.

---

## Status atual da implementação

```text
FIRST EPSS                 IMPLEMENTED through Athena
CISA KEV                   IMPLEMENTED through Athena
NVD / CVE                  IMPLEMENTED through authoritative analytics + Athena
GitHub Security Advisories NOT STARTED
EPSS historical expansion  NOT STARTED
Phase 3 AI reasoning       NOT STARTED
```

Status detalhado do NVD:

```text
Phase 2.3A — NVD Source Contract            COMPLETE
Phase 2.3B — NVD Bootstrap Bronze           COMPLETE
Phase 2.3C — NVD Incremental API Contract   COMPLETE
Phase 2.3D — NVD Versioned Silver Contract  COMPLETE
Phase 2.3E — NVD Silver AWS Runtime         COMPLETE
Phase 2.3F — NVD Authoritative Watermark    COMPLETE
Phase 2.3G — NVD Glue/Athena Analytics      COMPLETE
```

Ingestão GHSA e Phase 3 permanecem intencionalmente fora do milestone NVD concluído.
