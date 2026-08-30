from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file_path = Path(path)
    text = file_path.read_text()
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:80]!r}")
    file_path.write_text(text.replace(old, new, 1))


compat = "docs/labs/phase-2-epss-history-source-compatibility.md"
design = "docs/labs/phase-2-epss-history-bronze-silver-design.md"

replace_once(
    compat,
    "Status: **COMPLETE**",
    "Status: **COMPLETE — reconciled with transition-boundary source proof**",
)

replace_once(
    compat,
    "The probe selected the first published archive snapshot in each documented model era:\n\n```text\nv1 -> 2021-04-14\nv2 -> 2022-02-04\nv3 -> 2023-03-07\nv4 -> 2025-03-17\nv5 -> 2026-06-15\n```",
    "The original compatibility probe selected the first published archive snapshot in each documented model era:\n\n```text\nv1 -> 2021-04-14\nv2 -> 2022-02-04\nv3 -> 2023-03-07\nv4 -> 2025-03-17\nv5 -> 2026-06-15\n```\n\nA later transition-boundary probe also inspected `2022-02-03`, the final v1-era day, because a model era must not be assumed to imply one physical CSV shape.",
)

replace_once(
    compat,
    "### v1 physical shape",
    "### Early v1 physical shape",
)

replace_once(
    compat,
    "This proves two separate legacy gaps:\n\n```text\nv1 has no FIRST metadata comment\nv1 has no percentile field\n```\n\nOpsLens must not synthesize either as though it were source-declared evidence.",
    "This proves two gaps for the earliest observed v1 shape:\n\n```text\nearly v1 has no FIRST metadata comment\nearly v1 has no percentile field\n```\n\nOpsLens must not synthesize either as though it were source-declared evidence. It must also not generalize the early-v1 two-column shape to every v1-era date.\n\n### Late v1 transition shape\n\nPinned file:\n\n```text\n2022/epss_scores-2022-02-03.csv.gz\n```\n\nObserved by the exact transition-boundary probe:\n\n```text\nmetadata comment:              absent\nCSV header:                    cve,epss,percentile\npercentile column:             present\nsource-declared model version: absent\nsource-declared score date:    absent\ncompressed bytes:              403,029\nuncompressed bytes:            3,375,720\nsource SHA-256:                 49c983102fd76369a3dce375ba7cf7d4889767989baf296919ea0169efffd349\n```\n\nTherefore v1 is a model era, not a single physical source shape. The historical parser must preserve percentile when the exact legacy file publishes it while keeping model version and score timestamp null because no modern metadata row is present.",
)

replace_once(
    compat,
    "The v1 source cannot truthfully satisfy that contract because both `percentile` and source-declared model/timestamp metadata are absent.",
    "The earliest v1 source cannot truthfully satisfy the old non-null contract because `percentile` and source-declared model/timestamp metadata are absent. Late-v1 files can publish `percentile`, but still lack source-declared model/timestamp metadata. Therefore nullability must follow exact physical evidence, not model era alone.",
)

replace_once(
    compat,
    "EPSS_HISTORY_V1_NO_PERCENTILE_GATE=PASS\nEPSS_HISTORY_V2_V5_METADATA_GATE=PASS",
    "EPSS_HISTORY_EARLY_V1_NO_PERCENTILE_GATE=PASS\nEPSS_HISTORY_LATE_V1_PERCENTILE_PRESERVATION_GATE=PASS\nEPSS_HISTORY_V2_V5_METADATA_GATE=PASS",
)

replace_once(
    compat,
    "Phase 2.5C must freeze and implement the historical Bronze/Silver evidence contract before any bulk backfill:\n\n1. exact immutable historical source coordinates and Bronze identity;\n2. legacy v1 representation without fabricated percentile/metadata;\n3. exact S3 `VersionId` reads in Silver;\n4. replay verification of existing Silver bytes rather than accepting `412` blindly;\n5. coexistence with the forward-daily pipeline;\n6. a controlled backfill trigger boundary that cannot fan out 1,956 objects accidentally.",
    "Phase 2.5C-1 design and 2.5C-2 legacy-capable parser/Silver schema v2 are now complete. The next authorized gate is 2.5C-3: implement the exact historical Bronze manifest reader and `VersionId` authority boundary before any AWS backfill. Replay hardening, completion evidence, and controlled explicit invocation remain subsequent C-subgates.",
)

replace_once(
    design,
    "Status: **2.5C-1 DESIGN COMPLETE — implementation not yet authorized**",
    "Status: **2.5C-1 DESIGN COMPLETE; 2.5C-2 PARSER/SCHEMA COMPLETE; 2.5C-3 NEXT**",
)

