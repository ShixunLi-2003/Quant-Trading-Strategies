"""Attribution-analysis tool used to produce the packaged attribution outputs."""

from __future__ import annotations
import argparse
import math
import os
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot
from plotly.subplots import make_subplots
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from core.model.backtest_config import load_config
from core.model.strategy_config import FactorConfig, FilterFactorConfig
from core.utils.path_kit import get_file_path
OUTPUT_DIR = Path(__file__).resolve().parent / 'output'
FACTOR_NAME_MAP = {'Volume Contraction Factor': 'Volume Contraction Factor', 'Volume Volatility Contraction Factor': 'Volume Volatility Contraction Factor', 'Turnover Rate': 'Turnover Rate', 'Normalized Turnover Rate': 'Normalized Turnover Rate', 'Long-Term Low Volume': 'Long-Term Low Volume', 'Oversold': 'Oversold', 'Net Capital Inflow': 'Net Capital Inflow', 'Normalized Net Capital Inflow': 'Normalized Net Capital Inflow', 'Rolling PE': 'Rolling PE', 'Ret': 'Return', 'close': 'Close Price', 'Market Capitalization': 'Market Capitalization', 'Average Market Capitalization': 'Average Market Capitalization', 'Short-Term Momentum': 'Short-Term Momentum', 'Normalized Short-Term Momentum': 'Normalized Short-Term Momentum', 'Bollinger Breakout': 'Bollinger Breakout', 'N-Day Breakout': 'N-Day Breakout', 'RSI': 'RSI', 'Volatility': 'Volatility', 'Amplitude': 'Amplitude', 'Breakout': 'Breakout', 'Power-Enhanced Breakout': 'Power-Enhanced Breakout', 'Settlement Ratio': 'Settlement Ratio', 'Month': 'Month', 'Net Profit Decline': 'Net Profit Decline', 'ROE': 'ROE', 'Composite_Overbought': 'Composite Overbought', 'W-22': 'W-22', 'W-24': 'W-24', 'W-42': 'W-42'}
STRATEGY_NAME_MAP = {'Oversold Rebound Timing Strategy': 'Oversold Rebound Timing Strategy', 'Limit-Up Breakout Timing Strategy': 'Limit-Up Breakout Timing Strategy'}

@dataclass(frozen=True)
class FactorDescriptor:
    factor_id: str
    english_name: str
    raw_name: str
    column_name: str
    parameter: str
    sort_order: str
    normalized_weight: float

def english_name(raw_name: str) -> str:
    return FACTOR_NAME_MAP.get(raw_name, raw_name)

def english_strategy_name(raw_name: str) -> str:
    return STRATEGY_NAME_MAP.get(raw_name, raw_name)

def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return float('nan')
    return numerator / denominator

def weighted_mean(series: pd.Series, weights: pd.Series | None=None) -> float:
    if series.empty:
        return float('nan')
    if weights is None:
        return float(series.mean())
    valid = pd.concat([series, weights], axis=1).dropna()
    if valid.empty:
        return float('nan')
    series_valid = valid.iloc[:, 0]
    weights_valid = valid.iloc[:, 1]
    weight_sum = weights_valid.sum()
    if weight_sum == 0:
        return float('nan')
    return float(np.average(series_valid, weights=weights_valid))

def to_display_parameter(param: Any) -> str:
    return str(param)

def figure_to_html(fig: go.Figure, include_js: bool=False) -> str:
    return plot(fig, output_type='div', include_plotlyjs='cdn' if include_js else False)

def open_file(path: Path) -> None:
    if os.name == 'nt':
        os.system(f'start "" "{path}"')
    else:
        webbrowser.open(path.as_uri())

def load_inputs():
    conf = load_config()
    strategy = conf.strategy
    if strategy is None:
        raise RuntimeError('Failed to load strategy from config.py.')
    factor_cache_path = get_file_path('data', 'runtime_cache', 'factor_calculation_results.pkl')
    if not factor_cache_path.exists():
        raise FileNotFoundError(f'Factor cache not found: {factor_cache_path}')
    selection_path = conf.get_result_folder() / f'{strategy.name}selection_results.pkl'
    if not selection_path.exists():
        raise FileNotFoundError(f'Selection result not found: {selection_path}\nPlease run the stock selection step before running the attribution analysis tool.')
    factor_df = pd.read_pickle(factor_cache_path)
    selection_df = pd.read_pickle(selection_path)
    return (conf, strategy, factor_df, selection_df)

