"""Measure what one finding costs in a response, because nothing here may be derived.

ADR 0087's correction left one number explicitly unmeasured: the size of a rebuilt
evidence item in an API response. It is neither the projected source row (385 bytes) nor
the stored DynamoDB item (1,078 bytes), and that correction exists precisely because
those two were once conflated.

```text
projected bytes != stored bytes != response bytes
```

Gate 21.1 has to bound a request, and a bound needs a number. This produces it the only
honest way available: build real findings through the real chain and measure the bytes
the final finding projection actually serializes to. No AWS, no network — the chain from
lock to analysis is deterministic and offline once the index is in memory.

What is measured is `RepositoryAnalysisFinding.canonical_json`, which is the only
serialization of a finding this system currently has. The HTTP wire format does not exist
yet, so a number for it would be a guess; when it lands, this script is what re-measures
it rather than a new estimate.

Run:

    uv run python scripts/measure_response_item_size.py
    uv run python scripts/measure_response_item_size.py --write labs/evidence/x.json
"""

import argparse
import base64
import gzip
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from opslens.correlation_index.adapters.in_memory_index_store import (
    InMemoryCorrelationIndexStore,
)
from opslens.correlation_index.domain.index_contract import (
    ProjectedGhsaIndexRow,
    ProjectedSourceIdentifier,
    SourceWatermark,
)
from opslens.ingestion.epss.domain.models import EpssSnapshot
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.public_analysis.adapters.correlation_index_threat_authority import (
    CorrelationIndexThreatEvidenceAuthority,
    ThreatSnapshotSet,
)
from opslens.public_analysis.application import (
    admit_public_analysis_request,
    build_public_repository_evidence,
)
from opslens.public_analysis.application.response_envelope import (
    build_public_analysis_envelope,
)
from opslens.public_analysis.application.threat_evidence_authority import (
    PublicThreatEvidenceRequest,
    build_public_threat_evidence_scope,
)
from opslens.repository_intelligence.domain import (
    compute_git_blob_sha1,
)
from opslens.shared.evidence import canonical_json

MEASUREMENT_CONTRACT_VERSION: Final = "opslens-response-item-size:v1"

_REPOSITORY_ID: Final = 1_333_092_779
_COMMIT_SHA: Final = "3f75a4fc2bd22589df0a5ffe98a8442fda81c8d3"
_TREE_SHA: Final = "01ac6fe03f1db867ef29c6652311ee43b1f63afb"
_ENTRY_DIGEST: Final = "f086757888580ceef4a1f94c58aacb2c28ae445a18fecdac07c6561ff0519f6d"
_BUILT_AT: Final = datetime(2026, 9, 17, 10, 11, 11, tzinfo=UTC)

# The measured page of the live index, from ADR 0087's correction. A request cannot read
# fewer rows than it emits findings, so this is the ceiling any row bound sits under.
_ITEMS_PER_PAGE: Final = 973
_STORED_ITEM_BYTES: Final = 1078


def _advisory_id(index: int) -> str:
    """Return one syntactically valid GHSA id for a generated advisory."""
    alphabet = "23456789cfghjmpqrvwx"
    digits: list[str] = []
    value = index
    for _ in range(12):
        digits.append(alphabet[value % len(alphabet)])
        value //= len(alphabet)
    body = "".join(digits)
    return f"GHSA-{body[0:4]}-{body[4:8]}-{body[8:12]}"


def _lock(package: str, version: str) -> bytes:
    """Build one uv.lock holding a single registry dependency."""
    return (
        b"version = 1\nrevision = 3\nrequires-python = \">=3.13\"\n"
        b"[[package]]\n"
        + f'name = "{package}"\n'.encode()
        + f'version = "{version}"\n'.encode()
        + b'source = { registry = "https://pypi.org/simple" }\n'
    )


@dataclass(slots=True)
class _Source:
    """A GitHub source that serves one fixed snapshot."""

    content: bytes

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        """Return the fixed repository."""
        del owner, name
        return {
            "id": _REPOSITORY_ID,
            "name": "opslens",
            "full_name": "brunovicco/opslens",
            "private": False,
            "visibility": "public",
            "default_branch": "main",
            "owner": {"login": "brunovicco"},
        }

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        """Return the fixed commit."""
        del owner, name, ref
        return {"sha": _COMMIT_SHA, "commit": {"tree": {"sha": _TREE_SHA}}}

    def get_uv_lock(self, owner: str, name: str, commit_sha: str) -> dict[str, object]:
        """Return the fixed lock payload."""
        del owner, name, commit_sha
        return {
            "type": "file",
            "path": "uv.lock",
            "name": "uv.lock",
            "encoding": "base64",
            "size": len(self.content),
            "sha": compute_git_blob_sha1(self.content),
            "content": base64.encodebytes(self.content).decode("ascii"),
        }


