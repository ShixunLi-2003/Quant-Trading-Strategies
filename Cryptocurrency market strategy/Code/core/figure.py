"""Render interactive portfolio diagnostics for the equity curve and benchmarks."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot
from plotly.subplots import make_subplots

from core.utils.path_kit import get_file_path


def draw_equity_curve_plotly(
    df: pd.DataFrame,
    data_dict: dict[str, str],
    date_col: str | None = None,
    right_axis: dict[str, str] | None = None,
    pic_size: list[int] | None = None,
    chg: bool = False,
    title: str | None = None,
    path=get_file_path("data", "equity_curve.html"),
    show: bool = True,
    desc: str | None = None,
):
    """Plot the strategy curve together with optional benchmark and drawdown series."""
    pic_size = pic_size or [1500, 800]
    draw_df = df.copy()
    time_data = draw_df[date_col] if date_col else draw_df.index

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for label, column in data_dict.items():
        if chg:
            draw_df[column] = (draw_df[column] + 1).fillna(1).cumprod()
        fig.add_trace(go.Scatter(x=time_data, y=draw_df[column], name=label))

    if right_axis:
        for i, (label, column) in enumerate(right_axis.items()):
            fig.add_trace(
                go.Scatter(
                    x=time_data,
                    y=draw_df[column],
                    name=f"{label} (rhs)",
                    marker_color="orange" if i == 0 else None,
                    opacity=0.15,
                    line=dict(width=0),
                    fill="tozeroy",
                    yaxis="y2",
                )
            )

    annotations = []
    if desc:
        annotations.append(
            dict(
                text=desc,
                xref="paper",
                yref="paper",
                x=0.5,
                y=1.05,
                showarrow=False,
                font=dict(size=12, color="black"),
                align="center",
                bgcolor="rgba(255,255,255,0.8)",
            )
        )

    fig.update_layout(
        template="none",
        width=pic_size[0],
        height=pic_size[1],
        title_text=title,
        hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(255,255,255,0.5)"),
        annotations=annotations,
        updatemenus=[
            dict(
                buttons=[
                    dict(label="Linear y-axis", method="relayout", args=[{"yaxis.type": "linear"}]),
                    dict(label="Log y-axis", method="relayout", args=[{"yaxis.type": "log"}]),
                ]
            )
        ],
    )

    plot(figure_or_data=fig, filename=str(path), auto_open=False)
    fig.update_yaxes(showspikes=True, spikemode="across", spikesnap="cursor", spikedash="solid", spikethickness=1)
    fig.update_xaxes(showspikes=True, spikemode="across+marker", spikesnap="cursor", spikedash="solid", spikethickness=1)
    if show:
        fig.show()
