"""Run the full backtest pipeline from raw data to final performance reports."""

import warnings

import pandas as pd

from core.model.backtest_config import load_config
from program.step1_prepare_data import prepare_data
from program.step2_calculate_factors import calculate_factors
from program.step3_select_stocks import select_stocks
from program.step4_simulate_performance import simulate_performance

warnings.filterwarnings("ignore")
pd.set_option("expand_frame_repr", False)
pd.set_option("display.unicode.ambiguous_as_wide", True)
pd.set_option("display.unicode.east_asian_width", True)


def main() -> None:
    """Execute data preparation, factor construction, selection, and portfolio simulation."""
    conf = load_config()
    prepare_data(conf)
    calculate_factors(conf)
    select_results = select_stocks(conf)
    simulate_performance(conf, select_results)


if __name__ == "__main__":
    main()
