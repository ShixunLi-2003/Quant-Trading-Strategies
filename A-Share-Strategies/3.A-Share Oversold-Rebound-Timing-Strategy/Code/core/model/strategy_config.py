"""Define factor, filter, and strategy configuration objects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import Callable

import numpy as np
import pandas as pd

from config import days_listed


def filter_series_by_range(series: pd.Series, range_str: str) -> pd.Series:
    """Apply a textual comparison rule such as `<=0.4` to a pandas Series."""
    operator = range_str[:2] if range_str[:2] in [">=", "<=", "==", "!="] else range_str[0]
    value = float(range_str[len(operator):])
    match operator:
        case ">=":
            return series >= value
        case "<=":
            return series <= value
        case "==":
            return series == value
        case "!=":
            return series != value
        case ">":
            return series > value
        case "<":
            return series < value
        case _:
            raise ValueError(f"Unsupported operator: {operator}")


def normalize_name(name: str) -> str:
    """Convert a display name into a stable snake-case identifier."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def format_param(param) -> str:
    """Render a factor parameter into a compact string for column naming."""
    if param is None:
        return "none"
    if isinstance(param, (tuple, list)):
        return "_".join(str(item).replace(".", "_") for item in param)
    if isinstance(param, dict):
        return "_".join(f"{k}_{v}" for k, v in sorted(param.items()))
    return str(param).replace(".", "_")


def get_col_name(factor_name: str, factor_param) -> str:
    """Build the dataframe column name used to store a factor value."""
    return f"{normalize_name(factor_name)}_{format_param(factor_param)}"


class HashableDict:
    """Hashable wrapper used when a factor parameter is itself a dictionary."""

    def __init__(self, data: dict):
        self.data = tuple(sorted(data.items()))

    def __repr__(self):
        return "{" + ", ".join(f"{k}: {v}" for k, v in self.data) + "}"

    def __eq__(self, other):
        return self.data == other.data

    def __hash__(self):
        return hash(self.data)

    def __getitem__(self, key):
        return dict(self.data)[key]


def parse_param(param):
    """Normalize factor parameters into a consistent internal type."""
    if isinstance(param, list):
        return tuple(param)
    if isinstance(param, dict):
        return HashableDict(param)
    if isinstance(param, (str, int, float, tuple, bool)) or param is None:
        return param
    raise ValueError(f"Unsupported parameter type: {type(param)}")


@dataclass(frozen=True)
class FactorConfig:
    """Store configuration for one ranking factor."""

    name: str = "factor"
    is_sort_asc: bool = True
    param: tuple | HashableDict | str | int | float | bool | None = 3
    weight: float = 1.0

    @classmethod
    def parse_config_list(cls, config_list: list[tuple]) -> list["FactorConfig"]:
        total_weight = sum(factor[3] for factor in config_list)
        return [
            cls(
                name=factor_name,
                is_sort_asc=is_sort_asc,
                param=parse_param(param),
                weight=weight / total_weight,
            )
            for factor_name, is_sort_asc, param, weight in config_list
        ]

    @cached_property
    def col_name(self) -> str:
        return get_col_name(self.name, self.param)

    def __repr__(self) -> str:
        direction = "asc" if self.is_sort_asc else "desc"
        return f"{self.col_name}[{direction}]@{self.weight:.4f}"

    def to_tuple(self) -> tuple:
        return self.name, self.is_sort_asc, self.param, self.weight


@dataclass(frozen=True)
class FilterMethod:
    """Store the method and threshold used by a filter factor."""

    how: str = ""
    range: str = ""

    def __repr__(self) -> str:
        display_map = {"rank": "rank", "pct": "percentile", "val": "value"}
        if self.how not in display_map:
            raise ValueError(f"Unsupported filter method: {self.how}")
        return f"{display_map[self.how]}:{self.range}"

    def to_val(self) -> str:
        return f"{self.how}:{self.range}"


@dataclass(frozen=True)
class FilterFactorConfig:
    """Store configuration for one pre-selection filter factor."""

    name: str = "factor"
    param: tuple | HashableDict | str | int | float | bool | None = 3
    method: FilterMethod | None = None
    is_sort_asc: bool = True

    @cached_property
    def col_name(self) -> str:
        return get_col_name(self.name, self.param)

    def __repr__(self) -> str:
        direction = "asc" if self.is_sort_asc else "desc"
        return f"{self.col_name}[{direction}]#{self.method}"

    @classmethod
    def init(cls, filter_factor: tuple) -> "FilterFactorConfig":
        config = {"name": filter_factor[0], "param": parse_param(filter_factor[1])}
        if len(filter_factor) > 2:
            how, range_str = re.sub(r"\s+", "", filter_factor[2]).split(":")
            config["method"] = FilterMethod(how=how, range=range_str)
        if len(filter_factor) > 3:
            config["is_sort_asc"] = filter_factor[3]
        return cls(**config)

    def to_tuple(self, full_mode: bool = False) -> tuple:
        if full_mode:
            return self.name, self.param, self.method.to_val(), self.is_sort_asc
        return self.name, self.param


