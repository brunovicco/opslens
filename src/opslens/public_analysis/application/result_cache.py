"""Retain one answer under everything that answer depended on.

Gate 21.3 asks for a result cache "keyed on `(commit sha, index manifest identity)`".
That key is not enough, and the gap is the kind that produces a wrong answer rather than
a slow one.

A verdict depends on four things, not two. The repository pins what is installed. The
index pins which advisories exist and how fresh their sources were. And the KEV and EPSS
snapshots decide `kev_state`, `epss_state` and therefore the Risk Policy score — they are
refreshed on their own schedules, KEV nightly at 23:30 UTC. Same commit, same index, a
KEV refresh in between, and a CVE that was not known-exploited yesterday is today: the
verdict changes while the proposed key does not.

```text
same inputs != same answer
a cache key that omits an input is a stale answer with a fresh timestamp
```

So the key is taken over all four, and it is content-addressed like everything else here,
which makes the omission impossible to reintroduce quietly: adding a source to the
answer without adding it to the key leaves the key computable from fewer things than the
answer, and the type will not let you build it.

**What the key can cost.** It has to be computable before the work it saves, or it saves
nothing. On the dependency path that is free: the request identity is known from the
caller's string, the index identity from one pointer read, the snapshot digests from the
worker's own snapshots. On the repository path the subject identity is the execution id,
which exists only after the lock has been fetched and parsed — so the cache saves
correlation, enrichment and scoring, and does not save the GitHub read.

```text
a cache saves what happens after its key is computable, and nothing before
```

**What it stores is opaque.** The cache holds bytes and the envelope identity that
produced them. It does not know the response format, because the response format does not
exist yet — the wire shape is Phase 22's. A cache that invented one would be the third
place in this system to guess at a serialization, and the other two both had to be
corrected.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Protocol

from opslens.public_analysis.domain import PublicAnalysisValidationError
from opslens.shared.evidence import canonical_json, evidence_id

PUBLIC_ANALYSIS_CACHE_KEY_CONTRACT_VERSION: Final = "public-analysis-cache-key:v1"

_SHA256_LENGTH: Final = 64


@dataclass(frozen=True, slots=True)
class AnalysisCacheKey:
    """Everything one answer depended on, as one content-addressed key.

    Attributes:
        subject_id: What was asked about — a repository execution id, or a dependency
            request id. Both are already content-addressed over their own subject.
        index_id: The correlation index generation that answered.
        kev_sha256: Digest of the complete KEV snapshot used.
        epss_sha256: Digest of the complete EPSS snapshot used.
    """

    subject_id: str
    index_id: str
    kev_sha256: str
    epss_sha256: str

    def __post_init__(self) -> None:
        """Reject a key that does not pin every input.

        Raises:
            PublicAnalysisValidationError: If an identity is missing or malformed.
        """
        for field, value in (
            ("subject_id", self.subject_id),
            ("index_id", self.index_id),
        ):
            if type(value) is not str or "@sha256:" not in value:
                raise PublicAnalysisValidationError(
                    f"analysis cache key {field} must be content-addressed"
                )
        for field, value in (
            ("kev_sha256", self.kev_sha256),
            ("epss_sha256", self.epss_sha256),
        ):
            if (
                type(value) is not str
                or len(value) != _SHA256_LENGTH
                or value != value.lower()
                or not all(character in "0123456789abcdef" for character in value)
            ):
                raise PublicAnalysisValidationError(
                    f"analysis cache key {field} must be a lowercase sha-256 digest"
                )

    @property
    def canonical_payload(self) -> Mapping[str, object]:
        """Project the payload this key's identity is taken over."""
        return {
            "contract_version": PUBLIC_ANALYSIS_CACHE_KEY_CONTRACT_VERSION,
            "epss_sha256": self.epss_sha256,
            "index_id": self.index_id,
            "kev_sha256": self.kev_sha256,
            "subject_id": self.subject_id,
        }

    @property
    def canonical_json(self) -> bytes:
        """Return the exact bytes this key's identity is taken over."""
        return canonical_json(self.canonical_payload)

    @property
    def key_id(self) -> str:
        """Return one content-addressed identity for this key."""
        return evidence_id(
            PUBLIC_ANALYSIS_CACHE_KEY_CONTRACT_VERSION, self.canonical_payload
        )


