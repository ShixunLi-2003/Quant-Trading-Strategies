from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass

import pandas as pd


DEFAULT_EXECUTION_CONFIG = {
    "signal_delay_days": 1,
    "trade_price": "open",
    "allow_partial_fill": True,
    "board_lot_default": 500,
    "board_lots": {},
    "min_daily_volume_shares": 0,
    "min_daily_amount_hkd": 2_000_000,
    "max_participation_volume_ratio": 0.05,
    "max_participation_amount_ratio": 0.05,
    "base_slippage_bps": 15.0,
    "impact_slippage_bps_at_max_participation": 35.0,
    "fees": {
        "broker_commission_rate": 0.0008,
        "broker_min_commission_hkd": 30.0,
        "platform_fee_hkd": 15.0,
        "stamp_duty_rate": 0.001,
        "transaction_levy_rate": 0.000027,
        "trading_fee_rate": 0.0000565,
        "settlement_fee_rate": 0.000042,
        "afrc_levy_rate": 0.0000015,
    },
}


def _deep_merge(base: dict, updates: dict | None) -> dict:
    merged = deepcopy(base)
    if not updates:
        return merged
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def build_execution_config(strategy_config: dict) -> dict:
    return _deep_merge(DEFAULT_EXECUTION_CONFIG, strategy_config.get("execution"))


def get_board_lot(symbol: str, execution_config: dict) -> int:
    board_lots = execution_config.get("board_lots", {})
    return int(board_lots.get(str(symbol), execution_config.get("board_lot_default", 500)))


def round_down_to_lot(shares: float, lot_size: int) -> int:
    if shares <= 0 or lot_size <= 0:
        return 0
    return int(math.floor(shares / lot_size) * lot_size)


def is_tradable_row(row: pd.Series, execution_config: dict) -> bool:
    required_fields = ["open", "close", "volume", "amount"]
    for field in required_fields:
        if field not in row or pd.isna(row[field]):
            return False
    if row["open"] <= 0 or row["close"] <= 0:
        return False
    if row["volume"] <= execution_config.get("min_daily_volume_shares", 0):
        return False
    if row["amount"] <= execution_config.get("min_daily_amount_hkd", 0):
        return False
    return True


def _round_cent(value: float) -> float:
    return math.floor(value * 100 + 0.5) / 100.0


def calculate_hk_fees(notional: float, side: str, execution_config: dict) -> dict[str, float]:
    fees_config = execution_config["fees"]
    broker_commission = max(
        float(notional) * fees_config["broker_commission_rate"],
        fees_config["broker_min_commission_hkd"],
    )
    platform_fee = float(fees_config.get("platform_fee_hkd", 0.0))
    stamp_duty = math.ceil(float(notional) * fees_config["stamp_duty_rate"])
    transaction_levy = _round_cent(float(notional) * fees_config["transaction_levy_rate"])
    trading_fee = _round_cent(float(notional) * fees_config["trading_fee_rate"])
    settlement_fee = _round_cent(float(notional) * fees_config["settlement_fee_rate"])
    afrc_levy = _round_cent(float(notional) * fees_config["afrc_levy_rate"])

    total = (
        broker_commission
        + platform_fee
        + stamp_duty
        + transaction_levy
        + trading_fee
        + settlement_fee
        + afrc_levy
    )
    return {
        "broker_commission": broker_commission,
        "platform_fee": platform_fee,
        "stamp_duty": stamp_duty,
        "transaction_levy": transaction_levy,
        "trading_fee": trading_fee,
        "settlement_fee": settlement_fee,
        "afrc_levy": afrc_levy,
        "total": total,
        "side": side,
    }


def estimate_slippage_rate(
    order_shares: int,
    volume_shares: float,
    execution_config: dict,
) -> float:
    if order_shares <= 0 or volume_shares <= 0:
        return 0.0
    participation = min(order_shares / volume_shares, execution_config["max_participation_volume_ratio"])
    ratio = participation / execution_config["max_participation_volume_ratio"] if execution_config["max_participation_volume_ratio"] > 0 else 0.0
    slippage_bps = execution_config["base_slippage_bps"] + execution_config["impact_slippage_bps_at_max_participation"] * ratio
    return slippage_bps / 10000.0


