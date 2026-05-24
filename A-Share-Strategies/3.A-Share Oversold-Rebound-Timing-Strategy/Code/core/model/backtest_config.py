"""Load configuration, prepare trading calendars, and manage result paths."""

from __future__ import annotations

from datetime import datetime
from itertools import product
from pathlib import Path
from types import ModuleType
from typing import Optional

import numpy as np
import pandas as pd

from core.market_essentials import get_trade_date, import_index_data
from core.model.strategy_config import StrategyConfig
from core.model.timing_signal import EquityTiming
from core.utils.factor_hub import FactorHub
from core.utils.path_kit import get_file_path, get_folder_path
from core.utils.strategy_hub import get_strategy_by_name


class BacktestConfig:
    """Carry the complete configuration needed by each backtest stage."""

    def __init__(self, **config_dict: dict):
        self.start_date: Optional[str] = config_dict.get("start_date")
        self.end_date: Optional[str] = config_dict.get("end_date")
        self.strategy_raw: dict = config_dict.get("strategy")
        self.strategy: Optional[StrategyConfig] = None
        self.initial_cash: float = config_dict.get("initial_cash", 1000000)
        self.c_rate: float = config_dict.get("c_rate", 1.2 / 10000)
        self.t_rate: float = config_dict.get("t_rate", 1 / 1000)

        data_center_path = config_dict.get("data_center_path", "not-provided")
        self.data_center_path = Path(data_center_path)
        if data_center_path == "not-provided":
            self.stock_data_path = self.data_center_path / "stock-trading-data"
            self.index_data_path = self.data_center_path / "stock-main-index-data"
            self.fin_data_path = self.data_center_path / "stock-fin-data-xbx"
        else:
            self.stock_data_path = Path(str(config_dict["stock_data_path"]))
            self.index_data_path = Path(str(config_dict["index_data_path"]))
            self.fin_data_path = Path(str(config_dict.get("fin_data_path", "not-provided")))

        self.has_fin_data: bool = self.fin_data_path.exists()
        self.factor_params_dict: dict = {}
        self.fin_cols: list[str] = []
        self.excluded_boards: list[str] = config_dict.get("excluded_boards", [])
        self.equity_timing: Optional[EquityTiming] = None
        self.agg_rules: dict = {}
        self.report: pd.DataFrame = pd.DataFrame()
        self.iter_round: int | str = 0

    def load_strategy(self, strategy=None, equity_timing=None) -> None:
        """Instantiate strategy and timing objects from raw config dictionaries."""
        if strategy is None:
            strategy_dict = self.strategy_raw
        else:
            self.strategy_raw = strategy
            strategy_dict = strategy

        strategy_name = strategy_dict["name"]
        strategy_dict["funcs"] = get_strategy_by_name(strategy_name)
        self.strategy = StrategyConfig.init(**strategy_dict)

        fin_cols: set[str] = set()
        for factor_config in self.strategy.all_factors:
            self.factor_params_dict.setdefault(factor_config.name, set()).add(factor_config.param)
            fin_cols.update(FactorHub.get_by_name(factor_config.name).fin_cols)
        self.fin_cols = list(fin_cols)

        if equity_timing is not None:
            self.equity_timing = EquityTiming.init(**equity_timing)

    def update_trading_date(self, tc_path: Path) -> pd.DataFrame | None:
        """Refresh the local trading calendar from the benchmark-index history."""
        index_data_all = import_index_data(self.index_data_path / "sh000001.csv")
        try:
            tc_df = get_trade_date(index_data_all)
            tc_df.to_csv(tc_path, index=False)
            return tc_df
        except Exception:
            return None

    def read_index_with_trading_date(self) -> pd.DataFrame:
        """Merge index returns with the generated trading-calendar structure."""
        today = datetime.today()
        index_data = import_index_data(
            self.index_data_path / "sh000001.csv",
            [self.start_date, self.end_date],
        )
        tc_path = get_file_path("data", "trading_calendar.csv")

        if tc_path.exists():
            tc_df = pd.read_csv(tc_path)
            if pd.to_datetime(tc_df["trade_date"].max()) - today <= pd.to_timedelta("30 days"):
                new_tc_df = self.update_trading_date(tc_path)
                if new_tc_df is not None:
                    tc_df = new_tc_df
        else:
            tc_df = self.update_trading_date(tc_path)

        if tc_df is None:
            raise RuntimeError("Trading calendar is unavailable.")

        tc_df["trade_date"] = pd.to_datetime(tc_df["trade_date"])
        tc_df["next_trade_date"] = tc_df["trade_date"].shift(-1)

        day_gap_prev = tc_df["trade_date"].diff().dt.days != 1
        day_gap_next = tc_df["trade_date"].diff(-1).dt.days != -1

        tc_df.loc[day_gap_prev, "weekly_start_date"] = tc_df["trade_date"]
        tc_df.loc[day_gap_prev & day_gap_next, "weekly_start_date"] = np.nan
        tc_df["weekly_start_date"] = tc_df["weekly_start_date"].ffill()
        tc_df["weekly_end_date"] = tc_df["weekly_start_date"] != tc_df["weekly_start_date"].shift(-1)

        month_change = tc_df["trade_date"].dt.month != tc_df["trade_date"].shift().dt.month
        tc_df.loc[month_change, "monthly_start_date"] = tc_df["trade_date"]
        tc_df["monthly_start_date"] = tc_df["monthly_start_date"].ffill()
        tc_df["monthly_end_date"] = tc_df["monthly_start_date"] != tc_df["monthly_start_date"].shift(-1)

        base_index = tc_df[tc_df["trade_date"] == pd.to_datetime("2007-01-04")].index.min()
        if pd.isnull(base_index):
            raise RuntimeError(
                "Trading calendar must start from 2007-01-04 and the sh000001 index "
                "history must include that date."
            )

        for n in [3, 5, 10]:
            prefix = f"period_{n}d_"
            mask = (tc_df.index - base_index) % n == 0
            tc_df.loc[mask, f"{prefix}start_date"] = tc_df["trade_date"]
            tc_df[f"{prefix}start_date"] = tc_df[f"{prefix}start_date"].ffill()
            tc_df[f"{prefix}end_date"] = (
                tc_df[f"{prefix}start_date"] != tc_df[f"{prefix}start_date"].shift(-1)
            )

        index_data = pd.merge(index_data, tc_df, on="trade_date", how="left")

        period_offset = tc_df[["trade_date"]].copy()
        for prefix, tag in {
            "weekly_": "W_0",
            "monthly_": "M_0",
            "period_3d_": "3_0",
            "period_5d_": "5_0",
            "period_10d_": "10_0",
        }.items():
            period_offset[tag] = 0
            period_offset.loc[
                period_offset["trade_date"] == tc_df[f"{prefix}start_date"],
                tag,
            ] = 1
            period_offset[tag] = period_offset[tag].cumsum()
        period_offset.to_csv(get_file_path("data", "period_offset.csv"), index=False)

        return index_data

    def get_result_folder(self) -> Path:
        """Return the path where this configuration stores its outputs."""
        if self.iter_round == 0:
            strategy_name = self.strategy.name if self.strategy is not None else "strategy"
            return get_folder_path("data", "backtest_results", strategy_name)
        return get_folder_path(
            "data",
            "parameter_sweep_results",
            self.strategy.name,
            f"parameter_set_{self.iter_round}" if isinstance(self.iter_round, int) else self.iter_round,
            path_type=True,
        )

    def get_fullname(self) -> str:
        """Create a readable description of the current configuration."""
        fullname = f"{self.strategy.get_fullname()}, initial_capital={self.initial_cash:,.2f}"
        if self.equity_timing is not None:
            fullname += f", retiming={(self.equity_timing.name, self.equity_timing.params)}"
        return fullname

    def set_report(self, report: pd.DataFrame) -> None:
        """Attach the parameter description to a generated performance report."""
        report["param"] = self.get_fullname()
        self.report = report

    def get_strategy_config_sheet(self, with_factors: bool = True) -> dict:
        """Build a summary row for parameter-sweep exports."""
        factor_dict = {
            "holding_period": self.strategy.hold_period,
            "selection_count": self.strategy.select_num,
        }
        result = {
            "strategy": self.strategy.name,
            "strategy_description": self.get_fullname(),
        }
        if with_factors:
            for factor_config in self.strategy.all_factors:
                factor_dict[f"factor-{factor_config.name}"] = factor_config.param
            result.update(**factor_dict)
        return result

    @classmethod
    def init_from_config(cls, load_strategy: bool = True) -> "BacktestConfig":
        """Instantiate the backtest config from `configuration.py`."""
        import configuration as config

        config_dict = {
            key: value
            for key, value in vars(config).items()
            if not key.startswith("__") and not isinstance(value, ModuleType)
        }
        conf = cls(**config_dict)
        if load_strategy:
            conf.load_strategy(equity_timing=getattr(config, "equity_timing", None))
        return conf


