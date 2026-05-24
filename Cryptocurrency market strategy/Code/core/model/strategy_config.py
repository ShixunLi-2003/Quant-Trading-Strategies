"""Represent factor definitions, filters, and portfolio selection rules."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import cached_property
from typing import Any

import numpy as np
import pandas as pd

from config import is_pure_long


def filter_series_by_range(series: pd.Series, range_str: str) -> pd.Series:
    """Convert a compact range expression into a boolean filter."""
    operator = range_str[:2] if range_str[:2] in {">=", "<=", "==", "!="} else range_str[0]
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


@dataclass(frozen=True)
class FactorConfig:
    """Describe one factor used in the composite ranking model."""

    name: str = "Bias"
    is_sort_asc: bool = True
    param: Any = 3
    weight: float = 1.0

    @classmethod
    def parse_config_list(cls, config_list: list[tuple]) -> list["FactorConfig"]:
        total_weight = sum(factor[3] for factor in config_list) or 1.0
        return [
            cls(
                name=factor_name,
                is_sort_asc=is_sort_asc,
                param=parameter,
                weight=weight / total_weight,
            )
            for factor_name, is_sort_asc, parameter, weight in config_list
        ]

    @cached_property
    def col_name(self) -> str:
        return f"{self.name}_{self.param}"

    def __repr__(self) -> str:
        direction = "asc" if self.is_sort_asc else "desc"
        return f"{self.col_name}<{direction}, weight={self.weight:.3f}>"


@dataclass(frozen=True)
class FilterMethod:
    """Represent a filtering rule such as rank, percentile, or raw value cutoff."""

    how: str = ""
    range: str = ""

    def __repr__(self) -> str:
        return f"{self.how}:{self.range}"

    def to_val(self) -> str:
        return f"{self.how}:{self.range}"


@dataclass(frozen=True)
class FilterFactorConfig:
    """Describe a factor-based filter applied before ranking the universe."""

    name: str = "Bias"
    param: Any = 3
    method: FilterMethod | None = None
    is_sort_asc: bool = True

    @cached_property
    def col_name(self) -> str:
        return f"{self.name}_{self.param}"

    @classmethod
    def init(cls, filter_factor: tuple) -> "FilterFactorConfig":
        config: dict[str, Any] = {"name": filter_factor[0], "param": filter_factor[1]}
        if len(filter_factor) > 2:
            how, range_value = re.sub(r"\s+", "", filter_factor[2]).split(":")
            config["method"] = FilterMethod(how=how, range=range_value)
        if len(filter_factor) > 3:
            config["is_sort_asc"] = filter_factor[3]
        return cls(**config)

    def __repr__(self) -> str:
        if self.method is None:
            return self.col_name
        direction = "asc" if self.is_sort_asc else "desc"
        return f"{self.col_name}<{direction}, {self.method}>"


def calc_factor_common(df: pd.DataFrame, factor_list: list[FactorConfig]) -> np.ndarray:
    """Aggregate multiple factor ranks into one composite score."""
    factor_val = np.zeros(df.shape[0])
    for factor_config in factor_list:
        rank = df.groupby("candle_begin_time")[factor_config.col_name].rank(
            ascending=factor_config.is_sort_asc,
            method="min",
        )
        factor_val += rank * factor_config.weight
    return factor_val


def filter_common(df: pd.DataFrame, filter_list: list[FilterFactorConfig]) -> pd.Series:
    """Build the universe mask implied by all configured factor filters."""
    condition = pd.Series(True, index=df.index)
    for filter_config in filter_list:
        if filter_config.method is None:
            continue
        col_name = filter_config.col_name
        match filter_config.method.how:
            case "rank":
                rank = df.groupby("candle_begin_time")[col_name].rank(
                    ascending=filter_config.is_sort_asc,
                    pct=False,
                )
                condition &= filter_series_by_range(rank, filter_config.method.range)
            case "pct":
                rank = df.groupby("candle_begin_time")[col_name].rank(
                    ascending=filter_config.is_sort_asc,
                    pct=True,
                )
                condition &= filter_series_by_range(rank, filter_config.method.range)
            case "val":
                condition &= filter_series_by_range(df[col_name], filter_config.method.range)
            case _:
                raise ValueError(f"Unsupported filter mode: {filter_config.method.how}")
    return condition


@dataclass
class StrategyConfig:
    """Capture the full definition of a cross-sectional selection strategy."""

    name: str = "Strategy"
    strategy: str = "Strategy"
    hold_period: str = "1D"
    offset_list: list[int] = None
    is_use_spot: bool = False
    long_select_coin_num: int | float = 0.1
    short_select_coin_num: int | float | str = "long_nums"
    factor_name: str = "composite_factor"
    factor_list: list[FactorConfig] = None
    filter_list: list[FilterFactorConfig] = None
    long_cap_weight: float = 1.0
    short_cap_weight: float = 1.0

    def __post_init__(self) -> None:
        self.hold_period = self.hold_period.replace("h", "H").replace("d", "D")
        self.offset_list = [0] if self.offset_list is None else list(self.offset_list)
        self.factor_list = [] if self.factor_list is None else list(self.factor_list)
        self.filter_list = [] if self.filter_list is None else list(self.filter_list)

    @cached_property
    def is_day_period(self) -> bool:
        return self.hold_period.endswith("D")

    @cached_property
    def is_hour_period(self) -> bool:
        return self.hold_period.endswith("H")

    @cached_property
    def period_num(self) -> int:
        return int(self.hold_period[:-1])

    @cached_property
    def period_type(self) -> str:
        return self.hold_period[-1]

    @cached_property
    def factor_columns(self) -> list[str]:
        columns = {factor.col_name for factor in self.factor_list}
        columns.update(filter_factor.col_name for filter_factor in self.filter_list)
        return list(columns)

    @cached_property
    def all_factors(self) -> set[FactorConfig | FilterFactorConfig]:
        return set(self.factor_list + self.filter_list)

    @classmethod
    def init(cls, **config: Any) -> "StrategyConfig":
        config["long_select_coin_num"] = config.get("long_select_coin_num", 0.1)
        config["short_select_coin_num"] = config.get("short_select_coin_num", "long_nums")
        config["factor_list"] = FactorConfig.parse_config_list(config.get("factor_list", []))
        config["filter_list"] = [
            FilterFactorConfig.init(filter_config)
            for filter_config in config.get("filter_list", [])
        ]
        return cls(**config)

    def get_fullname(self, as_folder_name: bool = False) -> str:
        factor_desc = "&".join([f"{self.factor_list}", f"filters={self.filter_list}"])
        fullname = (
            f"{self.name}-{self.hold_period}-long={self.long_select_coin_num}"
            f"-short={self.short_select_coin_num}-factors={factor_desc}"
        )
        md5_hash = hashlib.md5(f"{fullname}-{self.offset_list}".encode("utf-8")).hexdigest()
        return f"{self.name}-{md5_hash[:8]}" if as_folder_name else fullname

    def __repr__(self) -> str:
        run_mode = "long_only" if is_pure_long else "long_short"
        offset_mode = "enabled" if len(self.offset_list) > 1 else "disabled"
        return (
            f"- strategy: {self.name}\n"
            f"- holding period: {self.hold_period}\n"
            f"- offsets: {offset_mode}\n"
            f"- run mode: {run_mode}\n"
            f"- long count: {self.long_select_coin_num}\n"
            f"- short count: {self.short_select_coin_num}\n"
            f"- ranking factors: {self.factor_list}\n"
            f"- universe filters: {self.filter_list}"
        )

    def calc_factor(self, df: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
        raise NotImplementedError

    def calc_select_factor(self, df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({self.factor_name: calc_factor_common(df, self.factor_list)}, index=df.index)

    def before_filter(self, df: pd.DataFrame, **kwargs: Any) -> tuple[pd.DataFrame, pd.DataFrame]:
        raise NotImplementedError

    def filter_before_select(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        filter_condition = filter_common(df, self.filter_list)
        filtered = df[filter_condition].copy()
        return filtered, filtered.copy()

    def after_merge_index(self, candle_df, symbol, factor_dict, data_dict):
        return candle_df, factor_dict, data_dict
