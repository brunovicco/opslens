"""Guard test for the Phase 3 deterministic boundary."""

from pathlib import Path


def test_correlation_domain_does_not_import_llm_or_bedrock_clients() -> None:
    """Package applicability foundations remain independent of generative runtimes."""
    source = Path("src/opslens/correlation/domain/pypi.py").read_text(encoding="utf-8").lower()
    assert "bedrock" not in source
    assert "langchain" not in source
    assert "openai" not in source
