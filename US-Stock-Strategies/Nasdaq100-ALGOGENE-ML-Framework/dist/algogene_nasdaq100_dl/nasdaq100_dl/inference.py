"""Frozen bundle loading and Jupyter-to-Backtest parity checks."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from core import sha256_path


class FrozenBundle:
    def __init__(self, root):
        import joblib
        self.root = Path(root)
        self.manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        schema = json.loads((self.root / self.manifest["feature_schema"]).read_text(encoding="utf-8"))
        self.feature_columns = list(schema["columns"])
        self.model_path = self.root / self.manifest["model_file"]
        actual_hash = sha256_path(self.model_path)
        if actual_hash != self.manifest["model_sha256"]:
            raise RuntimeError("model SHA256 mismatch")
        package_root = Path(__file__).resolve().parent
        checks = {
            "feature_schema_sha256": self.root / self.manifest["feature_schema"],
            "factor_code_sha256": package_root / "core.py",
            "online_code_sha256": package_root / "online.py",
            "fundamentals_code_sha256": package_root / "fundamentals.py",
        }
        for field, path in checks.items():
            if sha256_path(path) != self.manifest[field]:
                raise RuntimeError(field + " mismatch")
        fundamentals_file = self.manifest.get("fundamentals_file")
        if fundamentals_file:
            expected = self.manifest.get("fundamentals_sha256")
            if not expected or sha256_path(self.root / fundamentals_file) != expected:
                raise RuntimeError("fundamentals_sha256 mismatch")
        self.model = joblib.load(self.model_path)
        self.verify_golden_sample()

    def predict(self, feature_rows):
        if hasattr(feature_rows, "loc"):
            matrix = feature_rows.loc[:, self.feature_columns].values
        else:
            matrix = np.asarray(feature_rows, dtype=float)
        values = np.asarray(self.model.predict(matrix), dtype=float).reshape(-1)
        if len(values) != len(matrix) or not np.isfinite(values).all():
            raise RuntimeError("invalid inference output")
        return values

    def verify_golden_sample(self, tolerance=1e-6):
        golden = np.load(self.root / self.manifest["golden_sample"])
        actual = np.asarray(self.model.predict(golden["features"]), dtype=float).reshape(-1)
        expected = golden["prediction"].reshape(-1)
        difference = float(np.max(np.abs(actual - expected))) if len(expected) else 0.0
        if difference > tolerance:
            raise RuntimeError("golden sample mismatch: {:.9g}".format(difference))
        return difference
