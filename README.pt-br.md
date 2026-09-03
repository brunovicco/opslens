<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Inteligência Determinística de Software Supply Chain e Threat Intelligence na AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Evidência Determinística · AWS Serverless · Automação de Segurança**

</div>

OpsLens é uma plataforma open source de inteligência para software supply chain construída na AWS.

Ela foi projetada para responder:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência prova isso e como esses findings devem ser priorizados no futuro?

O projeto estabelece primeiro evidência determinística, proveniência, correlação de package/version, limites de least privilege, observabilidade, recuperação de falhas e controles de custo. Raciocínio generativo e agentic entram somente depois dessas fundações.

> **Agents reason. Code verifies evidence.**

## Status atual

| Fase | Escopo | Status |
| --- | --- | --- |
| Phase 0 | AWS Foundation | ✅ Concluída |
| Phase 1 | EPSS Vertical Slice | ✅ Concluída |
| Phase 2 | Threat Intelligence Data Lake | ✅ Concluída |
| Phase 3 | Vulnerability Correlation Engine | ✅ Concluída |
| Phase 4 | Repository Intelligence | ✅ Concluída |
| Phase 5 | Risk Prioritization Engine | 🚧 Próxima |

Checkpoint de implementação após o fechamento da Phase 4:

```text
4baa9bddd20d827aa06654fc14f52c7ec5135f2c
```

Veja [Current State](docs/current-state.md) e [Roadmap](docs/roadmap.md) para o estado detalhado.

## O que o OpsLens já faz hoje

O caminho determinístico implementado consegue analisar um snapshot suportado de um repositório público no GitHub sem executar o código do repositório:

```text
repositório público GitHub
        |
        v
identidade imutável do repositório
commit + tree SHA exatos
        |
        v
aquisição GitHub REST limitada e GET-only
        |
        v
evidência inerte exata do uv.lock
Git blob SHA-1 + SHA-256 independente
        |
        v
parser determinístico com tomllib
        |
        v
normalização PyPI / PEP 440 / purl
        |
        v
aplicabilidade determinística do range GHSA
        |
        v
reconciliação CVE/GHSA <-> evidência NVD exata
        |
        +--> todas as observações CVSS preservadas
        +--> evidência CISA KEV de snapshot completo
        +--> evidência FIRST EPSS de data explícita
        |
        v
RepositoryAnalysisResult content-addressed
```

Um finding final pode conter:

- dependency e versão instalada;
- purl canônico;
- identificadores GHSA e CVE quando publicados;
- range vulnerável exato que foi avaliado;
- evidência determinística de match por cláusula;
- first patched version quando publicada;
- todas as observações NVD CVSS preservadas;
- estado KEV e registro positivo exato quando presente;
- estado EPSS, coordenadas do snapshot, score e percentile quando disponíveis;
- referências imutáveis de repositório, lockfile, advisory, NVD, KEV e EPSS.

O resultado atual propositalmente **não contém risk score nem prioridade**. Essa autoridade começa na Phase 5.

## Invariantes centrais

- Evidência e correlação determinísticas primeiro; raciocínio generativo depois.
- **Nenhum LLM decide aplicabilidade de vulnerabilidade.**
- A evidência bruta da fonte é preservada antes da transformação.
- Versões exatas da fonte e hashes de conteúdo participam da identidade da evidência.
- Semânticas inválidas ou não suportadas falham fechado.
- Findings de repositório são content-addressed e reproduzíveis.
- Código de repositórios de terceiros nunca é executado durante a análise.
- Repository Risk não é Runtime Exposure.
- Entrega duplicada é esperada e replay precisa ser seguro.
- IAM least privilege e separação de responsabilidades são requisitos arquiteturais.
- Serviços AWS entram apenas quando resolvem um requisito demonstrado.
- Planejamento em linguagem natural nunca recebe autoridade SQL irrestrita.

## Threat Intelligence Data Lake

A Phase 2 fornece a base determinística utilizada pelas fases posteriores.

### FIRST EPSS

```text
FIRST EPSS
 -> EventBridge Scheduler
 -> Lambda de ingestão
 -> S3 Bronze
 -> Silver / Parquet determinístico
 -> Glue Data Catalog
 -> Athena
```

A mesma relação Silver canônica também contém o histórico concluído do EPSS entre `2021-04-14` e `2026-08-13`, obtido de um commit de archive fixado.

### CISA KEV

```text
CISA KEV
 -> ingestão limitada
 -> Bronze imutável
 -> transformação Silver por versão exata
 -> Parquet
 -> Glue
 -> Athena
```

Presença e ausência só possuem significado contra um snapshot completo e explicitamente selecionado do catálogo.

### NVD / CVE

```text
NVD yearly feeds + CVE API 2.0
 -> Bronze imutável
 -> Silver versionado determinístico
 -> Silver COMPLETE
 -> watermark autoritativo
 -> projeção analítica permanente
 -> Glue / Athena
```

A autoridade permanece explícita:

```text
bronze_complete
    !=
silver_complete
    !=
watermark_committed
    -> analytics_eligible
    -> analytics_projected
```

### GitHub Security Advisories

