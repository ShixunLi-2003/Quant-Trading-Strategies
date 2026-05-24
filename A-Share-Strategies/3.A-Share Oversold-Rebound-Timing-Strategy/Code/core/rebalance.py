"""Rebalancing logic used by the simulator."""

import numba as nb
import numpy as np
from numba.experimental import jitclass
from core.model.type_def import SSE_STAR
LONG_ONLY_EQUITY_RATIO = 0.97

@nb.njit
def calc_target_lots_by_ratio(equity, prices, ratios, types):
    n_syms = len(prices)
    target_positions = np.zeros(n_syms, dtype=np.int64)
    target_equities = equity * ratios
    for idx_sym, (pr, eq, ty) in enumerate(zip(prices, target_equities, types)):
        if eq < 0.01 or np.isnan(pr):
            target_positions[idx_sym] = 0
            continue
        pos = int(eq / pr)
        if ty == SSE_STAR:
            if pos >= 200:
                target_positions[idx_sym] = pos
            else:
                target_positions[idx_sym] = 0
        else:
            target_positions[idx_sym] = pos - pos % 100
    return target_positions

@jitclass
class RebAlways:
    types: nb.int16[:]

    def __init__(self, types):
        self.types = types

    def calc_lots(self, equity, prices, ratios):
        equity *= LONG_ONLY_EQUITY_RATIO
        target_pos = calc_target_lots_by_ratio(equity, prices, ratios, self.types)
        return target_pos

@jitclass
class RebAlwaysSimple:
    types: nb.int16[:]

    def __init__(self, types):
        self.types = types

    def calc_lots(self, equity, prices, ratios):
        n_syms = len(prices)
        target_positions = np.zeros(n_syms, dtype=np.int64)
        target_equities = equity * ratios
        mask = target_equities > 0.01
        target_positions[mask] = (target_equities[mask] / prices[mask]).astype(np.int64)
        return target_positions