class BacktestConfigFactory:
    """Construct a family of configs for parameter-sweep experiments."""

    def __init__(self):
        self.config_list: list[BacktestConfig] = []
        self.full_conf: Optional[BacktestConfig] = None

    @property
    def result_folder(self) -> Path:
        return get_folder_path("data", "parameter_sweep_results", path_type=True)

    def generate_all_factor_config(self) -> BacktestConfig:
        import configuration as config

        backtest_config = BacktestConfig.init_from_config(load_strategy=False)
        factor_list = []
        filter_list = []
        for conf in self.config_list:
            factor_list += conf.strategy_raw["factor_list"]
            filter_list += conf.strategy_raw["filter_list"]
        backtest_config.load_strategy(
            {**config.strategy, "factor_list": factor_list, "filter_list": filter_list}
        )
        return backtest_config

    def get_name_params_sheet(self) -> pd.DataFrame:
        rows = [config.get_strategy_config_sheet() for config in self.config_list]
        sheet = pd.DataFrame(rows)
        sheet.to_excel(
            self.config_list[-1].get_result_folder().parent
            / "strategy_backtest_parameter_summary.xlsx",
            index=False,
        )
        return sheet

    def generate_by_strategies(
        self,
        strategies: list[dict],
        equity_signals: tuple = (None,),
    ) -> list[BacktestConfig]:
        config_list = []
        iter_round = 0
        for strategy, equity_signal in product(strategies, equity_signals):
            iter_round += 1
            backtest_config = BacktestConfig.init_from_config(load_strategy=False)
            backtest_config.load_strategy(strategy, equity_signal)
            backtest_config.iter_round = iter_round
            config_list.append(backtest_config)
        self.config_list = config_list
        self.full_conf = self.generate_all_factor_config()
        return config_list


def load_config() -> BacktestConfig:
    """Convenience constructor for the default config."""
    return BacktestConfig.init_from_config()


def create_factory(strategies, re_timing_strategies=(None,)) -> BacktestConfigFactory:
    """Create a parameter-sweep factory from strategy and retiming combinations."""
    if not re_timing_strategies:
        re_timing_strategies = (None,)
    factory = BacktestConfigFactory()
    factory.generate_by_strategies(strategies, re_timing_strategies)
    return factory