def build_factor_descriptors(strategy) -> list[FactorDescriptor]:
    descriptors: list[FactorDescriptor] = []
    for index, factor_config in enumerate(strategy.factor_list, start=1):
        descriptors.append(FactorDescriptor(factor_id=f'F{index:02d}', english_name=english_name(factor_config.name), raw_name=factor_config.name, column_name=factor_config.col_name, parameter=to_display_parameter(factor_config.param), sort_order='Ascending' if factor_config.is_sort_asc else 'Descending', normalized_weight=float(factor_config.weight)))
    return descriptors

def build_factor_config_frame(descriptors: list[FactorDescriptor]) -> pd.DataFrame:
    return pd.DataFrame([{'factor_id': d.factor_id, 'factor_name': d.english_name, 'raw_factor_name': d.raw_name, 'factor_column': d.column_name, 'parameter': d.parameter, 'sort_order': d.sort_order, 'normalized_weight': d.normalized_weight} for d in descriptors])

def build_filter_config_frame(filter_list: list[FilterFactorConfig]) -> pd.DataFrame:
    rows = []
    for index, filter_config in enumerate(filter_list, start=1):
        rows.append({'filter_id': f'FL{index:02d}', 'filter_name': english_name(filter_config.name), 'raw_filter_name': filter_config.name, 'filter_column': filter_config.col_name, 'parameter': to_display_parameter(filter_config.param), 'method': filter_config.method.how if filter_config.method else '', 'rule': filter_config.method.range if filter_config.method else '', 'sort_order': 'Ascending' if filter_config.is_sort_asc else 'Descending'})
    return pd.DataFrame(rows)

def select_top_n(period_df: pd.DataFrame, select_num: float | int, factor_name: str) -> pd.DataFrame:
    df = period_df.copy()
    df['composite_rank'] = df.groupby('trade_date')[factor_name].rank(method='min', ascending=True)
    df['total_count'] = df.groupby('trade_date')['stock_code'].transform('size')
    if int(select_num) == 0:
        df = df[df['composite_rank'] <= df['total_count'] * select_num].copy()
    else:
        df = df[df['composite_rank'] <= select_num].copy()
    df['portfolio_weight'] = 1 / df.groupby('trade_date')['stock_code'].transform('size')
    return df

