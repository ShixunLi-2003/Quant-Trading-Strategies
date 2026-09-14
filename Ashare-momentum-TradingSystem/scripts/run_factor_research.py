from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ashare_momentum.data import (
    DAILY_COLUMNS,
    MINUTE_COLUMNS,
    normalize_daily,
    normalize_minute,
    read_market_table,
)
from ashare_momentum.factors import FACTOR_COLUMNS, build_factor_panel, low_volatility_score
from ashare_momentum.validation import factor_ic_summary, quantile_backtest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run point-in-time factor research on standardized market tables."
    )
    parser.add_argument("--daily", required=True, help="Daily CSV or Parquet table.")
    parser.add_argument("--minute", required=True, help="One-minute CSV or Parquet table.")
    parser.add_argument("--output", default="results/reproduced", help="Output directory.")
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--low-volatility-weight", type=float, default=0.6)
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    daily = normalize_daily(read_market_table(args.daily, DAILY_COLUMNS))
    minute = normalize_minute(read_market_table(args.minute, MINUTE_COLUMNS))
    panel = build_factor_panel(daily, minute, args.horizon)
    panel["low_volatility_score"] = low_volatility_score(panel, args.low_volatility_weight)
    target = f"fwd_ret_{args.horizon}d"
    factor_ic_summary(panel, FACTOR_COLUMNS, target).to_csv(output / "factor_ic.csv", index=False)
    returns, nav = quantile_backtest(panel, "low_volatility_score", target)
    returns.to_csv(output / "quantile_returns.csv", index=False)
    nav.to_csv(output / "quantile_nav.csv", index=False)
    panel.to_parquet(output / "factor_panel.parquet", index=False)


if __name__ == "__main__":
    main()
