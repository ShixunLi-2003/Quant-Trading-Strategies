# Reproducibility Guide

[Cantonese version](REPRODUCIBILITY.yue.md)

## Reproduction Levels

### Level 1: Repository Verification

This level requires no market data. It verifies package installation, tests, public result integrity, and figure generation.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
pytest
python scripts/generate_report_assets.py
python scripts/build_results_manifest.py
```

Expected outputs include all figures under `results/figures/`, the compact headline table, the selected-strategy rolling table, and a SHA256 manifest of published artifacts.

### Level 2: Factor Research with Licensed Data

Provide standardized daily and one-minute tables that satisfy `DATA_CONTRACT.md`.

```bash
python scripts/run_factor_research.py \
  --daily data/raw/daily.parquet \
  --minute data/raw/minute.parquet \
  --output results/reproduced/factors \
  --horizon 3 \
  --low-volatility-weight 0.6
```

This rebuilds the 16-factor panel, factor IC table, selected composite score, quantile returns, and diagnostic NAV.

### Level 3: Walk-Forward Model Comparison

Use the factor panel created at Level 2.

```bash
python scripts/run_model_comparison.py \
  --panel results/reproduced/factors/factor_panel.parquet \
  --output results/reproduced/models \
  --target fwd_ret_3d \
  --train-days 120 \
  --embargo-days 3
```

The script generates embargoed predictions for ridge regression, random forest, and multilayer perceptron models.

### Level 4: Generic Cost-Aware Portfolio Simulation

Provide a candidate table with `signal_date`, `stock_code`, `score`, `entry_price`, and `exit_price`.

```bash
python scripts/run_portfolio_backtest.py \
  --candidates data/derived/candidates.parquet \
  --output results/reproduced/backtest \
  --initial-capital 30000 \
  --top-n 3
```

This simulator applies finite capital, board lots, minimum commission, commission, stamp duty, and adverse slippage. Candidate construction and licensed minute-price extraction remain data-provider-specific and are not represented as vendor-neutral operations.

### Level 5: ETF Exposure Schedule

Provide an ETF table containing `stock_code`, `trade_date`, and `close`.

```bash
python scripts/run_etf_regime_research.py \
  --prices data/raw/etf_daily.parquet \
  --output results/reproduced/etf_exposure.csv \
  --breadth-threshold 0.5 \
  --confirmation-days 2 \
  --half-after 2 \
  --cash-after 3
```

The generated exposure is lagged to the next session. The public script reproduces the regime mechanism, not the full historical nested search that produced every archived ETF comparison.

## Exact Headline Reproduction Boundary

The repository alone cannot regenerate the exact headline return series from raw inputs. Exact reproduction requires:

- licensed daily, minute, and ETF market history;
- the historical eligible-universe inputs used by each archived experiment;
- the original vendor-specific minute retrieval and adjustment convention;
- the archived candidate-generation and nested-selection input state.

The included aggregate tables are evidence snapshots used to regenerate the published figures. They are hashed in `results/manifest.csv`. This distinction is intentional: the repository is reproducible at the method and public-artifact levels without redistributing licensed data or private execution state.

## Data Provenance Checklist

Before comparing reproduced results with the published tables, record:

1. vendor and extraction timestamp;
2. corporate-action adjustment convention;
3. exchange timezone and minute-bar timestamp convention;
4. trading-calendar version;
5. point-in-time universe source and effective dates;
6. suspended, limit-up, limit-down, and missing-bar treatment;
7. fee, tax, slippage, and board-lot assumptions;
8. code revision and configuration hash.

Differences in any of these fields may produce legitimate deviations from the published evidence.
