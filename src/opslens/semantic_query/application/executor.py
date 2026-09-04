"""Application service that preserves compiler ownership before Athena execution."""

from __future__ import annotations

from typing import Protocol

from opslens.semantic_query.application.compiler import compile_semantic_query
from opslens.semantic_query.application.models import AthenaQueryResult
from opslens.semantic_query.domain import CompiledAthenaQuery, SemanticQuery


class CompiledQueryExecutor(Protocol):
    """Define the bounded execution capability required by the application layer."""

    def execute(
        self,
        query: CompiledAthenaQuery,
        *,
        max_rows: int,
    ) -> AthenaQueryResult:
        """Execute one compiler-owned query with an explicit row bound."""
        ...


class ExecuteSemanticQuery:
    """Compile a typed semantic query and execute only the resulting SQL artifact."""

    def __init__(self, executor: CompiledQueryExecutor) -> None:
        """Initialize the use case with an explicit outbound executor."""
        self._executor = executor

    def execute(self, query: SemanticQuery) -> AthenaQueryResult:
        """Compile and execute one already-validated semantic query."""
        compiled = compile_semantic_query(query)
        return self._executor.execute(compiled, max_rows=query.limit)
