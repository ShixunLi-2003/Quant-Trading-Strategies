"""Transform target portfolio weights into discrete spot and swap position sizes."""

from __future__ import annotations

import numba as nb
import numpy as np
from numba.experimental import jitclass


@jitclass
class RebAlways:
    """Rebalance to target weights on every decision timestamp."""

    spot_lot_sizes: nb.float64[:]
    swap_lot_sizes: nb.float64[:]

    def __init__(self, spot_lot_sizes, swap_lot_sizes):
        self.spot_lot_sizes = np.zeros(len(spot_lot_sizes), dtype=np.float64)
        self.spot_lot_sizes[:] = spot_lot_sizes

        self.swap_lot_sizes = np.zeros(len(swap_lot_sizes), dtype=np.float64)
        self.swap_lot_sizes[:] = swap_lot_sizes

    def _calc(self, equity, prices, ratios, lot_sizes):
        target_lots = np.zeros(len(lot_sizes), dtype=np.int64)
        symbol_equity = equity * ratios
        mask = np.abs(symbol_equity) > 0.01
        target_lots[mask] = (symbol_equity[mask] / prices[mask] / lot_sizes[mask]).astype(np.int64)
        return target_lots

    def calc_lots(self, equity, spot_prices, spot_lots, spot_ratios, swap_prices, swap_lots, swap_ratios):
        is_spot_only = False
        if np.sum(np.abs(swap_ratios)) < 1e-6:
            is_spot_only = True
            equity *= 0.99

        spot_target_lots = self._calc(equity, spot_prices, spot_ratios, self.spot_lot_sizes)
        if is_spot_only:
            return spot_target_lots, np.zeros(len(self.swap_lot_sizes), dtype=np.int64)

        swap_target_lots = self._calc(equity, swap_prices, swap_ratios, self.swap_lot_sizes)
        return spot_target_lots, swap_target_lots