def prepare_attribution_frames(conf, strategy, factor_df: pd.DataFrame, selection_df: pd.DataFrame):
    descriptors = build_factor_descriptors(strategy)
    selected_dates = sorted(pd.to_datetime(selection_df['trade_date']).unique())
    factor_df = factor_df.copy()
    if 'next_period_return' not in factor_df.columns:
        if not {'stock_code', 'close', 'adj_factor'}.issubset(factor_df.columns):
            raise KeyError("The factor cache does not contain 'next_period_return', and the required columns ('stock_code', 'close', 'adj_factor') are not available to rebuild it.")
        factor_df = factor_df.sort_values(['stock_code', 'trade_date']).copy()
        first_close = factor_df.groupby('stock_code', observed=False)['close'].transform('first')
        first_adj_factor = factor_df.groupby('stock_code', observed=False)['adj_factor'].transform('first')
        factor_df['adjusted_close'] = factor_df['adj_factor'] * (first_close / first_adj_factor)
        factor_df['next_period_return'] = factor_df.groupby('stock_code', observed=False)['adjusted_close'].transform(lambda x: x.pct_change().shift(-1))
    required_base_columns = ['trade_date', 'stock_code', 'stock_name', 'total_market_cap', 'float_market_cap', 'is_tradable', 'trading_day_count', 'market_trading_day_count', 'next_day_tradable', 'next_day_open_limit_up', 'next_day_st', 'next_day_delisted', 'listed_trading_days', 'next_period_return']
    required_columns = list(dict.fromkeys(required_base_columns + strategy.factor_columns))
    analysis_df = factor_df[factor_df['trade_date'].isin(selected_dates)][required_columns].copy()
    analysis_df['trade_date'] = pd.to_datetime(analysis_df['trade_date'])
    selection_df = selection_df.copy()
    selection_df['trade_date'] = pd.to_datetime(selection_df['trade_date'])
    date_summary_rows = []
    attribution_rows = []
    latest_holdings_rows = []
    latest_factor_detail_rows = []
    latest_trade_date = max(selected_dates)
    for trade_date in selected_dates:
        date_slice = analysis_df[analysis_df['trade_date'] == trade_date].copy()
        base_universe = date_slice[date_slice['is_tradable'] == 1].dropna(subset=strategy.factor_columns).copy()
        eligible_universe = strategy.filter_before_select(base_universe.copy()).copy()
        eligible_universe = eligible_universe.sort_values(['trade_date', 'stock_code']).reset_index(drop=True)
        eligible_universe = eligible_universe.join(strategy.calc_select_factor(eligible_universe))
        selected_snapshot = selection_df.loc[selection_df['trade_date'] == trade_date, ['trade_date', 'stock_code', 'target_position_weight']].rename(columns={'target_position_weight': 'portfolio_weight'})
        selected_candidates = select_top_n(eligible_universe.copy(), strategy.select_num, strategy.factor_name)
        selected_candidates = selected_candidates[['trade_date', 'stock_code', 'portfolio_weight']]
        selected_view = eligible_universe.merge(selected_snapshot, on=['trade_date', 'stock_code'], how='left', suffixes=('', '_actual'))
        if selected_view['portfolio_weight'].isna().all():
            selected_view = eligible_universe.merge(selected_candidates, on=['trade_date', 'stock_code'], how='left')
        selected_view['selected_flag'] = selected_view['portfolio_weight'].notna()
        selected_view['market_cap_bn_cny'] = selected_view['total_market_cap'] / 100000000.0
        selected_view['float_market_cap_bn_cny'] = selected_view['float_market_cap'] / 100000000.0
        selected_view['composite_rank'] = selected_view[strategy.factor_name].rank(method='min', ascending=True)
        for descriptor, factor_config in zip(descriptors, strategy.factor_list):
            rank_column = f'{descriptor.factor_id}_rank'
            percentile_column = f'{descriptor.factor_id}_percentile'
            score_column = f'{descriptor.factor_id}_score_component'
            selected_view[rank_column] = selected_view[descriptor.column_name].rank(ascending=factor_config.is_sort_asc, method='min')
            selected_view[percentile_column] = selected_view[descriptor.column_name].rank(ascending=factor_config.is_sort_asc, pct=True, method='min')
            selected_view[score_column] = selected_view[rank_column] * descriptor.normalized_weight
        selected_rows = selected_view[selected_view['selected_flag']].copy()
        base_count = int(len(base_universe))
        eligible_count = int(len(eligible_universe))
        selected_count = int(len(selected_rows))
        weighted_forward_return = weighted_mean(selected_rows['next_period_return'], selected_rows['portfolio_weight'])
        mean_composite_score = weighted_mean(selected_rows[strategy.factor_name], selected_rows['portfolio_weight'])
        date_summary_rows.append({'trade_date': trade_date, 'base_universe_count': base_count, 'eligible_universe_count': eligible_count, 'selected_count': selected_count, 'filter_pass_rate': safe_div(eligible_count, base_count), 'selection_rate': safe_div(selected_count, eligible_count), 'weighted_next_period_return': weighted_forward_return, 'weighted_composite_score': mean_composite_score})
        for descriptor in descriptors:
            percentile_column = f'{descriptor.factor_id}_percentile'
            score_column = f'{descriptor.factor_id}_score_component'
            rank_ic = selected_view[descriptor.column_name].corr(selected_view['next_period_return'], method='spearman')
            selected_percentile = weighted_mean(selected_rows[percentile_column], selected_rows['portfolio_weight'])
            universe_percentile = weighted_mean(selected_view[percentile_column])
            selection_edge = universe_percentile - selected_percentile
            attribution_rows.append({'trade_date': trade_date, 'factor_id': descriptor.factor_id, 'factor_name': descriptor.english_name, 'raw_factor_name': descriptor.raw_name, 'factor_column': descriptor.column_name, 'sort_order': descriptor.sort_order, 'normalized_weight': descriptor.normalized_weight, 'selected_weighted_raw_value': weighted_mean(selected_rows[descriptor.column_name], selected_rows['portfolio_weight']), 'eligible_universe_raw_value_mean': weighted_mean(selected_view[descriptor.column_name]), 'selected_weighted_percentile': selected_percentile, 'eligible_universe_percentile_mean': universe_percentile, 'selection_edge': selection_edge, 'selected_weighted_score_component': weighted_mean(selected_rows[score_column], selected_rows['portfolio_weight']), 'rank_ic': rank_ic})
        if trade_date == latest_trade_date:
            latest_holdings_rows.extend(selected_rows[['trade_date', 'stock_code', 'stock_name', 'portfolio_weight', 'total_market_cap', 'float_market_cap', 'market_cap_bn_cny', 'float_market_cap_bn_cny', strategy.factor_name, 'composite_rank', 'next_period_return']].rename(columns={'trade_date': 'trade_date', 'stock_code': 'stock_code', 'stock_name': 'stock_name', 'total_market_cap': 'total_market_cap_cny', 'float_market_cap': 'float_market_cap_cny', strategy.factor_name: 'composite_score', 'next_period_return': 'next_period_return'}).to_dict('records'))
            for descriptor in descriptors:
                rank_column = f'{descriptor.factor_id}_rank'
                percentile_column = f'{descriptor.factor_id}_percentile'
                score_column = f'{descriptor.factor_id}_score_component'
                latest_factor_detail_rows.extend(selected_rows[['trade_date', 'stock_code', 'stock_name', 'portfolio_weight', descriptor.column_name, rank_column, percentile_column, score_column]].rename(columns={'trade_date': 'trade_date', 'stock_code': 'stock_code', 'stock_name': 'stock_name', descriptor.column_name: 'raw_value', rank_column: 'eligible_rank', percentile_column: 'eligible_percentile', score_column: 'weighted_score_component'}).assign(factor_id=descriptor.factor_id, factor_name=descriptor.english_name, raw_factor_name=descriptor.raw_name, factor_column=descriptor.column_name).to_dict('records'))
    date_summary_df = pd.DataFrame(date_summary_rows).sort_values('trade_date').reset_index(drop=True)
    attribution_df = pd.DataFrame(attribution_rows).sort_values(['trade_date', 'factor_id']).reset_index(drop=True)
    latest_holdings_df = pd.DataFrame(latest_holdings_rows).sort_values('portfolio_weight', ascending=False)
    latest_factor_detail_df = pd.DataFrame(latest_factor_detail_rows).sort_values(['factor_id', 'portfolio_weight'], ascending=[True, False])
    return (descriptors, date_summary_df, attribution_df, latest_holdings_df, latest_factor_detail_df)

