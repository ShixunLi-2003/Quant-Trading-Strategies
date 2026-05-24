"""Load market data, align it to the trading calendar, and build selection diagnostics."""

from __future__ import annotations

import json
import os
import random
import time
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

import numpy as np
import pandas as pd
import requests

from core.figure import draw_equity_curve_plotly

pd.set_option("expand_frame_repr", False)
pd.set_option("future.no_silent_downcasting", True)
pd.set_option("display.unicode.ambiguous_as_wide", True)
pd.set_option("display.unicode.east_asian_width", True)


def cal_fuquan_price(df: pd.DataFrame, fuquan_type: str = "backward_adjusted", method=None) -> pd.DataFrame:
    """Build backward- or forward-adjusted OHLC prices."""
    fq_factor = (df["close"] / df["prev_close"]).cumprod()
    if fuquan_type == "backward_adjusted":
        fq_close = fq_factor * (df.iloc[0]["close"] / fq_factor.iloc[0])
    elif fuquan_type == "forward_adjusted":
        fq_close = fq_factor * (df.iloc[-1]["close"] / fq_factor.iloc[-1])
    else:
        raise ValueError(f"Unsupported adjustment type when calculating adjusted prices: {fuquan_type}")

    fq_open = df["open"] / df["close"] * fq_close
    fq_high = df["high"] / df["close"] * fq_close
    fq_low = df["low"] / df["close"] * fq_close
    df = df.assign(
        adj_factor=fq_factor,
        adjusted_close=fq_close,
        adjusted_open=fq_open,
        adjusted_high=fq_high,
        adjusted_low=fq_low,
    )
    if method and method != "open":
        df[f"{method}_adjusted"] = df[method] / df["close"] * fq_close
    return df


def get_file_in_folder(path, file_type, contains=None, filters=(), drop_type=False):
    """List files in a folder with simple extension and substring filters."""
    file_list = [file for file in os.listdir(path) if file.endswith(file_type)]
    if contains:
        file_list = [file for file in file_list if contains in file]
    for keyword in filters:
        file_list = [file for file in file_list if keyword not in file]
    if drop_type:
        file_list = [file[: file.rfind(".")] for file in file_list]
    return file_list


def import_index_data(path, date_range=(None, None), max_param=0) -> pd.DataFrame:
    """Read benchmark index data and convert it to a simple return series."""
    df_index = pd.read_csv(path, parse_dates=["candle_end_time"], encoding="gbk")
    df_index["index_return"] = df_index["close"].pct_change()
    df_index["index_return"] = df_index["index_return"].fillna(df_index["close"] / df_index["open"] - 1)
    df_index = df_index[["candle_end_time", "index_return"]].dropna(subset=["index_return"])
    df_index = df_index.rename(columns={"candle_end_time": "trade_date"})

    if date_range[0]:
        if max_param == 0:
            df_index = df_index[df_index["trade_date"] >= pd.to_datetime(date_range[0])]
        else:
            start_index = df_index[df_index["trade_date"] >= pd.to_datetime(date_range[0])].index[0]
            shifted_date = df_index["trade_date"].shift(max_param).bfill()
            df_index = df_index[df_index["trade_date"] >= shifted_date[start_index]]
    if date_range[1]:
        df_index = df_index[df_index["trade_date"] <= pd.to_datetime(date_range[1])]

    return df_index.sort_values(by=["trade_date"]).reset_index(drop=True)


