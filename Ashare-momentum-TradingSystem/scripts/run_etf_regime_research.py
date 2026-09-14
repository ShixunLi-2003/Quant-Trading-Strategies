from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from ashare_momentum.risk import build_etf_exposure_schedule, build_etf_regime_table


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a lagged ETF breadth exposure schedule.")
    parser.add_argument(
        "--prices",
        required=True,
        help="ETF price table with stock_code, trade_date, and close.",
    )
    parser.add_argument("--output", default="results/reproduced/etf_exposure.csv")
    parser.add_argument("--breadth-threshold", type=float, default=0.5)
    parser.add_argument("--confirmation-days", type=int, default=2)
    parser.add_argument("--half-after", type=int, default=2)
    parser.add_argument("--cash-after", type=int, default=3)
    args = parser.parse_args()

    path = Path(args.prices)
    prices = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
    regime = build_etf_regime_table(prices)
    schedule = build_etf_exposure_schedule(
        regime,
        breadth_threshold=args.breadth_threshold,
        confirmation_days=args.confirmation_days,
        half_after=args.half_after,
        cash_after=args.cash_after,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    schedule.to_csv(output, index=False)


if __name__ == "__main__":
    main()