def build_factor_summary(attribution_df: pd.DataFrame) -> pd.DataFrame:
    factor_summary = attribution_df.groupby(['factor_id', 'factor_name', 'raw_factor_name', 'factor_column', 'sort_order'], as_index=False).agg(normalized_weight=('normalized_weight', 'first'), average_selected_percentile=('selected_weighted_percentile', 'mean'), average_universe_percentile=('eligible_universe_percentile_mean', 'mean'), average_selection_edge=('selection_edge', 'mean'), average_rank_ic=('rank_ic', 'mean'), latest_selected_percentile=('selected_weighted_percentile', 'last'), latest_selection_edge=('selection_edge', 'last'), latest_selected_raw_value=('selected_weighted_raw_value', 'last'), latest_universe_raw_value=('eligible_universe_raw_value_mean', 'last'), latest_score_component=('selected_weighted_score_component', 'last'))
    factor_summary['latest_raw_value_spread'] = factor_summary['latest_selected_raw_value'] - factor_summary['latest_universe_raw_value']
    factor_summary = factor_summary.sort_values(['latest_selection_edge', 'average_selection_edge'], ascending=False).reset_index(drop=True)
    return factor_summary

def build_strategy_metadata(conf, strategy, date_summary_df: pd.DataFrame, latest_holdings_df: pd.DataFrame) -> pd.DataFrame:
    latest_date = latest_holdings_df['trade_date'].max() if not latest_holdings_df.empty else pd.NaT
    strategy_display = english_strategy_name(strategy.name)
    rows = [{'metric': 'Strategy Name', 'value': strategy_display}, {'metric': 'Raw Strategy Name', 'value': strategy.name}, {'metric': 'Holding Period', 'value': strategy.hold_period}, {'metric': 'Selection Count', 'value': strategy.select_num}, {'metric': 'Configured Start Date', 'value': conf.start_date}, {'metric': 'Configured End Date', 'value': conf.end_date or 'Latest Available Data'}, {'metric': 'Latest Trade Date', 'value': latest_date}, {'metric': 'Average Eligible Universe Size', 'value': date_summary_df['eligible_universe_count'].mean()}, {'metric': 'Average Selected Count', 'value': date_summary_df['selected_count'].mean()}, {'metric': 'Average Filter Pass Rate', 'value': date_summary_df['filter_pass_rate'].mean()}]
    return pd.DataFrame(rows)

