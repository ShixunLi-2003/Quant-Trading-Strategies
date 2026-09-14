from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ashare_momentum.backtest import CostModel, periodic_top_n_backtest, summarize_periods


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the cost-aware periodic top-N portfolio backtest.")
    parser.add_argument("--candidates", required=True, help="Candidate table with entry and exit prices.")
    parser.add_argument("--output", default="results/reproduced/backtest")
    parser.add_argument("--initial-capital", type=float, default=30_000.0)
    parser.add_argument("--top-n", type=int, default=3)
    args = parser.parse_args()

    path = Path(args.candidates)
    candidates = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
    periods, trades = periodic_top_n_backtest(
        candidates,
        initial_capital=args.initial_capital,
        top_n=args.top_n,
        cost_model=CostModel(),
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    periods.to_csv(output / "periods.csv", index=False)
    trades.to_csv(output / "trades.csv", index=False)
    (output / "summary.json").write_text(
        json.dumps(summarize_periods(periods), indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

