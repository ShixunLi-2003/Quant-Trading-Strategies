"""
Backtrader CLI Entry Point

Launches the Backtrader reference backtest from a JSON strategy configuration.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hk_quant.backtests.backtrader_engine import run_backtrader_strategy
from hk_quant.config import load_project_and_job_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Backtrader backtest.")
    parser.add_argument("--config", default="configs/backtrader_ma_cross.json", help="Path to strategy config")
    args = parser.parse_args()

    project_config, strategy_config = load_project_and_job_config(args.config)
    result = run_backtrader_strategy(project_config, strategy_config)
    print(f"Backtrader finished. Output: {result['output_dir']}")


if __name__ == "__main__":
    main()
