# A-Share Cross-Factor Alpha Research & Live Execution System

## 1. Project Overview

This project is an A-share multi-factor equity strategy framework covering factor research, portfolio construction, backtesting, attribution analysis, and signal forwarding for live execution.

The strategy combines technical factors, fundamental factors, industry regime checks, style-aware portfolio construction, and layered risk controls. It is designed as a full research workflow rather than a single backtest script.

The repository includes:

- the original end-to-end strategy implementation
- a modularized codebase for cleaner structure review
- single-factor research notebooks
- raw backtest exports across multiple market regimes
- attribution and risk analysis outputs
- summary result images

## 2. Strategy Framework

The strategy is built around the following components:

- Technical factors: price momentum, volatility, volume ratio, RSI, breakout strength
- Fundamental factors: rolling PE, expected growth, net profit growth, gross margin, debt ratio, market capitalization
- Industry and style overlays: industry boom checks, sector preference scoring, region bonus logic, style exposure analysis
- Risk controls: position-level stop-loss and take-profit rules, portfolio drawdown control, rise filters, profit deterioration filters
- Portfolio execution: scheduled rebalancing, position constraints, signal forwarding, trading statistics, and slippage sensitivity analysis

In essence, the strategy is a medium-frequency active stock selection model that integrates stock picking, portfolio control, and execution-aware research review.

## 3. Repository Structure

```text
1.A-Share Cross-Factor Alpha Research & Live Execution System/
├─ Code/
│  ├─ Complete_code.py
│  └─ modular_alpha/
├─ Factor_Analysis/
├─ Backtest-Raw-Results/
├─ Attribution analysis/
├─ Result_Images/
└─ README.md
```

### `Code/`

Core strategy implementation.

- `Complete_code.py`: original monolithic strategy script containing initialization, factor calculation, rebalancing, risk management, and QMT signal forwarding
- `modular_alpha/`: modularized version of the same strategy logic, split into configuration, factor libraries, filters, portfolio construction, risk controls, and execution bridge modules

### `Factor_Analysis/`

Single-factor research and diagnostic notebooks, including:

- Price Momentum
- Volatility
- Volume Ratio
- RSI
- Breakout
- Rolling PE
- Gross Margin
- Debt Ratio
- Market Cap
- Factor Correlation Diagnostic

This directory shows that the final strategy was not constructed as a pure factor stack without intermediate inspection.

### `Backtest-Raw-Results/`

Raw backtest exports across multiple market environments.

Current backtest windows include:

- `2011-2026`
- `2014-2015`
- `2018`
- `2022-2024`
- `2024-2026`

Each subdirectory typically contains:

- `daily_holdings_and_exposure.csv`: daily holdings and exposure records
- `trade_execution_details.csv`: trade-level execution records
- `strategy_summary_metrics.csv`: backtest metric summaries

The top level also includes:

- `Performance_Summary.csv`: cross-period summary table of key performance metrics

### `Attribution analysis/`

Performance attribution and risk review outputs, including cumulative return, annual and monthly return structure, style exposure, sector allocation, Brinson decomposition, drawdown analysis, trading statistics, and slippage sensitivity analysis.

This directory also includes a dedicated summary document:

- `README.md`

### `Result_Images/`

High-level result snapshots for different backtest windows.

## 4. Backtest Summary

According to `Backtest-Raw-Results/Performance_Summary.csv`, the main backtest results are:

| Backtest Period | Annualized Return | Benchmark Return | Alpha | Beta | Sharpe | Sortino | Information Ratio | Max Drawdown | Profit/Loss Ratio | Win Rate | Volatility |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2011-2026 | 35.36% | 50.90% | 0.319 | 0.488 | 1.586 | 2.547 | 1.622 | 14.54% | 2.092 | 0.477 | 0.198 |
| 2014-2015 | 66.85% | 60.13% | 0.524 | 0.451 | 2.540 | 3.951 | 1.492 | 12.57% | 2.580 | 0.486 | 0.247 |
| 2018 | 9.26% | -25.31% | 0.167 | 0.384 | 0.323 | 0.440 | 1.830 | 14.26% | 1.404 | 0.460 | 0.162 |
| 2022-2024 | 16.14% | -21.77% | 0.197 | 0.500 | 0.703 | 1.240 | 1.574 | 13.54% | 1.571 | 0.442 | 0.173 |
| 2024-2026 | 24.43% | 39.00% | 0.139 | 0.549 | 1.091 | 1.687 | 0.478 | 11.23% | 1.769 | 0.464 | 0.187 |

