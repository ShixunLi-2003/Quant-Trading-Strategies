"""Plotly chart helpers for performance and analysis outputs."""

import os
import plotly.graph_objects as go
from plotly.offline import plot
from plotly.subplots import make_subplots
from core.utils.path_kit import get_file_path

def draw_equity_curve_plotly(df, data_dict, date_col=None, right_axis=None, pic_size=None, chg=False, title=None, path=get_file_path('data', 'pic.html'), show=True, desc=None):
    if pic_size is None:
        pic_size = [1500, 800]
    draw_df = df.copy()
    if date_col:
        time_data = draw_df[date_col]
    else:
        time_data = draw_df.index
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    for key in data_dict:
        if chg:
            draw_df[data_dict[key]] = (draw_df[data_dict[key]] + 1).fillna(1).cumprod()
        fig.add_trace(go.Scatter(x=time_data, y=draw_df[data_dict[key]], name=key))
    if right_axis:
        key = list(right_axis.keys())[0]
        fig.add_trace(go.Scatter(x=time_data, y=draw_df[right_axis[key]], name=key + ' (Right Axis)', marker=dict(color='rgba(220, 220, 220, 0.8)'), opacity=0.1, line=dict(width=0), fill='tozeroy', yaxis='y2'))
        for key in list(right_axis.keys())[1:]:
            fig.add_trace(go.Scatter(x=time_data, y=draw_df[right_axis[key]], name=key + ' (Right Axis)', opacity=0.1, line=dict(width=0), fill='tozeroy', yaxis='y2'))
    fig.update_layout(template='none', width=pic_size[0], height=pic_size[1], title_text=title, hovermode='x unified', hoverlabel=dict(bgcolor='rgba(255,255,255,0.5)'), annotations=[dict(text=desc, xref='paper', yref='paper', x=0.5, y=1.05, showarrow=False, font=dict(size=12, color='black'), align='center', bgcolor='rgba(255,255,255,0.8)')])
    fig.update_layout(updatemenus=[dict(buttons=[dict(label='Linear Y-Axis', method='relayout', args=[{'yaxis.type': 'linear'}]), dict(label='Log Y-Axis', method='relayout', args=[{'yaxis.type': 'log'}])])])
    plot(figure_or_data=fig, filename=str(path), auto_open=False)
    fig.update_yaxes(showspikes=True, spikemode='across', spikesnap='cursor', spikedash='solid', spikethickness=1)
    fig.update_xaxes(showspikes=True, spikemode='across+marker', spikesnap='cursor', spikedash='solid', spikethickness=1)
    if show:
        res = os.system('start ' + str(path))
        if res != 0:
            os.system('open ' + str(path))
