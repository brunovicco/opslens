"""Tests for the result cache, and mostly for its key.

The cache itself is a dictionary. The part worth testing is the key, because the failure
it guards is not a slow response — it is a stale verdict served with confidence after a
source refreshed underneath it.

```text
same inputs != same answer
a cache miss != a wrong answer
```

The load-bearing case is `test_a_kev_refresh_changes_the_key`. Gate 21.3 proposed keying
on `(commit sha, index manifest identity)`; KEV refreshes nightly and decides
`kev_state`, so that key would have served yesterday's verdict for a CVE that became
known-exploited overnight.
"""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from opslens.public_analysis.application.result_cache import (
    PUBLIC_ANALYSIS_CACHE_KEY_CONTRACT_VERSION,
    AnalysisCacheKey,
    CachedAnalysisResult,
    InMemoryAnalysisResultCache,
    retain,
)
from opslens.public_analysis.domain import PublicAnalysisValidationError

_EXECUTION = "public-repository-evidence:v1@sha256:" + ("e" * 64)
_INDEX = "opslens-correlation-index:v2@sha256:" + ("b" * 64)
_ENVELOPE = "public-analysis-envelope:v1@sha256:" + ("f" * 64)
_KEV = "c" * 64
_EPSS = "d" * 64
_NOW = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)


def _key(**overrides: str) -> AnalysisCacheKey:
    """Build one valid cache key, with fields overridden for the case at hand."""
    fields: dict[str, str] = {
        "subject_id": _EXECUTION,
        "index_id": _INDEX,
        "kev_sha256": _KEV,
        "epss_sha256": _EPSS,
    }
    fields.update(overrides)
    return AnalysisCacheKey(**fields)


class TestTheKeyPinsEveryInput:
    """Four inputs decide a verdict; a key over two of them is a stale answer."""

    def test_the_same_inputs_produce_the_same_key(self) -> None:
        """Otherwise nothing ever hits."""
        assert _key().key_id == _key().key_id

    def test_a_different_repository_state_changes_the_key(self) -> None:
        """The execution id is content-addressed over the commit and the lock."""
        assert _key().key_id != _key(subject_id=_EXECUTION.replace("e" * 64, "a" * 64)).key_id

    def test_a_rebuilt_index_with_new_content_changes_the_key(self) -> None:
        """A new advisory is a different answer."""
        assert _key().key_id != _key(index_id=_INDEX.replace("b" * 64, "a" * 64)).key_id

    def test_a_kev_refresh_changes_the_key(self) -> None:
        """The case Gate 21.3's proposed key would have missed.

        KEV refreshes nightly at 23:30 UTC and decides `kev_state`, which feeds the Risk
        Policy. Same commit, same index, a refresh in between, and a CVE that was not
        known-exploited yesterday is today.
        """
        assert _key().key_id != _key(kev_sha256="a" * 64).key_id

    def test_an_epss_refresh_changes_the_key(self) -> None:
        """The same reasoning, for the other snapshot."""
        assert _key().key_id != _key(epss_sha256="a" * 64).key_id

    def test_the_key_names_its_contract(self) -> None:
        """A retained key from another contract version must not be read as this one."""
        assert _key().key_id.startswith(
            f"{PUBLIC_ANALYSIS_CACHE_KEY_CONTRACT_VERSION}@sha256:"
        )

    def test_the_payload_carries_exactly_the_four_inputs(self) -> None:
        """Adding an input to the answer without adding it here is the failure mode."""
        assert set(_key().canonical_payload) == {
            "contract_version",
            "epss_sha256",
            "index_id",
            "kev_sha256",
            "subject_id",
        }


class TestTheKeyRefusesWhatItCannotPin:
    """An identity that is not content-addressed cannot pin anything."""

    @pytest.mark.parametrize("field", ["subject_id", "index_id"])
    def test_an_identity_without_a_digest_is_refused(self, field: str) -> None:
        """`opslens-correlation-index:v2` names a contract and no content."""
        with pytest.raises(PublicAnalysisValidationError, match="content-addressed"):
            _key(**{field: "public-repository-evidence:v1"})

    @pytest.mark.parametrize("field", ["kev_sha256", "epss_sha256"])
    def test_a_malformed_snapshot_digest_is_refused(self, field: str) -> None:
        """A truncated or uppercase digest would key two snapshots to one entry."""
        with pytest.raises(PublicAnalysisValidationError, match="sha-256"):
            _key(**{field: "C" * 64})
        with pytest.raises(PublicAnalysisValidationError, match="sha-256"):
            _key(**{field: "c" * 63})


class TestRetention:
    """What is stored is opaque; what is refused is not."""

    def test_an_answer_round_trips(self) -> None:
        """Store, then read back under the same inputs."""
        cache = InMemoryAnalysisResultCache()
        stored = retain(
            cache, key=_key(), envelope_id=_ENVELOPE, payload=b"{}", now=_NOW
        )
        assert cache.get(_key()) == stored
        assert cache.size == 1

    def test_different_inputs_miss(self) -> None:
        """A miss is the correct outcome, not a fallback to the nearest entry."""
        cache = InMemoryAnalysisResultCache()
        retain(cache, key=_key(), envelope_id=_ENVELOPE, payload=b"{}", now=_NOW)
        assert cache.get(_key(kev_sha256="a" * 64)) is None

    def test_re_retaining_under_one_key_replaces(self) -> None:
        """The key pins every input, so two answers under one key are one answer."""
        cache = InMemoryAnalysisResultCache()
        retain(cache, key=_key(), envelope_id=_ENVELOPE, payload=b"first", now=_NOW)
        retain(cache, key=_key(), envelope_id=_ENVELOPE, payload=b"second", now=_NOW)
        entry = cache.get(_key())
        assert entry is not None
        assert entry.payload == b"second"
        assert cache.size == 1

    def test_an_empty_payload_is_refused(self) -> None:
        """An empty response is a result; an empty cache entry is a bug."""
        with pytest.raises(PublicAnalysisValidationError, match="cannot be empty"):
            CachedAnalysisResult(
                key=_key(), envelope_id=_ENVELOPE, payload=b"", stored_at=_NOW
            )

    def test_an_unidentified_answer_is_refused(self) -> None:
        """A retained answer that cannot be named cannot be checked against a rebuild."""
        with pytest.raises(PublicAnalysisValidationError, match="envelope identity"):
            CachedAnalysisResult(
                key=_key(), envelope_id="an answer", payload=b"{}", stored_at=_NOW
            )

    def test_a_naive_timestamp_is_refused(self) -> None:
        """An instant with no zone cannot say how old an answer is."""
        with pytest.raises(PublicAnalysisValidationError, match="with a zone"):
            CachedAnalysisResult(
                key=_key(),
                envelope_id=_ENVELOPE,
                payload=b"{}",
                stored_at=datetime(2026, 9, 17, 12, 0),  # noqa: DTZ001
            )

    def test_the_stored_key_is_the_key_that_was_asked_for(self) -> None:
        """A retained entry must be self-describing, not trusted from its position."""
        cache = InMemoryAnalysisResultCache()
        retain(cache, key=_key(), envelope_id=_ENVELOPE, payload=b"{}", now=_NOW)
        entry = cache.get(_key())
        assert entry is not None
        assert replace(entry.key).key_id == _key().key_id
