"""Factor-analysis tool used to produce the packaged factor-analysis outputs."""

import datetime
import warnings
from typing import Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from plotly.offline import plot
from plotly.subplots import make_subplots
import tools.utils.pfunctions as PFun
import tools.utils.tfunctions as tFun
from core.model.backtest_config import BacktestConfig, load_config
from core.utils.path_kit import get_file_path
warnings.filterwarnings('ignore')
pd.set_option('expand_frame_repr', False)
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)

def calc_group_nav(data: pd.DataFrame, conf: BacktestConfig) -> pd.DataFrame:
    temp = data.copy()
    temp['next_period_nav'] = temp['next_period_return'] + 1
    fee_factor = (1 - conf.c_rate) * (1 - conf.c_rate - conf.t_rate)
    temp['next_period_nav_after_fees'] = temp['next_period_nav'] * fee_factor
    group_nav = temp.groupby(['trade_date', 'groups'])['next_period_nav_after_fees'].mean().reset_index()
    group_nav = group_nav.sort_values(['groups', 'trade_date']).reset_index(drop=True)
    group_nav['cumulative_nav'] = group_nav.groupby('groups')['next_period_nav_after_fees'].cumprod()
    group_nav['group_label'] = group_nav['groups'].apply(lambda x: f'Group {int(x)}')
    return group_nav

def build_ic_summary(ic_df: pd.DataFrame) -> str:
    ic_mean = ic_df['RankIC'].mean()
    ic_std = ic_df['RankIC'].std()
    ic_ir = ic_mean / ic_std if pd.notna(ic_std) and ic_std != 0 else 0.0
    if ic_df['cumulative_rank_ic'].iloc[-1] > 0:
        ic_win_rate = (ic_df['RankIC'] > 0).sum() / len(ic_df) * 100
    else:
        ic_win_rate = (ic_df['RankIC'] < 0).sum() / len(ic_df) * 100
    return f'IC Mean: {tFun.float_num_process(ic_mean)} | IC Std: {tFun.float_num_process(ic_std)} | ICIR: {tFun.float_num_process(ic_ir)} | IC Win Rate: {tFun.float_num_process(ic_win_rate)}%'

def fig_to_html(fig, include_js=False) -> str:
    return plot(fig, include_plotlyjs='cdn' if include_js else False, output_type='div')

def IC_GNV_analysis(data: pd.DataFrame, factor_name: str, conf: BacktestConfig) -> Tuple[pd.DataFrame, pd.DataFrame, str, pd.DataFrame, pd.DataFrame]:
    data = data.dropna(subset=['trade_date', 'stock_code', 'stock_name', 'trading_day_count', 'market_trading_day_count', 'next_day_tradable', 'next_day_open_limit_up', 'next_day_st', 'next_day_delisted', 'listed_trading_days', 'next_period_return'], how='any')
    data = tFun.filter_stock(data)
    data[factor_name] = data[factor_name].astype(float)
    data['period_stock_count'] = data.groupby('trade_date')['trade_date'].transform('count')
    data = data[data['period_stock_count'] > 100].reset_index(drop=True)
    data = tFun.offset_grouping(data, factor_name)
    ic_data = tFun.get_IC(data, factor_name)
    ic_df, _ = tFun.IC_analysis(ic_data)
    ic_info = build_ic_summary(ic_df)
    group_value = tFun.get_group_hold_value(data, conf)
    group_nav = calc_group_nav(data, conf)
    return (data, ic_df, ic_info, group_value, group_nav)

