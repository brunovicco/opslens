# OpsLens Demo

The canonical V1 demonstration path is **offline-first, deterministic, and reviewer-oriented**. It reuses retained OpsLens authority and never executes third-party repository code.

## Gate 19.10 runner

Gate 19.10 implements one admitted scenario:

```bash
uv sync --frozen
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
```

Stable machine-readable projection:

```bash
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format json
```

The scenario is a synthetic inert fixture. It does not describe or scan a live repository. The runner uses existing typed repository-evidence, vulnerability correlation/enrichment, and Risk Policy v1 code to demonstrate the authority chain end to end.

Canonical properties:

```text
AWS credentials required: NO
network after setup: NO
live provider execution: NO
model execution: NO
third-party repository code execution: NO
stable JSON output: YES
human-readable output: YES
```

Supporting authority and scenario documents:

- [`AUTHORITY.md`](AUTHORITY.md)
- [`QUICKSTART_TARGET.md`](QUICKSTART_TARGET.md)
- [`SCENARIOS.md`](SCENARIOS.md)

Remaining slices after Gate 19.10:

```text
Gate 19.11  curated scenarios + deterministic evaluation
Gate 19.12  minimal local visual demo
```
