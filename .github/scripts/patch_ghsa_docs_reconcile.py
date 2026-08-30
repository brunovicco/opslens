from pathlib import Path

path = Path(".github/scripts/ghsa_analytics_docs_reconcile.py")
text = path.read_text()

old_literal = (
    '"Phase 2.4A — GHSA Source Contract & Workload Spike é o próximo gate de '
    'implementação. O EPSS histórico vem depois, antes do closeout da Phase 2. '
    'A aplicabilidade de vulnerabilidade por package/version permanece trabalho '
    'determinístico da Phase 3 e não é delegada a um LLM.",'
)
actual_literal = (
    '"A Phase 2.4A — GHSA Source Contract & Workload Spike é o próximo gate de '
    'implementação. A expansão histórica do EPSS vem depois, antes do encerramento '
    'da Phase 2. A aplicabilidade de vulnerabilidade para package/version permanece '
    'um trabalho determinístico da Phase 3 e não é delegada a um LLM.",'
)

old_target = (
    '"Phase 2.4E — GHSA Glue/Athena Analytics está concluída. Phase 2.4F — '
    'evidência determinística cross-source e closeout de GHSA — é o próximo gate '
    'de implementação. O EPSS histórico vem depois, antes do closeout da Phase 2. '
    'A aplicabilidade de vulnerabilidade por package/version permanece trabalho '
    'determinístico da Phase 3 e não é delegada a um LLM.",'
)
new_target = (
    '"A Phase 2.4E — GHSA Glue/Athena Analytics está concluída. A Phase 2.4F — '
    'evidência determinística cross-source e closeout de GHSA — é o próximo gate '
    'de implementação. A expansão histórica do EPSS vem depois, antes do '
    'encerramento da Phase 2. A aplicabilidade de vulnerabilidade para '
    'package/version permanece um trabalho determinístico da Phase 3 e não é '
    'delegada a um LLM.",'
)

if text.count(old_literal) != 1:
    raise RuntimeError("temporary script old PT-BR source literal mismatch")
if text.count(old_target) != 1:
    raise RuntimeError("temporary script old PT-BR target literal mismatch")

text = text.replace(old_literal, actual_literal, 1)
text = text.replace(old_target, new_target, 1)
path.write_text(text)
print("GHSA_DOCS_RECONCILE_TEMP_PATCH=PASS")
