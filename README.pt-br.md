<div align="center">

🇺🇸 [English](README.md) &nbsp;|&nbsp; 🇧🇷 **Português**

# OpsLens

### Inteligência Determinística de Software Supply Chain e Threat Intelligence na AWS

**Threat Intelligence · Repository Intelligence · Vulnerability Correlation · Risk Prioritization · Evidência Determinística · AWS Serverless**

</div>

OpsLens é uma plataforma open source de inteligência para software supply chain construída na AWS.

Ela foi projetada para responder:

> Considerando o software que eu realmente utilizo, quais vulnerabilidades o afetam, qual evidência prova isso e quais findings devo priorizar?

O projeto estabelece primeiro evidência determinística, proveniência, correlação de package/version, enforcement de política de risco, limites de least privilege, observabilidade, recuperação de falhas e controles de custo. Raciocínio semântico, generativo e agentic entram somente depois dessas fundações.

> **Agents reason. Code verifies evidence.**

## Status atual

| Fase | Escopo | Status |
| --- | --- | --- |
| Phase 0 | AWS Foundation | ✅ Concluída |
| Phase 1 | EPSS Vertical Slice | ✅ Concluída |
| Phase 2 | Threat Intelligence Data Lake | ✅ Concluída |
| Phase 3 | Vulnerability Correlation Engine | ✅ Concluída |
| Phase 4 | Repository Intelligence | ✅ Concluída |
| Phase 5 | Risk Prioritization Engine | ✅ Concluída |
| Phase 6 | Semantic Query Layer | 🚧 Próxima |

Último checkpoint de implementação antes do closeout documental da Phase 5:

```text
81a2e78a3e8329aa811c20012bc565f35f1a87e5
```

Veja [Current State](docs/current-state.md) e [Roadmap](docs/roadmap.md) para o estado detalhado.

## O que o OpsLens já faz hoje

O caminho determinístico atual consegue analisar um snapshot suportado de um repositório público no GitHub sem executar o código do repositório, correlacionar dependências PyPI travadas com ranges vulneráveis GHSA exatos, enriquecer findings afetados com threat intelligence source-preserving e priorizá-los por uma política explícita e versionada.

```text
NVD / CVE -----------+
CISA KEV ------------+
FIRST EPSS ----------+----> evidência de threat intelligence preservada
GitHub Advisories ---+
                              |
                              v
repositório público GitHub
 -> snapshot imutável do repositório
 -> aquisição GET-only limitada
 -> evidência inerte exata do uv.lock
 -> parsing determinístico com tomllib
 -> normalização PyPI / PEP 440 / purl
 -> aplicabilidade do vulnerable range GHSA
 -> enrichment NVD/CVSS exato
 -> evidência CISA KEV de snapshot completo
 -> evidência FIRST EPSS de snapshot explícito
 -> RepositoryAnalysisResult content-addressed
 -> Risk Policy v1 determinística
 -> contribuições por fator
 -> priority score / tier / completude
 -> RiskPrioritizationResult content-addressed
```

Nenhum código de repositório de terceiro é executado.

## Invariantes centrais

- Evidência e correlação determinísticas primeiro; raciocínio de modelo depois.
- **Nenhum LLM decide aplicabilidade de vulnerabilidade.**
- **Avaliação da política de risco é determinística.**
- A evidência bruta da fonte é preservada antes da transformação.
- Versões exatas da fonte e hashes de conteúdo participam da identidade da evidência.
- Semânticas inválidas ou não suportadas falham fechado.
- Código de repositórios de terceiros nunca é executado durante a análise.
- Repository Risk não é Runtime Exposure.
- Evidência ausente não é interpretada silenciosamente como evidência benigna.
- Entrega duplicada é esperada e replay precisa ser seguro.
- IAM least privilege e separação de responsabilidades são requisitos arquiteturais.
- Serviços AWS entram apenas quando resolvem um requisito demonstrado.
- Planejamento em linguagem natural nunca recebe autoridade SQL irrestrita.

## Threat Intelligence Data Lake — Phase 2

A Phase 2 fornece a evidência determinística consumida pelas fases posteriores.

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

A relação Silver canônica também contém o intervalo histórico concluído entre `2021-04-14` e `2026-08-13`, sob um commit de archive histórico fixado.

### CISA KEV

```text
CISA KEV
 -> ingestão limitada
 -> Bronze imutável
 -> Silver determinístico
 -> Parquet
 -> Glue
 -> Athena
```

Presença ou ausência KEV só tem significado contra um snapshot do catálogo completo, validado e explicitamente selecionado.

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
 -> normalização determinística
 -> Silver imutável por versão de advisory
 -> Silver COMPLETE
 -> Glue / Athena
