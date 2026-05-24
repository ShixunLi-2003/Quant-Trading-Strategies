"""Financial-data loading and preprocessing helpers."""

import numpy as np
import pandas as pd
from core.model.backtest_config import BacktestConfig
pd.set_option('expand_frame_repr', False)

def mark_old_report(date_list):
    date_list = date_list.tolist()
    res = []
    for index, date in enumerate(date_list):
        flag = 0
        for i in sorted(range(index), reverse=True):
            if date_list[i] > date:
                flag = 1
                break
        res.append(flag)
    return res

def get_last_quarter_and_year_index(date_list):
    date_list = date_list.tolist()
    last_q_index = []
    last_4q_index = []
    last_y_index = []
    last_y_3q_index = []
    last_y_2q_index = []
    last_y_q_index = []
    no_meaning_index = len(date_list) - 1
    for index, date in enumerate(date_list):
        if index == 0:
            last_q_index.append(no_meaning_index)
            last_4q_index.append(no_meaning_index)
            last_y_index.append(no_meaning_index)
            last_y_3q_index.append(no_meaning_index)
            last_y_2q_index.append(no_meaning_index)
            last_y_q_index.append(no_meaning_index)
            continue
        q_finish = False
        _4q_finish = False
        y_finish = False
        _y_3q_index = False
        _y_2q_index = False
        _y_q_index = False
        for i in sorted(range(index), reverse=True):
            delta_month = (date - date_list[i]).days / 30
            delta_month = round(delta_month)
            if delta_month == 3 and q_finish is False:
                last_q_index.append(i)
                q_finish = True
            if delta_month == 12 and _4q_finish is False:
                last_4q_index.append(i)
                _4q_finish = True
            if date.year - date_list[i].year == 1 and date_list[i].month == 3 and (_y_q_index is False):
                last_y_q_index.append(i)
                _y_q_index = True
            if date.year - date_list[i].year == 1 and date_list[i].month == 6 and (_y_2q_index is False):
                last_y_2q_index.append(i)
                _y_2q_index = True
            if date.year - date_list[i].year == 1 and date_list[i].month == 9 and (_y_3q_index is False):
                last_y_3q_index.append(i)
                _y_3q_index = True
            if date.year - date_list[i].year == 1 and date_list[i].month == 12 and (y_finish is False):
                last_y_index.append(i)
                y_finish = True
            if q_finish and _4q_finish and y_finish and _y_q_index and _y_2q_index and _y_3q_index:
                break
        if q_finish is False:
            last_q_index.append(no_meaning_index)
        if _4q_finish is False:
            last_4q_index.append(no_meaning_index)
        if y_finish is False:
            last_y_index.append(no_meaning_index)
        if _y_q_index is False:
            last_y_q_index.append(no_meaning_index)
        if _y_2q_index is False:
            last_y_2q_index.append(no_meaning_index)
        if _y_3q_index is False:
            last_y_3q_index.append(no_meaning_index)
    return (last_q_index, last_4q_index, last_y_index, last_y_q_index, last_y_2q_index, last_y_3q_index)

def get_index_data(data, index_list, col_list):
    col_list = [col for col in col_list if col in data.columns]
    df = data.loc[index_list, col_list].reset_index()
    df = df[df['index'] != df.shape[0] - 1]
    return df

