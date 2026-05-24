"""Simulate mark-to-market PnL, trading costs, and position updates bar by bar."""

from __future__ import annotations

import numba as nb
import numpy as np
from numba.experimental import jitclass


@jitclass
class Simulator:
    """Maintain account state for one market sleeve throughout the backtest."""

    equity: float
    fee_rate: float
    min_order_limit: float
    lot_sizes: nb.float64[:]
    lots: nb.int64[:]
    target_lots: nb.int64[:]
    last_prices: nb.float64[:]
    has_last_prices: bool

    def __init__(self, init_capital, lot_sizes, fee_rate, init_lots, min_order_limit):
        self.equity = init_capital
        self.fee_rate = fee_rate
        self.min_order_limit = min_order_limit

        n = len(lot_sizes)
        self.lot_sizes = np.zeros(n, dtype=np.float64)
        self.lot_sizes[:] = lot_sizes

        self.last_prices = np.zeros(n, dtype=np.float64)
        self.has_last_prices = False

        self.lots = np.zeros(n, dtype=np.int64)
        self.lots[:] = init_lots

        self.target_lots = np.zeros(n, dtype=np.int64)
        self.target_lots[:] = init_lots

    def set_target_lots(self, target_lots):
        self.target_lots[:] = target_lots

    def fill_last_prices(self, prices):
        mask = np.logical_not(np.isnan(prices))
        self.last_prices[mask] = prices[mask]
        self.has_last_prices = True

    def settle_equity(self, prices):
        mask = np.logical_and(self.lots != 0, np.logical_not(np.isnan(prices)))
        equity_delta = np.sum((prices[mask] - self.last_prices[mask]) * self.lot_sizes[mask] * self.lots[mask])
        self.equity += equity_delta

    def on_open(self, open_prices, funding_rates, mark_prices):
        if not self.has_last_prices:
            self.fill_last_prices(open_prices)

        self.settle_equity(open_prices)

        mask = np.logical_and(self.lots != 0, np.logical_not(np.isnan(mark_prices)))
        pos_val = self.lot_sizes[mask] * self.lots[mask] * mark_prices[mask]
        funding_fee = np.sum(pos_val * funding_rates[mask])
        self.equity -= funding_fee

        self.fill_last_prices(open_prices)
        return self.equity, funding_fee, pos_val

    def on_execution(self, exec_prices):
        if not self.has_last_prices:
            self.fill_last_prices(exec_prices)

        self.settle_equity(exec_prices)

        delta = self.target_lots - self.lots
        mask = np.logical_and(delta != 0, np.logical_not(np.isnan(exec_prices)))

        turnover = np.zeros(len(self.lot_sizes), dtype=np.float64)
        turnover[mask] = np.abs(delta[mask]) * self.lot_sizes[mask] * exec_prices[mask]
        mask = np.logical_and(mask, turnover >= self.min_order_limit)

        turnover_total = turnover[mask].sum()
        if np.isnan(turnover_total):
            raise RuntimeError("Turnover is NaN.")

        fee = turnover_total * self.fee_rate
        self.equity -= fee
        self.lots[mask] = self.target_lots[mask]
        self.fill_last_prices(exec_prices)
        return self.equity, turnover_total, fee

    def on_close(self, close_prices):
        if not self.has_last_prices:
            self.fill_last_prices(close_prices)

        self.settle_equity(close_prices)
        self.fill_last_prices(close_prices)
        return self.equity