def _rows(package: str, count: int, *, identifiers: int) -> list[ProjectedGhsaIndexRow]:
    """Build `count` advisory rows against one package, each with a CVE."""
    rows: list[ProjectedGhsaIndexRow] = []
    for index in range(count):
        advisory = _advisory_id(index)
        digest = hashlib.sha256(advisory.encode()).hexdigest()
        cve = f"CVE-2026-{10000 + index}"
        rows.append(
            ProjectedGhsaIndexRow(
                package_name_canonical=package,
                observed_advisory_version_id=f"{advisory}@sha256:{digest}",
                source_advisory_sha256=digest,
                source_entry_sha256=_ENTRY_DIGEST,
                ghsa_id=advisory,
                github_cve_id=cve,
                github_identifiers=tuple(
                    ProjectedSourceIdentifier(
                        identifier_type="CVE" if position else "GHSA",
                        value=cve if position else advisory,
                    )
                    for position in range(identifiers)
                ),
                vulnerability_entry_id=f"ghsa-entry:v1:{advisory}",
                source_index=0,
                ecosystem_original="pip",
                package_name_original=package,
                vulnerable_range_original=">= 1.0.0, < 99.0.0",
                first_patched_version_original="99.0.0",
            )
        )
    return rows


def _kev(cves: list[str]) -> KevCatalogSnapshot:
    """Build one complete KEV snapshot listing those CVEs."""
    document: dict[str, object] = {
        "title": "CISA Known Exploited Vulnerabilities Catalog",
        "catalogVersion": "2026.09.03",
        "dateReleased": "2026-09-03T12:00:00Z",
        "count": max(len(cves), 1),
        "vulnerabilities": [
            {
                "cveID": cve,
                "vendorProject": "Example",
                "product": "Example",
                "vulnerabilityName": "Example vulnerability",
                "dateAdded": "2026-09-01",
                "shortDescription": "Example description of the vulnerability.",
                "requiredAction": "Apply updates per vendor instructions.",
                "dueDate": "2026-09-22",
                "knownRansomwareCampaignUse": "Unknown",
                "notes": "https://example.com/advisory",
                "cwes": ["CWE-79"],
            }
            for cve in cves or ["CVE-1999-0001"]
        ],
    }
    payload = json.dumps(document, separators=(",", ":")).encode()
    return KevCatalogSnapshot(
        raw_bytes=payload,
        catalog_version="2026.09.03",
        date_released=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
        retrieved_at=datetime(2026, 9, 3, 12, 30, tzinfo=UTC),
        sha256=hashlib.sha256(payload).hexdigest(),
        record_count=max(len(cves), 1),
    )


def _epss(cves: list[str]) -> EpssSnapshot:
    """Build one complete EPSS snapshot scoring those CVEs."""
    lines = [
        "#model_version:v2026.06.15,score_date:2026-09-03T12:00:00Z",
        "cve,epss,percentile",
    ]
    # A complete snapshot always carries rows. When the measurement wants KEV and EPSS
    # to miss, they miss because they name a different CVE, not because the snapshot is
    # empty — an empty snapshot is a different condition and is refused upstream.
    lines.extend(f"{cve},0.42,0.88" for cve in cves or ["CVE-1999-0001"])
    text = "\n".join(lines) + "\n"
    return EpssSnapshotParser().parse(gzip.compress(text.encode(), mtime=0))


@dataclass(frozen=True, slots=True)
class Measurement:
    """One measured finding shape.

    Attributes:
        advisories: How many advisories applied to the dependency.
        enriched: Whether KEV and EPSS knew the CVEs.
        findings: How many findings the chain produced.
        finding_bytes_mean: Mean size of one final finding projection.
        finding_bytes_max: Largest single finding.
        finding_bytes_total: Every finding together.
        identifiers_per_advisory: Source identifiers each advisory carried.
        analysis_projection_bytes: The whole analysis projection.
        envelope_identity_bytes: The envelope identity payload, which is not the body.
    """

    advisories: int
    enriched: bool
    findings: int
    finding_bytes_mean: int
    finding_bytes_max: int
    finding_bytes_total: int
    identifiers_per_advisory: int
    analysis_projection_bytes: int
    envelope_identity_bytes: int

    @property
    def payload(self) -> dict[str, object]:
        """Project this measurement for retention."""
        return {
            "advisories": self.advisories,
            "analysis_projection_bytes": self.analysis_projection_bytes,
            "enriched": self.enriched,
            "envelope_identity_bytes": self.envelope_identity_bytes,
            "finding_bytes_max": self.finding_bytes_max,
            "finding_bytes_mean": self.finding_bytes_mean,
            "finding_bytes_total": self.finding_bytes_total,
            "findings": self.findings,
            "identifiers_per_advisory": self.identifiers_per_advisory,
        }


