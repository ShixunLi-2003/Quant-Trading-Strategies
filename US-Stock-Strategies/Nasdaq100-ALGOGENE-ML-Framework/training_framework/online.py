"""Chronological feature state shared by ALGOGENE Backtest inference."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

import numpy as np
import pandas as pd

from core import BASE_FEATURES, _daily_close_features
from fundamentals import attach_point_in_time_fundamentals


def _timestamp(value):
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _safe_symbol(value):
    return "".join(ch if ch.isalnum() else "_" for ch in value).lower()


class OnlineFeatureEngine:
    """Builds yesterday's close-only factors as a new session starts."""

    def __init__(self, stock_symbols, context_symbols, fundamentals=None,
                 fundamental_config=None):
        self.stocks = tuple(stock_symbols)
        self.context = tuple(context_symbols)
        self.all_symbols = set(self.stocks) | set(self.context)
        self.current_date = None
        self.current = defaultdict(list)
        self.history = defaultdict(list)
        self.latest_prices = {}
        self.fundamentals = fundamentals
        self.fundamental_config = dict(fundamental_config or {})

    def update(self, bulk_data):
        available = []
        for symbol, item in (bulk_data or {}).items():
            if symbol not in self.all_symbols or not isinstance(item, dict):
                continue
            if item.get("timestamp") is None or item.get("lastPrice") is None:
                continue
            try:
                moment = _timestamp(item["timestamp"])
                price = float(item["lastPrice"])
            except (TypeError, ValueError):
                continue
            if np.isfinite(price) and price > 0:
                available.append((symbol, moment, price))
        if not available:
            return pd.DataFrame()
        observed_date = max(item[1] for item in available).date()
        completed = pd.DataFrame()
        if self.current_date is None:
            self.current_date = observed_date
        elif observed_date > self.current_date:
            completed = self._finalize(self.current_date)
            self.current = defaultdict(list)
            self.current_date = observed_date
        for symbol, moment, price in available:
            if moment.date() == self.current_date:
                self.current[symbol].append((moment, price))
                self.latest_prices[symbol] = price
        return completed

    def _finalize(self, trade_date):
        for symbol, observations in self.current.items():
            ordered = [price for _, price in sorted(observations, key=lambda item: item[0])]
            values = _daily_close_features(ordered)
            if values is None:
                continue
            values["trade_date"] = pd.Timestamp(trade_date)
            self.history[symbol].append(values)
            self.history[symbol] = self.history[symbol][-25:]

        context_values = {}
        for symbol in self.context:
            rows = self.history.get(symbol, [])
            safe = _safe_symbol(symbol)
            context_values["ctx_{}_realized_vol".format(safe)] = rows[-1]["realized_vol"] if rows else 0.0
            context_values["ctx_{}_ret_1d".format(safe)] = (
                rows[-1]["close"] / rows[-2]["close"] - 1.0 if len(rows) >= 2 else 0.0)

        records = []
        for symbol in self.stocks:
            rows = self.history.get(symbol, [])
            if len(rows) < 20:
                continue
            closes = np.asarray([row["close"] for row in rows], dtype=float)
            row = dict(rows[-1])
            row.update({
                "symbol": symbol,
                "ret_1d": float(closes[-1] / closes[-2] - 1.0),
                "ret_3d": float(closes[-1] / closes[-4] - 1.0),
                "ret_5d": float(closes[-1] / closes[-6] - 1.0),
                "close_to_ma5": float(closes[-1] / closes[-5:].mean() - 1.0),
                "close_to_ma20": float(closes[-1] / closes[-20:].mean() - 1.0),
            })
            row.update(context_values)
            if all(np.isfinite(float(row[name])) for name in BASE_FEATURES):
                records.append(row)
        result = pd.DataFrame(records)
        if self.fundamental_config.get("enabled", False):
            result = attach_point_in_time_fundamentals(
                result, self.fundamentals, self.fundamental_config)
        return result
