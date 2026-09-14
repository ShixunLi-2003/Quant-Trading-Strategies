from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor

from ashare_momentum.factors import FACTOR_COLUMNS
from ashare_momentum.models import walk_forward_predictions


def model_factory(name: str):
    if name == "ridge":
        return lambda: Ridge(alpha=1.0)
    if name == "random_forest":
        return lambda: RandomForestRegressor(
            n_estimators=80,
            max_features=0.7,
            min_samples_leaf=20,
            max_depth=8,
            random_state=20260913,
            n_jobs=-1,
        )
    return lambda: MLPRegressor(
        hidden_layer_sizes=(32, 16),
        alpha=0.001,
        batch_size=256,
        learning_rate_init=0.001,
        max_iter=150,
        early_stopping=True,
        random_state=20260913,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate embargoed walk-forward model predictions.")
    parser.add_argument("--panel", required=True, help="Factor-panel Parquet file.")
    parser.add_argument("--output", default="results/reproduced/models")
    parser.add_argument("--target", default="fwd_ret_3d")
    parser.add_argument("--train-days", type=int, default=120)
    parser.add_argument("--embargo-days", type=int, default=3)
    args = parser.parse_args()

    panel = pd.read_parquet(args.panel)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for name in ["ridge", "random_forest", "neural_network"]:
        predictions = walk_forward_predictions(
            panel=panel,
            feature_columns=FACTOR_COLUMNS,
            target_column=args.target,
            model_factory=model_factory(name),
            train_days=args.train_days,
            embargo_days=args.embargo_days,
        )
        predictions.to_parquet(output / f"{name}_predictions.parquet", index=False)


if __name__ == "__main__":
    main()

