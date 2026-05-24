"""Load repository-level settings into a runtime configuration object."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd

from config import backtest_name, backtest_path, is_pure_long, use_offset
from core.model.strategy_config import StrategyConfig
from core.utils.path_kit import get_folder_path


class BacktestConfig:
    """Central runtime configuration for data, strategy, and simulation settings."""

    data_file_fingerprint: str = ""

    def __init__(self, name: str, **config: Any) -> None:
        self.name = name
        self.start_date = config.get("start_date", "2021-01-01")
        self.end_date = config.get("end_date", "2024-03-30")

        self.initial_usdt = config.get("initial_usdt", 10000)
        self.leverage = config.get("leverage", 1)
        self.margin_rate = 5 / 100

        self.swap_c_rate = config.get("swap_c_rate", 6e-4)
        self.spot_c_rate = config.get("spot_c_rate", 2e-3)
        self.swap_min_order_limit = 5
        self.spot_min_order_limit = 10

        self.black_list = config.get("black_list", [])
        self.min_kline_num = config.get("min_kline_num", 168)

        self.is_use_spot = False
        self.is_day_period = False
        self.is_hour_period = False
        self.factor_params_dict: dict[str, set] = {}
        self.factor_col_name_list: list[str] = []
        self.hold_period = "1H"
        self.strategy: StrategyConfig | None = None
        self.strategy_raw: dict | None = None
        self.report: pd.DataFrame | None = None
        self.iter_round: int | str = 0

    def __repr__(self) -> str:
        strategy_repr = self.strategy if self.strategy is not None else "<not loaded>"
        return (
            f"{'+' * 56}\n"
            f"# {self.name}\n"
            f"+ backtest window: {self.start_date} -> {self.end_date}\n"
            f"+ trading costs: swap={self.swap_c_rate:.4%}, spot={self.spot_c_rate:.4%}\n"
            f"+ leverage: {self.leverage:.2f}\n"
            f"+ minimum warm-up bars: {self.min_kline_num}\n"
            f"+ blacklist: {self.black_list}\n"
            f"+ strategy:\n{strategy_repr}\n"
            f"{'+' * 56}"
        )

    @property
    def hold_period_type(self) -> str:
        return "D" if self.is_day_period else "H"

    def info(self) -> None:
        print(self)

    def get_fullname(self, as_folder_name: bool = False) -> str:
        fullname = f"{self.name} {self.strategy.get_fullname(as_folder_name=False)}"
        md5_hash = hashlib.md5(fullname.encode("utf-8")).hexdigest()
        return f"{self.name}-{md5_hash[:8]}" if as_folder_name else fullname

    def load_strategy_config(self, strategy_dict: dict) -> None:
        self.strategy_raw = strategy_dict
        strategy_cfg = StrategyConfig.init(**strategy_dict)

        if strategy_cfg.is_day_period:
            self.is_day_period = True
        else:
            self.is_hour_period = True

        self.hold_period = strategy_cfg.hold_period.lower()
        self.is_use_spot = strategy_cfg.is_use_spot = is_pure_long

        if is_pure_long:
            strategy_cfg.long_cap_weight = 1.0
            strategy_cfg.short_cap_weight = 0.0

        if self.is_use_spot and self.leverage >= 2:
            raise ValueError("Spot mode does not support leverage >= 2 in this simulator.")

        if strategy_cfg.long_select_coin_num == 0 and (
            strategy_cfg.short_select_coin_num == 0
            or strategy_cfg.short_select_coin_num == "long_nums"
        ):
            raise ValueError("Both long and short selection counts are zero.")
        if strategy_cfg.short_select_coin_num == 0 and strategy_cfg.short_cap_weight == 0:
            raise ValueError("Short leg is disabled while short capital weight is also zero.")

        if use_offset:
            strategy_cfg.offset_list = list(range(strategy_cfg.period_num))

        self.strategy = strategy_cfg
        self.factor_col_name_list += strategy_cfg.factor_columns

        for factor_config in strategy_cfg.all_factors:
            self.factor_params_dict.setdefault(factor_config.name, set()).add(factor_config.param)

        self.factor_col_name_list = list(set(self.factor_col_name_list))

    @classmethod
    def init_from_config(cls, load_strategy_list: bool = True) -> "BacktestConfig":
        import config

        backtest_config = cls(
            config.backtest_name,
            start_date=config.start_date,
            end_date=config.end_date,
            initial_usdt=config.initial_usdt,
            leverage=config.leverage,
            swap_c_rate=config.swap_c_rate,
            spot_c_rate=config.spot_c_rate,
            black_list=config.black_list,
            min_kline_num=config.min_kline_num,
        )
        if load_strategy_list:
            backtest_config.load_strategy_config(config.strategy)
        return backtest_config

    def set_report(self, report: pd.DataFrame) -> None:
        report = report.copy()
        report["strategy"] = self.get_fullname()
        self.report = report

    def get_result_folder(self) -> Path:
        if self.iter_round == 0:
            return get_folder_path(backtest_path, self.name, path_type=True)
        suffix = (
            f"parameter_sweep_{self.iter_round}"
            if isinstance(self.iter_round, int)
            else str(self.iter_round)
        )
        return get_folder_path("data", "parameter_sweeps", self.name, suffix, path_type=True)

    def get_strategy_config_sheet(self, with_factors: bool = True) -> dict[str, Any]:
        ret = {"strategy": self.name, "fullname": self.get_fullname()}
        if not with_factors:
            return ret
        factor_dict = {"hold_period": self.strategy.hold_period}
        for factor_config in self.strategy.all_factors:
            factor_dict[f"factor::{factor_config.name}"] = factor_config.param
        ret.update(factor_dict)
        return ret


class BacktestConfigFactory:
    """Generate multiple runtime configurations for parameter sweeps."""

    def __init__(self) -> None:
        self.config_list: list[BacktestConfig] = []

    @property
    def result_folder(self) -> Path:
        return get_folder_path("data", "parameter_sweeps", backtest_name, path_type=True)

    def generate_all_factor_config(self) -> BacktestConfig:
        import config

        backtest_config = BacktestConfig.init_from_config(load_strategy_list=False)
        factor_list: list[tuple] = []
        filter_list: list[tuple] = []
        for conf in self.config_list:
            factor_list += conf.strategy_raw["factor_list"]
            filter_list += conf.strategy_raw["filter_list"]
        backtest_config.load_strategy_config({
            **config.strategy,
            "factor_list": factor_list,
            "filter_list": filter_list,
        })
        return backtest_config

    def get_name_params_sheet(self) -> pd.DataFrame:
        rows = [config.get_strategy_config_sheet() for config in self.config_list]
        sheet = pd.DataFrame(rows)
        output_path = self.config_list[-1].get_result_folder().parent / "strategy_parameter_grid.xlsx"
        sheet.to_excel(output_path, index=False)
        return sheet

    def generate_by_strategies(self, strategies: list[dict]) -> list[BacktestConfig]:
        config_list: list[BacktestConfig] = []
        for iter_round, strategy in enumerate(strategies, start=1):
            backtest_config = BacktestConfig.init_from_config(load_strategy_list=False)
            backtest_config.load_strategy_config(strategy)
            backtest_config.iter_round = iter_round
            config_list.append(backtest_config)
        self.config_list = config_list
        return config_list


def load_config() -> BacktestConfig:
    """Load `Code/config.py` into a runtime backtest configuration object."""
    conf = BacktestConfig.init_from_config()
    conf.info()
    return conf


def create_factory(strategies: list[dict]) -> BacktestConfigFactory:
    factory = BacktestConfigFactory()
    factory.generate_by_strategies(strategies)
    return factory
