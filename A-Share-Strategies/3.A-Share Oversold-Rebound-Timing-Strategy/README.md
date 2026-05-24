# Oversold Rebound Timing Strategy QR Package

## Strategy Snapshot

- Strategy: Oversold Rebound Timing Strategy
- Configured holding period: 5 trading days
- Selection count: 10 stocks per rebalance
- Equity timing: Volume Expansion Moving Average Timing `(40, 0.6, 15)`
- Full-period output source: original framework result directories packaged into an English presentation layer

## Full-Period Performance

| Version | Cumulative NAV | Annual Return | Max Drawdown | Return / Drawdown |
| --- | --- | --- | --- | --- |
| Original | 10.66 | 16.97% | -51.78% | 0.33 |
| Retimed | 12.32 | 18.10% | -16.58% | 1.09 |

![Full-Period NAV Comparison](./Result/Full%20Period/Performance/nav_comparison.png)

## Active Factor Stack

| Factor | Role | Direction | Parameter | Weight | Avg Rank IC |
| --- | --- | --- | --- | --- | --- |
| Volume Contraction Factor ((15, 80)) | ranking | Ascending | (15, 80) | 0.0317 | -0.0554 |
| Turnover Rate (15) | ranking | Descending | 15 | 0.0444 | -0.0574 |
| Long-Term Low Volume (30) | ranking | Ascending | 30 | 0.0317 | -0.0510 |
| Oversold (39) | ranking | Ascending | 39 | 0.7605 | -0.0584 |
| Oversold (270) | ranking | Ascending | 270 | 0.1267 | -0.0281 |
| Net Capital Inflow ((6,)) | ranking | Ascending | (6,) | 0.0051 | -0.0608 |
| Turnover Rate (30) | filter | Ascending | 30 |  | -0.0501 |
| Rolling PE (None) | filter | Ascending |  |  | -0.0350 |

![Configured Factor Weights](./Factor%20Analysis/factor_weight.png)

## Factor Logic

- `Volume Contraction Factor (15, 80)`: short-window turnover divided by a longer turnover baseline to isolate temporary activity compression.
- `Turnover Rate (15)`: 15-day average turnover ranked descending, so higher recent liquidity is preferred inside the rebalance universe.
- `Long-Term Low Volume (30)`: 30-day average volume ranked ascending to preserve the low-activity oversold rebound profile.
- `Oversold (39)`: medium-horizon price drawdown signal and the dominant driver of the composite ranking.
- `Oversold (270)`: long-horizon oversold anchor that reinforces deeper multi-month dislocations.
- `Net Capital Inflow (6)`: six-day rolling price-turnover flow proxy ranked ascending, consistent with a rebound-from-pressure setup.
- `Turnover Rate (30)` filter: keeps candidates inside the lower-liquidity slice of the cross-section via `pct <= 0.4`.
- `Rolling PE` filter: excludes securities with rolling PE above `60`.

## Package Structure

- `Code`: English-only interview package for the production framework subset, including active factor and timing modules.
- `Result`: full-period and market-regime outputs, with source metrics preserved and additional static visuals for rapid review.
- `Factor Analysis`: active-factor diagnostics, per-factor reports, and cross-factor correlation outputs.
- `Attribution Analysis`: factor-level selection-edge and contribution analysis for the configured strategy.
- `Stability`: parameter-sweep outputs summarised around return, drawdown, and robustness trade-offs.
- `REPRODUCIBILITY.md`: raw-data schema, field-level requirements, and execution notes needed to rerun the package after relocation.
