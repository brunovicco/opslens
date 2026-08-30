from pathlib import Path


def replace_exact(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{path}: expected exactly one match, found {count}: {old[:120]!r}"
        )
    p.write_text(text.replace(old, new, 1))


# Phase 2.4E design closeout.
replace_exact(
    "docs/labs/phase-2-ghsa-glue-athena-design.md",
    "_Status: SELECTED FOR IMPLEMENTATION_",
    "_Status: COMPLETE — live Glue deployment and bounded Athena proof passed on 2026-08-30_",
)
replace_exact(
    "docs/labs/phase-2-ghsa-glue-athena-design.md",
    """2.4E-1  freeze direct-Silver analytics contract                 COMPLETE by this document
2.4E-2  add explicit Glue ghsa_advisory_versions table
2.4E-3  static Terraform/schema validation
2.4E-4  live Terraform plan/apply
2.4E-5  deterministic Athena query + PyArrow equivalence proof
2.4E-6  cost/cardinality/nested-evidence proof
2.4E-7  closeout and handoff to 2.4F""",
    """2.4E-1  freeze direct-Silver analytics contract                 COMPLETE
2.4E-2  add explicit Glue ghsa_advisory_versions table            COMPLETE
2.4E-3  static Terraform/schema validation                         COMPLETE
2.4E-4  live Terraform plan/apply                                  COMPLETE
2.4E-5  deterministic Athena query / exact Silver identity proof   COMPLETE
2.4E-6  cost/cardinality/nested-evidence/CVSS proof                COMPLETE
2.4E-7  closeout and handoff to 2.4F                               COMPLETE""",
)
replace_exact(
    "docs/labs/phase-2-ghsa-glue-athena-design.md",
    """GHSA_2_4E_1_GATE=PASS
```

Phase 2.4E overall remains open until the real Glue/Athena proof passes.""",
    """GHSA_2_4E_1_GATE=PASS
GHSA_ANALYTICS_GLUE_SCHEMA_STATIC_GATE=PASS
GHSA_ANALYTICS_NO_PARTITION_GATE=PASS
GHSA_ANALYTICS_DEPLOYMENT_IAM_STATIC_GATE=PASS
GHSA_ANALYTICS_BOOTSTRAP_LIVE_PLAN_GATE=PASS
GHSA_ANALYTICS_BOOTSTRAP_LIVE_APPLY_GATE=PASS
GHSA_ANALYTICS_DEV_LIVE_PLAN_GATE=PASS
GHSA_ANALYTICS_DEV_LIVE_APPLY_GATE=PASS
GHSA_ANALYTICS_ATHENA_BASE_QUERY_GATE=PASS
GHSA_ANALYTICS_ATHENA_IDENTITY_GATE=PASS
GHSA_ANALYTICS_ATHENA_COST_GATE=PASS
GHSA_ANALYTICS_COMPLEX_TYPES_GATE=PASS
GHSA_ANALYTICS_CVSS_SEMANTIC_GATE=PASS
GHSA_2_4E_GATE=PASS
```

Real proof is recorded in `phase-2-ghsa-glue-athena-closeout.md`. Phase 2.4F is the next authorized GHSA gate.""",
)

