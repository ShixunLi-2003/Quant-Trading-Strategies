"""Select stocks from the factor panel and persist the rebalance schedule."""

import warnings

import pandas as pd

from core.market_essentials import save_latest_result, select_analysis
from core.model.backtest_config import BacktestConfig, load_config
from core.utils.path_kit import get_file_path

warnings.filterwarnings("ignore")
pd.set_option("expand_frame_repr", False)
pd.set_option("display.unicode.ambiguous_as_wide", True)
pd.set_option("display.unicode.east_asian_width", True)

FACTOR_COLS = ["trade_date", "stock_code", "stock_name"]


def select_stocks(conf: BacktestConfig, show_plot: bool = True):
    """Filter the factor panel, rank securities, and save the selected holdings."""
    strategy = conf.strategy
    period_df = pd.read_pickle(get_file_path("data", "runtime_cache", "factor_calculation_results.pkl"))
    factor_columns_dict = pd.read_pickle(
        get_file_path("data", "runtime_cache", "strategy_factor_columns.pkl")
    )
    factor_columns_dict = {
        key: value
        for key, value in factor_columns_dict.items()
        if key in conf.strategy.factor_columns
    }

    period_df["market_cap_percentile"] = period_df.groupby("trade_date")["total_market_cap"].rank(pct=True)
    period_df = period_df[period_df["is_tradable"] == 1].dropna(subset=factor_columns_dict.keys()).copy()
    period_df.dropna(subset=["stock_code"], inplace=True)
    period_df.sort_values(by=["trade_date", "stock_code"], inplace=True)
    period_df.reset_index(drop=True, inplace=True)

    period_df = strategy.filter_before_select(period_df)
    result_df = strategy.calc_select_factor(period_df)
    period_df = period_df.join(result_df)

    index_data = conf.read_index_with_trading_date()
    select_dates = index_data[index_data[f"{conf.strategy.hold_period_name}end_date"]]["trade_date"]
    period_df = period_df[period_df["trade_date"].isin(select_dates)]
    period_df = select_by_factor(period_df, strategy.select_num, strategy.factor_name)

    select_result_df = period_df[[*FACTOR_COLS, "target_position_weight"]].copy()
    if select_result_df.empty:
        return None

    file_path = conf.get_result_folder() / f"{strategy.name}selection_results.pkl"
    select_result_df.to_pickle(file_path)
    select_result_df.to_csv(
        conf.get_result_folder() / f"{strategy.name}selection_results.csv",
        encoding="utf-8-sig",
    )
    save_latest_result(conf, select_result_df)
    select_analysis(conf, period_df, 10, show_plot=show_plot)
    return select_result_df


def select_by_factor(period_df: pd.DataFrame, select_num: float | int, factor_name: str) -> pd.DataFrame:
    """Select the top-N or top-percentile stocks by composite factor score."""
    period_df = calc_select_factor_rank(period_df, factor_column=factor_name, ascending=True)
    if int(select_num) == 0:
        period_df = period_df[period_df["rank"] <= period_df["total_count"] * select_num].copy()
    else:
        period_df = period_df[period_df["rank"] <= select_num].copy()

    period_df["target_position_weight"] = 1 / period_df.groupby("trade_date")["stock_code"].transform("size")
    period_df.sort_values(by="trade_date", inplace=True)
    period_df.reset_index(drop=True, inplace=True)
    period_df.drop(columns=["total_count", "rank_max"], inplace=True)
    return period_df


def calc_select_factor_rank(df: pd.DataFrame, factor_column: str = "factor", ascending: bool = True):
    """Add within-date ranking columns for a target factor column."""
    df["rank"] = df.groupby("trade_date")[factor_column].rank(method="min", ascending=ascending)
    df["rank_max"] = df.groupby("trade_date")["rank"].transform("max")
    df.sort_values(by=["trade_date", "rank"], inplace=True)
    df["total_count"] = df.groupby("trade_date")["stock_code"].transform("size")
    return df


if __name__ == "__main__":
    backtest_config = load_config()
    select_stocks(backtest_config)
