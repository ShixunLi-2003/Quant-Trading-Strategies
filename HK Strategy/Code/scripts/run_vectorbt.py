"""
Vectorbt CLI Entry Point

Launches the vectorbt backtest from a JSON strategy configuration.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hk_quant.backtests.vectorbt_engine import run_vectorbt_strategy
from hk_quant.config import load_project_and_job_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run vectorbt backtest.")
    parser.add_argument("--config", default="configs/vectorbt_w42_bear_defense_recommended.json", help="Path to strategy config")
    args = parser.parse_args()

    project_config, strategy_config = load_project_and_job_config(args.config)
    result = run_vectorbt_strategy(project_config, strategy_config)
    print(f"vectorbt finished. Output: {result['output_dir']}")


if __name__ == "__main__":
    main()
