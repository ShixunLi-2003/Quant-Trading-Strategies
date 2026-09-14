from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
FIGURES = ROOT / "results" / "figures"


def save_figure(name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(FIGURES / name, dpi=180, bbox_inches="tight")
    plt.close()


def plot_research_workflow() -> None:
    stages = [
        ("Market Inputs", "Daily bars\nOne-minute bars\nETF closes"),
        ("Point-in-Time Layer", "Schema checks\nUniverse dates\nTimestamp alignment"),
        ("Signal Research", "16 factors\nCross-sectional z-scores\n60/40 defensive blend"),
        ("Validation", "Rank IC and HAC\nNon-overlapping bins\nEmbargoed walk-forward"),
        ("Execution Simulation", "Top-three portfolio\nCosts and board lots\n14:53 minute exit"),
        ("Regime Control", "ETF breadth\nFull/half/cash exposure\nNested OOS selection"),
    ]
    colors = ["#E9F1F7", "#DDEBF2", "#D4E9E4", "#CCE3DE", "#F3E3C8", "#E8D8C4"]
    figure, axis = plt.subplots(figsize=(15, 5.2))
    axis.set_xlim(0, 15)
    axis.set_ylim(0, 5.2)
    axis.axis("off")
    box_width = 2.05
    box_height = 2.45
    gap = 0.35
    start = 0.5
    y_position = 1.75
    for index, ((title, body), color) in enumerate(zip(stages, colors)):
        x_position = start + index * (box_width + gap)
        box = FancyBboxPatch(
            (x_position, y_position),
            box_width,
            box_height,
            boxstyle="round,pad=0.08,rounding_size=0.12",
            facecolor=color,
            edgecolor="#264653",
            linewidth=1.2,
        )
        axis.add_patch(box)
        axis.text(
            x_position + box_width / 2,
            y_position + 1.78,
            title,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color="#1D3557",
        )
        axis.text(
            x_position + box_width / 2,
            y_position + 0.85,
            body,
            ha="center",
            va="center",
            fontsize=9.5,
            linespacing=1.45,
            color="#263238",
        )
        if index < len(stages) - 1:
            axis.annotate(
                "",
                xy=(x_position + box_width + gap - 0.07, y_position + box_height / 2),
                xytext=(x_position + box_width + 0.07, y_position + box_height / 2),
                arrowprops={"arrowstyle": "-|>", "color": "#457B9D", "linewidth": 1.5},
            )
    axis.text(
        7.5,
        4.72,
        "Research Architecture: From Licensed Market Data to Out-of-Sample Evidence",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color="#1D3557",
    )
    control = FancyBboxPatch(
        (0.8, 0.45),
        13.4,
        0.65,
        boxstyle="round,pad=0.06,rounding_size=0.1",
        facecolor="#F6F7F8",
        edgecolor="#6C757D",
        linewidth=1.0,
    )
    axis.add_patch(control)
    axis.text(
        7.5,
        0.78,
        "Cross-cutting controls: signal timing  |  embargo  |  adverse slippage  |  "
        "minimum commission  |  ownership safeguards",
        ha="center",
        va="center",
        fontsize=10,
        color="#37474F",
    )
    figure.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.04)
    save_figure("research_workflow.png")


def plot_factor_ic() -> None:
    frame = pd.read_csv(TABLES / "minute_momentum_ic_h3.csv").sort_values("mean_ic")
    colors = np.where(frame["mean_ic"] >= 0, "#2A9D8F", "#E76F51")
    plt.figure(figsize=(9, 6))
    plt.barh(frame["factor"], frame["mean_ic"], color=colors)
    plt.axvline(0.0, color="#333333", linewidth=0.8)
    plt.xlabel("Mean daily rank IC")
    plt.title("Factor Information Coefficients: Three-Day Horizon")
    save_figure("factor_information_coefficients.png")