replace_once(
    design,
    "Representative source-byte proof established two physical contracts:\n\n```text\nEPSS v1\n  metadata comment: absent\n  columns:          cve,epss\n  percentile:       absent\n\nEPSS v2-v5\n  metadata comment: present\n  columns:          cve,epss,percentile\n  model_version:    source-declared\n  score_date:       source-declared\n```\n\nThe current OpsLens parser accepts v2-v5 and correctly rejects v1 under its modern-only contract.",
    "Representative and transition-boundary source-byte proof established three physical contracts:\n\n```text\nEPSS v1 early legacy\n  metadata comment: absent\n  columns:          cve,epss\n  percentile:       absent\n\nEPSS v1 late legacy (observed 2022-02-03)\n  metadata comment: absent\n  columns:          cve,epss,percentile\n  percentile:       present\n\nEPSS v2-v5 modern\n  metadata comment: present\n  columns:          cve,epss,percentile\n  model_version:    source-declared\n  score_date:       source-declared\n```\n\nThe forward/current OpsLens parser remains modern-only. The historical parser introduced in 2.5C-2 classifies both observed v1 legacy headers explicitly and delegates v2-v5 to the proven modern parser.",
)

replace_once(
    design,
    "source_shape                  v1 | modern",
    "source_shape                  legacy_two_column | legacy_three_column | modern_metadata",
)

replace_once(
    design,
    "For v1:\n\n```text\nsource_shape             = v1\npercentile               = NULL\nsource_model_version     = NULL\nsource_score_timestamp   = NULL\nsource_metadata_present  = false\n```",
    "For v1, metadata remains absent in both observed source shapes:\n\n```text\nearly legacy:\n  source_shape             = legacy_two_column\n  percentile               = NULL\n  source_model_version     = NULL\n  source_score_timestamp   = NULL\n  source_metadata_present  = false\n\nlate legacy:\n  source_shape             = legacy_three_column\n  percentile               = exact source value\n  source_model_version     = NULL\n  source_score_timestamp   = NULL\n  source_metadata_present  = false\n```",
)

replace_once(
    design,
    "v1 percentile unexpectedly present under the frozen v1 contract",
    "unknown or malformed legacy v1 header/row shape",
)

replace_once(
    design,
    "2.5C-2 — legacy-capable source model + parser + Silver schema v2\n  STATUS: NEXT\n\n2.5C-3 — exact historical Bronze manifest reader + VersionId boundary\n  STATUS: NOT STARTED",
    "2.5C-2 — legacy-capable source model + parser + Silver schema v2\n  STATUS: COMPLETE\n\n2.5C-3 — exact historical Bronze manifest reader + VersionId boundary\n  STATUS: NEXT",
)

replace_once(
    design,
    "## Next authorized step\n\nImplement only **2.5C-2**:\n\n1. introduce a legacy-capable historical source model and parser;\n2. keep v1 `percentile`, `model_version`, and `score_timestamp` genuinely nullable;\n3. evolve the EPSS Silver physical schema to version 2 with those three fields nullable;\n4. preserve modern v2-v5 behavior unchanged;\n5. add focused unit tests for v1 and modern metadata/date/model-era validation;\n6. run repository regression gates.\n\nDo not create historical Bronze objects in AWS and do not start bulk backfill in 2.5C-2.",
    "## 2.5C-2 gates\n\n```text\nEPSS_HISTORY_LEGACY_TWO_COLUMN_SOURCE_GATE=PASS\nEPSS_HISTORY_LEGACY_THREE_COLUMN_SOURCE_GATE=PASS\nEPSS_HISTORY_LATE_V1_PERCENTILE_PRESERVATION_GATE=PASS\nEPSS_HISTORY_V1_NO_FABRICATED_METADATA_GATE=PASS\nEPSS_HISTORY_MODERN_PARSER_COMPATIBILITY_GATE=PASS\nEPSS_HISTORY_SILVER_SCHEMA_V2_GATE=PASS\nEPSS_HISTORY_SILVER_V2_NULLABLE_LEGACY_FIELDS_GATE=PASS\nEPSS_HISTORY_REAL_FORMAT_BOUNDARY_GATE=PASS\nEPSS_HISTORY_RUFF_GATE=PASS\nEPSS_HISTORY_PYRIGHT_GATE=PASS\nEPSS_HISTORY_UNIT_TEST_GATE=PASS\nEPSS_2_5C2_GATE=PASS\n```\n\n## Next authorized step\n\nImplement only **2.5C-3**: the exact historical Bronze manifest reader and S3 `VersionId` authority boundary. Do not create historical Bronze objects in AWS and do not start bulk backfill yet.",
)

print("EPSS_HISTORY_C2_DOC_RECONCILIATION=PASS")
