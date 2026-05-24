# Code

This directory contains the package-local research framework used to generate the reported results.

## Layout

- `configs/`: package-local strategy configuration and dependency list.
- `framework/`: annotated file-by-file snapshot for review and reading.
- `scripts/`: command-line entry points adjusted to the package directory layout.
- `src/`: runnable source tree used by the scripts in this folder.

## Package-Local Configuration

- `project.json` resolves paths against `HK Strategy/HK Data`.
- `configs/vectorbt_w42_bear_defense_recommended.json` is the active strategy configuration used in the report.

## Notes

- `framework/` is optimized for code review and discussion.
- `src/` contains the executable modules used by the CLI scripts.
- `src/hk_quant/` is a compatibility namespace that keeps the original import paths valid inside this standalone package.
