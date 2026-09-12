# V1 Quickstart

Gate 19.10 implements the canonical reviewer path:

```bash
uv sync --frozen
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format text
```

Machine-readable deterministic form:

```bash
uv run python scripts/demo_opslens.py --scenario material-vulnerability --format json
```

The runner satisfies the V1 quickstart contract:

- no AWS credentials required for the canonical offline path;
- no network requirement after dependencies are installed;
- no execution of third-party repository code;
- deterministic scenario identity and output evidence;
- stable JSON output;
- human-readable summary output;
- non-zero process exit for invalid CLI inputs;
- retained correlation/risk authorities are reused rather than copied into demo-only logic.

Target reviewer time from completed setup to first result remains less than ten minutes.

Gate 19.11 will add the controlled-benign and fail-closed incomplete/ambiguous scenario classes without changing this canonical runner boundary.