def calc_factor_common(df: pd.DataFrame, factor_list: list[FactorConfig]) -> np.ndarray:
    """Build the composite ranking score from weighted factor ranks."""
    factor_val = np.zeros(df.shape[0])
    for factor_config in factor_list:
        rank = df.groupby("trade_date")[factor_config.col_name].rank(
            ascending=factor_config.is_sort_asc,
            method="min",
        )
        factor_val += rank * factor_config.weight
    return factor_val


def filter_common(df: pd.DataFrame, filter_list: list[FilterFactorConfig]) -> pd.Series:
    """Apply configured filter factors to the period dataframe."""
    condition = pd.Series(True, index=df.index)
    for filter_config in filter_list:
        col_name = filter_config.col_name
        match filter_config.method.how:
            case "rank":
                rank = df.groupby("trade_date")[col_name].rank(
                    ascending=filter_config.is_sort_asc,
                    pct=False,
                )
                condition &= filter_series_by_range(rank, filter_config.method.range)
            case "pct":
                rank = df.groupby("trade_date")[col_name].rank(
                    ascending=filter_config.is_sort_asc,
                    pct=True,
                )
                condition &= filter_series_by_range(rank, filter_config.method.range)
            case "val":
                condition &= filter_series_by_range(df[col_name], filter_config.method.range)
            case _:
                raise ValueError(f"Unsupported filter method: {filter_config.method.how}")
    return condition


@dataclass
class StrategyConfig:
    """Represent the complete stock-selection strategy configuration."""

    name: str = "Strategy"
    hold_period: str = "W"
    candle_period: str = "D"
    select_num: int | float = 0.1
    factor_name: str = "composite_factor"
    factor_list: list[FactorConfig] = field(default_factory=list)
    filter_list: list[FilterFactorConfig] = field(default_factory=list)
    funcs: dict[str, Callable] = field(default_factory=dict)

    @cached_property
    def hold_period_name(self) -> str:
        period_map = {
            "W": "weekly_",
            "M": "monthly_",
            "3D": "period_3d_",
            "5D": "period_5d_",
            "10D": "period_10d_",
        }
        return period_map.get(self.hold_period, f"{self.hold_period.lower()}_")

    @cached_property
    def factor_columns(self) -> list[str]:
        columns = {factor_config.col_name for factor_config in self.factor_list}
        columns.update(filter_factor.col_name for filter_factor in self.filter_list)
        return list(columns)

    @cached_property
    def all_factors(self) -> set:
        factors = set(self.factor_list)
        factors.update(self.filter_list)
        return factors

    @classmethod
    def init(cls, **config) -> "StrategyConfig":
        config["factor_list"] = FactorConfig.parse_config_list(config.get("factor_list", []))
        config["filter_list"] = [
            FilterFactorConfig.init(filter_config)
            for filter_config in config.get("filter_list", [])
        ]
        return cls(**config)

    def __repr__(self) -> str:
        return (
            f"{self.name}-{self.hold_period}-{self.select_num}-"
            f"{self.factor_list}-{self.filter_list}"
        )

    def get_fullname(self) -> str:
        return (
            f"{self.name}-holding_period{self.hold_period}-selection_count{self.select_num}-"
            f"factors:{self.factor_list}-filters:{self.filter_list}"
        )

    def max_int_param(self) -> int:
        max_int = 0
        for factor_config in self.all_factors:
            if isinstance(factor_config.param, int):
                max_int = max(max_int, factor_config.param)
        return max_int

    def filter_before_select(self, period_df: pd.DataFrame) -> pd.DataFrame:
        if "filter_stock" in self.funcs:
            return self.funcs["filter_stock"](period_df, self)

        common_filter = (
            ~period_df["stock_name"].str.contains("ST", regex=False, na=False)
            & ~period_df["stock_name"].str.contains("S", regex=False, na=False)
            & ~period_df["stock_name"].str.contains("*", regex=False, na=False)
            & ~period_df["stock_name"].str.contains("Delisted", regex=False, na=False)
            & (period_df["trading_day_count"] / period_df["market_trading_day_count"] >= 0.8)
            & (period_df["next_day_tradable"] == 1)
            & (period_df["next_day_open_limit_up"] != 1)
            & (period_df["next_day_st"] != 1)
            & (period_df["next_day_delisted"] != 1)
            & (period_df["listed_trading_days"] > days_listed)
        )
        period_df = period_df[common_filter]
        filter_condition = filter_common(period_df, self.filter_list)
        return period_df[filter_condition]

    def calc_select_factor(self, period_df: pd.DataFrame) -> pd.DataFrame:
        if "calc_select_factor" in self.funcs:
            return self.funcs["calc_select_factor"](period_df, self)
        return pd.DataFrame(
            {self.factor_name: self.calc_select_factor_default(period_df)},
            index=period_df.index,
        )

    def calc_select_factor_default(self, period_df: pd.DataFrame) -> np.ndarray:
        return calc_factor_common(period_df, self.factor_list)
