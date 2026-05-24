# Code

## Scope

This folder contains the interview-oriented English code package for the active oversold rebound strategy configuration. It keeps the production workflow split into configuration, data preparation, factor construction, stock selection, equity simulation, and analysis tooling.

## Active Modules

- `backtest_main.py`: end-to-end pipeline entry point.
- `configuration.py`: current strategy, filters, and timing configuration.
- `program/`: the four-stage workflow from raw data to performance output.
- `factor_library/`: active factor implementations used by the package.
- `signal_library/`: timing-signal implementations, including the active volume-expansion moving-average overlay.
- `core/`: market alignment, finance preprocessing, config models, plotting, and simulation internals.
- `analysis_tools/`: factor-analysis and attribution-analysis tool implementations retained for inspection.

## Validation

The packaged code passes a syntax-level `compileall` check after the English translation pass.