def cal_fin_data(data, flow_fin_list=(), cross_fin_list=(), discard=True):
    data.sort_values(['publish_date', 'report_date'], inplace=True)
    data.reset_index(drop=True, inplace=True)

    def time_change(x):
        try:
            return pd.to_datetime(x, format='%Y%m%d')
        except Exception as e:
            return pd.to_datetime(x)
    try:
        data['report_date'] = pd.to_datetime(data['report_date'], format='%Y%m%d')
    except Exception as exp:
        data['report_date'] = data['report_date'].apply(time_change)
    last_q_index, last_4q_index, last_y_index, last_y_q_index, last_y_2q_index, last_y_3q_index = get_last_quarter_and_year_index(data['report_date'])
    last_q_df = get_index_data(data, last_q_index, flow_fin_list)
    last_4q_df = get_index_data(data, last_4q_index, flow_fin_list)
    last_y_df = get_index_data(data, last_y_index, flow_fin_list)
    data_columns = data.columns

    def need_col(col_list: list) -> bool:
        for _col in col_list:
            if _col in data_columns:
                return True
        return False
    for col in flow_fin_list:
        if need_col([col + '_single_quarter', col + '_single_quarter_qoq', col + '_single_quarter_yoy']):
            data[col + '_single_quarter'] = data[col] - last_q_df[col]
            data.loc[data['report_date'].dt.month == 3, col + '_single_quarter'] = data[col]
        if need_col([col + '_cumulative_yoy']):
            data[col + '_cumulative_yoy'] = data[col] / last_4q_df[col] - 1
            minus_index = last_4q_df[last_4q_df[col] < 0].index
            data.loc[minus_index, col + '_cumulative_yoy'] = 1 - data[col] / last_4q_df[col]
        if need_col([col + '_ttm', col + '_ttm_yoy']):
            data[col + '_ttm'] = data[col] + last_y_df[col] - last_4q_df[col]
            data.loc[data['report_date'].dt.month == 12, col + '_ttm'] = data[col]
    last_q_df = get_index_data(data, last_q_index, [c + '_single_quarter' for c in flow_fin_list])
    last_4q_df = get_index_data(data, last_4q_index, [c + '_single_quarter' for c in flow_fin_list] + [c + '_ttm' for c in flow_fin_list])
    for col in flow_fin_list:
        if need_col([col + '_single_quarter_qoq']):
            data[col + '_single_quarter_qoq'] = data[col + '_single_quarter'] / last_q_df[col + '_single_quarter'] - 1
            minus_index = last_q_df[last_q_df[col + '_single_quarter'] < 0].index
            data.loc[minus_index, col + '_single_quarter_qoq'] = 1 - data[col + '_single_quarter'] / last_q_df[col + '_single_quarter']
        if need_col([col + '_single_quarter_yoy']):
            data[col + '_single_quarter_yoy'] = data[col + '_single_quarter'] / last_4q_df[col + '_single_quarter'] - 1
            minus_index = last_4q_df[last_4q_df[col + '_single_quarter'] < 0].index
            data.loc[minus_index, col + '_single_quarter_yoy'] = 1 - data[col + '_single_quarter'] / last_4q_df[col + '_single_quarter']
        if need_col([col + '_ttm_yoy']):
            data[col + '_ttm_yoy'] = data[col + '_ttm'] / last_4q_df[col + '_ttm'] - 1
            minus_index = last_4q_df[last_4q_df[col + '_ttm'] < 0].index
            data.loc[minus_index, col + '_ttm_yoy'] = 1 - data[col + '_ttm'] / last_4q_df[col + '_ttm']
    last_q_df = get_index_data(data, last_q_index, cross_fin_list)
    last_4q_df = get_index_data(data, last_4q_index, cross_fin_list)
    for col in cross_fin_list:
        if need_col([col + '_qoq']):
            data[col + '_qoq'] = data[col] / last_q_df[col] - 1
            minus_index = last_q_df[last_q_df[col] < 0].index
            data.loc[minus_index, col + '_qoq'] = 1 - data[col] / last_q_df[col]
        if need_col([col + '_yoy']):
            data[col + '_yoy'] = data[col] / last_4q_df[col] - 1
            minus_index = last_4q_df[last_4q_df[col] < 0].index
            data.loc[minus_index, col + '_yoy'] = 1 - data[col] / last_4q_df[col]
    if discard:
        data['deprecated_report'] = mark_old_report(data['report_date'])
        data = data[data['deprecated_report'] != 1]
        del data['deprecated_report']
    return data

