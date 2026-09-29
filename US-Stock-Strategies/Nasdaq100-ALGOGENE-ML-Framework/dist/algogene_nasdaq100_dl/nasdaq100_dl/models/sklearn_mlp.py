from pathlib import Path

import numpy as np


class Model:
    """Default neural-network baseline; teammates may replace this plugin."""

    def __init__(self, hidden_layer_sizes=(64, 32), alpha=0.001,
                 max_iter=100, random_state=7):
        from sklearn.neural_network import MLPRegressor
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        self.pipeline = make_pipeline(
            StandardScaler(),
            MLPRegressor(hidden_layer_sizes=tuple(hidden_layer_sizes), alpha=float(alpha),
                         max_iter=int(max_iter), random_state=int(random_state),
                         early_stopping=True, validation_fraction=0.1),
        )

    def fit(self, x_train, y_train, x_validation, y_validation):
        self.pipeline.fit(x_train, y_train)
        metrics = {}
        if len(x_validation):
            prediction = self.pipeline.predict(x_validation)
            metrics["validation_mse"] = float(np.mean((prediction - y_validation) ** 2))
            if np.std(prediction) and np.std(y_validation):
                metrics["validation_ic"] = float(np.corrcoef(prediction, y_validation)[0, 1])
        return metrics

    def predict(self, features):
        return self.pipeline.predict(features)

    def save(self, path: Path):
        import joblib
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path)
