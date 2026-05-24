"""Run a lightweight parameter sweep using the packaged framework components."""

import itertools
import time
import warnings
from copy import deepcopy

import pandas as pd

from core.model.backtest_config import create_factory
from program.step1_prepare_data import prepare_data
from program.step2_calculate_factors import calculate_factors
from program.step3_select_stocks import select_stocks
from program.step4_simulate_performance import simulate_performance

warnings.filterwarnings("ignore")
pd.set_option("expand_frame_repr", False)
pd.set_option("display.unicode.ambiguous_as_wide", True)
pd.set_option("display.unicode.east_asian_width", True)


def dict_itertools(parameter_dict: dict) -> list[dict]:
    """Expand a dictionary of parameter grids into a list of concrete configurations."""
    parameter_dict = deepcopy(parameter_dict)
    parameter_dict.pop("re_timing", None)
    keys = list(parameter_dict.keys())
    values = list(parameter_dict.values())
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def find_best_params(factory) -> list[pd.DataFrame]:
    """Run the full pipeline for every configuration in the factory."""
    full_conf = factory.full_conf
    prepare_data(full_conf)
    calculate_factors(full_conf)

    reports = []
    for config in factory.config_list:
        select_results = select_stocks(config, show_plot=False)
        if select_results is None or select_results.empty:
            continue
        report = simulate_performance(config, select_results, show_plot=False)
        reports.append(report)
    return reports


if __name__ == "__main__":
    start_time = time.time()

    traversal_name = "Small-Cap Strategy"
    batch = {
        "select_num": [5],
        "hold_period": ["5D", "10D"],
        "oversold_days": list(range(30, 51)),
        "turnover_days": list(range(10, 26)),
    }

    strategies = []
    for params_dict in dict_itertools(batch):
        strategy = {
            "name": "Oversold Rebound Timing Strategy",
            "hold_period": params_dict["hold_period"],
            "select_num": params_dict["select_num"],
            "factor_list": [
                ("Volume Contraction Factor", True, (15, 80), 0.5),
                ("Turnover Rate", False, params_dict["turnover_days"], 0.7),
                ("Long-Term Low Volume", True, 30, 0.5),
                ("Oversold", True, params_dict["oversold_days"], 5),
                ("Oversold", True, 270, 2),
            ],
            "filter_list": [
                ("Turnover Rate", 30, "pct:<=0.4"),
                ("Rolling PE", None, "val:<60"),
            ],
        }
        strategies.append(strategy)

    re_timing_strategies = [
        {"name": "Moving Average Timing", "params": [timing_param]}
        for timing_param in batch.get("re_timing", [])
    ]

    backtest_factory = create_factory(strategies, re_timing_strategies)
    report_list = find_best_params(backtest_factory)

    all_params_map = pd.concat(report_list, ignore_index=True)
    report_columns = all_params_map.columns
    sheet = backtest_factory.get_name_params_sheet()
    all_params_map = all_params_map.merge(
        sheet,
        left_on="param",
        right_on="strategy_description",
        how="left",
    )
    all_params_map.sort_values(by="cumulative_nav", ascending=False, inplace=True)
    all_params_map = all_params_map[[*sheet.columns, *report_columns]].drop(columns=["param"])

    save_folder = backtest_factory.result_folder / traversal_name
    save_folder.mkdir(parents=True, exist_ok=True)
    all_params_map.to_excel(save_folder / "optimal_parameters.xlsx", index=False)