def get_his_data(fin_df, data_cols, span='q'):
    data = fin_df.copy()
    last_q_index, last_4q_index, last_y_index, last_y_q_index, last_y_2q_index, last_y_3q_index = get_last_quarter_and_year_index(data['report_date'])
    if span == '4q':
        last_index = last_4q_index
        label = 'same_period_last_year'
    elif span == 'y':
        last_index = last_y_index
        label = 'last_year_annual_report'
    elif span == 'y_q':
        last_index = last_y_q_index
        label = 'last_year_q1'
    elif span == 'y_2q':
        last_index = last_y_2q_index
        label = 'last_year_q2'
    elif span == 'y_3q':
        last_index = last_y_3q_index
        label = 'last_year_q3'
    else:
        last_index = last_q_index
        label = 'previous_quarter'
    last_df = get_index_data(data, last_index, data_cols)
    del last_df['index']
    data = pd.merge(left=data, right=last_df, left_index=True, right_index=True, how='left', suffixes=('', '_' + label))
    new_cols = [col + '_' + label for col in data_cols]
    keep_col = ['publish_date', 'report_date'] + new_cols
    data = data[keep_col].copy()
    return (data, new_cols)

def merge_with_finance_data(conf: BacktestConfig, stock_code, stock_df):
    stock_fin_folder = conf.fin_data_path / stock_code
    fin_cols = conf.fin_cols
    if stock_fin_folder.exists():
        flow_fin_cols = list(set([col.split('@xbx')[0] + '@xbx' for col in fin_cols if col.startswith('R_') or col.startswith('C_')]))
        cross_fin_cols = list(set([col.split('@xbx')[0] + '@xbx' for col in fin_cols if col.startswith('B_')]))
        finance_dfs = []
        for file in stock_fin_folder.iterdir():
            finance_df = pd.read_csv(stock_fin_folder / file, parse_dates=['publish_date'], skiprows=1, encoding='gbk')
            for col in set(flow_fin_cols + cross_fin_cols + fin_cols):
                if col not in finance_df.columns:
                    finance_df[col] = np.nan
            necessary_cols = ['stock_code', 'report_date', 'publish_date']
            finance_df = finance_df[list(set(necessary_cols + flow_fin_cols + cross_fin_cols + fin_cols))]
            finance_df = cal_fin_data(data=finance_df, flow_fin_list=flow_fin_cols, cross_fin_list=cross_fin_cols, discard=False)
            col = ['publish_date', 'report_date'] + fin_cols
            finance_dfs.append(finance_df[col])
        all_finance_df = pd.concat(finance_dfs, ignore_index=True)
        all_finance_df.sort_values(by=['publish_date', 'report_date'], inplace=True)
        all_finance_df_not_discord = all_finance_df.copy()
        all_finance_df['deprecated_report'] = mark_old_report(all_finance_df['report_date'])
        all_finance_df = all_finance_df[all_finance_df['deprecated_report'] != 1]
        del all_finance_df['deprecated_report']
        all_finance_df.drop_duplicates(subset=['publish_date'], keep='last', inplace=True)
        all_finance_df.reset_index(drop=True, inplace=True)
        stock_df = pd.merge_asof(stock_df, all_finance_df, left_on='trade_date', right_on='publish_date', direction='backward')
    else:
        all_finance_df = pd.DataFrame()
        for col in ['publish_date', 'report_date'] + fin_cols:
            stock_df[f'{col}'] = np.nan
            all_finance_df[f'{col}'] = np.nan
        all_finance_df_not_discord = all_finance_df.copy()
    return (stock_df, all_finance_df, all_finance_df_not_discord)

def merge_with_calc_fin_data(stock_df, no_discard_finance_df, calc_fin_cols, extra_agg_dict):
    if len(calc_fin_cols) == 0:
        return stock_df
    for col_dict in calc_fin_cols:
        cols = col_dict.get('col')
        q = col_dict.get('quarter')
        if len(cols) == 0 or len(q) == 0:
            continue
        fin_df, new_cols = get_his_data(no_discard_finance_df, cols, q)
        if fin_df.empty:
            for new_col in new_cols:
                stock_df[new_col] = np.nan
                extra_agg_dict[new_col] = 'last'
            continue
        stock_df = pd.merge_asof(left=stock_df, right=fin_df, left_on='trade_date', right_on='publish_date', direction='backward', suffixes=('', '_y'))
        for new_col in new_cols:
            stock_df[new_col].fillna(method='ffill', inplace=True)
            extra_agg_dict[new_col] = 'last'
    return stock_df
