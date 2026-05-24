"""
Single-Factor Analysis Runner

Runs IC and quantile analysis for a single configured factor.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hk_quant.analysis.factor_analysis import compute_factor_analysis
from hk_quant.config import ensure_directory, load_project_and_job_config, write_json
from hk_quant.data.loaders import load_market_data, resolve_universe_symbols
from hk_quant.factors.registry import compute_factor
from hk_quant.visualization.plots import plot_factor_ic, plot_quantile_returns


def resolve_output_dir(project_config: dict, subdir: str) -> Path:
    output_root = (Path(project_config["_meta"]["base_dir"]) / project_config["output_root"]).resolve()
    return output_root / subdir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run factor analysis.")
    parser.add_argument("--config", default="configs/w42_factor_analysis.json", help="Path to analysis config")
    args = parser.parse_args()

    project_config, analysis_config = load_project_and_job_config(args.config)
    date_range = analysis_config.get("date_range", {})
    symbols = resolve_universe_symbols(analysis_config["universe"], project_config)
    fields = analysis_config.get("fields", ["close", "amount"])
    market_data = load_market_data(
        symbols=symbols,
        fields=fields,
        project_config=project_config,
        start=date_range.get("start"),
        end=date_range.get("end"),
    )
    factor = compute_factor(
        analysis_config["factor"]["name"],
        market_data=market_data,
        params=analysis_config["factor"].get("params"),
    )
    result = compute_factor_analysis(
        factor=factor,
        close=market_data["close"],
        forward_periods=analysis_config["analysis"].get("forward_periods", [1, 5, 20]),
        quantiles=analysis_config["analysis"].get("quantiles", 5),
    )

    output_dir = ensure_directory(resolve_output_dir(project_config, analysis_config["output"]["subdir"]))
    factor.to_csv(output_dir / "factor.csv")
    result["ic_frame"].to_csv(output_dir / "ic_series.csv")
    result["ic_summary"].to_csv(output_dir / "ic_summary.csv")
    write_json(result["factor_summary"], output_dir / "factor_summary.json")
    for period, quantile_frame in result["quantile_frames"].items():
        quantile_frame.to_csv(output_dir / f"quantile_returns_{period}d.csv")
        result["quantile_summary"][period].to_csv(output_dir / f"quantile_summary_{period}d.csv", header=["mean_return"])

    if analysis_config["output"].get("plot", True):
        plot_factor_ic(result["ic_frame"], output_dir / "ic_plot.png")
        for period, quantile_frame in result["quantile_frames"].items():
            plot_quantile_returns(
                quantile_frame,
                output_dir / f"quantile_plot_{period}d.png",
                title=f"Quantile Forward Returns {period}D",
            )

    print(f"Factor analysis exported to {output_dir}")


if __name__ == "__main__":
    main()
