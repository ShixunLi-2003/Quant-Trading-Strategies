from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from hk_quant.analysis.performance import calculate_drawdown_series


def plot_equity_curve(
    equity_curve: pd.Series,
    output_path: str | Path,
    benchmark_equity: pd.Series | None = None,
    title: str = "Equity Curve",
) -> Path:
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(equity_curve.index, equity_curve.values, label="strategy", linewidth=1.5)
    if benchmark_equity is not None:
        axes[0].plot(benchmark_equity.index, benchmark_equity.values, label="benchmark", linewidth=1.2)
    axes[0].set_title(title)
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    drawdown = calculate_drawdown_series(equity_curve)
    axes[1].fill_between(drawdown.index, drawdown.values, 0, color="#d65f5f", alpha=0.5)
    axes[1].set_title("Drawdown")
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_factor_ic(ic_frame: pd.DataFrame, output_path: str | Path) -> Path:
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 4))
    for column in ic_frame.columns:
        rolling_ic = ic_frame[column].rolling(20).mean()
        ax.plot(rolling_ic.index, rolling_ic.values, label=column)
    ax.axhline(0.0, color="black", linewidth=1.0, alpha=0.6)
    ax.set_title("20D Rolling IC")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_quantile_returns(quantile_frame: pd.DataFrame, output_path: str | Path, title: str) -> Path:
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cumulative = (1.0 + quantile_frame.fillna(0.0)).cumprod()
    fig, ax = plt.subplots(figsize=(12, 5))
    for column in cumulative.columns:
        ax.plot(cumulative.index, cumulative[column].values, label=column)
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path