These results indicate:

- strong long-horizon absolute return generation
- meaningful resilience during weak-market periods such as `2018` and `2022-2024`
- relatively low beta compared with broad market exposure
- acceptable Sharpe, Sortino, Information Ratio, and drawdown characteristics

The reported results are strong. For that reason, the burden of robustness, reproducibility, and overfitting control is correspondingly higher.

## 5. Current Strengths

From a research repository perspective, the current project already has several strengths:

- It is more than a single backtest script and already includes research, strategy logic, backtest exports, attribution, and result presentation.
- It preserves multiple market-regime slices instead of only showing one favorable sample window.
- It includes single-factor notebooks, which helps demonstrate intermediate research work behind the final strategy.
- It retains trade-level records, daily holdings, and attribution charts, which improves auditability.
- It includes a modularized version of the strategy, showing awareness of code organization beyond a monolithic research script.
- It covers slippage sensitivity, sector exposure, style exposure, Brinson attribution, and trading diagnostics.

## 6. Current Limitations

### 6.1 Reproducibility Is Not Yet Fully Documented

This is one of the most important limitations of the current repository.

The entire project relies heavily on the JoinQuant / jqdata environment, but it does not yet include a complete environment specification, dependency description, reproducibility path, or data interface documentation. Top-tier firms care a great deal about reproducibility.

More specifically, the repository still lacks:

- a complete Python dependency specification
- a clear explanation of JoinQuant / jqdata runtime requirements
- a definition of the data fields and data-source assumptions
- step-by-step backtest execution instructions
- a documented path from factor research to final strategy backtest
- a clear explanation of the differences between local execution and platform execution

At the current stage, the repository shows results and research outputs, but it does not yet meet a strict external reproducibility standard.

### 6.2 Robustness and Overfitting Defense Can Be Strengthened

Although the project already includes multi-period backtests and attribution outputs, the following areas can still be improved:

- more explicit in-sample and out-of-sample separation
- walk-forward validation
- parameter sensitivity analysis
- ablation tests after removing or replacing factors
- stability checks under different universes and benchmarks
- deeper turnover, transaction-cost, capacity, and implementation analysis

### 6.3 Presentation and Encoding Details Need Further Cleanup

Some raw CSV files contain encoding issues in Chinese security names, and chart naming conventions are not yet fully standardized. These issues do not change the logic of the strategy itself, but they do affect the professional presentation quality of the repository.

## 7. What This Project Demonstrates

This repository is well suited to demonstrate the following capabilities:

- independent development of a multi-factor A-share equity strategy
- integration of technical and fundamental signals
- position control, risk management, and rebalancing logic
- structured handling of backtest outputs and analytical data
- basic attribution and risk review capability
- awareness of engineering structure through modular refactoring

## 8. Suggested Reading Order

### 8.1 Code Review Path

If the goal is to understand the strategy logic quickly, a practical reading order is:

1. `Code/Complete_code.py`
2. `Code/modular_alpha/`
3. `Factor_Analysis/`
4. `Backtest-Raw-Results/Performance_Summary.csv`
5. `Attribution analysis/README.md`

### 8.2 Result Review Path

If the goal is to understand the performance profile quickly, a practical reading order is:

1. `Result_Images/`
2. `Backtest-Raw-Results/Performance_Summary.csv`
3. `Attribution analysis/`

## 9. Recommended Next Improvements

To improve the repository further as a research-grade project, the following additions would be valuable:

- a complete English-first project presentation with consistent naming
- environment and dependency documentation
- explicit data-interface and data-field documentation
- a documented reproducibility workflow
- stronger notebook-level writeups for factor research
- parameter sensitivity analysis, ablation tests, and out-of-sample stability checks
- consistent naming and cleanup of intermediate cache artifacts such as `__pycache__/`

## 10. Conclusion

Overall, this repository is no longer just a collection of strategy scripts. It is a multi-component A-share alpha research project with code, factor analysis, backtest exports, attribution outputs, and result presentation.

Its strongest value lies in showing strategy research ability, data analysis ability, and basic engineering organization. The most important next step is not simply adding another return chart, but strengthening reproducibility, research narration, and robustness evidence.