def merge_with_index_data(df: pd.DataFrame, index_data: pd.DataFrame, fill_0_list=()) -> pd.DataFrame:
    """Right-join one stock with the trading calendar and forward-fill static fields."""
    listing_dt = df["trade_date"].iloc[0]
    max_candle_time = index_data["trade_date"].max()
    df = pd.merge(
        left=df,
        right=index_data[index_data["trade_date"] <= max_candle_time],
        on="trade_date",
        how="right",
        sort=True,
        indicator=True,
    )

    close = df["close"].ffill()
    df = df.assign(
        close=close,
        open=df["open"].fillna(close),
        high=df["high"].fillna(close),
        low=df["low"].fillna(close),
        average_price=df["average_price"].fillna(close),
        prev_close=df["prev_close"].fillna(close.shift()),
    )

    if "adjusted_close" in df.columns:
        adjusted_columns = {"adjusted_close": df["adjusted_close"].ffill()}
        for col in ["adjusted_open", "adjusted_high", "adjusted_low"]:
            if col in df.columns:
                adjusted_columns[col] = df[col].fillna(adjusted_columns["adjusted_close"])
        df = df.assign(**adjusted_columns)

    fill_0_list = list(set(["volume", "turnover", "return"] + list(fill_0_list)))
    df[fill_0_list] = df[fill_0_list].fillna(0)

    cash_flow_columns = [
        "retail_buy_amount",
        "mid_buy_amount",
        "large_buy_amount",
        "institutional_buy_amount",
        "retail_sell_amount",
        "mid_sell_amount",
        "large_sell_amount",
        "institutional_sell_amount",
    ]
    existing_cash_flow_columns = [col for col in cash_flow_columns if col in df.columns]
    if existing_cash_flow_columns:
        df[existing_cash_flow_columns] = df[existing_cash_flow_columns].fillna(0)

    member_columns = [
        "sse50_member",
        "csi300_member",
        "csi500_member",
        "csi1000_member",
        "csi2000_member",
        "chinext_member",
    ]
    existing_member_columns = [col for col in member_columns if col in df.columns]
    if existing_member_columns:
        filled_values = df[existing_member_columns].ffill()
        is_stop = df["_merge"] == "right_only"
        df[existing_member_columns] = df[existing_member_columns].where(~is_stop, filled_values)
        df[existing_member_columns] = df[existing_member_columns].fillna("N")

    df = df[df["trade_date"] >= listing_dt]

    is_delisted = df["stock_name"].str.contains("Delisted", na=False)
    temp = df[is_delisted]
    if not temp.empty:
        delisted_dt = temp["trade_date"].iloc[-1]
        df = df[df["trade_date"] <= delisted_dt]

    df = df.ffill()
    df = df[df["stock_code"].notnull()]
    df["is_tradable"] = (df["_merge"] != "right_only").astype(np.int8)
    del df["_merge"]
    return df.reset_index(drop=True)


def transfer_to_period_data(df: pd.DataFrame, period: str, extra_agg_dict=None) -> pd.DataFrame:
    """Aggregate daily data into the configured holding period."""
    if extra_agg_dict is None:
        extra_agg_dict = {}

    df["period_last_trade_date"] = df["trade_date"]
    agg_dict = {
        "period_last_trade_date": "last",
        "stock_code": "last",
        "stock_name": "last",
        "is_tradable": ["last", "sum", "count"],
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "turnover": "sum",
        "float_market_cap": "last",
        "total_market_cap": "last",
        "listed_trading_days": "last",
        "next_day_tradable": "last",
        "next_day_open_limit_up": "last",
        "next_day_st": "last",
        "next_day_delisted": "last",
        "adj_factor": "last",
    }
    agg_dict = {**agg_dict, **extra_agg_dict}

    group_tag = f"{period}start_date"
    period_df = df.groupby(group_tag).agg(agg_dict)
    period_df.columns = [
        "is_tradable"
        if col == ("is_tradable", "last")
        else "trading_day_count"
        if col == ("is_tradable", "sum")
        else "market_trading_day_count"
        if col == ("is_tradable", "count")
        else col[0]
        if isinstance(col, tuple)
        else col
        for col in period_df.columns
    ]
    period_df.dropna(subset=["stock_code"], inplace=True)

    period_pct_change = period_df["adj_factor"].pct_change(fill_method=None)
    first_ret = (np.array(period_pct_change.iloc[0]) + 1).prod() - 1
    period_pct_change = period_pct_change.fillna(first_ret)

    period_df = period_df.rename(columns={"period_last_trade_date": "trade_date"})
    period_df = period_df.assign(
        **{
            "return": period_pct_change,
            "next_period_return": period_pct_change.shift(-1),
        }
    )
    period_df = period_df.reset_index(drop=True)
    return period_df[period_df["is_tradable"] == 1]


