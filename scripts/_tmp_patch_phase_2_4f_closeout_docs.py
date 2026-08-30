from pathlib import Path

REPLACEMENTS = {
    "README.md": [
        (
            "| Phase 2.4 | GitHub Security Advisories | 🚧 In progress — 2.4E Glue/Athena complete; 2.4F cross-source closeout next |\n| Phase 2.5 | Historical EPSS expansion | ⏳ Not started |",
            "| Phase 2.4 | GitHub Security Advisories | ✅ Complete — Bronze, immutable Silver, Glue/Athena, cross-source proof |\n| Phase 2.5 | Historical EPSS expansion | 🚧 Next |",
        ),
        (
            "The NVD deterministic evidence path is complete from immutable source ingestion through versioned Silver evidence, authoritative watermark promotion, permanent analytics projection, AWS Glue, and bounded Athena queries. The GHSA path is now complete through reviewed-advisory Bronze ingestion, immutable advisory-version Silver runtime, an explicit Glue external table over authoritative Silver bytes, and bounded Athena nested-evidence queries. The current roadmap milestone is Phase 2.4F — GHSA cross-source deterministic evidence and closeout.",
            "The NVD deterministic evidence path is complete from immutable source ingestion through versioned Silver evidence, authoritative watermark promotion, permanent analytics projection, AWS Glue, and bounded Athena queries. The GHSA path is complete through reviewed-advisory Bronze ingestion, immutable advisory-version Silver runtime, an explicit Glue external table over authoritative Silver bytes, bounded Athena nested-evidence queries, and a real CVE-centered cross-source proof across NVD, CISA KEV, FIRST EPSS, and GHSA. The current roadmap milestone is Phase 2.5 — Historical EPSS expansion.",
        ),
        (
            "Phase 2.4D proved a real 10-advisory Bronze attempt end to end. Ten authoritative one-row Parquet objects and one Silver COMPLETE manifest were created, and replay created zero additional S3 versions. Phase 2.4E then exposed the authoritative Silver relation directly through `opslens_dev.ghsa_advisory_versions`: Athena reproduced 10 unique content versions, 18 vulnerability entries, valid nested evidence, seven unavailable CVSS v4 placeholders with zero typed-v4 normalization violations, and remained far below the 10 MiB workgroup cutoff. Package/version applicability remains deterministic Phase 3 work.",
            "Phase 2.4D proved a real 10-advisory Bronze attempt end to end. Ten authoritative one-row Parquet objects and one Silver COMPLETE manifest were created, and replay created zero additional S3 versions. Phase 2.4E then exposed the authoritative Silver relation directly through `opslens_dev.ghsa_advisory_versions`: Athena reproduced 10 unique content versions, 18 vulnerability entries, valid nested evidence, seven unavailable CVSS v4 placeholders with zero typed-v4 normalization violations, and remained far below the 10 MiB workgroup cutoff. Phase 2.4F closed the milestone with `CVE-2026-42350`: one NVD observation, explicit KEV absence for snapshot `2026-08-29`, EPSS `0.00312` at percentile `0.23543` for snapshot `2026-08-30`, one exact GHSA advisory version, and four published Go package ranges with four first-patched versions. Package/version applicability remains deterministic Phase 3 work.",
        ),
    ],
    "README.pt-br.md": [
        (
            "| Phase 2.4 | GitHub Security Advisories | 🚧 Em andamento — Glue/Athena 2.4E concluído; closeout cross-source 2.4F é o próximo gate |\n| Phase 2.5 | Expansão histórica do EPSS | ⏳ Não iniciada |",
            "| Phase 2.4 | GitHub Security Advisories | ✅ Concluída — Bronze, Silver imutável, Glue/Athena e prova cross-source |\n| Phase 2.5 | Expansão histórica do EPSS | 🚧 Próxima |",
        ),
        (
            "O caminho determinístico de evidência do NVD está completo desde a ingestão imutável da fonte até Silver versionado, promoção do watermark autoritativo, projeção analítica permanente, AWS Glue e consultas Athena com custo limitado. O caminho GHSA agora está concluído até a ingestão Bronze de advisories reviewed, o runtime Silver imutável por versão de conteúdo, uma tabela Glue explícita sobre os bytes Silver autoritativos e consultas Athena limitadas por custo sobre evidência nested. O milestone atual do roadmap é a Phase 2.4F — evidência determinística cross-source e closeout de GHSA.",
            "O caminho determinístico de evidência do NVD está completo desde a ingestão imutável da fonte até Silver versionado, promoção do watermark autoritativo, projeção analítica permanente, AWS Glue e consultas Athena com custo limitado. O caminho GHSA está completo até a ingestão Bronze de advisories reviewed, o runtime Silver imutável por versão de conteúdo, uma tabela Glue explícita sobre os bytes Silver autoritativos, consultas Athena limitadas por custo sobre evidência nested e uma prova cross-source real entre NVD, CISA KEV, FIRST EPSS e GHSA. O milestone atual do roadmap é a Phase 2.5 — expansão histórica do EPSS.",
        ),
        (
            "A Phase 2.4D comprovou end to end um attempt Bronze real com 10 advisories. Foram criados dez objetos Parquet autoritativos de uma linha e um manifest Silver COMPLETE; o replay criou zero novas versões S3. A Phase 2.4E então expôs a relação Silver autoritativa diretamente por `opslens_dev.ghsa_advisory_versions`: o Athena reproduziu 10 versões de conteúdo únicas, 18 entradas de vulnerabilidade, evidência nested estruturalmente válida, sete placeholders CVSS v4 indisponíveis sem violações de normalização tipada e scans muito abaixo do cutoff de 10 MiB. A aplicabilidade de package/version permanece trabalho determinístico da Phase 3.",
            "A Phase 2.4D comprovou end to end um attempt Bronze real com 10 advisories. Foram criados dez objetos Parquet autoritativos de uma linha e um manifest Silver COMPLETE; o replay criou zero novas versões S3. A Phase 2.4E então expôs a relação Silver autoritativa diretamente por `opslens_dev.ghsa_advisory_versions`: o Athena reproduziu 10 versões de conteúdo únicas, 18 entradas de vulnerabilidade, evidência nested estruturalmente válida, sete placeholders CVSS v4 indisponíveis sem violações de normalização tipada e scans muito abaixo do cutoff de 10 MiB. A Phase 2.4F fechou o milestone com `CVE-2026-42350`: uma observação NVD, ausência KEV explícita no snapshot `2026-08-29`, EPSS `0.00312` no percentil `0.23543` no snapshot `2026-08-30`, uma versão exata de advisory GHSA e quatro ranges publicados para pacote Go com quatro first-patched versions. A aplicabilidade de package/version permanece trabalho determinístico da Phase 3.",
        ),
    ],
    "docs/README.md": [
        (
            "Phase 2.4A completed the GitHub Security Advisory source/synchronization contract, Phase 2.4B froze deterministic advisory-content identity and Silver schema v1, Phase 2.4C proved the reviewed-only GHSA Bronze AWS runtime, Phase 2.4D proved immutable advisory-version Silver persistence with exact Bronze VersionIds and zero-new-version replay, and Phase 2.4E exposed that authoritative Silver relation directly through an explicit Glue table and bounded Athena queries. Phase 2.4F — cross-source deterministic evidence and GHSA closeout — is next.",
            "Phase 2.4A completed the GitHub Security Advisory source/synchronization contract, Phase 2.4B froze deterministic advisory-content identity and Silver schema v1, Phase 2.4C proved the reviewed-only GHSA Bronze AWS runtime, Phase 2.4D proved immutable advisory-version Silver persistence with exact Bronze VersionIds and zero-new-version replay, Phase 2.4E exposed that authoritative Silver relation directly through an explicit Glue table and bounded Athena queries, and Phase 2.4F proved source-local cross-source evidence across NVD, CISA KEV, FIRST EPSS, and GHSA. Phase 2.4 is complete; Phase 2.5 — Historical EPSS expansion — is next.",
        ),
        (
            "- [`phase-2-ghsa-glue-athena-closeout.md`](labs/phase-2-ghsa-glue-athena-closeout.md) — completed Phase 2.4E Glue deployment and real Athena evidence for exact content identity, nested package/CWE/CVSS structures, CVSS placeholder preservation, and bounded scans.",
            "- [`phase-2-ghsa-glue-athena-closeout.md`](labs/phase-2-ghsa-glue-athena-closeout.md) — completed Phase 2.4E Glue deployment and real Athena evidence for exact content identity, nested package/CWE/CVSS structures, CVSS placeholder preservation, and bounded scans.\n- [`phase-2-ghsa-cross-source-evidence-contract.md`](labs/phase-2-ghsa-cross-source-evidence-contract.md) — Phase 2.4F contract for explicit source-time coordinates, source-local authority, no lossy four-way join, and the Phase 3 package-range boundary.\n- [`phase-2-ghsa-cross-source-coordinate-discovery.md`](labs/phase-2-ghsa-cross-source-coordinate-discovery.md) — real read-only AWS discovery of EPSS, KEV, NVD, GHSA, Glue, and Athena proof coordinates.\n- [`phase-2-ghsa-cross-source-cve-selection.md`](labs/phase-2-ghsa-cross-source-cve-selection.md) — deterministic GHSA-seeded CVE overlap selection proving the empirical 3/4 maximum overlap and selecting `CVE-2026-42350`.\n- [`phase-2-ghsa-cross-source-closeout.md`](labs/phase-2-ghsa-cross-source-closeout.md) — completed Phase 2.4F source-local evidence bundle, package/range/fix proof, scan-cost evidence, and Phase 2.4 closeout.",
        ),
        (
            "Phase 2.4E — GHSA Glue/Athena Analytics:     COMPLETE\nPhase 2.4F — GHSA Cross-source Closeout:     NEXT\nPhase 2.5 — Historical EPSS expansion:       NOT STARTED",
            "Phase 2.4E — GHSA Glue/Athena Analytics:     COMPLETE\nPhase 2.4F — GHSA Cross-source Closeout:     COMPLETE\nPhase 2.4 — GitHub Security Advisories:       COMPLETE\nPhase 2.5 — Historical EPSS expansion:       NEXT",
        ),
        (
            "Phase 2.4E — GHSA Glue/Athena Analytics — is complete. The authoritative one-row Silver Parquets are now queryable directly through `opslens_dev.ghsa_advisory_versions`; real Athena proofs returned 10/10 unique content versions, 18 vulnerability entries, structurally valid nested evidence, seven unavailable CVSS v4 placeholders with zero fabricated typed metrics, and scans of 6,035 and 72,077 bytes. Phase 2.4F is next. Phase 2 remains open; cross-source exit criteria and historical EPSS expansion must still pass or be explicitly deferred before Phase 3 begins.",
            "Phase 2.4E — GHSA Glue/Athena Analytics — is complete. The authoritative one-row Silver Parquets are queryable directly through `opslens_dev.ghsa_advisory_versions`; real Athena proofs returned 10/10 unique content versions, 18 vulnerability entries, structurally valid nested evidence, seven unavailable CVSS v4 placeholders with zero fabricated typed metrics, and scans of 6,035 and 72,077 bytes. Phase 2.4F is also complete: the real `CVE-2026-42350` bundle preserved one NVD observation, explicit KEV absence, one EPSS score, one exact GHSA advisory version, and four package/range/fix entries while every source-local query remained below the unchanged 10 MiB cutoff. Phase 2.4 is closed. Phase 2 remains open only for Phase 2.5 Historical EPSS expansion before Phase 3 begins, unless that requirement is explicitly deferred under the roadmap rules.",
        ),
    ],
    "docs/architecture.md": [
        (
            "- explicit GHSA Glue catalog over authoritative Silver and bounded Athena nested-evidence analytics;",
            "- explicit GHSA Glue catalog over authoritative Silver and bounded Athena nested-evidence analytics;\n- deterministic CVE-centered cross-source evidence across NVD, CISA KEV, FIRST EPSS, and GHSA with explicit source-time coordinates;",
        ),
        (
            "GitHub Security Advisories          IMPLEMENTED through immutable Silver; Glue/Athena next\nEPSS historical expansion           NOT STARTED",
            "GitHub Security Advisories          IMPLEMENTED through cross-source deterministic evidence\nEPSS historical expansion           NEXT",
        ),
        (
            "GHSA Phase 2.4A source contract, 2.4B advisory/Silver contract, 2.4C Bronze runtime, and 2.4D immutable Silver runtime are complete. Phase 2.4E — GHSA Glue/Athena Analytics — is the next implementation gate.\n\nPackage/version vulnerability applicability remains deterministic Phase 3 work. Phase 2 remains open until GHSA analytics/cross-source exit criteria and historical EPSS requirements are completed or explicitly deferred; no Bedrock, RAG, or agentic phase should begin as a substitute for those remaining deterministic data-plane milestones.",
            "GHSA Phase 2.4A source contract, 2.4B advisory/Silver contract, 2.4C Bronze runtime, 2.4D immutable Silver runtime, 2.4E Glue/Athena analytics, and 2.4F cross-source deterministic evidence are complete. The closing 2.4F proof selected `CVE-2026-42350` from real GHSA-seeded overlap and preserved one NVD observation, explicit KEV absence for snapshot `2026-08-29`, EPSS evidence for snapshot `2026-08-30`, one exact GHSA advisory content version, and four published package ranges with four first-patched versions.\n\nPackage/version vulnerability applicability remains deterministic Phase 3 work. Phase 2 now remains open only for Historical EPSS expansion in Phase 2.5, unless that requirement is explicitly deferred under the roadmap rules; no Bedrock, RAG, or agentic phase should begin as a substitute for that remaining deterministic data-plane milestone.",
        ),
    ],
    "docs/architecture.pt-br.md": [
        (
            "- catálogo Glue explícito de GHSA sobre Silver autoritativo e analytics Athena com custo limitado sobre evidência nested;",
            "- catálogo Glue explícito de GHSA sobre Silver autoritativo e analytics Athena com custo limitado sobre evidência nested;\n- evidência cross-source determinística centrada em CVE entre NVD, CISA KEV, FIRST EPSS e GHSA com coordenadas temporais explícitas por fonte;",
        ),
        (
            "GitHub Security Advisories          IMPLEMENTED through immutable Silver; Glue/Athena next\nEPSS historical expansion           NOT STARTED",
            "GitHub Security Advisories          IMPLEMENTED through cross-source deterministic evidence\nEPSS historical expansion           NEXT",
        ),
        (
            "As Phases GHSA 2.4A source contract, 2.4B advisory/Silver contract, 2.4C Bronze runtime e 2.4D runtime Silver imutável estão concluídas. A Phase 2.4E — GHSA Glue/Athena Analytics — é o próximo gate de implementação.\n\nA aplicabilidade de vulnerabilidade para package/version permanece um trabalho determinístico da Phase 3. A Phase 2 continua aberta até que os requisitos de analytics/cross-source de GHSA e histórico EPSS sejam concluídos ou explicitamente adiados; Bedrock, RAG ou fases agentic não devem substituir esses milestones determinísticos restantes do data plane.",
            "As Phases GHSA 2.4A source contract, 2.4B advisory/Silver contract, 2.4C Bronze runtime, 2.4D runtime Silver imutável, 2.4E Glue/Athena analytics e 2.4F evidência determinística cross-source estão concluídas. A prova final 2.4F selecionou `CVE-2026-42350` por overlap GHSA real e preservou uma observação NVD, ausência KEV explícita no snapshot `2026-08-29`, evidência EPSS no snapshot `2026-08-30`, uma versão exata de conteúdo GHSA e quatro ranges publicados com quatro first-patched versions.\n\nA aplicabilidade de vulnerabilidade para package/version permanece um trabalho determinístico da Phase 3. A Phase 2 agora continua aberta apenas para a expansão histórica do EPSS na Phase 2.5, salvo adiamento explícito conforme as regras do roadmap; Bedrock, RAG ou fases agentic não devem substituir esse milestone determinístico restante do data plane.",
        ),
    ],
}

for filename, replacements in REPLACEMENTS.items():
    path = Path(filename)
    text = path.read_text()
    for old, new in replacements:
        count = text.count(old)
        if count != 1:
            raise RuntimeError(f"{filename}: expected exactly one occurrence, found {count}: {old[:100]!r}")
        text = text.replace(old, new, 1)
    path.write_text(text)
    print(f"patched {filename}")
