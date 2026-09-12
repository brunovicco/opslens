# V1 Quickstart Target

Gate 19.10 must converge on a reviewer experience approximately equivalent to:

```bash
uv sync --frozen
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
```

The exact command may change during Gate 19.10, but the resulting contract must satisfy:

- no AWS credentials required for the canonical offline path;
- no network requirement after dependencies are installed;
- no execution of third-party repository code;
- deterministic scenario identity and output evidence;
- stable JSON output option;
- human-readable summary option;
- non-zero process exit for invalid/incomplete demo inputs where fail-closed behavior is expected.

Target reviewer time from completed setup to first result: less than ten minutes.

This is a target contract only; Gate 19.10 owns implementation and verification.
