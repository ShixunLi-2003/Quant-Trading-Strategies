"""Performance evaluation utilities used by the backtest framework."""

import itertools
from datetime import timedelta
import numpy as np
import pandas as pd

def strategy_evaluate(equity, net_col='nav', pct_col='return'):
    results = pd.DataFrame()

    def num_to_pct(value):
        return '%.2f%%' % (value * 100)
    results.loc[0, 'cumulative_nav'] = round(equity[net_col].iloc[-1], 2)
    days = (equity['trade_date'].iloc[-1] - equity['trade_date'].iloc[0]) / timedelta(days=1)
    annual_return = equity[net_col].iloc[-1] ** (365 / days) - 1
    results.loc[0, 'annual_return'] = num_to_pct(annual_return)
    equity[f"{net_col.split('equity_curve')[0]}max2here"] = equity[net_col].expanding().max()
    equity[f"{net_col.split('equity_curve')[0]}dd2here"] = equity[net_col] / equity[f"{net_col.split('equity_curve')[0]}max2here"] - 1
    end_date, max_draw_down = tuple(equity.sort_values(by=[f"{net_col.split('equity_curve')[0]}dd2here"]).iloc[0][['trade_date', f"{net_col.split('equity_curve')[0]}dd2here"]])
    start_date = equity[equity['trade_date'] <= end_date].sort_values(by=net_col, ascending=False).iloc[0]['trade_date']
    results.loc[0, 'max_drawdown'] = num_to_pct(max_draw_down)
    results.loc[0, 'max_drawdown_start'] = str(start_date)
    results.loc[0, 'max_drawdown_end'] = str(end_date)
    results.loc[0, 'return_drawdown_ratio'] = round(annual_return / abs(max_draw_down), 2)
    results.loc[0, 'winning_periods'] = len(equity.loc[equity[pct_col] > 0])
    results.loc[0, 'losing_periods'] = len(equity.loc[equity[pct_col] <= 0])
    results.loc[0, 'win_rate'] = num_to_pct(results.loc[0, 'winning_periods'] / len(equity))
    results.loc[0, 'average_return_per_period'] = num_to_pct(equity[pct_col].mean())
    results.loc[0, 'profit_loss_ratio'] = round(equity.loc[equity[pct_col] > 0][pct_col].mean() / equity.loc[equity[pct_col] <= 0][pct_col].mean() * -1, 2)
    results.loc[0, 'best_period_return'] = num_to_pct(equity[pct_col].max())
    results.loc[0, 'worst_period_return'] = num_to_pct(equity[pct_col].min())
    results.loc[0, 'max_consecutive_winning_periods'] = max([len(list(v)) for k, v in itertools.groupby(np.where(equity[pct_col] > 0, 1, np.nan))])
    results.loc[0, 'max_consecutive_losing_periods'] = max([len(list(v)) for k, v in itertools.groupby(np.where(equity[pct_col] <= 0, 1, np.nan))])
    results.loc[0, 'return_std_dev'] = num_to_pct(equity[pct_col].std())
    temp = equity.copy()
    temp.set_index('trade_date', inplace=True)
    year_return = temp[[pct_col]].resample(rule='YE').apply(lambda x: (1 + x).prod() - 1)
    month_return = temp[[pct_col]].resample(rule='ME').apply(lambda x: (1 + x).prod() - 1)
    quarter_return = temp[[pct_col]].resample(rule='QE').apply(lambda x: (1 + x).prod() - 1)

    def num2pct(x):
        if str(x) != 'nan':
            return str(round(x * 100, 2)) + '%'
        else:
            return x
    year_return['return'] = year_return[pct_col].apply(num2pct)
    month_return['return'] = month_return[pct_col].apply(num2pct)
    quarter_return['return'] = quarter_return[pct_col].apply(num2pct)
    return (results.T, year_return, month_return, quarter_return)