def plot_factor_robustness() -> None:
    robustness = pd.read_csv(TABLES / "factor_ic_robustness.csv")
    score_labels = {
        "minute_momentum_score": "Broad momentum",
        "defensive_low_volatility_score": "Defensive low volatility",
        "tuned_blend_score": "Selected 60/40 blend",
    }
    selected = robustness[
        robustness["factor"].isin(score_labels) & robustness["split"].isin(["development", "holdout"])
    ].copy()
    selected["score"] = selected["factor"].map(score_labels)
    pivot = selected.pivot(index="score", columns="split", values="mean_ic").reindex(score_labels.values())
    errors = selected.pivot(index="score", columns="split", values="hac_standard_error").reindex(
        score_labels.values()
    )
    positions = np.arange(len(pivot))
    width = 0.36
    plt.figure(figsize=(9, 5.2))
    plt.bar(
        positions - width / 2,
        pivot["development"],
        width,
        yerr=1.96 * errors["development"],
        capsize=3,
        label="Development",
        color="#457B9D",
    )
    plt.bar(
        positions + width / 2,
        pivot["holdout"],
        width,
        yerr=1.96 * errors["holdout"],
        capsize=3,
        label="Holdout",
        color="#2A9D8F",
    )
    plt.axhline(0.0, color="#333333", linewidth=0.8)
    plt.xticks(positions, pivot.index, rotation=10)
    plt.ylabel("Mean daily rank IC")
    plt.title("Composite-Score Stability with Newey-West 95% Intervals")
    plt.legend()
    save_figure("factor_ic_robustness.png")

    quantiles = pd.read_csv(TABLES / "composite_nonoverlap_quantiles.csv")
    selected_quantiles = quantiles[quantiles["split"] == "full"]
    means = selected_quantiles[[f"q{quantile}_mean_return" for quantile in range(1, 6)]].mean()
    plt.figure(figsize=(7.5, 4.6))
    plt.bar([f"Q{quantile}" for quantile in range(1, 6)], means.values, color="#457B9D")
    plt.axhline(0.0, color="#333333", linewidth=0.8)
    plt.ylabel("Mean non-overlapping three-session return")
    plt.title("Selected Composite: Non-Overlapping Quantile Returns")
    save_figure("factor_nonoverlap_quantiles.png")


def plot_quantiles() -> None:
    nav = pd.read_csv(TABLES / "minute_momentum_quantile_nav_h3.csv")
    nav["trade_date"] = pd.to_datetime(nav["trade_date"])
    plt.figure(figsize=(10, 5.5))
    for column, color in [("q1", "#E76F51"), ("q3", "#6C757D"), ("q5", "#2A9D8F"), ("long_short", "#264653")]:
        plt.plot(nav["trade_date"], nav[column], label=column.upper(), color=color, linewidth=1.6)
    plt.axhline(1.0, color="#333333", linewidth=0.8)
    plt.ylabel("Cumulative NAV")
    plt.title("Composite-Factor Quantile Portfolios")
    plt.legend(ncol=4)
    save_figure("factor_quantile_nav.png")

    terminal = nav[["q1", "q2", "q3", "q4", "q5"]].iloc[-1] - 1.0
    plt.figure(figsize=(7.5, 4.5))
    plt.bar(terminal.index.str.upper(), terminal.values, color="#457B9D")
    plt.axhline(0.0, color="#333333", linewidth=0.8)
    plt.ylabel("Cumulative return")
    plt.title("Terminal Return by Factor Quantile")
    save_figure("factor_quantile_bins.png")