```

A evidência GHSA de package/range/fix continua source-local mesmo quando o mesmo CVE é observado independentemente pelo NVD.

## Vulnerability Correlation Engine — Phase 3

A Phase 3 está concluída para o primeiro ecossistema suportado: **PyPI**.

Semânticas implementadas:

```text
normalização PyPA de package name
versões concretas PEP 440
purl PyPI canônico
operadores de range GHSA: = < <= > >=
affected | not_affected | unsupported
first-patched-version como evidência
proveniência exata da ocorrência GHSA
reconciliação CVE/GHSA/NVD
correlation:v1@sha256:<digest>
```

`first_patched_version` é evidência de remediação. Nunca substitui a aplicabilidade do vulnerable range.

Veja [Phase 3 correlation closeout](docs/labs/phase-3-correlation-engine-closeout.md).

## Repository Intelligence — Phase 4

O escopo v1 de repositório é intencionalmente estreito:

```text
provider:        GitHub público
arquivo:         uv.lock na raiz
dependências:    registros PyPI canônicos
transporte:      read only
execução código: nunca
```

A autoridade do repositório é a identidade numérica imutável do GitHub mais o commit SHA exato. Leituras de dependências são vinculadas ao commit, não a um branch móvel.

A identidade agregada final da Phase 4 é:

```text
repository-analysis:v1@sha256:<digest>
```

O commit do repositório sozinho não é uma futura cache key segura porque as evidências KEV/EPSS selecionadas são temporais. Por isso a Phase 4 adiou infraestrutura de cache até que um workload medido justifique storage, invalidação, IAM, observabilidade e custo.

Veja [Phase 4 Repository Intelligence closeout](docs/labs/phase-4-repository-intelligence-closeout.md).

## Risk Prioritization Engine — Phase 5

A Phase 5 está concluída com uma **Risk Policy v1** determinística e separada da verdade das fontes.

A política consome apenas fatos já estabelecidos pela Phase 4:

```text
KEV presente                         +40
EPSS >= 0.70 / 0.30 / 0.10           +30 / +20 / +10
maior CVSS suportado >= 9 / 7 / 4     +20 / +10 / +5
fixed version conhecida              +10
máximo                                100
```

Priority tiers:

```text
P0 >= 80
P1 >= 60
P2 >= 30
P3 < 30
```

Esse valor é um **priority score do OpsLens**. Não é probabilidade de exploração, substituto de CVSS, reescrita de KEV/EPSS ou score de runtime exposure.

O máximo CVSS é uma agregação downstream explícita da política. As observações NVD CVSS originais continuam preservadas.

Evidência ausente permanece explícita:

```text
evidência negativa completa
  KEV ausente em catálogo completo
  score EPSS ausente em snapshot completo

partial / review_required
  CVE indisponível
  nenhuma evidência CVSS suportada
  família CVSS futura não suportada
```

Identidades content-addressed da política:

```text
risk-policy:v1@sha256:<digest>
risk-evaluation:v1@sha256:<digest>
risk-prioritization:v1@sha256:<digest>
```

Findings empatados em score usam um ID opaco estável somente como tie breaker determinístico; esse critério não possui semântica de risco.

A Phase 5 adicionou **zero recursos AWS, zero permissões IAM e zero chamadas de modelo**.

Veja [Phase 5 Risk Policy closeout](docs/labs/phase-5-risk-policy-closeout.md) e [ADR 0019](docs/adr/0019-deterministic-risk-policy-v1.md).

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

A arquitetura evita serviços que ainda não resolveram um requisito medido.

Exemplos:

- sem Glue crawler quando schemas explícitos são suficientes;
- sem Step Functions apenas por conveniência arquitetural;
- sem DynamoDB/cache antes de um workload real de reuse;
- sem requisito de Iceberg até aqui;
- sem vector database antes de uma fase de retrieval;
- sem chamada Bedrock na aplicabilidade ou priorização determinística;
- sem text-to-SQL irrestrito;
- workgroup dev do Athena com cutoff de `10.485.760` bytes por scan.

## Quality gates

Slices determinísticos dedicados de CI cobrem agora:

```text
Correlation
Repository Intelligence
Risk Policy
```

Validação de closeout da Phase 5:

```text
Risk Policy Ruff:                 PASS
Risk Policy Pyright:              0 errors / 0 warnings
Risk Policy pytest:               31 passed
Repository Intelligence pytest:   174 passed
Correlation pytest:               116 passed
```

Mudanças com AWS usam adicionalmente Terraform fmt/validate, TFLint, Checkov, planos canônicos, verificação de deployment e checks de convergência pós-apply.

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
│       ├── repository_intelligence/
│       └── risk_policy/
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

## Próxima fase — Phase 6: Semantic Query Layer

A Phase 6 introduz o primeiro FM planner na sequência atual do roadmap:

```text
Pergunta do usuário
 -> planner Bedrock
 -> SemanticQuery tipada
 -> validação determinística
 -> compilador SQL determinístico
 -> Athena read-only e limitado
 -> evidência estruturada
```

Guardrail permanente:

> **No unrestricted text-to-SQL.**

Antes de escrever código da Phase 6, a documentação oficial atual do Amazon Bedrock e Athena deverá ser verificada para APIs, disponibilidade de modelos, IAM, limites e pricing. A primeira implementação deve congelar um contrato pequeno e tipado de semantic query antes de qualquer API, UI, RAG ou integração agentic.

---

O OpsLens é construído intencionalmente primeiro como sistema de evidência e só depois como sistema agentic.
