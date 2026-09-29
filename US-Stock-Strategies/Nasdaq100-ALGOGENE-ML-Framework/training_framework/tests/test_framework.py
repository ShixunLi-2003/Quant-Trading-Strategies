import sys
import tempfile
import types
import unittest
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from contracts import TrainingConfig
from core import (BASE_FEATURES, minute_to_daily, select_dataset_columns,
                  platform_like_backtest, train_walk_forward)
from fundamentals import (attach_point_in_time_fundamentals,
                          audit_no_future_financials,
                          load_point_in_time_fundamentals)
from online import OnlineFeatureEngine


class FrameworkTests(unittest.TestCase):
    def test_platform_nasdaq100_universe_fits_verified_limit(self):
        symbols = [line.strip() for line in (ROOT.parent / "nasdaq100_symbols.txt")
                   .read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(symbols), 100)
        self.assertEqual(len(set(symbols)), 100)
        self.assertIn("GOOGL", symbols)
        self.assertNotIn("GOOG", symbols)
        config = json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
        self.assertEqual(config["platform_subscription_limit"], 100)
        self.assertEqual(config["market_context"], [])
        self.assertEqual(config["sector_context"], [])

    def test_window_limit(self):
        payload = {
            "mode": "debug", "train_days": 43, "max_train_days": 43,
            "validation_days": 5, "test_days": 5, "step_days": 5,
            "embargo_days": 1, "model_entrypoint": "x:Y",
        }
        with self.assertRaises(ValueError):
            TrainingConfig(payload).validate()

    def test_strict_point_in_time_cannot_be_disabled(self):
        payload = {
            "mode": "debug", "train_days": 40, "max_train_days": 42,
            "validation_days": 5, "test_days": 5, "step_days": 5,
            "embargo_days": 1, "model_entrypoint": "x:Y",
            "fundamentals": {"enabled": True, "path": "financials.csv",
                             "strict_point_in_time": False},
        }
        with self.assertRaises(ValueError):
            TrainingConfig(payload).validate()

    def test_model_name_and_dataset_columns_are_the_only_required_selectors(self):
        config = TrainingConfig({
            "mode": "debug", "train_days": 40, "max_train_days": 42,
            "validation_days": 5, "test_days": 5, "step_days": 5,
            "embargo_days": 1, "model_name": "sklearn_mlp",
            "dataset_columns": ["*", "fin_eps_ttm"],
        })
        config.validate()
        self.assertEqual(config.model_entrypoint, "models.sklearn_mlp:Model")
        selected = select_dataset_columns(
            BASE_FEATURES + ["fin_eps_ttm", "fin_revenue_ttm"],
            config.payload["dataset_columns"])
        self.assertTrue(set(BASE_FEATURES).issubset(selected))
        self.assertIn("fin_eps_ttm", selected)
        self.assertNotIn("fin_revenue_ttm", selected)

    def test_fundamentals_are_available_only_after_filing_date(self):
        panel = pd.DataFrame({
            "symbol": ["AAPL", "AAPL", "AAPL"],
            "trade_date": pd.to_datetime(["2025-10-31", "2025-11-02", "2026-02-03"]),
            "close": [100.0, 105.0, 120.0],
        })
        raw = pd.DataFrame({
            "symbol": ["AAPL", "AAPL"],
            "filed_at": ["2025-11-01T00:00:00Z", "2026-02-01T00:00:00Z"],
            "report_date": ["2025-09-30", "2025-12-31"],
            "eps_ttm": [5.0, 6.0],
            "revenue_ttm": [1000.0, 1100.0],
        })
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "financials.csv"
            raw.to_csv(path, index=False)
            financials = load_point_in_time_fundamentals(path, availability_lag_hours=24)
        enriched = attach_point_in_time_fundamentals(panel, financials, {
            "feature_columns": ["eps_ttm", "revenue_ttm"],
            "feature_prefix": "fin_",
        })
        self.assertTrue(np.isnan(enriched.iloc[0]["fin_eps_ttm"]))
        self.assertEqual(enriched.iloc[1]["fin_eps_ttm"], 5.0)
        self.assertEqual(enriched.iloc[2]["fin_eps_ttm"], 6.0)
        effective = pd.to_datetime(enriched["financial_effective_at"], utc=True)
        prediction = (pd.to_datetime(enriched["trade_date"], utc=True) +
                      pd.Timedelta(hours=23, minutes=59))
        valid = effective.notna()
        self.assertTrue((effective[valid] <= prediction[valid]).all())

    def test_future_financial_timestamp_is_a_hard_failure(self):
        frame = pd.DataFrame({
            "symbol": ["AAPL"],
            "trade_date": pd.to_datetime(["2025-01-01"]),
            "financial_effective_at": pd.to_datetime(["2025-01-03"], utc=True),
        })
        with self.assertRaises(RuntimeError):
            audit_no_future_financials(frame)

    def test_report_date_cannot_replace_public_filing_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            pd.DataFrame({"symbol": ["AAPL"], "report_date": ["2025-09-30"],
                          "revenue": [1.0]}).to_csv(path, index=False)
            with self.assertRaises(ValueError):
                load_point_in_time_fundamentals(path)

    def test_batch_and_online_features_match(self):
        start = datetime(2026, 1, 2, 14, 31, tzinfo=timezone.utc)
        rows = []
        engine = OnlineFeatureEngine(["AAPL"], ["SPXUSD"])
        for day in range(25):
            bulk = {}
            for minute in range(390):
                moment = start + timedelta(days=day, minutes=minute)
                price = 100 + day + minute * 0.001
                rows.append({"symbol": "AAPL", "time": moment, "close": price})
                bulk = {"AAPL": {"timestamp": moment, "lastPrice": price},
                        "SPXUSD": {"timestamp": moment, "lastPrice": 4000 + day + minute * 0.002}}
                result = engine.update(bulk)
        result = engine.update({
            "AAPL": {"timestamp": start + timedelta(days=26), "lastPrice": 130},
            "SPXUSD": {"timestamp": start + timedelta(days=26), "lastPrice": 4030},
        })
        batch = minute_to_daily(pd.DataFrame(rows), regular_session_only=False)
        self.assertGreaterEqual(len(batch), 20)
        self.assertTrue(set(BASE_FEATURES).issubset(result.columns))
        self.assertTrue(np.isfinite(result[BASE_FEATURES].values).all())

    def test_platform_like_backtest_uses_whole_shares_and_next_session_prices(self):
        frame = pd.DataFrame({
            "trade_date": pd.to_datetime(["2025-01-02", "2025-01-02"]),
            "entry_date": pd.to_datetime(["2025-01-03", "2025-01-03"]),
            "exit_date": pd.to_datetime(["2025-01-06", "2025-01-06"]),
            "symbol": ["AAPL", "MSFT"],
            "entry_price": [100.0, 200.0],
            "exit_price": [110.0, 180.0],
            "forward_return": [0.10, -0.10],
        })
        config = TrainingConfig({
            "selection_top_n": 1, "initial_capital_usd": 10000,
            "entry_slippage_bps": 0, "exit_slippage_bps": 0,
            "commission_bps": 0, "minimum_commission_usd": 0,
            "limit_buffer": 0.002,
        })
        metrics, equity, trades = platform_like_backtest(
            frame, np.array([1.0, 0.0]), config)
        self.assertAlmostEqual(metrics["ending_equity_usd"], 11000.0)
        self.assertEqual(int(trades.iloc[0]["quantity"]), 100)
        self.assertEqual(int(equity.iloc[0]["positions"]), 1)

    def test_walk_forward_accepts_replaceable_model(self):
        class MeanModel:
            def fit(self, x_train, y_train, x_validation, y_validation):
                self.mean = float(np.mean(y_train))
                return {"validation_rows": int(len(y_validation))}

            def predict(self, features):
                return np.full(len(features), self.mean)

            def save(self, path):
                Path(path).write_text(str(self.mean), encoding="utf-8")

        module = types.ModuleType("test_model_plugin")
        module.Model = MeanModel
        sys.modules[module.__name__] = module
        dates = pd.date_range("2025-01-01", periods=60, freq="B")
        records = []
        for date_index, trade_date in enumerate(dates):
            for symbol_index in range(8):
                row = {"trade_date": trade_date, "symbol": "S{}".format(symbol_index),
                       "forward_return": 0.001 * symbol_index,
                       "target_residual_return": 0.001 * (symbol_index - 3.5)}
                row.update({name: 0.01 * date_index + symbol_index for name in BASE_FEATURES})
                records.append(row)
        config = TrainingConfig({
            "mode": "debug", "train_days": 30, "max_train_days": 42,
            "validation_days": 5, "test_days": 5, "step_days": 5,
            "embargo_days": 1, "minimum_train_rows": 100,
            "model_entrypoint": "test_model_plugin:Model", "model_params": {},
        })
        config.validate()
        with tempfile.TemporaryDirectory() as directory:
            predictions, windows, model_path = train_walk_forward(
                pd.DataFrame(records), BASE_FEATURES, config, directory)
            self.assertFalse(predictions.empty)
            self.assertTrue(windows)
            self.assertTrue(model_path.exists())


if __name__ == "__main__":
    unittest.main()
