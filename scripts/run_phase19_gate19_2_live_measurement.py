"""Run the human-operated Gate 19.2 live measurement composition root."""

from _bootstrap import ensure_repository_src_on_path

ensure_repository_src_on_path()

from opslens.public_analysis.cli.run_live_measurement import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