@dataclass(frozen=True, slots=True)
class CachedAnalysisResult:
    """One retained answer, and what produced it.

    Attributes:
        key: The inputs this answer depended on.
        envelope_id: The identity of the answer itself.
        payload: The retained bytes, whatever the caller chose to store.
        stored_at: When it was retained.
    """

    key: AnalysisCacheKey
    envelope_id: str
    payload: bytes
    stored_at: datetime

    def __post_init__(self) -> None:
        """Reject a retained answer that cannot be trusted or identified.

        Raises:
            PublicAnalysisValidationError: If the answer is unidentified, empty, or
                carries a timestamp with no zone.
        """
        if type(self.envelope_id) is not str or "@sha256:" not in self.envelope_id:
            raise PublicAnalysisValidationError(
                "a retained answer must carry a content-addressed envelope identity"
            )
        if type(self.payload) is not bytes or not self.payload:
            raise PublicAnalysisValidationError(
                "a retained answer cannot be empty; an empty response is a result, not a "
                "cache entry"
            )
        if self.stored_at.tzinfo is None:
            raise PublicAnalysisValidationError(
                "a retained answer must record when it was retained, with a zone"
            )


class AnalysisResultCache(Protocol):
    """Retention for answers, keyed on everything they depended on."""

    def get(self, key: AnalysisCacheKey) -> CachedAnalysisResult | None:
        """Return the retained answer for exactly these inputs, or `None`."""
        ...

    def put(self, result: CachedAnalysisResult) -> None:
        """Retain one answer under the inputs it depended on."""
        ...


class InMemoryAnalysisResultCache:
    """Retention for the lifetime of one worker.

    A warm Lambda serves many requests, and the cheapest cache is the one that needs no
    store. It is deliberately not shared: two workers holding different KEV snapshots
    would key differently, which is correct, and would not see each other's entries,
    which is a miss rather than a wrong answer.

    ```text
    a cache miss != a wrong answer
    ```
    """

    def __init__(self) -> None:
        """Start empty."""
        self._entries: dict[str, CachedAnalysisResult] = {}

    @property
    def size(self) -> int:
        """Return how many answers are retained."""
        return len(self._entries)

    def get(self, key: AnalysisCacheKey) -> CachedAnalysisResult | None:
        """Return the retained answer for exactly these inputs.

        Args:
            key: The inputs an answer would depend on.

        Returns:
            The retained answer, or `None`.
        """
        return self._entries.get(key.key_id)

    def put(self, result: CachedAnalysisResult) -> None:
        """Retain one answer.

        Re-retaining under the same key replaces the entry. The key pins every input, so
        two answers under one key are the same answer — and if they are not, the key is
        wrong and overwriting is the lesser of the two problems.

        Args:
            result: The answer to retain.
        """
        self._entries[result.key.key_id] = result


def retain(
    cache: AnalysisResultCache,
    *,
    key: AnalysisCacheKey,
    envelope_id: str,
    payload: bytes,
    now: datetime | None = None,
) -> CachedAnalysisResult:
    """Retain one answer and return what was retained.

    Args:
        cache: Where to retain it.
        key: The inputs the answer depended on.
        envelope_id: The identity of the answer.
        payload: The bytes to retain.
        now: When it is being retained; defaults to the current instant.

    Returns:
        The retained entry.

    Raises:
        PublicAnalysisValidationError: If the entry is not retainable.
    """
    result = CachedAnalysisResult(
        key=key,
        envelope_id=envelope_id,
        payload=payload,
        stored_at=now or datetime.now(UTC),
    )
    cache.put(result)
    return result


__all__ = [
    "PUBLIC_ANALYSIS_CACHE_KEY_CONTRACT_VERSION",
    "AnalysisCacheKey",
    "AnalysisResultCache",
    "CachedAnalysisResult",
    "InMemoryAnalysisResultCache",
    "retain",
]