# Documentation index.
replace_exact(
    "docs/README.md",
    "Phase 2.4A completed the GitHub Security Advisory source/synchronization contract, Phase 2.4B froze deterministic advisory-content identity and Silver schema v1, Phase 2.4C proved the reviewed-only GHSA Bronze AWS runtime, and Phase 2.4D proved immutable advisory-version Silver persistence with exact Bronze VersionIds, deterministic one-row Parquet content objects, COMPLETE provenance, least-privilege IAM, and zero-new-version replay. Phase 2.4E — GHSA Glue/Athena Analytics — is next.",
    "Phase 2.4A completed the GitHub Security Advisory source/synchronization contract, Phase 2.4B froze deterministic advisory-content identity and Silver schema v1, Phase 2.4C proved the reviewed-only GHSA Bronze AWS runtime, Phase 2.4D proved immutable advisory-version Silver persistence with exact Bronze VersionIds and zero-new-version replay, and Phase 2.4E exposed that authoritative Silver relation directly through an explicit Glue table and bounded Athena queries. Phase 2.4F — cross-source deterministic evidence and GHSA closeout — is next.",
)
replace_exact(
    "docs/README.md",
    "- [`phase-2-ghsa-silver-runtime-closeout.md`](labs/phase-2-ghsa-silver-runtime-closeout.md) — completed Phase 2.4D exact Bronze-to-Silver runtime, immutable content objects, COMPLETE provenance, CVSS placeholder refinement, Terraform deployment, and zero-new-version replay proof.",
    "- [`phase-2-ghsa-silver-runtime-closeout.md`](labs/phase-2-ghsa-silver-runtime-closeout.md) — completed Phase 2.4D exact Bronze-to-Silver runtime, immutable content objects, COMPLETE provenance, CVSS placeholder refinement, Terraform deployment, and zero-new-version replay proof.\n- [`phase-2-ghsa-glue-athena-design.md`](labs/phase-2-ghsa-glue-athena-design.md) — selected Phase 2.4E direct-Silver analytics boundary, explicit schema, zero-partition v1 table, cost boundary, and current-state semantics.\n- [`phase-2-ghsa-glue-athena-closeout.md`](labs/phase-2-ghsa-glue-athena-closeout.md) — completed Phase 2.4E Glue deployment and real Athena evidence for exact content identity, nested package/CWE/CVSS structures, CVSS placeholder preservation, and bounded scans.",
)
replace_exact(
    "docs/README.md",
    "Phase 2.4E — GHSA Glue/Athena Analytics:     NEXT\nPhase 2.4F — GHSA Cross-source Closeout:     NOT STARTED",
    "Phase 2.4E — GHSA Glue/Athena Analytics:     COMPLETE\nPhase 2.4F — GHSA Cross-source Closeout:     NEXT",
)
replace_exact(
    "docs/README.md",
    "Phase 2.4E — GHSA Glue/Athena Analytics — is next. Phase 2 remains open; GHSA analytics/cross-source exit criteria and historical EPSS expansion must still pass or be explicitly deferred before Phase 3 begins.",
    "Phase 2.4E — GHSA Glue/Athena Analytics — is complete. The authoritative one-row Silver Parquets are now queryable directly through `opslens_dev.ghsa_advisory_versions`; real Athena proofs returned 10/10 unique content versions, 18 vulnerability entries, structurally valid nested evidence, seven unavailable CVSS v4 placeholders with zero fabricated typed metrics, and scans of 6,035 and 72,077 bytes. Phase 2.4F is next. Phase 2 remains open; cross-source exit criteria and historical EPSS expansion must still pass or be explicitly deferred before Phase 3 begins.",
)

# Root README EN.
replace_exact(
    "README.md",
    "| Phase 2.4 | GitHub Security Advisories | 🚧 In progress — 2.4D Silver runtime complete; 2.4E Glue/Athena next |",
    "| Phase 2.4 | GitHub Security Advisories | 🚧 In progress — 2.4E Glue/Athena complete; 2.4F cross-source closeout next |",
)
replace_exact(
    "README.md",
    "The NVD deterministic evidence path is complete from immutable source ingestion through versioned Silver evidence, authoritative watermark promotion, permanent analytics projection, AWS Glue, and bounded Athena queries. The GHSA path is now complete through reviewed-advisory Bronze ingestion and immutable advisory-version Silver runtime with exact S3 VersionId provenance and replay-safe COMPLETE evidence. The current roadmap milestone is Phase 2.4E — GHSA Glue/Athena Analytics.",
    "The NVD deterministic evidence path is complete from immutable source ingestion through versioned Silver evidence, authoritative watermark promotion, permanent analytics projection, AWS Glue, and bounded Athena queries. The GHSA path is now complete through reviewed-advisory Bronze ingestion, immutable advisory-version Silver runtime, an explicit Glue external table over authoritative Silver bytes, and bounded Athena nested-evidence queries. The current roadmap milestone is Phase 2.4F — GHSA cross-source deterministic evidence and closeout.",
)
replace_exact(
    "README.md",
    """Silver COMPLETE manifest
  occurrence -> exact content VersionId
```""",
    """Silver COMPLETE manifest
  occurrence -> exact content VersionId
        |
        v
AWS Glue Data Catalog
opslens_dev.ghsa_advisory_versions
        |
        v
Amazon Athena
```""",
)
replace_exact(
    "README.md",
    "Phase 2.4D proved a real 10-advisory Bronze attempt end to end. Ten authoritative one-row Parquet objects and one Silver COMPLETE manifest were created. A second invocation reproduced the same identities and created zero additional S3 versions. Package/version applicability remains deterministic Phase 3 work.",
    "Phase 2.4D proved a real 10-advisory Bronze attempt end to end. Ten authoritative one-row Parquet objects and one Silver COMPLETE manifest were created, and replay created zero additional S3 versions. Phase 2.4E then exposed the authoritative Silver relation directly through `opslens_dev.ghsa_advisory_versions`: Athena reproduced 10 unique content versions, 18 vulnerability entries, valid nested evidence, seven unavailable CVSS v4 placeholders with zero typed-v4 normalization violations, and remained far below the 10 MiB workgroup cutoff. Package/version applicability remains deterministic Phase 3 work.",
)
replace_exact(
    "README.md",
    "- no Glue crawler for EPSS, KEV, or NVD;",
    "- no Glue crawler for EPSS, KEV, NVD, or GHSA;",
)
replace_exact(
    "README.md",
    "Phase 2.4A — GHSA Source Contract & Workload Spike is the next implementation gate. Historical EPSS follows before Phase 2 closeout. Package/version vulnerability applicability remains deterministic Phase 3 work and is not delegated to an LLM.",
    "Phase 2.4E — GHSA Glue/Athena Analytics is complete. Phase 2.4F — cross-source deterministic evidence and GHSA closeout — is the next implementation gate. Historical EPSS follows before Phase 2 closeout. Package/version vulnerability applicability remains deterministic Phase 3 work and is not delegated to an LLM.",
)

