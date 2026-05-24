"""Run the end-to-end backtest pipeline for a cross-sectional crypto selection strategy."""

from __future__ import annotations

import warnings

import pandas as pd

from core.model.backtest_config import load_config
from program.step1_prepare_data import prepare_data
from program.step2_calculate_factors import calc_factors
from program.step3_select_coins import select_coins
from program.step4_simulate_performance import simulate_performance

warnings.filterwarnings("ignore")
pd.set_option("expand_frame_repr", False)
pd.set_option("display.unicode.ambiguous_as_wide", True)
pd.set_option("display.unicode.east_asian_width", True)


def main() -> None:
    """Execute the research pipeline from raw data to portfolio report."""
    print("Starting backtest pipeline...")
    conf = load_config()

    prepare_data()
    calc_factors(conf)
    select_results = select_coins(conf)
    simulate_performance(conf, select_results)


if __name__ == "__main__":
    main()