def cal_zdt_price(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily limit-up and limit-down prices under A-share trading rules."""
    cond = df["stock_name"].str.contains("ST", na=False)
    df["limit_up_price"] = df["prev_close"] * 1.1
    df["limit_down_price"] = df["prev_close"] * 0.9
    df.loc[cond, "limit_up_price"] = df["prev_close"] * 1.05
    df.loc[cond, "limit_down_price"] = df["prev_close"] * 0.95

    rule_kcb = df["stock_code"].str.contains("sh68", na=False)
    new_rule_cyb = (df["trade_date"] > pd.to_datetime("2020-08-23")) & df["stock_code"].str.contains("sz3", na=False)
    df.loc[rule_kcb | new_rule_cyb, "limit_up_price"] = df["prev_close"] * 1.2
    df.loc[rule_kcb | new_rule_cyb, "limit_down_price"] = df["prev_close"] * 0.8

    cond_bj = df["stock_code"].str.contains("bj", na=False)
    df.loc[cond_bj, "limit_up_price"] = df["prev_close"] * 1.3
    df.loc[cond_bj, "limit_down_price"] = df["prev_close"] * 0.7

    def price_round(x):
        return float(Decimal(x + 1e-07).quantize(Decimal("1.00"), ROUND_HALF_UP))

    def price_round_bj(x):
        return float(Decimal(x).quantize(Decimal("0.00"), rounding=ROUND_DOWN))

    df.loc[~cond_bj, "limit_up_price"] = df["limit_up_price"].apply(price_round)
    df.loc[~cond_bj, "limit_down_price"] = df["limit_down_price"].apply(price_round)
    df.loc[cond_bj, "limit_up_price"] = df["limit_up_price"].apply(price_round_bj)
    df.loc[cond_bj, "limit_down_price"] = df["limit_down_price"].apply(price_round_bj)

    df["limit_up_locked"] = False
    df.loc[df["low"] >= df["limit_up_price"], "limit_up_locked"] = True
    df["limit_down_locked"] = False
    df.loc[df["high"] <= df["limit_down_price"], "limit_down_locked"] = True
    df["open_limit_up"] = False
    df.loc[df["open"] >= df["limit_up_price"], "open_limit_up"] = True
    df["open_limit_down"] = False
    df.loc[df["open"] <= df["limit_down_price"], "open_limit_down"] = True
    return df


def get_trade_date(index_data: pd.DataFrame) -> pd.DataFrame:
    """Download the official exchange holiday table and convert it to trading dates."""
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPTA_WEB_ZGXSRL",
        "columns": "ALL",
        "pageSize": 200,
        "sortColumns": "SDATE",
        "sortTypes": -1,
        "callback": f"jQuery1123{random.randint(10**16, 10**17 - 1)}_{int(time.time() * 1000)}",
        "_": int(time.time() * 1000),
    }
    response = requests.get(url, params=params)
    content = response.text
    start = content.find("(") + 1
    end = content.rfind(")")
    json_data = json.loads(content[start:end])
    holiday_df = pd.DataFrame(json_data["result"]["data"])
    holiday_df = holiday_df[holiday_df["MKT"].astype(str).str.startswith("A", na=False)]
    holiday_df = holiday_df.sort_values("SDATE").reset_index(drop=True)
    holiday_df["SDATE"] = pd.to_datetime(holiday_df["SDATE"])
    holiday_df["EDATE"] = pd.to_datetime(holiday_df["EDATE"])

    date_range = pd.DataFrame(
        pd.date_range(start=holiday_df["SDATE"].min(), end=f"{holiday_df['EDATE'].max().year}-12-31"),
        columns=["trade_date"],
    )
    for idx in holiday_df.index:
        condition = (
            (date_range["trade_date"] >= holiday_df.loc[idx, "SDATE"])
            & (date_range["trade_date"] <= holiday_df.loc[idx, "EDATE"])
        )
        date_range.loc[condition, "trade_date"] = np.nan
    weekend = date_range["trade_date"].dt.weekday.isin([5, 6])
    date_range.loc[weekend, "trade_date"] = np.nan
    date_range = date_range[date_range["trade_date"].notnull()]

    trade_date_df = pd.concat([index_data[["trade_date"]], date_range], ignore_index=True)
    return trade_date_df.drop_duplicates(subset="trade_date", keep="first").reset_index(drop=True)


def save_latest_result(conf, select_result_df: pd.DataFrame) -> None:
    """Save the most recent rebalance output in a dedicated convenience file."""
    index_data = conf.read_index_with_trading_date()
    last_date = select_result_df["trade_date"].max()
    period_end = index_data[index_data["trade_date"] == last_date][
        f"{conf.strategy.hold_period_name}end_date"
    ].iloc[0]

    if pd.isnull(conf.end_date) and period_end:
        new_select_df = select_result_df[select_result_df["trade_date"] == last_date].rename(
            columns={"trade_date": "selection_date"}
        )
        trade_date = index_data[index_data["trade_date"] == last_date]["next_trade_date"].iloc[0]
        new_select_df["trade_date"] = trade_date
        keep_cols = ["selection_date", "trade_date", "stock_code", "stock_name"]
        new_select_df = new_select_df[keep_cols]

        new_result_path = conf.get_result_folder() / "latest_selection_results.csv"
        if new_result_path.exists():
            old_result_df = pd.read_csv(
                new_result_path,
                encoding="utf-8-sig",
                parse_dates=["selection_date", "trade_date"],
            )
            result_df = old_result_df[
                (old_result_df["selection_date"] != last_date)
                & (old_result_df["trade_date"] != trade_date)
            ]
            result_df = pd.concat([result_df, new_select_df], ignore_index=True)
        else:
            result_df = new_select_df
        result_df.to_csv(new_result_path, encoding="utf-8-sig", index=False)


def select_analysis(conf, select_df: pd.DataFrame, top_n: int = 10, show_plot: bool = True) -> None:
    """Export descriptive diagnostics for the selected-stock universe."""
    last_stock_name = (
        pd.DataFrame(select_df.groupby("stock_code")["stock_name"].last()).reset_index()
    )
    select_df["year"] = select_df["trade_date"].dt.year
    year_count = (
        pd.DataFrame(select_df.groupby(["year", "stock_code"])["stock_code"].count())
        .rename(columns={"stock_code": "selection_count"})
        .reset_index()
    )
    year_count = year_count.merge(last_stock_name, on="stock_code", how="left")
    year_count["selection_count_rank"] = year_count.groupby("year")["selection_count"].rank(
        method="min",
        ascending=False,
    )
    year_count = year_count[year_count["selection_count_rank"] <= top_n]

    years = pd.DataFrame()
    for year, group in year_count.groupby("year"):
        idx = 0 if pd.isnull(years.index.max()) else years.index.max() + 1
        years.loc[idx, "year"] = str(int(year))
        group = group.sort_values(by="selection_count_rank").reset_index(drop=True)
        group["most_frequently_selected_by_year"] = (
            group["stock_name"].astype(str) + "_" + group["selection_count"].astype(str) + " "
        )
        years.loc[idx, "most_frequently_selected_by_year"] = group[
            "most_frequently_selected_by_year"
        ].sum()
    years.to_csv(
        conf.get_result_folder() / f"{conf.strategy.name}most_frequently_selected_by_year.csv",
        encoding="utf-8-sig",
    )

    period_market_value = (
        select_df.groupby("trade_date")
        .agg(
            holding_market_cap=("total_market_cap", "mean"),
            median_holding_market_cap=("total_market_cap", "median"),
        )
        .reset_index()
    )
    period_market_value[["holding_market_cap", "median_holding_market_cap"]] /= 100000000

    holding_desc = period_market_value["holding_market_cap"]
    draw_equity_curve_plotly(
        period_market_value,
        {"Holding Market Cap": "holding_market_cap"},
        "trade_date",
        desc=(
            f"Mean: {holding_desc.mean():.2f} (100M CNY)  "
            f"Median: {holding_desc.median():.2f} (100M CNY)  "
            f"Min: {holding_desc.min():.2f} (100M CNY)  "
            f"Max: {holding_desc.max():.2f} (100M CNY)"
        ),
        title="Holding Market Cap",
        path=conf.get_result_folder() / "holding_market_cap.html",
        show=show_plot,
    )

    median_desc = period_market_value["median_holding_market_cap"]
    draw_equity_curve_plotly(
        period_market_value,
        {"Median Holding Market Cap": "median_holding_market_cap"},
        "trade_date",
        desc=(
            f"Mean: {median_desc.mean():.2f} (100M CNY)  "
            f"Median: {median_desc.median():.2f} (100M CNY)  "
            f"Min: {median_desc.min():.2f} (100M CNY)  "
            f"Max: {median_desc.max():.2f} (100M CNY)"
        ),
        title="Median Holding Market Cap",
        path=conf.get_result_folder() / "median_holding_market_cap.html",
        show=show_plot,
    )