# Root README PT-BR.
replace_exact(
    "README.pt-br.md",
    "| Phase 2.4 | GitHub Security Advisories | 🚧 Em andamento — runtime Silver 2.4D concluído; Glue/Athena 2.4E é o próximo gate |",
    "| Phase 2.4 | GitHub Security Advisories | 🚧 Em andamento — Glue/Athena 2.4E concluído; closeout cross-source 2.4F é o próximo gate |",
)
replace_exact(
    "README.pt-br.md",
    "O caminho determinístico de evidência do NVD está completo desde a ingestão imutável da fonte até Silver versionado, promoção do watermark autoritativo, projeção analítica permanente, AWS Glue e consultas Athena com custo limitado. O caminho GHSA agora está concluído até a ingestão Bronze de advisories reviewed e o runtime Silver imutável de versões de advisory, com proveniência por VersionId exato do S3 e evidência COMPLETE segura para replay. O milestone atual do roadmap é a Phase 2.4E — GHSA Glue/Athena Analytics.",
    "O caminho determinístico de evidência do NVD está completo desde a ingestão imutável da fonte até Silver versionado, promoção do watermark autoritativo, projeção analítica permanente, AWS Glue e consultas Athena com custo limitado. O caminho GHSA agora está concluído até a ingestão Bronze de advisories reviewed, o runtime Silver imutável por versão de conteúdo, uma tabela Glue explícita sobre os bytes Silver autoritativos e consultas Athena limitadas por custo sobre evidência nested. O milestone atual do roadmap é a Phase 2.4F — evidência determinística cross-source e closeout de GHSA.",
)
replace_exact(
    "README.pt-br.md",
    """manifest Silver COMPLETE
  ocorrência -> VersionId exato do conteúdo
```""",
    """manifest Silver COMPLETE
  ocorrência -> VersionId exato do conteúdo
        |
        v
AWS Glue Data Catalog
opslens_dev.ghsa_advisory_versions
        |
        v
Amazon Athena
```""",
)
replace_exact(
    "README.pt-br.md",
    "A Phase 2.4D comprovou end to end um attempt Bronze real com 10 advisories. Foram criados dez objetos Parquet autoritativos de uma linha e um manifest Silver COMPLETE. Uma segunda invocação reproduziu as mesmas identidades e criou zero novas versões S3. A aplicabilidade de package/version permanece trabalho determinístico da Phase 3.",
    "A Phase 2.4D comprovou end to end um attempt Bronze real com 10 advisories. Foram criados dez objetos Parquet autoritativos de uma linha e um manifest Silver COMPLETE; o replay criou zero novas versões S3. A Phase 2.4E então expôs a relação Silver autoritativa diretamente por `opslens_dev.ghsa_advisory_versions`: o Athena reproduziu 10 versões de conteúdo únicas, 18 entradas de vulnerabilidade, evidência nested estruturalmente válida, sete placeholders CVSS v4 indisponíveis sem violações de normalização tipada e scans muito abaixo do cutoff de 10 MiB. A aplicabilidade de package/version permanece trabalho determinístico da Phase 3.",
)
replace_exact(
    "README.pt-br.md",
    "- nenhum Glue crawler para EPSS, KEV ou NVD;",
    "- nenhum Glue crawler para EPSS, KEV, NVD ou GHSA;",
)
replace_exact(
    "README.pt-br.md",
    "Phase 2.4A — GHSA Source Contract & Workload Spike é o próximo gate de implementação. O EPSS histórico vem depois, antes do closeout da Phase 2. A aplicabilidade de vulnerabilidade por package/version permanece trabalho determinístico da Phase 3 e não é delegada a um LLM.",
    "Phase 2.4E — GHSA Glue/Athena Analytics está concluída. Phase 2.4F — evidência determinística cross-source e closeout de GHSA — é o próximo gate de implementação. O EPSS histórico vem depois, antes do closeout da Phase 2. A aplicabilidade de vulnerabilidade por package/version permanece trabalho determinístico da Phase 3 e não é delegada a um LLM.",
)

