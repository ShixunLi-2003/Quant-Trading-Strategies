"""Simulate portfolio equity and render the strategy equity curve."""

from __future__ import annotations

import numba as nb
import numpy as np
import pandas as pd

from core.evaluate import strategy_evaluate
from core.figure import draw_equity_curve_plotly
from core.market_essentials import import_index_data
from core.model.backtest_config import BacktestConfig
from core.model.type_def import SimuParams, StockMarketData, get_symbol_type
from core.rebalance import RebAlways
from core.simulator import Simulator
from core.utils.path_kit import get_file_path

pd.set_option("display.max_rows", 1000)
pd.set_option("expand_frame_repr", False)


def read_trading_dates(first_date, last_date):
    """Load the trading calendar between the requested dates."""
    calendar = pd.read_csv(
        get_file_path("data", "trading_calendar.csv"),
        encoding="utf-8",
        parse_dates=["trade_date"],
    )
    trading_dates = calendar["trade_date"]
    return trading_dates[(trading_dates >= first_date) & (trading_dates <= last_date)]


def get_stock_market(
    pivot_dict_stock: dict,
    trading_dates: pd.Series,
    symbols: list[str],
    symbol_types: list[int],
) -> StockMarketData:
    """Build the market data container consumed by the simulator."""
    df_open = pivot_dict_stock["open"].loc[trading_dates, symbols]
    df_close = pivot_dict_stock["close"].loc[trading_dates, symbols]
    df_preclose = pivot_dict_stock["preclose"].loc[trading_dates, symbols]
    should_copy = True
    return StockMarketData(
        candle_begin_ts=(trading_dates.astype(np.int64) // 1000000000).to_numpy(copy=should_copy),
        op=df_open.to_numpy(copy=should_copy),
        cl=df_close.to_numpy(copy=should_copy),
        pre_cl=df_preclose.to_numpy(copy=should_copy),
        types=np.array(symbol_types, dtype=np.int16),
    )


def calc_equity(conf: BacktestConfig, pivot_dict_stock: dict, df_stock_ratio: pd.DataFrame):
    """Simulate the full account history from a target-weight schedule."""
    symbols = sorted(df_stock_ratio.columns)
    symbol_types = [get_symbol_type(sym) for sym in symbols]
    start_date = max(df_stock_ratio.index.min(), pd.to_datetime(conf.start_date))
    trading_dates = read_trading_dates(start_date, conf.end_date)
    market = get_stock_market(pivot_dict_stock, trading_dates, symbols, symbol_types)
    df_stock_ratio = df_stock_ratio.loc[start_date:conf.end_date, symbols]

    params = SimuParams(
        init_cash=conf.initial_cash,
        stamp_tax_rate=conf.t_rate,
        commission_rate=conf.c_rate,
    )
    adj_dts = df_stock_ratio.index.to_numpy().astype(np.int64) // 1000000000
    ratios = df_stock_ratio.to_numpy()
    pos_calc = RebAlways(market.types)
    cashes, pos_values, stamp_taxes, commissions = start_simulation(
        market,
        params,
        adj_dts,
        ratios,
        pos_calc,
    )

    account_df = pd.DataFrame(
        {
            "trade_date": trading_dates,
            "available_cash": cashes,
            "holding_market_value": pos_values,
            "stamp_tax": stamp_taxes,
            "broker_commission": commissions,
        }
    )
    account_df["total_assets"] = account_df["available_cash"] + account_df["holding_market_value"]
    account_df["nav"] = account_df["total_assets"] / conf.initial_cash
    account_df["transaction_cost"] = account_df["stamp_tax"] + account_df["broker_commission"]
    account_df["return"] = account_df["nav"].pct_change()

    rtn, year_return, month_return, quarter_return = strategy_evaluate(
        account_df,
        net_col="nav",
        pct_col="return",
    )
    conf.set_report(rtn.T)
    return account_df, rtn, year_return, month_return, quarter_return


@nb.njit(boundscheck=True)
def start_simulation(market, simu_params, adj_dts, ratios, pos_calc):
    """Run the low-level buy-sell simulation in numba."""
    n_bars = len(market.candle_begin_ts)
    n_syms = len(market.types)
    pos_values = np.zeros(n_bars, dtype=np.float64)
    cashes = np.zeros(n_bars, dtype=np.float64)
    stamp_taxes = np.zeros(n_bars, dtype=np.float64)
    commissions = np.zeros(n_bars, dtype=np.float64)
    init_pos_values = np.zeros(n_syms, dtype=np.float64)
    simu = Simulator(
        simu_params.init_cash,
        simu_params.commission_rate,
        simu_params.stamp_tax_rate,
        init_pos_values,
    )
    idx_adj = 0
    buy_next_open = False

    for idx_bar in range(n_bars):
        simu.fill_last_prices(market.pre_cl[idx_bar])
        simu.settle_pos_values(market.op[idx_bar])
        simu.fill_last_prices(market.op[idx_bar])
        stamp_tax = commission = 0.0

        if buy_next_open:
            target_pos = pos_calc.calc_lots(simu.cash, market.op[idx_bar], ratios[idx_adj])
            idx_adj += 1
            buy_next_open = False
            commission = simu.buy_stocks(market.op[idx_bar], target_pos)
        elif idx_adj < len(adj_dts) and adj_dts[idx_adj] == market.candle_begin_ts[idx_bar]:
            stamp_tax, commission = simu.sell_all(market.cl[idx_bar])
            buy_next_open = True

        simu.settle_pos_values(market.cl[idx_bar])
        stamp_taxes[idx_bar] = stamp_tax
        commissions[idx_bar] = commission
        pos_values[idx_bar] = simu.get_pos_value()
        cashes[idx_bar] = simu.cash

    return cashes, pos_values, stamp_taxes, commissions


def show_plot_performance(
    conf: BacktestConfig,
    account_df: pd.DataFrame,
    rtn: pd.DataFrame,
    year_return: pd.DataFrame,
    title_prefix: str = "",
    **kwargs,
):
    """Add benchmark series and render the final interactive equity-curve report."""
    del year_return

    for index_code, index_name in zip(["sh000300", "sh000905"], ["CSI 300", "CSI 500"]):
        index_path = conf.index_data_path / f"{index_code}.csv"
        if not index_path.exists():
            continue
        index_df = import_index_data(index_path, [account_df["trade_date"].min(), conf.end_date])
        account_df = pd.merge(
            left=account_df,
            right=index_df[["trade_date", "index_return"]],
            on=["trade_date"],
            how="left",
        )
        account_df[f"{index_name} Index"] = (account_df["index_return"] + 1).cumprod()
        del account_df["index_return"]

    data_dict = {
        "Equity Curve": "nav",
        "CSI 300": "CSI 300 Index",
        "CSI 500": "CSI 500 Index",
    }
    right_axis = {"Max Drawdown": "nav_peak_to_date"}
    for col_name, col_series in kwargs.items():
        account_df[col_name] = col_series.reset_index(drop=True)
        data_dict[col_name] = col_name

    pic_title = (
        f"Cumulative NAV: {rtn.at['cumulative_nav', 0]} | "
        f"Annual Return: {rtn.at['annual_return', 0]} | "
        f"Max Drawdown: {rtn.at['max_drawdown', 0]}"
    )
    file_prefix = "retimed_" if title_prefix == "Retimed" else title_prefix
    draw_equity_curve_plotly(
        account_df,
        data_dict=data_dict,
        date_col="trade_date",
        right_axis=right_axis,
        title=pic_title,
        desc=conf.get_fullname(),
        path=conf.get_result_folder() / f"{file_prefix}equity_curve.html",
    )
