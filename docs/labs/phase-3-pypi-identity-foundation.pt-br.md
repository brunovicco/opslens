# Phase 3 — Fundação de identidade PyPI

Este laboratório possui uma versão técnica principal em inglês em `phase-3-pypi-identity-foundation.md`.

Resumo da decisão:

- primeiro ecossistema: PyPI;
- alias GHSA aceito: `pip -> pypi`;
- nomes seguem a normalização oficial PyPA;
- versões concretas seguem PEP 440 por meio de um parser compatível;
- purls são validados de forma restrita e fail-closed;
- qualifiers/subpaths ficam explicitamente fora do contrato v1;
- nenhuma decisão de vulnerabilidade é feita por LLM;
- esta etapa ainda não avalia o vulnerable range.

Próximo gate: parser tipado de ranges GHSA e avaliação determinística `affected / not_affected / unsupported`.