# Architecture EN.
replace_exact(
    "docs/architecture.md",
    "- GHSA immutable advisory-version Silver content objects and attempt-level COMPLETE provenance;",
    "- GHSA immutable advisory-version Silver content objects and attempt-level COMPLETE provenance;\n- explicit GHSA Glue catalog over authoritative Silver and bounded Athena nested-evidence analytics;",
)
replace_exact(
    "docs/architecture.md",
    """Silver COMPLETE manifest
```""",
    """Silver COMPLETE manifest
        |
        v
AWS Glue Data Catalog
opslens_dev.ghsa_advisory_versions
        |
        v
Amazon Athena
```""",
)
replace_exact(
    "docs/architecture.md",
    "GHSA Glue/Athena analytics is intentionally deferred to Phase 2.4E. Package/version applicability remains deterministic Phase 3 work.",
    "Phase 2.4E exposes the authoritative Silver relation directly as `opslens_dev.ghsa_advisory_versions`, with no projector, crawler, or Glue partitions. Real Athena proofs returned 10 unique content versions, 18 vulnerability entries, structurally valid nested identifiers/CWEs/CVSS/package evidence, seven unavailable CVSS v4 placeholders with zero fabricated typed metrics, and scans of 6,035 and 72,077 bytes under the unchanged 10 MiB cutoff. Package/version applicability remains deterministic Phase 3 work.",
)

# Architecture PT-BR.
replace_exact(
    "docs/architecture.pt-br.md",
    "- objetos Silver imutáveis por versão de advisory GHSA e proveniência COMPLETE por attempt;",
    "- objetos Silver imutáveis por versão de advisory GHSA e proveniência COMPLETE por attempt;\n- catálogo Glue explícito para GHSA sobre Silver autoritativo e analytics nested no Athena com custo limitado;",
)
replace_exact(
    "docs/architecture.pt-br.md",
    """manifest Silver COMPLETE
```""",
    """manifest Silver COMPLETE
        |
        v
AWS Glue Data Catalog
opslens_dev.ghsa_advisory_versions
        |
        v
Amazon Athena
```""",
)
replace_exact(
    "docs/architecture.pt-br.md",
    "Glue/Athena para GHSA fica intencionalmente para a Phase 2.4E. Aplicabilidade de package/version permanece trabalho determinístico da Phase 3.",
    "A Phase 2.4E expõe a relação Silver autoritativa diretamente como `opslens_dev.ghsa_advisory_versions`, sem projector, crawler ou partições Glue. Provas reais no Athena retornaram 10 versões de conteúdo únicas, 18 entradas de vulnerabilidade, identifiers/CWEs/CVSS/evidência de package nested estruturalmente válidos, sete placeholders CVSS v4 indisponíveis sem métricas tipadas fabricadas e scans de 6.035 e 72.077 bytes sob o cutoff inalterado de 10 MiB. Aplicabilidade de package/version permanece trabalho determinístico da Phase 3.",
)

for path in [
    "README.md",
    "README.pt-br.md",
    "docs/README.md",
    "docs/architecture.md",
    "docs/architecture.pt-br.md",
    "docs/labs/phase-2-ghsa-glue-athena-design.md",
]:
    text = Path(path).read_text()
    if "2.4E — GHSA Glue/Athena Analytics — is next" in text:
        raise RuntimeError(f"{path}: stale English 2.4E-next marker remains")

print("GHSA_ANALYTICS_DOC_RECONCILIATION=PASS")