def build_html_report(strategy_metadata_df: pd.DataFrame, factor_config_df: pd.DataFrame, filter_config_df: pd.DataFrame, date_summary_df: pd.DataFrame, factor_summary_df: pd.DataFrame, attribution_df: pd.DataFrame, latest_holdings_df: pd.DataFrame) -> str:
    figures: list[str] = []
    fig = go.Figure(data=[go.Scatter(x=date_summary_df['trade_date'], y=date_summary_df['eligible_universe_count'], mode='lines', name='Eligible Universe Size'), go.Scatter(x=date_summary_df['trade_date'], y=date_summary_df['selected_count'], mode='lines', name='Selected Count')])
    fig.update_layout(title='Universe and Selection Counts Over Time', width=1500, height=520, hovermode='x unified')
    figures.append(figure_to_html(fig, include_js=True))
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    fig.add_trace(go.Scatter(x=date_summary_df['trade_date'], y=date_summary_df['filter_pass_rate'], mode='lines', name='Filter Pass Rate'), secondary_y=False)
    fig.add_trace(go.Scatter(x=date_summary_df['trade_date'], y=date_summary_df['selection_rate'], mode='lines', name='Selection Rate'), secondary_y=False)
    fig.add_trace(go.Scatter(x=date_summary_df['trade_date'], y=date_summary_df['weighted_next_period_return'], mode='lines', name='Selected Next-Period Return', line=dict(color='firebrick')), secondary_y=True)
    fig.update_layout(title='Selection Efficiency and Next-Period Return', width=1500, height=520, hovermode='x unified')
    figures.append(figure_to_html(fig))
    latest_factor_summary = factor_summary_df.sort_values('latest_selection_edge', ascending=True)
    fig = go.Figure(data=[go.Bar(x=latest_factor_summary['latest_selection_edge'], y=latest_factor_summary['factor_name'], orientation='h', text=latest_factor_summary['latest_selection_edge'].round(4), textposition='outside', name='Latest Selection Edge')])
    fig.update_layout(title='Latest Factor Selection Edge', width=1500, height=max(480, 90 * len(latest_factor_summary)))
    figures.append(figure_to_html(fig))
    fig = go.Figure(data=[go.Bar(x=factor_summary_df['factor_name'], y=factor_summary_df['average_rank_ic'], text=factor_summary_df['average_rank_ic'].round(4), textposition='outside', name='Average Rank IC')])
    fig.update_layout(title='Average Rank IC by Factor', width=1500, height=540, xaxis_tickangle=-25)
    figures.append(figure_to_html(fig))
    fig = go.Figure()
    for factor_name, sub_df in attribution_df.groupby('factor_name'):
        fig.add_trace(go.Scatter(x=sub_df['trade_date'], y=sub_df['selected_weighted_percentile'], mode='lines', name=factor_name))
    fig.update_layout(title='Selected Weighted Percentile by Factor', width=1500, height=620, hovermode='x unified')
    figures.append(figure_to_html(fig))
    fig = go.Figure()
    for factor_name, sub_df in attribution_df.groupby('factor_name'):
        fig.add_trace(go.Scatter(x=sub_df['trade_date'], y=sub_df['selection_edge'], mode='lines', name=factor_name))
    fig.update_layout(title='Selection Edge by Factor', width=1500, height=620, hovermode='x unified')
    figures.append(figure_to_html(fig))
    latest_holdings_display = latest_holdings_df.copy()
    if not latest_holdings_display.empty:
        latest_holdings_display['portfolio_weight'] = latest_holdings_display['portfolio_weight'].map(lambda x: round(x, 6))
        latest_holdings_display['next_period_return'] = latest_holdings_display['next_period_return'].map(lambda x: round(x, 6) if pd.notna(x) else x)
        latest_holdings_display = latest_holdings_display.head(20)
    sections = [('Strategy Metadata', strategy_metadata_df.to_html(index=False)), ('Factor Configuration', factor_config_df.to_html(index=False)), ('Filter Configuration', filter_config_df.to_html(index=False) if not filter_config_df.empty else '<p>No additional filters configured.</p>'), ('Date Summary', date_summary_df.to_html(index=False)), ('Factor Summary', factor_summary_df.to_html(index=False)), ('Latest Holdings Snapshot', latest_holdings_display.to_html(index=False) if not latest_holdings_display.empty else '<p>No latest holdings available.</p>')]
    section_html = []
    for title, table_html in sections:
        section_html.append(f'\n            <section class="card">\n                <h2>{title}</h2>\n                <div class="table-wrap">{table_html}</div>\n            </section>\n            ')
    figure_html = ''.join((f'<section class="card chart-card">{item}</section>' for item in figures))
    return f"""<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <title>Attribution Analysis Report</title>\n    <style>\n        body {{\n            font-family: Arial, sans-serif;\n            margin: 0;\n            padding: 24px;\n            background: #f3f6fb;\n            color: #17202a;\n        }}\n        h1 {{\n            margin-top: 0;\n        }}\n        .subtitle {{\n            color: #566573;\n            margin-bottom: 24px;\n        }}\n        .card {{\n            background: white;\n            border-radius: 14px;\n            padding: 20px;\n            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);\n            margin-bottom: 20px;\n        }}\n        .chart-card {{\n            overflow-x: auto;\n        }}\n        .table-wrap {{\n            overflow-x: auto;\n        }}\n        table {{\n            border-collapse: collapse;\n            width: 100%;\n            font-size: 14px;\n        }}\n        th, td {{\n            border: 1px solid #d5dbe3;\n            padding: 8px 10px;\n            text-align: left;\n            white-space: nowrap;\n        }}\n        th {{\n            background: #eef3f8;\n        }}\n    </style>\n</head>\n<body>\n    <h1>Attribution Analysis Report</h1>\n    <div class="subtitle">This report explains how the currently configured strategy selected holdings and how each factor contributed across time.</div>\n    {''.join(section_html)}\n    {figure_html}\n</body>\n</html>"""

