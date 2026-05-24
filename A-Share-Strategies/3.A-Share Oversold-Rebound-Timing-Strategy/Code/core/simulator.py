"""Execute basic portfolio accounting for buy-and-sell cycle simulation."""

import numba as nb
import numpy as np
from numba.experimental import jitclass


@jitclass
class Simulator:
    """Track cash, holdings, and transaction costs through time."""

    cash: float
    pos_values: nb.float64[:]
    commission_rate: float
    stamp_tax_rate: float
    last_prices: nb.float64[:]

    def __init__(self, init_capital, commission_rate, stamp_tax_rate, init_pos_values):
        self.cash = init_capital
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        n_positions = len(init_pos_values)
        self.pos_values = np.zeros(n_positions, dtype=np.float64)
        self.pos_values[:] = init_pos_values
        self.last_prices = np.zeros(n_positions, dtype=np.float64)

    def fill_last_prices(self, prices):
        mask = np.logical_not(np.isnan(prices))
        self.last_prices[mask] = prices[mask]

    def settle_pos_values(self, prices):
        mask = np.logical_and(self.pos_values > 1e-06, np.logical_not(np.isnan(prices)))
        self.pos_values[mask] *= prices[mask] / self.last_prices[mask]

    def get_pos_value(self):
        return np.sum(self.pos_values)

    def sell_all(self, exec_prices):
        self.settle_pos_values(exec_prices)
        total_position_value = np.sum(self.pos_values)
        stamp_tax = total_position_value * self.stamp_tax_rate
        commission = total_position_value * self.commission_rate
        self.cash += total_position_value - stamp_tax - commission
        self.pos_values[:] = 0
        self.fill_last_prices(exec_prices)
        return stamp_tax, commission

    def buy_stocks(self, exec_prices, target_pos):
        self.settle_pos_values(exec_prices)
        mask = target_pos > 0
        buy_values = exec_prices[mask] * target_pos[mask]
        buy_values_total = np.sum(buy_values)
        self.pos_values[mask] = buy_values
        commission = np.sum(self.pos_values * self.commission_rate)
        self.cash -= buy_values_total + commission
        self.fill_last_prices(exec_prices)
        return commission