```text
GitHub reviewed advisories
 -> páginas Bronze versionadas + COMPLETE
 -> normalização determinística do advisory
 -> um Parquet imutável por versão de conteúdo
 -> Silver COMPLETE
 -> Glue / Athena
```

A evidência source-local de advisory/package/range/fix do GHSA continua separada da evidência NVD mesmo quando ambas se referem ao mesmo CVE.

## Phase 3 — Vulnerability Correlation Engine

A Phase 3 está concluída para o primeiro ecossistema suportado: **PyPI**.

Semânticas implementadas:

```text
normalização PyPA de package name
parsing PEP 440 de versão
purl PyPI canônico
operadores de range GitHub: = < <= > >=
conjunções separadas por vírgula
affected | not_affected | unsupported
fixed version como evidência explícita
proveniência GHSA exata
reconciliação de alias CVE/GHSA/NVD
correlation:v1@sha256:<digest>
```

`first_patched_version` é evidência de remediação e nunca substitui a verdade do vulnerable range.

Veja [Phase 3 correlation closeout](docs/labs/phase-3-correlation-engine-closeout.md).

## Phase 4 — Repository Intelligence

O escopo v1 atual é intencionalmente estreito:

```text
provider:        GitHub público
manifesto:       uv.lock
dependências:    registros PyPI canônicos
transporte:      read only
execução código: nunca
```

A Phase 4 adiciona identidade imutável do repositório, transporte GitHub limitado, aquisição exata do lockfile inerte, parsing determinístico, normalização/correlação da Phase 3 e enrichment exato com NVD/CVSS, KEV e EPSS.

A identidade final agregada é:

```text
repository-analysis:v1@sha256:<digest>
```

Essa identidade também define a coordenada segura para futuro reuse/cache. Apenas o commit do repositório não é suficiente, porque threat intelligence é temporal.

Nenhum backend de cache foi criado na Phase 4 porque ainda não existe workload medido que justifique a nova superfície de storage, invalidação, IAM, observabilidade e custo.

## Fundação AWS

```text
environment:             dev
primary workload Region: us-east-1
Infrastructure as Code:  Terraform
human access:            AWS IAM Identity Center
CI/CD identity:          GitHub Actions OIDC -> AWS STS
Terraform state:         Amazon S3
observability:           CloudWatch + X-Ray
analytics:               AWS Glue + Amazon Athena
```

O GitHub Actions não armazena access keys persistentes da AWS. Identidades de deployment continuam separadas das identidades de runtime.

## Disciplina de custo e segurança

A arquitetura atual evita serviços que ainda não resolveram um requisito medido.

Exemplos:

- sem Glue crawler quando schemas explícitos são suficientes;
- sem Step Functions apenas por conveniência de desenho;
- sem DynamoDB/cache antes de um workload real de reuse;
- sem requisito de Iceberg até aqui;
- sem vector database antes de uma fase de retrieval;
- sem text-to-SQL irrestrito;
- sem model call na verdade de aplicabilidade ou finding de repositório;
- workgroup dev do Athena com cutoff de `10.485.760` bytes por scan.

## Quality gates

O repositório utiliza atualmente:

```text
Ruff
strict Pyright
Pytest
Terraform fmt / validate
TFLint
Checkov
GitHub Actions
planos Terraform canônicos
checks de convergência pós-deploy
```

Validação final da Phase 4:

```text
Repository Intelligence Ruff:     PASS
Repository Intelligence Pyright:  0 errors / 0 warnings
Repository Intelligence pytest:   174 passed
Correlation Ruff:                 PASS
Correlation Pyright:              0 errors / 0 warnings
Correlation pytest:               116 passed
```

## Estrutura do repositório

```text
.
├── .github/
├── docs/
│   ├── adr/
│   ├── labs/
│   ├── architecture.md
│   ├── architecture.pt-br.md
│   ├── current-state.md
│   ├── roadmap.md
│   └── README.md
├── infra/
│   ├── bootstrap/
│   └── environments/dev/
├── scripts/
├── src/
│   └── opslens/
│       ├── correlation/
│       └── repository_intelligence/
├── tests/
├── README.md
├── README.pt-br.md
├── pyproject.toml
└── uv.lock
```

## Documentação

- [Current State](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [Architecture — English](docs/architecture.md)
- [Arquitetura — Português](docs/architecture.pt-br.md)
- [Índice de ADRs](docs/adr/README.md)
- [Labs e evidência operacional](docs/README.md)

## Próxima fase — Phase 5: Risk Prioritization Engine

A Phase 5 introduz um novo boundary de autoridade: **Risk Policy v1**.

As Phases 0–4 respondem perguntas factuais como “essa versão travada está afetada?” e “qual evidência KEV/EPSS/CVSS existe?”. A Phase 5 passará a mapear deterministicamente esses fatos para uma decisão de prioridade versionada.

Fatores candidatos incluem affected status, KEV, EPSS, CVSS, disponibilidade de correção, futura evidência direct/transitive e runtime, e completude da evidência.

A política deverá ser reproduzível, explicável por fator, versionada e testável sem depender de LLM.

---

O OpsLens é construído intencionalmente primeiro como sistema de evidência e só depois como sistema agentic.
