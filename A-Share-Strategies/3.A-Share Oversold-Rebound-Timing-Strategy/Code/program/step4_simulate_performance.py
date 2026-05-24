"""Portfolio performance simulation and result export."""

import time
import warnings
import pandas as pd
from core.equity import calc_equity, show_plot_performance
from core.model.backtest_config import BacktestConfig, load_config
from core.model.timing_signal import EquityTiming
from core.utils.path_kit import get_file_path
warnings.filterwarnings('ignore')
pd.set_option('expand_frame_repr', False)
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)

def save_performance_df_csv(conf: BacktestConfig, **kwargs):
    for name, df in kwargs.items():
        file_path = conf.get_result_folder() / f'{name}.csv'
        df.to_csv(file_path, encoding='utf-8-sig')

def simu_equity_timing(conf: BacktestConfig, pivot_dict_stock: dict, df_stock_ratio: pd.DataFrame):
    s_time = time.time()
    account_df = pd.read_csv(conf.get_result_folder() / 'equity_curve.csv', index_col=0, encoding='utf-8-sig')
    equity_signal = conf.equity_timing.get_equity_signal(account_df)
    equity_signal.index = pd.to_datetime(account_df['trade_date'])
    df_stock_ratio = df_stock_ratio.mul(equity_signal.reindex(df_stock_ratio.index), axis=0)
    s_time = time.time()
    account_df, rtn, year_return, month_return, quarter_return = calc_equity(conf, pivot_dict_stock, df_stock_ratio)
    save_performance_df_csv(conf, retimed_equity_curve=account_df, retimed_performance_summary=rtn, retimed_yearly_account_return=year_return, retimed_quarterly_account_return=quarter_return, retimed_monthly_account_return=month_return)
    return (account_df, rtn, year_return)

def simulate_performance(conf: BacktestConfig, select_results, show_plot=True):
    s_time = time.time()
    df_stock_ratio = select_results.pivot(index='trade_date', columns='stock_code', values='target_position_weight').fillna(0)
    pivot_dict_stock = pd.read_pickle(get_file_path('data', 'runtime_cache', 'full_market_price_pivot.pkl'))
    data_date_max = f'{df_stock_ratio.index.max().date()}'
    conf.start_date = max(conf.start_date, f'{df_stock_ratio.index.min().date()}')
    conf.end_date = min(conf.end_date or data_date_max, data_date_max)
    index_data = conf.read_index_with_trading_date()
    rebalance_dates = index_data.groupby(f'{conf.strategy.hold_period_name}start_date')['trade_date'].last()
    df_stock_ratio = df_stock_ratio.reindex(rebalance_dates, fill_value=0)
    df_stock_ratio = df_stock_ratio.sort_index()
    account_df, rtn, year_return, month_return, quarter_return = calc_equity(conf, pivot_dict_stock, df_stock_ratio)
    save_performance_df_csv(conf, equity_curve=account_df, performance_summary=rtn, yearly_account_return=year_return, quarterly_account_return=quarter_return, monthly_account_return=month_return)
    has_equity_signal = isinstance(conf.equity_timing, EquityTiming)
    if has_equity_signal:
        account_df2, rtn2, year_return2 = simu_equity_timing(conf, pivot_dict_stock, df_stock_ratio)
        if show_plot:
            show_plot_performance(conf, account_df2, rtn2, year_return2, title_prefix='Retimed-', **{'Pre-Retiming Equity Curve': account_df['nav']})
    elif show_plot:
        show_plot_performance(conf, account_df, rtn, year_return)
    return conf.report
if __name__ == '__main__':
    backtest_config = load_config()
    select_stock_result = backtest_config.get_result_folder() / f'{backtest_config.strategy.name}selection_results.pkl'
    _results = pd.read_pickle(select_stock_result)
    simulate_performance(backtest_config, _results)