def plot_strict_backtests() -> None:
    current = pd.read_csv(TABLES / "strict_stress_current_full_periods.csv")
    tuned = pd.read_csv(TABLES / "strict_stress_tuned_candidate_full_periods.csv")
    plt.figure(figsize=(10, 5.5))
    plt.plot(pd.to_datetime(current["signal_date"]), current["nav"], label="Baseline", color="#E76F51")
    plt.plot(
        pd.to_datetime(tuned["signal_date"]),
        tuned["nav"],
        label="Tuned low-volatility blend",
        color="#2A9D8F",
    )
    plt.axhline(1.0, color="#333333", linewidth=0.8)
    plt.ylabel("NAV")
    plt.title("Strict Cost-and-Slippage Backtest")
    plt.legend()
    save_figure("strict_backtest_equity_curves.png")

    rolling_rows = []
    window_size = 20
    for start in range(0, len(tuned) - window_size + 1):
        window = tuned.iloc[start : start + window_size].copy()
        returns = pd.to_numeric(window["account_return"], errors="coerce").fillna(0.0)
        nav = (1.0 + returns).cumprod()
        rolling_rows.append(
            {
                "window_start": window["signal_date"].iloc[0],
                "window_end": window["signal_date"].iloc[-1],
                "n_periods": window_size,
                "compound_return": float(nav.iloc[-1] - 1.0),
                "avg_period_return": float(returns.mean()),
                "period_vol": float(returns.std(ddof=1)),
                "win_rate": float((returns > 0).mean()),
                "max_drawdown": float((nav / nav.cummax() - 1.0).min()),
            }
        )
    rolling = pd.DataFrame(rolling_rows)
    rolling.to_csv(TABLES / "strict_tuned_rolling_20periods.csv", index=False)
    plt.figure(figsize=(10, 4.8))
    plt.plot(pd.to_datetime(rolling["window_end"]), rolling["compound_return"], color="#264653")
    plt.axhline(0.0, color="#333333", linewidth=0.8)
    plt.ylabel("Rolling compounded return")
    plt.title("Selected 60/40 Blend: Twenty-Period Rolling Returns")
    save_figure("rolling_window_returns.png")


def plot_execution_sensitivity() -> None:
    comparison = pd.read_csv(TABLES / "scheduled_exit_minute_comparison.csv")
    comparison = comparison[comparison["exit_variant"] != "daily_close_reference"].copy()
    comparison["exit_label"] = comparison["exit_variant"].astype(str).str.replace(".0", "", regex=False)
    plt.figure(figsize=(8, 4.8))
    plt.bar(comparison["exit_label"], comparison["total_return"], color="#457B9D")
    plt.ylabel("Total return")
    plt.xlabel("Scheduled exit time")
    plt.title("Minute-Level Exit-Time Sensitivity")
    save_figure("exit_time_sensitivity.png")

    periods = pd.read_csv(TABLES / "scheduled_exit_minute_periods.csv")
    selected = periods[periods["exit_variant"].astype(str).isin(["1453", "1453.0"])].copy()
    plt.figure(figsize=(10, 5.2))
    plt.plot(pd.to_datetime(selected["signal_date"]), selected["nav"], color="#2A9D8F")
    plt.axhline(1.0, color="#333333", linewidth=0.8)
    plt.ylabel("NAV")
    plt.title("14:53 Minute-Execution Equity Curve")
    save_figure("scheduled_1453_equity_curve.png")


def plot_model_comparison() -> None:
    files = {
        "Ridge": "robust_model_predictions_h3_a1p0_backtest_summary.csv",
        "Random forest": "random_forest_predictions_h3_backtest_summary.csv",
        "Neural network": "neural_network_predictions_h3_backtest_summary.csv",
    }
    rows = []
    for label, file_name in files.items():
        frame = pd.read_csv(TABLES / file_name)
        row = frame[frame["split"] == "holdout"].iloc[0]
        rows.append(
            {
                "model": label,
                "total_return": row["total_return"],
                "max_drawdown": row["max_drawdown"],
            }
        )
    comparison = pd.DataFrame(rows)
    comparison.to_csv(TABLES / "public_model_holdout_comparison.csv", index=False)
    plt.figure(figsize=(8, 4.8))
    plt.bar(comparison["model"], comparison["total_return"], color=["#457B9D", "#E76F51", "#6C757D"])
    plt.axhline(0.0, color="#333333", linewidth=0.8)
    plt.ylabel("Holdout total return")
    plt.title("Model Holdout Comparison")
    save_figure("model_holdout_comparison.png")


def plot_etf_overlay() -> None:
    summary = pd.read_csv(TABLES / "etf_regime_continuous_oos.csv")
    order = ["none", "fixed_etf", "adaptive_etf"]
    summary["model"] = pd.Categorical(summary["model"], order, ordered=True)
    summary = summary.sort_values("model")
    plt.figure(figsize=(8, 4.8))
    plt.bar(summary["model"].astype(str), summary["total_return"], color=["#6C757D", "#457B9D", "#2A9D8F"])
    plt.ylabel("Continuous OOS total return")
    plt.title("ETF Regime Overlay Comparison")
    save_figure("etf_overlay_oos_comparison.png")

    periods = pd.read_csv(TABLES / "etf_regime_continuous_oos_periods.csv")
    plt.figure(figsize=(10, 5.2))
    plt.plot(pd.to_datetime(periods["signal_date"]), periods["nav"], color="#264653")
    plt.axhline(1.0, color="#333333", linewidth=0.8)
    plt.ylabel("NAV")
    plt.title("Adaptive ETF Overlay: Continuous Out-of-Sample NAV")
    save_figure("etf_overlay_continuous_oos_equity.png")