def build_factor_analysis_figures(factor_data: pd.DataFrame, ic_df: pd.DataFrame, ic_info: str, group_value: pd.DataFrame, group_nav: pd.DataFrame, factor_name: str) -> list[str]:
    figures: list[str] = []
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    fig.add_trace(go.Bar(x=ic_df['trade_date'], y=ic_df['RankIC'], name='Rank IC', marker_color='orange'), secondary_y=False)
    fig.add_trace(go.Scatter(x=ic_df['trade_date'], y=ic_df['cumulative_rank_ic'], name='Cumulative Rank IC', line=dict(color='royalblue')), secondary_y=True)
    fig.update_layout(width=1800, height=620, title=f'{factor_name} Rank IC Overview', hovermode='x unified', annotations=[dict(text=ic_info, xref='paper', yref='paper', x=0.5, y=1.08, showarrow=False)])
    figures.append(fig_to_html(fig, include_js=True))
    fig = go.Figure()
    for group_id, sub_df in group_nav.groupby('groups'):
        fig.add_trace(go.Scatter(x=sub_df['trade_date'], y=sub_df['cumulative_nav'], mode='lines', name=f'Group {int(group_id)}'))
    fig.update_layout(width=1800, height=650, title=f'{factor_name} Group Cumulative NAV', hovermode='x unified')
    figures.append(fig_to_html(fig))
    fig = go.Figure(data=[go.Bar(x=[f'Group {int(x)}' for x in group_value['groups']], y=group_value['nav'], text=group_value['nav'].round(4), textposition='outside', name='Final NAV')])
    fig.update_layout(width=1600, height=600, title=f'{factor_name} Final Group NAV')
    figures.append(fig_to_html(fig))
    group_forward_return = factor_data.groupby('groups')['next_period_return'].mean().reset_index()
    fig = go.Figure(data=[go.Bar(x=[f'Group {int(x)}' for x in group_forward_return['groups']], y=group_forward_return['next_period_return'], text=(group_forward_return['next_period_return'] * 100).round(2).astype(str) + '%', textposition='outside', name='Mean Forward Return')])
    fig.update_layout(width=1600, height=600, title=f'{factor_name} Mean Forward Return by Group')
    figures.append(fig_to_html(fig))
    group_nav_pivot = group_nav.pivot(index='trade_date', columns='groups', values='cumulative_nav').sort_index()
    bottom_group = int(group_nav['groups'].min())
    top_group = int(group_nav['groups'].max())
    long_short_nav = group_nav_pivot[top_group] / group_nav_pivot[bottom_group]
    fig = go.Figure(data=[go.Scatter(x=long_short_nav.index, y=long_short_nav.values, mode='lines', name=f'Group {top_group} / Group {bottom_group}', line=dict(color='firebrick'))])
    fig.update_layout(width=1800, height=600, title=f'{factor_name} Long-Short NAV')
    figures.append(fig_to_html(fig))
    monthly_ic = ic_df.copy()
    monthly_ic['Year'] = monthly_ic['trade_date'].dt.year
    monthly_ic['Month'] = monthly_ic['trade_date'].dt.month.map(lambda x: f'{x:02d}')
    monthly_ic_pivot = monthly_ic.pivot_table(index='Year', columns='Month', values='RankIC', aggfunc='mean')
    fig = px.imshow(monthly_ic_pivot, text_auto='.3f', aspect='auto', color_continuous_scale='RdBu', origin='lower', title=f'{factor_name} Monthly Rank IC Heatmap')
    fig.update_layout(width=1600, height=700)
    figures.append(fig_to_html(fig))
    fig = go.Figure(data=[go.Histogram(x=ic_df['RankIC'], nbinsx=40, name='Rank IC', marker_color='teal')])
    fig.add_vline(x=ic_df['RankIC'].mean(), line_dash='dash', line_color='red')
    fig.update_layout(width=1600, height=600, title=f'{factor_name} Rank IC Distribution')
    figures.append(fig_to_html(fig))
    factor_quantiles = factor_data.groupby('trade_date')[factor_name].quantile([0.1, 0.5, 0.9]).unstack()
    factor_quantiles.columns = ['P10', 'P50', 'P90']
    fig = go.Figure()
    for col_name, color in [('P10', '#1f77b4'), ('P50', '#ff7f0e'), ('P90', '#2ca02c')]:
        fig.add_trace(go.Scatter(x=factor_quantiles.index, y=factor_quantiles[col_name], mode='lines', name=col_name, line=dict(color=color)))
    fig.update_layout(width=1800, height=600, title=f'{factor_name} Factor Quantiles Over Time', hovermode='x unified')
    figures.append(fig_to_html(fig))
    factor_box = factor_data[['groups', factor_name]].dropna().copy()
    factor_box['Group'] = factor_box['groups'].apply(lambda x: f'Group {int(x)}')
    fig = px.box(factor_box, x='Group', y=factor_name, points=False, title=f'{factor_name} Factor Distribution by Group')
    fig.update_layout(width=1700, height=650)
    figures.append(fig_to_html(fig))
    return figures

def factor_analysis(conf: BacktestConfig, factor_name: str) -> None:
    factor_data_path = get_file_path('data', 'runtime_cache', 'factor_calculation_results.pkl', auto_create=False)
    start_time = datetime.datetime.now()
    data = tFun.cal_next_period_returns(factor_data_path)
    factor_data, ic_df, ic_info, group_value, group_nav = IC_GNV_analysis(data, factor_name, conf)
    figures = build_factor_analysis_figures(factor_data, ic_df, ic_info, group_value, group_nav, factor_name)
    report_path = get_file_path('data', 'factor_analysis', f'{factor_name}_factor_analysis_report.html', auto_create=True)
    PFun.merge_html_flexible(figures, report_path, title=f'{factor_name} Factor Analysis Report')
    elapsed = (datetime.datetime.now() - start_time).total_seconds()
if __name__ == '__main__':
    backtest_config = load_config()
    factor_analysis(backtest_config, factor_name='Oversold_39')