def max_fillable_shares(
    symbol: str,
    desired_shares: int,
    price: float,
    volume_shares: float,
    amount_hkd: float,
    execution_config: dict,
) -> int:
    lot_size = get_board_lot(symbol, execution_config)
    desired_shares = round_down_to_lot(desired_shares, lot_size)
    if desired_shares <= 0:
        return 0

    cap_by_volume = round_down_to_lot(volume_shares * execution_config["max_participation_volume_ratio"], lot_size)
    cap_by_amount = round_down_to_lot(
        amount_hkd * execution_config["max_participation_amount_ratio"] / max(price, 1e-9),
        lot_size,
    )
    fillable = min(desired_shares, cap_by_volume, cap_by_amount)
    if not execution_config.get("allow_partial_fill", True) and fillable < desired_shares:
        return 0
    return max(fillable, 0)


@dataclass
class SimulationResult:
    equity_curve: pd.Series
    returns: pd.Series
    actual_weights: pd.DataFrame
    target_weights: pd.DataFrame
    positions: pd.DataFrame
    trades: pd.DataFrame
    costs: pd.DataFrame


def simulate_target_weights(
    open_price: pd.DataFrame,
    close_price: pd.DataFrame,
    volume: pd.DataFrame,
    amount: pd.DataFrame,
    target_weights: pd.DataFrame,
    initial_cash: float,
    execution_config: dict,
) -> SimulationResult:
    index = close_price.index
    symbols = list(close_price.columns)
    target_weights = target_weights.reindex(index).fillna(0.0)
    delayed_weights = target_weights.shift(execution_config["signal_delay_days"]).fillna(0.0)
    valuation_close = close_price.where(close_price > 0).ffill()
    valuation_open = open_price.where(open_price > 0, valuation_close).ffill()

    holdings = pd.Series(0, index=symbols, dtype="int64")
    cash = float(initial_cash)

    equity_records = []
    actual_weight_records = []
    position_records = []
    trade_records: list[dict] = []
    cost_records = []

    for date in index:
        open_row = open_price.loc[date]
        close_row = close_price.loc[date]
        volume_row = volume.loc[date]
        amount_row = amount.loc[date]
        desired_weight_row = delayed_weights.loc[date]

        marked_open = valuation_open.loc[date].fillna(0.0)
        portfolio_value_open = cash + float((holdings * marked_open).sum())

        desired_shares = {}
        for symbol in symbols:
            target_value = float(desired_weight_row.get(symbol, 0.0)) * portfolio_value_open
            lot_size = get_board_lot(symbol, execution_config)
            desired_shares[symbol] = round_down_to_lot(target_value / max(marked_open.get(symbol, 0.0), 1e-9), lot_size)

        pending_changes = {symbol: desired_shares[symbol] - int(holdings[symbol]) for symbol in symbols}

        daily_cost = 0.0
        daily_turnover = 0.0
        daily_trades = 0

        for symbol in symbols:
            delta = pending_changes[symbol]
            if delta >= 0:
                continue
            row = pd.Series(
                {
                    "open": open_row[symbol],
                    "close": close_row[symbol],
                    "volume": volume_row[symbol],
                    "amount": amount_row[symbol],
                }
            )
            if not is_tradable_row(row, execution_config):
                continue
            fill = max_fillable_shares(
                symbol=symbol,
                desired_shares=abs(delta),
                price=float(row["open"]),
                volume_shares=float(row["volume"]),
                amount_hkd=float(row["amount"]),
                execution_config=execution_config,
            )
            if fill <= 0:
                continue
            slippage_rate = estimate_slippage_rate(fill, float(row["volume"]), execution_config)
            execution_price = float(row["open"]) * (1.0 - slippage_rate)
            notional = fill * execution_price
            fees = calculate_hk_fees(notional, side="sell", execution_config=execution_config)
            cash += notional - fees["total"]
            holdings[symbol] -= fill
            daily_cost += fees["total"]
            daily_turnover += notional
            daily_trades += 1
            trade_records.append(
                {
                    "date": date,
                    "symbol": symbol,
                    "side": "sell",
                    "shares": fill,
                    "price": execution_price,
                    "notional": notional,
                    "fees": fees["total"],
                    "slippage_rate": slippage_rate,
                }
            )

        buy_candidates = [symbol for symbol in symbols if pending_changes[symbol] > 0]
        buy_candidates.sort(key=lambda item: desired_weight_row.get(item, 0.0), reverse=True)

        for symbol in buy_candidates:
            delta = desired_shares[symbol] - int(holdings[symbol])
            if delta <= 0:
                continue
            row = pd.Series(
                {
                    "open": open_row[symbol],
                    "close": close_row[symbol],
                    "volume": volume_row[symbol],
                    "amount": amount_row[symbol],
                }
            )
            if not is_tradable_row(row, execution_config):
                continue
            fill_cap = max_fillable_shares(
                symbol=symbol,
                desired_shares=delta,
                price=float(row["open"]),
                volume_shares=float(row["volume"]),
                amount_hkd=float(row["amount"]),
                execution_config=execution_config,
            )
            lot_size = get_board_lot(symbol, execution_config)
            fill = fill_cap
            while fill > 0:
                slippage_rate = estimate_slippage_rate(fill, float(row["volume"]), execution_config)
                execution_price = float(row["open"]) * (1.0 + slippage_rate)
                notional = fill * execution_price
                fees = calculate_hk_fees(notional, side="buy", execution_config=execution_config)
                gross_cash_needed = notional + fees["total"]
                if gross_cash_needed <= cash + 1e-9:
                    cash -= gross_cash_needed
                    holdings[symbol] += fill
                    daily_cost += fees["total"]
                    daily_turnover += notional
                    daily_trades += 1
                    trade_records.append(
                        {
                            "date": date,
                            "symbol": symbol,
                            "side": "buy",
                            "shares": fill,
                            "price": execution_price,
                            "notional": notional,
                            "fees": fees["total"],
                            "slippage_rate": slippage_rate,
                        }
                    )
                    break
                fill -= lot_size

        marked_close = valuation_close.loc[date].fillna(marked_open).fillna(0.0)
        equity = cash + float((holdings * marked_close).sum())
        equity_records.append({"date": date, "equity": equity})
        position_records.append({"date": date, **{symbol: int(holdings[symbol]) for symbol in symbols}})
        if equity > 0:
            actual_weights = (holdings * marked_close) / equity
        else:
            actual_weights = pd.Series(0.0, index=symbols)
        actual_weight_records.append({"date": date, **{symbol: float(actual_weights[symbol]) for symbol in symbols}})
        cost_records.append(
            {
                "date": date,
                "turnover_hkd": daily_turnover,
                "trading_cost_hkd": daily_cost,
                "trade_count": daily_trades,
                "cash": cash,
            }
        )

    equity_curve = pd.DataFrame(equity_records).set_index("date")["equity"]
    returns = equity_curve.pct_change().fillna(0.0)
    actual_weights = pd.DataFrame(actual_weight_records).set_index("date").reindex(index).fillna(0.0)
    positions = pd.DataFrame(position_records).set_index("date").reindex(index).fillna(0).astype(int)
    costs = pd.DataFrame(cost_records).set_index("date").reindex(index).fillna(0.0)
    trades = pd.DataFrame(trade_records)
    if not trades.empty:
        trades = trades.sort_values(["date", "symbol", "side"]).reset_index(drop=True)

    return SimulationResult(
        equity_curve=equity_curve,
        returns=returns,
        actual_weights=actual_weights,
        target_weights=delayed_weights,
        positions=positions,
        trades=trades,
        costs=costs,
    )