def save_outputs(strategy_metadata_df: pd.DataFrame, factor_config_df: pd.DataFrame, filter_config_df: pd.DataFrame, date_summary_df: pd.DataFrame, attribution_df: pd.DataFrame, factor_summary_df: pd.DataFrame, latest_holdings_df: pd.DataFrame, latest_factor_detail_df: pd.DataFrame) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    strategy_metadata_df.to_csv(OUTPUT_DIR / 'strategy_metadata.csv', index=False, encoding='utf-8-sig')
    factor_config_df.to_csv(OUTPUT_DIR / 'factor_configuration.csv', index=False, encoding='utf-8-sig')
    filter_config_df.to_csv(OUTPUT_DIR / 'filter_configuration.csv', index=False, encoding='utf-8-sig')
    date_summary_df.to_csv(OUTPUT_DIR / 'date_summary.csv', index=False, encoding='utf-8-sig')
    attribution_df.to_csv(OUTPUT_DIR / 'factor_attribution_timeseries.csv', index=False, encoding='utf-8-sig')
    factor_summary_df.to_csv(OUTPUT_DIR / 'factor_summary.csv', index=False, encoding='utf-8-sig')
    latest_holdings_df.to_csv(OUTPUT_DIR / 'latest_holdings_snapshot.csv', index=False, encoding='utf-8-sig')
    latest_factor_detail_df.to_csv(OUTPUT_DIR / 'latest_holdings_factor_details.csv', index=False, encoding='utf-8-sig')
    report_html = build_html_report(strategy_metadata_df=strategy_metadata_df, factor_config_df=factor_config_df, filter_config_df=filter_config_df, date_summary_df=date_summary_df, factor_summary_df=factor_summary_df, attribution_df=attribution_df, latest_holdings_df=latest_holdings_df)
    report_path = OUTPUT_DIR / 'attribution_analysis_report.html'
    report_path.write_text(report_html, encoding='utf-8')
    return report_path

def main(open_report: bool):
    conf, strategy, factor_df, selection_df = load_inputs()
    descriptors, date_summary_df, attribution_df, latest_holdings_df, latest_factor_detail_df = prepare_attribution_frames(conf=conf, strategy=strategy, factor_df=factor_df, selection_df=selection_df)
    factor_config_df = build_factor_config_frame(descriptors)
    filter_config_df = build_filter_config_frame(strategy.filter_list)
    factor_summary_df = build_factor_summary(attribution_df)
    strategy_metadata_df = build_strategy_metadata(conf, strategy, date_summary_df, latest_holdings_df)
    report_path = save_outputs(strategy_metadata_df=strategy_metadata_df, factor_config_df=factor_config_df, filter_config_df=filter_config_df, date_summary_df=date_summary_df, attribution_df=attribution_df, factor_summary_df=factor_summary_df, latest_holdings_df=latest_holdings_df, latest_factor_detail_df=latest_factor_detail_df)
    if open_report:
        open_file(report_path)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run attribution analysis for the current strategy in config.py.')
    parser.add_argument('--open-report', action='store_true', help='Open the generated HTML report after the analysis finishes.')
    args = parser.parse_args()
    main(open_report=args.open_report)