def plot_benchmark_comparison() -> None:
    comparison = pd.read_csv(TABLES / "matched_period_benchmark_comparison.csv")
    colors = np.where(comparison["series_type"] == "strategy", "#2A9D8F", "#6C757D")
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    axes[0].bar(comparison["series"], comparison["total_return"], color=colors)
    axes[0].axhline(0.0, color="#333333", linewidth=0.8)
    axes[0].set_ylabel("Total return")
    axes[0].set_title("Matched-Period Total Return")
    axes[1].bar(comparison["series"], comparison["max_drawdown"], color=colors)
    axes[1].axhline(0.0, color="#333333", linewidth=0.8)
    axes[1].set_ylabel("Maximum drawdown")
    axes[1].set_title("Matched-Period Drawdown")
    for axis in axes:
        axis.tick_params(axis="x", rotation=25)
    figure.suptitle("Adaptive Strategy versus Broad and Growth Benchmarks")
    save_figure("matched_period_benchmark_comparison.png")


def observed_range(path: Path, variant: str | None = None) -> tuple[str, str, int]:
    frame = pd.read_csv(path)
    if variant is not None:
        normalized = frame["exit_variant"].astype(str).str.replace(".0", "", regex=False)
        frame = frame[normalized == variant]
    dates = pd.to_datetime(frame["signal_date"])
    return dates.min().date().isoformat(), dates.max().date().isoformat(), int(len(frame))


def write_headline_metrics() -> None:
    strict = pd.read_csv(TABLES / "strict_stress_current_vs_tuned.csv")
    exit_results = pd.read_csv(TABLES / "scheduled_exit_minute_comparison.csv")
    etf = pd.read_csv(TABLES / "etf_regime_continuous_oos.csv")
    rows = []
    for _, row in strict.iterrows():
        rows.append(
            {
                "experiment": f"strict_{row['case']}_{row['split']}",
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "periods": row["n_periods"],
                "total_return": row["total_return"],
                "max_drawdown": row["max_drawdown"],
                "win_rate": row["win_rate"],
            }
        )
    selected_exit = exit_results[exit_results["exit_variant"].astype(str).isin(["1453", "1453.0"])].iloc[0]
    exit_start, exit_end, exit_periods = observed_range(TABLES / "scheduled_exit_minute_periods.csv", "1453")
    rows.append(
        {
            "experiment": "minute_execution_1453",
            "start_date": exit_start,
            "end_date": exit_end,
            "periods": exit_periods,
            "total_return": selected_exit["total_return"],
            "max_drawdown": selected_exit["max_drawdown"],
            "win_rate": selected_exit["trade_win_rate"],
        }
    )
    etf_start, etf_end, etf_periods = observed_range(TABLES / "etf_regime_continuous_oos_periods.csv")
    for _, row in etf.iterrows():
        rows.append(
            {
                "experiment": f"continuous_oos_{row['model']}",
                "start_date": etf_start,
                "end_date": etf_end,
                "periods": etf_periods,
                "total_return": row["total_return"],
                "max_drawdown": row["max_drawdown"],
                "win_rate": row["win_rate"],
            }
        )
    pd.DataFrame(rows).to_csv(TABLES / "public_headline_metrics.csv", index=False)


def main() -> None:
    plt.rcParams.update({"axes.grid": True, "grid.alpha": 0.25, "font.size": 10})
    plot_research_workflow()
    plot_factor_ic()
    plot_factor_robustness()
    plot_quantiles()
    plot_strict_backtests()
    plot_execution_sensitivity()
    plot_model_comparison()
    plot_etf_overlay()
    plot_benchmark_comparison()
    write_headline_metrics()


if __name__ == "__main__":
    main()
