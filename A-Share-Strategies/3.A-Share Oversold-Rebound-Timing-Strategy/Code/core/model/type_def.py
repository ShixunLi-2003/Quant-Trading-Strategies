"""Typed market structures and simulation parameter definitions."""

import numba as nb
from numba.experimental import jitclass
BSE_MAIN = 0
SSE_MAIN = 1
SSE_STAR = 2
SZSE_MAIN = 3
SZSE_CHINEXT = 4

@jitclass
class StockMarketData:
    candle_begin_ts: nb.int64[:]
    op: nb.float64[:, :]
    cl: nb.float64[:, :]
    pre_cl: nb.float64[:, :]
    types: nb.int16[:]

    def __init__(self, candle_begin_ts, op, cl, pre_cl, types):
        self.candle_begin_ts = candle_begin_ts
        self.op = op
        self.cl = cl
        self.pre_cl = pre_cl
        self.types = types

@jitclass
class SimuParams:
    init_cash: float
    commission_rate: float
    stamp_tax_rate: float

    def __init__(self, init_cash, commission_rate, stamp_tax_rate):
        self.init_cash = init_cash
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate

def get_symbol_type(symbol: str) -> int:
    if symbol.startswith('bj'):
        return BSE_MAIN
    if symbol.startswith('sh'):
        if symbol.startswith('sh68'):
            return SSE_STAR
        else:
            return SSE_MAIN
    if symbol.startswith('sz'):
        if symbol.startswith('sz0'):
            return SZSE_MAIN
        else:
            return SZSE_CHINEXT
    raise ValueError(f'Unknown stock {symbol}')