def measure(*, advisories: int, identifiers: int, enriched: bool) -> Measurement:
    """Measure one shape of finding, end to end through the real chain.

    Args:
        advisories: How many advisories apply to the single dependency.
        identifiers: How many source identifiers each advisory carries.
        enriched: Whether KEV and EPSS know the CVEs.

    Returns:
        One measurement row.
    """
    package = "requests"
    execution = build_public_repository_evidence(
        admit_public_analysis_request(
            b'{"repository_url":"https://github.com/brunovicco/opslens",'
            b'"requested_ref":null}'
        ).request,
        _Source(content=_lock(package, "2.31.0")),
    )
    rows = _rows(package, advisories, identifiers=identifiers)
    cves = [row.github_cve_id for row in rows if row.github_cve_id is not None]
    known = cves if enriched else []

    store = InMemoryCorrelationIndexStore(
        built_at=_BUILT_AT,
        ghsa=rows,
        nvd=(),
        watermarks=(
            SourceWatermark(
                source="ghsa",
                observed_through="2026-09-16T18:56:22Z",
                record_count=35584,
            ),
        ),
    )
    authority = CorrelationIndexThreatEvidenceAuthority(
        store=store,
        snapshots=ThreatSnapshotSet(kev=_kev(known), epss=_epss(known)),
    )
    loaded = authority.load_with_provenance(
        PublicThreatEvidenceRequest(
            scope=build_public_threat_evidence_scope(execution)
        )
    )
    envelope = build_public_analysis_envelope(execution, loaded)

    finding_bytes = [len(finding.canonical_json) for finding in envelope.analysis.findings]
    return Measurement(
        advisories=advisories,
        enriched=enriched,
        findings=len(finding_bytes),
        finding_bytes_mean=(
            round(sum(finding_bytes) / len(finding_bytes)) if finding_bytes else 0
        ),
        finding_bytes_max=max(finding_bytes) if finding_bytes else 0,
        finding_bytes_total=sum(finding_bytes),
        identifiers_per_advisory=identifiers,
        analysis_projection_bytes=len(envelope.analysis.canonical_json),
        envelope_identity_bytes=len(envelope.canonical_json),
    )


def main() -> int:
    """Run the measurements and print, optionally retaining them.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", help="path to retain the measurement as evidence")
    arguments = parser.parse_args()

    shapes = (
        {"advisories": 1, "identifiers": 0, "enriched": False},
        {"advisories": 1, "identifiers": 2, "enriched": True},
        {"advisories": 10, "identifiers": 2, "enriched": True},
        {"advisories": 100, "identifiers": 2, "enriched": True},
    )
    measurements = [measure(**shape) for shape in shapes]  # pyright: ignore[reportArgumentType]
    heaviest = max(row.finding_bytes_max for row in measurements)

    print("OpsLens response item size")
    print()
    print(
        f"{'advisories':>11}  {'enriched':>8}  {'findings':>8}  "
        f"{'mean B':>8}  {'max B':>8}  {'total B':>9}"
    )
    for row in measurements:
        print(
            f"{row.advisories:>11}  {row.enriched!s:>8}  {row.findings:>8}  "
            f"{row.finding_bytes_mean:>8}  {row.finding_bytes_max:>8}  "
            f"{row.finding_bytes_total:>9}"
        )
    print()
    print("against the measured index page (ADR 0087, Correction)")
    print(f"  stored item             {_STORED_ITEM_BYTES:>8} B")
    print(f"  heaviest response item  {heaviest:>8} B")
    print(f"  ratio                   {heaviest / _STORED_ITEM_BYTES:>8.2f}x")
    print()
    for budget_mib in (1, 4):
        budget = budget_mib * 1024 * 1024
        print(
            f"  a {budget_mib} MiB response holds {budget // heaviest:>6} findings "
            f"at the heaviest measured size"
        )
    print(f"  one 1 MB index page holds {_ITEMS_PER_PAGE} rows to read")

    if arguments.write:
        payload: dict[str, object] = {
            "contract_version": MEASUREMENT_CONTRACT_VERSION,
            "heaviest_response_item_bytes": heaviest,
            "measurements": [row.payload for row in measurements],
            "method": {
                "measured": (
                    "RepositoryAnalysisFinding.canonical_json, the only serialization of "
                    "a finding this system currently has"
                ),
                "note": (
                    "Built through the real chain — lock, inventory, index, correlation, "
                    "enrichment, analysis — over an in-memory index. Offline and "
                    "deterministic; no AWS is involved."
                ),
                "unmeasured": (
                    "The HTTP wire format, which does not exist yet. A number for it "
                    "would be a guess; this script re-measures when it lands."
                ),
            },
            "reference": {
                "projected_source_row_bytes": 385,
                "stored_index_item_bytes": _STORED_ITEM_BYTES,
                "stored_items_per_1mb_page": _ITEMS_PER_PAGE,
            },
        }
        Path(arguments.write).write_bytes(canonical_json(payload) + b"\n")
        print()
        print(f"retained {arguments.write}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
