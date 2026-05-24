# Quant Research Interview Core

This directory contains the runnable core engine behind the strategy artifacts in this project. It is not a toy demo: it keeps the full research workflow intact from raw market data to performance reports.

## What This Package Does

- prepares raw hourly market data
- computes modular cross-sectional factors
- filters and ranks the trading universe
- constructs long/short target allocations
- simulates execution with fees, funding, and lot-size constraints
- exports performance tables and interactive equity curves

## Pipeline Overview

### Entry point

- `backtest.py`: runs the full workflow end to end

### Configuration

- `config.py`: data paths, backtest dates, factor mix, filters, leverage, fees, and portfolio sizing rules

### Research steps

- `program/step1_prepare_data.py`: loads raw candle files, fills missing bars, and builds cached market matrices
- `program/step2_calculate_factors.py`: computes per-symbol factor values and stores the factor cache
- `program/step3_select_coins.py`: applies filters, ranks the universe, and generates long/short target weights
- `program/step4_simulate_performance.py`: aggregates target weights through time and runs the execution simulator

### Reusable components

- `core/`: simulation, evaluation, plotting, path utilities, and backtest configuration models
- `factors/`: modular factor definitions loaded dynamically at runtime

## Strategy Characteristics In This Snapshot

- **Data frequency**: hourly
- **Holding period**: 21 days
- **Portfolio style**: cross-sectional long/short
- **Selection factors**: `W24`, `W22`, `W42`, `PctChange`
- **Universe filters**: `QuoteVolumeMean`, `VolumeMeanRatio`
- **Execution frictions modeled**:
  - spot and perpetual trading fees
  - perpetual funding fees
  - minimum order size constraints
  - liquidation threshold checks

## Running The Pipeline

```bash
python Code/backtest.py
```

## Requirements Before Running

### Local data

The current configuration expects local raw market data directories defined in [`config.py`](./config.py). These paths are intentionally left configurable because the repository is a presentation-ready extraction rather than a bundled public dataset release.

### Python packages

The codebase currently relies on:

- `pandas`
- `numpy`
- `numba`
- `plotly`
- `ccxt` for refreshing exchange lot-size metadata

### Support files

The backtest writes and reuses generated files under the repository-level `data/` directory, including:

- cached candle dictionaries
- cached factor tables
- pivoted market matrices
- minimum tradable quantity tables
- backtest result folders

## Typical Output Artifacts

Each backtest run exports:

- `equity_curve.csv`
- `strategy_metrics.csv`
- `yearly_returns.csv`
- `quarterly_returns.csv`
- `monthly_returns.csv`
- `equity_curve.html`

## Design Notes

- The package is optimized for research clarity rather than deployment abstraction.
- The factor layer is modular, which makes it easy to add new signals for evaluation.
- The simulation is execution-aware and captures several crypto-specific frictions that are often ignored in simplified academic backtests.

## Interview Framing

If you are reviewing this directory in an interview context, the most useful path is:

1. read `config.py` to understand the portfolio rules
2. open `backtest.py` to see the orchestration
3. review `program/` for the research flow
4. inspect `core/equity.py` for the simulation and reporting logic
