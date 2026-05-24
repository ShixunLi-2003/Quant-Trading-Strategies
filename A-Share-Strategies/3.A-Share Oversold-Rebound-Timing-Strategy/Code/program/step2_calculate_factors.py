"""Calculate ranking and filter factors, then cache the period-level factor panel."""

import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from typing import Dict

import pandas as pd
from tqdm import tqdm

from config import n_jobs
from core.fin_essentials import merge_with_finance_data
from core.market_essentials import transfer_to_period_data
from core.model.backtest_config import BacktestConfig, load_config
from core.model.strategy_config import get_col_name
from core.utils.factor_hub import FactorHub
from core.utils.path_kit import get_file_path

warnings.filterwarnings("ignore")
pd.set_option("expand_frame_repr", False)
pd.set_option("display.unicode.ambiguous_as_wide", True)
pd.set_option("display.unicode.east_asian_width", True)

FACTOR_COLS = [
    "trade_date",
    "stock_code",
    "stock_name",
    "weekly_start_date",
    "monthly_start_date",
    "period_3d_start_date",
    "period_5d_start_date",
    "period_10d_start_date",
    "listed_trading_days",
    "adj_factor",
    "open",
    "high",
    "low",
    "close",
    "turnover",
    "is_tradable",
    "float_market_cap",
    "total_market_cap",
    "next_day_open_limit_up",
    "next_day_st",
    "next_day_tradable",
    "next_day_delisted",
]


def cal_strategy_factors(
    conf: BacktestConfig,
    stock_code: str,
    candle_df: pd.DataFrame,
    fin_data: Dict[str, pd.DataFrame] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Calculate every configured factor for one stock."""
    factor_series_dict = {}
    before_len = len(candle_df)
    agg_dict = {}

    for factor_name, param_list in conf.factor_params_dict.items():
        factor_file = FactorHub.get_by_name(factor_name)
        for param in param_list:
            col_name = get_col_name(factor_name, param)
            factor_df, column_dict = factor_file.add_factor(
                candle_df.copy(),
                param,
                fin_data=fin_data,
                col_name=col_name,
            )
            factor_series_dict[col_name] = factor_df[col_name].values
            if before_len != len(factor_series_dict[col_name]):
                raise ValueError(
                    "Factor calculation changed the row count. "
                    "Do not alter row counts inside factor modules."
                )
            agg_dict.update(column_dict)

    kline_with_factor_df = pd.DataFrame(
        {
            **{col_name: candle_df[col_name] for col_name in FACTOR_COLS},
            **factor_series_dict,
        }
    )
    kline_with_factor_df.sort_values(by="trade_date", inplace=True)
    return kline_with_factor_df, agg_dict


def process_by_stock(
    conf: BacktestConfig,
    stock_code: str,
    candle_df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Merge finance data when needed, then convert daily factors to holding-period factors."""
    if conf.fin_cols:
        candle_df, fin_df, raw_fin_df = merge_with_finance_data(conf, stock_code, candle_df)
        fin_data = {"financial_data": fin_df, "raw_financial_data": raw_fin_df}
    else:
        fin_data = None

    factor_df, agg_dict = cal_strategy_factors(conf, stock_code, candle_df, fin_data=fin_data)
    period_df = transfer_to_period_data(factor_df, conf.strategy.hold_period_name, agg_dict)
    return period_df, agg_dict


def calculate_factors(conf: BacktestConfig) -> None:
    """Build the full factor cache for every stock in the selected universe."""
    if conf.fin_cols and not conf.has_fin_data:
        raise ValueError("Financial-data factors are enabled but `fin_data_path` is unavailable.")

    candle_df_dict: Dict[str, pd.DataFrame] = pd.read_pickle(
        get_file_path("data", "runtime_cache", "stock_preprocessed_data.pkl")
    )
    all_factor_df_list = []
    factor_col_info = {}

    with ProcessPoolExecutor(max_workers=n_jobs) as executor:
        futures = []
        for stock_code, candle_df in candle_df_dict.items():
            futures.append(executor.submit(process_by_stock, conf, stock_code, candle_df))

        for future in tqdm(futures, desc="Calculate factors", total=len(futures)):
            period_df, agg_dict = future.result()
            factor_col_info.update(agg_dict)
            all_factor_df_list.append(period_df)

    all_factors_df = (
        pd.concat(all_factor_df_list, ignore_index=True)
        .assign(
            stock_code=lambda df: df["stock_code"].astype("category"),
            stock_name=lambda df: df["stock_name"].astype("category"),
        )
        .sort_values(by=["trade_date", "stock_code"])
        .reset_index(drop=True)
    )
    all_factors_df.to_pickle(get_file_path("data", "runtime_cache", "factor_calculation_results.pkl"))
    pd.to_pickle(
        factor_col_info,
        get_file_path("data", "runtime_cache", "strategy_factor_columns.pkl"),
    )


if __name__ == "__main__":
    backtest_config = load_config()
    calculate_factors(backtest_config)
