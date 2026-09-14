from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CostModel:
    commission_bps: float = 5.0
    stamp_duty_bps: float = 10.0
    minimum_commission: float = 5.0
    buy_slippage_bps: float = 30.0
    sell_slippage_bps: float = 30.0

    def buy_cost(self, notional: float) -> float:
        return max(notional * self.commission_bps / 10_000.0, self.minimum_commission)

    def sell_cost(self, notional: float) -> float:
        commission = max(notional * self.commission_bps / 10_000.0, self.minimum_commission)
        return commission + notional * self.stamp_duty_bps / 10_000.0


def minute_execution_price(
    bars: pd.DataFrame,
    target_hhmm: int,
    side: str,
    slippage_bps: float,
) -> tuple[float, int]:
    eligible = bars[bars["minute"] >= target_hhmm].sort_values("datetime")
    if eligible.empty:
        raise ValueError(f"No minute bar available at or after {target_hhmm}")
    bar = eligible.iloc[0]
    basis = float(bar["open"])
    direction = 1.0 if side == "buy" else -1.0
    return basis * (1.0 + direction * slippage_bps / 10_000.0), int(bar["minute"])


def maximum_drawdown(nav: pd.Series) -> float:
    running_high = nav.cummax()
    return float((nav / running_high - 1.0).min())


def periodic_top_n_backtest(
    candidates: pd.DataFrame,
    initial_capital: float = 30_000.0,
    top_n: int = 3,
    lot_size: int = 100,
    cost_model: CostModel | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    costs = cost_model or CostModel()
    capital = float(initial_capital)
    periods: list[dict[str, object]] = []
    trades: list[dict[str, object]] = []
    required = {"signal_date", "stock_code", "score", "entry_price", "exit_price"}
    missing = sorted(required - set(candidates.columns))
    if missing:
        raise ValueError(f"Missing candidate columns: {missing}")
    for signal_date, group in candidates.groupby("signal_date", sort=True):
        selected = group.sort_values("score", ascending=False).head(top_n)
        start_capital = capital
        slot_budget = capital / max(top_n, 1)
        period_profit = 0.0
        positions = 0
        for row in selected.itertuples(index=False):
            entry = float(row.entry_price) * (1.0 + costs.buy_slippage_bps / 10_000.0)
            exit_price = float(row.exit_price) * (1.0 - costs.sell_slippage_bps / 10_000.0)
            quantity = int(slot_budget // (entry * lot_size)) * lot_size
            if quantity < lot_size:
                continue
            buy_notional = quantity * entry
            sell_notional = quantity * exit_price
            profit = (
                sell_notional
                - buy_notional
                - costs.buy_cost(buy_notional)
                - costs.sell_cost(sell_notional)
            )
            period_profit += profit
            positions += 1
            trades.append(
                {
                    "signal_date": signal_date,
                    "stock_code": row.stock_code,
                    "quantity": quantity,
                    "entry_price": entry,
                    "exit_price": exit_price,
                    "net_profit": profit,
                    "net_return": profit / buy_notional,
                }
            )
        capital += period_profit
        periods.append(
            {
                "signal_date": signal_date,
                "start_capital": start_capital,
                "end_capital": capital,
                "account_return": capital / start_capital - 1.0,
                "positions_bought": positions,
                "nav": capital / initial_capital,
            }
        )
    return pd.DataFrame(periods), pd.DataFrame(trades)


def summarize_periods(periods: pd.DataFrame, periods_per_year: float = 84.0) -> dict[str, float | int]:
    returns = periods["account_return"].astype(float)
    nav = periods["nav"].astype(float)
    volatility = float(returns.std())
    return {
        "n_periods": int(len(periods)),
        "total_return": float(nav.iloc[-1] - 1.0) if len(nav) else np.nan,
        "annualized_return_approx": float((nav.iloc[-1] ** (periods_per_year / len(nav))) - 1.0)
        if len(nav)
        else np.nan,
        "sharpe_approx": (
            float(returns.mean() / volatility * np.sqrt(periods_per_year)) if volatility else np.nan
        ),
        "max_drawdown": maximum_drawdown(nav) if len(nav) else np.nan,
        "win_rate": float((returns > 0).mean()) if len(returns) else np.nan,
    }
